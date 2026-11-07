"""
Cliente do Acervo Digital da Biblioteca da FEMA (sistema Extra FEMA / CEPEIN).

A página https://cepein.fema.edu.br/aplicacoes/extra-fema/consulta-acervo-biblioteca
é um app Angular que consome uma API REST pública. Em vez de fazer scraping do
HTML renderizado (que exigiria Selenium), consumimos diretamente essa API —
mesma técnica de "inspecionar a aba Network" usada no prisma-scraper.

Endpoints descobertos:
    GET {API}/consulta-acervo/buscar-lista-cursos
    GET {API}/consulta-acervo/buscar-lista-tipo
    GET {API}/consulta-acervo/buscar-lista-filtrada
        ?page=0&size=100&tipo=TCC&curso=BCC&palavrasChave=&titulo=&autor=
    GET {DOWNLOAD}/download/14/{uuid_arquivo}      -> PDF do trabalho

Comportamento observado da busca:
    * substring de UM termo (não aceita AND/OR) -> a lógica booleana é feita aqui;
    * ignora acentos e maiúsculas;
    * `palavrasChave` procura no campo `busca` (título + palavras-chave + nomes),
      mas NÃO no resumo.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

import requests
from django.core.cache import cache

log = logging.getLogger(__name__)

API_BASE = os.getenv("ACERVO_FEMA_API", "https://cepeinb.fema.edu.br/extra-fema/consulta-acervo")
DOWNLOAD_BASE = os.getenv("ACERVO_FEMA_DOWNLOAD", "https://cepeinb.fema.edu.br/download-extra-fema/download/14")
PAGINA_PUBLICA = "https://cepein.fema.edu.br/aplicacoes/extra-fema/consulta-acervo-biblioteca"

PAGE_SIZE = 100
MAX_PAGINAS = 50            # trava de segurança: no máximo 5.000 registros por consulta
TIMEOUT = 20
CACHE_TTL = 60 * 60         # 1 h — evita martelar o servidor da instituição

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "BiblioDist-PRISMA/1.0 (trabalho academico FEMA)",
}

# Usados se a API de listas estiver fora do ar
CURSOS_FALLBACK = ["TODOS", "BCC", "ADS", "ADM", "ARQ", "CONT", "DIR", "JOR", "MED", "QUIM"]
TIPOS_FALLBACK = ["TCC", "PIBIC", "PIBITI", "PIC", "LIVRO", "MANUAIS", "NORMAS TÉCNICAS", "TODOS"]


class AcervoIndisponivel(Exception):
    """A API da biblioteca não respondeu ou respondeu algo inesperado."""


@dataclass
class Trabalho:
    id: int
    titulo: str
    ano: str
    curso: str
    tipo: str
    autores: list[str] = field(default_factory=list)
    orientadores: list[str] = field(default_factory=list)
    palavras_chave: list[str] = field(default_factory=list)
    resumo: str = ""
    classificacao: str = ""
    uuid_arquivo: str = ""
    busca: str = ""

    @property
    def url_pdf(self) -> str:
        return f"{DOWNLOAD_BASE}/{self.uuid_arquivo}" if self.uuid_arquivo else ""

    @property
    def tem_pdf(self) -> bool:
        return bool(self.uuid_arquivo)

    @property
    def tem_resumo(self) -> bool:
        return len(self.resumo.strip()) >= 50

    @property
    def ano_int(self) -> int | None:
        try:
            ano = int(self.ano)
        except (TypeError, ValueError):
            return None
        return ano if 1900 <= ano <= 2100 else None   # há registros com ano "206"

    @property
    def texto_triagem(self) -> str:
        """Texto usado na triagem: título + palavras-chave + resumo."""
        return " ".join([self.titulo, " ".join(self.palavras_chave), self.resumo])

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "titulo": self.titulo,
            "ano": self.ano,
            "curso": self.curso,
            "tipo": self.tipo,
            "autores": "; ".join(self.autores),
            "orientadores": "; ".join(self.orientadores),
            "palavras_chave": "; ".join(self.palavras_chave),
            "resumo": self.resumo,
            "url_pdf": self.url_pdf,
        }


# ─── Normalização ────────────────────────────────────────────────────────────

def _extrair_palavras_chave(bruto: str) -> list[str]:
    """
    O campo vem no formato  "TÍTULO; KW1, KW2, KW3; ORIENTADOR; ALUNO; ANO".
    As palavras-chave reais ficam no 2º segmento.
    """
    if not bruto:
        return []
    segmentos = [s.strip() for s in bruto.split(";")]
    alvo = segmentos[1] if len(segmentos) >= 3 else bruto
    return [p.strip().title() for p in alvo.split(",") if p.strip()]


def _limpar_nome(texto: str) -> str:
    # "Orientado: FELIPE ARAÚJO DE ALMEIDA ( 2111600150 )" -> "Felipe Araújo De Almeida"
    nome = texto.split(":", 1)[-1]
    nome = nome.split("(", 1)[0]
    return " ".join(nome.split()).title()


def normalizar(reg: dict) -> Trabalho:
    autores, orientadores = [], []
    for p in reg.get("participantes") or []:
        papel = p.split(":", 1)[0].strip().lower()
        (orientadores if papel.startswith("orientador") else autores).append(_limpar_nome(p))

    return Trabalho(
        id=int(reg.get("id") or 0),
        titulo=" ".join((reg.get("titulo") or "").split()),
        ano=str(reg.get("ano") or "").strip(),
        curso=reg.get("curso") or "",
        tipo=reg.get("tipo") or "",
        autores=autores,
        orientadores=orientadores,
        palavras_chave=_extrair_palavras_chave(reg.get("palavras_chave") or ""),
        resumo=" ".join((reg.get("resumo") or "").split()),
        classificacao=reg.get("classificacao") or "",
        uuid_arquivo=reg.get("uuid_arquivo") or "",
        busca=reg.get("busca") or "",
    )


# ─── HTTP ────────────────────────────────────────────────────────────────────

def _get(caminho: str, params: dict | None = None):
    url = f"{API_BASE}/{caminho}"
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except (requests.RequestException, ValueError) as exc:
        log.warning("Falha ao consultar acervo FEMA (%s): %s", caminho, exc)
        raise AcervoIndisponivel(str(exc)) from exc


def buscar(termo: str = "", tipo: str = "TCC", curso: str = "BCC",
           campo: str = "palavrasChave") -> list[Trabalho]:
    """
    Busca paginada na API. `campo` pode ser palavrasChave, titulo ou autor.
    `termo` vazio traz o acervo inteiro do tipo/curso.
    """
    chave = f"acervo-fema:{tipo}:{curso}:{campo}:{termo.lower()}"
    em_cache = cache.get(chave)
    if em_cache is not None:
        return [normalizar(r) for r in em_cache]

    brutos: list[dict] = []
    for pagina in range(MAX_PAGINAS):
        params = {"page": pagina, "size": PAGE_SIZE, "tipo": tipo, "curso": curso,
                  "palavrasChave": "", "titulo": "", "autor": ""}
        params[campo] = termo
        lote = _get("buscar-lista-filtrada", params)
        if not isinstance(lote, list):
            raise AcervoIndisponivel("Resposta inesperada da API (esperava uma lista).")
        brutos.extend(lote)
        if len(lote) < PAGE_SIZE:
            break

    cache.set(chave, brutos, CACHE_TTL)
    return [normalizar(r) for r in brutos]


def _lista(caminho: str, chave_item: str, fallback: list[str]) -> list[str]:
    chave = f"acervo-fema:lista:{caminho}"
    valores = cache.get(chave)
    if valores is None:
        try:
            dados = _get(caminho)
            valores = [d[chave_item] for d in dados if d.get(chave_item)]
            cache.set(chave, valores, CACHE_TTL * 24)
        except (AcervoIndisponivel, KeyError, TypeError):
            return fallback
    return valores or fallback


def listar_cursos() -> list[str]:
    return _lista("buscar-lista-cursos", "curso", CURSOS_FALLBACK)


def listar_tipos() -> list[str]:
    tipos = _lista("buscar-lista-tipo", "tipo", TIPOS_FALLBACK)
    return tipos
