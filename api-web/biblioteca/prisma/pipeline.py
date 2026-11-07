"""
Fluxo PRISMA 2020 aplicado ao Acervo Digital da FEMA.

    IDENTIFICAÇÃO  -> uma consulta à API por termo positivo da expressão
                      (a API só aceita um termo por vez); remove duplicados.
    TRIAGEM        -> aplica a expressão booleana completa sobre
                      título + palavras-chave + resumo e o filtro de período.
    ELEGIBILIDADE  -> critérios de qualidade: texto completo (PDF) disponível
                      e, opcionalmente, resumo cadastrado.
    INCLUSÃO       -> trabalhos que passaram por todas as etapas.

No "modo amplo" a identificação baixa o acervo inteiro do tipo/curso
(o BCC tem ~600 registros) para que termos presentes só no resumo também
sejam encontrados — a API não pesquisa no resumo.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from . import acervo_fema
from .consulta import normalizar_texto, parse


@dataclass
class Criterios:
    expressao: str
    tipo: str = "TCC"
    curso: str = "BCC"
    ano_inicio: int | None = None
    ano_fim: int | None = None
    exigir_pdf: bool = True
    exigir_resumo: bool = False
    modo_amplo: bool = False


@dataclass
class Exclusao:
    trabalho: acervo_fema.Trabalho
    etapa: str
    motivo: str


@dataclass
class ResultadoPrisma:
    criterios: Criterios
    expressao_interpretada: str
    consultas: dict[str, int]                       # termo -> nº de registros retornados
    identificados: int = 0
    duplicados: int = 0
    triados: int = 0
    excl_triagem_expressao: int = 0
    excl_triagem_periodo: int = 0
    elegiveis_avaliados: int = 0
    excl_sem_pdf: int = 0
    excl_sem_resumo: int = 0
    incluidos: list[acervo_fema.Trabalho] = field(default_factory=list)
    excluidos: list[Exclusao] = field(default_factory=list)

    @property
    def total_incluidos(self):
        return len(self.incluidos)

    def por_ano(self) -> list[tuple[str, int]]:
        c = Counter(t.ano_int for t in self.incluidos if t.ano_int)
        return sorted(((str(a), n) for a, n in c.items()), key=lambda x: x[0])

    def top_palavras_chave(self, n: int = 15) -> list[tuple[str, int]]:
        c = Counter()
        for t in self.incluidos:
            for kw in {k.strip().title() for k in t.palavras_chave if 2 < len(k) < 60}:
                c[kw] += 1
        return c.most_common(n)

    def top_orientadores(self, n: int = 10) -> list[tuple[str, int]]:
        c = Counter(o for t in self.incluidos for o in t.orientadores)
        return c.most_common(n)


def executar(criterios: Criterios, buscar=None) -> ResultadoPrisma:
    buscar = buscar or acervo_fema.buscar
    arvore = parse(criterios.expressao)
    termos = list(dict.fromkeys(t for t in arvore.termos_positivos() if t.strip()))

    # ── 1. Identificação ────────────────────────────────────────────────────
    consultas: dict[str, int] = {}
    brutos: list[acervo_fema.Trabalho] = []
    if criterios.modo_amplo:
        lote = buscar("", tipo=criterios.tipo, curso=criterios.curso)
        consultas["(acervo completo)"] = len(lote)
        brutos.extend(lote)
    else:
        for termo in termos:
            lote = buscar(termo, tipo=criterios.tipo, curso=criterios.curso)
            consultas[termo] = len(lote)
            brutos.extend(lote)

    unicos: dict[int, acervo_fema.Trabalho] = {}
    for t in brutos:
        unicos.setdefault(t.id, t)

    res = ResultadoPrisma(
        criterios=criterios,
        expressao_interpretada=str(arvore),
        consultas=consultas,
        identificados=len(brutos),
        duplicados=len(brutos) - len(unicos),
        triados=len(unicos),
    )

    # ── 2. Triagem ──────────────────────────────────────────────────────────
    triados_ok = []
    for t in unicos.values():
        if not arvore.avaliar(normalizar_texto(t.texto_triagem)):
            res.excl_triagem_expressao += 1
            res.excluidos.append(Exclusao(t, "Triagem", "Não atende à expressão de busca"))
            continue
        ano = t.ano_int
        fora = (
            (criterios.ano_inicio and (ano is None or ano < criterios.ano_inicio))
            or (criterios.ano_fim and (ano is None or ano > criterios.ano_fim))
        )
        if fora:
            res.excl_triagem_periodo += 1
            res.excluidos.append(Exclusao(t, "Triagem", f"Fora do período (ano: {t.ano or 'n/d'})"))
            continue
        triados_ok.append(t)

    # ── 3. Elegibilidade ────────────────────────────────────────────────────
    res.elegiveis_avaliados = len(triados_ok)
    for t in triados_ok:
        if criterios.exigir_pdf and not t.tem_pdf:
            res.excl_sem_pdf += 1
            res.excluidos.append(Exclusao(t, "Elegibilidade", "Texto completo (PDF) indisponível"))
            continue
        if criterios.exigir_resumo and not t.tem_resumo:
            res.excl_sem_resumo += 1
            res.excluidos.append(Exclusao(t, "Elegibilidade", "Sem resumo cadastrado"))
            continue
        res.incluidos.append(t)

    # ── 4. Inclusão ─────────────────────────────────────────────────────────
    res.incluidos.sort(key=lambda t: (-(t.ano_int or 0), t.titulo))
    return res
