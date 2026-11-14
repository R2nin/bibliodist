"""Busca de metadados de livros pelo ISBN (Google Books + Open Library).

Retorna um dict com as chaves:
    titulo, autores, descricao, ano, data_publicacao, editora,
    capa_url, nota, nota_qtd, fonte
As fontes são combinadas: o Google Books é consultado primeiro e o
Open Library completa o que faltar (capa, nota, data...).
"""
import logging
import re

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

TIMEOUT = 6
CAMPOS = ("titulo", "autores", "descricao", "ano", "data_publicacao",
          "editora", "capa_url", "nota", "nota_qtd")


def normalizar_isbn(valor):
    """Remove tudo que não for dígito ou X (ISBN-10 pode terminar em X)."""
    return re.sub(r"[^0-9Xx]", "", valor or "").upper()


def isbn10_para_13(isbn):
    if len(isbn) != 10:
        return isbn
    base = "978" + isbn[:9]
    soma = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(base))
    return base + str((10 - soma % 10) % 10)


def _ano(data):
    m = re.search(r"\d{4}", str(data or ""))
    return m.group(0) if m else ""


_MESES = {m: i for i, m in enumerate(
    ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"), 1)}


def _data_br(data):
    """'2009-08-14' → '14/08/2009'; '2009-08' → '08/2009'; 'Sep 26, 2008' → '26/09/2008'."""
    data = str(data or "").strip()
    m = re.fullmatch(r"(\d{4})-(\d{2})(?:-(\d{2}))?", data)
    if m:
        a, mes, d = m.groups()
        return f"{d}/{mes}/{a}" if d else f"{mes}/{a}"
    m = re.fullmatch(r"([A-Za-z]{3})[a-z]*\.? (\d{1,2}), (\d{4})", data)
    if m and m.group(1).lower() in _MESES:
        return f"{int(m.group(2)):02d}/{_MESES[m.group(1).lower()]:02d}/{m.group(3)}"
    m = re.fullmatch(r"([A-Za-z]{3})[a-z]*\.? (\d{4})", data)
    if m and m.group(1).lower() in _MESES:
        return f"{_MESES[m.group(1).lower()]:02d}/{m.group(2)}"
    return data


def _https(url):
    return url.replace("http://", "https://", 1) if url else ""


# ─── Google Books ────────────────────────────────────────────────────────────

def buscar_google_books(isbn, avisos=None):
    avisos = avisos if avisos is not None else []
    params = {"q": f"isbn:{isbn}"}
    chave = getattr(settings, "GOOGLE_BOOKS_API_KEY", "")
    if chave:
        params["key"] = chave
    try:
        r = requests.get("https://www.googleapis.com/books/v1/volumes",
                         params=params, timeout=TIMEOUT)
        if r.status_code == 429:
            logger.warning("Google Books: cota esgotada (configure GOOGLE_BOOKS_API_KEY).")
            avisos.append("Google Books: cota diária esgotada"
                          + ("" if chave else " (sem chave de API configurada)"))
            return None
        if r.status_code in (400, 403) and chave:
            try:
                msg = r.json().get("error", {}).get("message", "")
            except ValueError:
                msg = ""
            logger.warning("Google Books recusou a chave: %s", msg)
            avisos.append("Google Books recusou a chave de API (" + (msg or str(r.status_code))[:80] + ")")
            return None
        r.raise_for_status()
        items = r.json().get("items") or []
        if not items:
            return None
        info = items[0].get("volumeInfo", {})
        imagens = info.get("imageLinks", {})
        capa = imagens.get("thumbnail") or imagens.get("smallThumbnail") or ""
        # remove o efeito de "página dobrada" que o Google adiciona à capa
        capa = _https(capa).replace("&edge=curl", "")
        return {
            "titulo": " — ".join(p for p in (info.get("title"), info.get("subtitle")) if p),
            "autores": ", ".join(info.get("authors", [])),
            "descricao": info.get("description", ""),
            "ano": _ano(info.get("publishedDate")),
            "data_publicacao": _data_br(info.get("publishedDate")),
            "editora": info.get("publisher", ""),
            "capa_url": capa,
            "nota": info.get("averageRating"),
            "nota_qtd": info.get("ratingsCount"),
        }
    except Exception:
        logger.exception("Erro ao consultar o Google Books (ISBN %s)", isbn)
        return None


# ─── Open Library ────────────────────────────────────────────────────────────

def _nota_open_library(isbn):
    """Média das avaliações da obra no Open Library (ou None, None)."""
    try:
        r = requests.get(f"https://openlibrary.org/isbn/{isbn}.json", timeout=TIMEOUT)
        if r.status_code != 200:
            return None, None
        obras = r.json().get("works") or []
        if not obras:
            return None, None
        r = requests.get(f"https://openlibrary.org{obras[0]['key']}/ratings.json", timeout=TIMEOUT)
        resumo = r.json().get("summary", {}) if r.status_code == 200 else {}
        if not resumo.get("count"):
            return None, None
        return round(float(resumo["average"]), 2), int(resumo["count"])
    except Exception:
        return None, None


def buscar_open_library(isbn):
    try:
        r = requests.get(
            "https://openlibrary.org/api/books",
            params={"bibkeys": f"ISBN:{isbn}", "format": "json", "jscmd": "data"},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        book = r.json().get(f"ISBN:{isbn}")
        if not book:
            return None
        descricao = book.get("description", "")
        if isinstance(descricao, dict):
            descricao = descricao.get("value", "")
        capa = book.get("cover", {})
        nota, nota_qtd = _nota_open_library(isbn)
        return {
            "titulo": book.get("title", ""),
            "autores": ", ".join(a.get("name", "") for a in book.get("authors", [])),
            "descricao": descricao,
            "ano": _ano(book.get("publish_date")),
            "data_publicacao": _data_br(book.get("publish_date")),
            "editora": ", ".join(p.get("name", "") for p in book.get("publishers", [])),
            "capa_url": _https(capa.get("large") or capa.get("medium") or ""),
            "nota": nota,
            "nota_qtd": nota_qtd,
        }
    except Exception:
        logger.exception("Erro ao consultar o Open Library (ISBN %s)", isbn)
        return None


def capa_open_library(isbn):
    """URL da capa pelo ISBN no Open Library, se existir."""
    url = f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg"
    try:
        r = requests.head(url + "?default=false", timeout=TIMEOUT, allow_redirects=True)
        return url if r.status_code == 200 else ""
    except Exception:
        return ""


# ─── Combinação ──────────────────────────────────────────────────────────────

def buscar(isbn, avisos=None):
    """Consulta as fontes e combina o resultado. Retorna dict ou None.

    Problemas nas fontes (cota esgotada, chave recusada) vão para `avisos`."""
    isbn = normalizar_isbn(isbn)
    if len(isbn) not in (10, 13):
        return None

    avisos = avisos if avisos is not None else []
    dados, fontes = {}, []
    for nome, func in (("Google Books", buscar_google_books), ("Open Library", buscar_open_library)):
        kwargs = {"avisos": avisos} if func is buscar_google_books else {}
        res = func(isbn, **kwargs)
        if not res and len(isbn) == 10:
            res = func(isbn10_para_13(isbn), **kwargs)
        if not res:
            continue
        novos = False
        for campo in CAMPOS:
            if res.get(campo) not in (None, "") and dados.get(campo) in (None, ""):
                dados[campo] = res[campo]
                novos = True
        if novos:
            fontes.append(nome)
        if all(dados.get(c) not in (None, "") for c in CAMPOS):
            break

    if not dados.get("titulo"):
        return None
    if not dados.get("capa_url"):
        dados["capa_url"] = capa_open_library(isbn)
    for campo in CAMPOS:
        dados.setdefault(campo, None if campo in ("nota", "nota_qtd") else "")
    dados["fonte"] = " + ".join(fontes)
    dados["avisos"] = list(dict.fromkeys(avisos))
    return dados
