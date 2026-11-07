"""
Parser de expressões de busca booleanas, no estilo das bases científicas:

    blockchain AND (educação OR "contrato inteligente") NOT bitcoin

Gramática (precedência: NOT > AND > OR; termos lado a lado = AND implícito):

    expr   := termo_or
    or     := and ( OR and )*
    and    := not ( [AND] not )*
    not    := NOT not | átomo
    átomo  := PALAVRA | "frase entre aspas" | ( expr )

Operadores aceitos em inglês ou português: AND/E, OR/OU, NOT/NAO/NÃO
(precisam estar em MAIÚSCULAS para não colidir com palavras comuns como "e").
A comparação ignora acentos e maiúsculas, e termos terminados em * fazem
busca por prefixo (ex.: educa* casa com educação, educacional...).
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

OPS = {"AND": "AND", "E": "AND", "OR": "OR", "OU": "OR", "NOT": "NOT", "NAO": "NOT", "NÃO": "NOT"}

_TOKEN = re.compile(r'\s*(?:(\()|(\))|"([^"]*)"|([^\s()"]+))')


class ErroConsulta(ValueError):
    pass


def normalizar_texto(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return " ".join(sem_acento.lower().split())


# ─── AST ─────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Termo:
    texto: str

    def avaliar(self, alvo: str) -> bool:
        t = normalizar_texto(self.texto)
        if t.endswith("*"):
            return re.search(r"\b" + re.escape(t[:-1]), alvo) is not None
        return re.search(r"\b" + re.escape(t) + r"\b", alvo) is not None

    def termos_positivos(self) -> list[str]:
        return [self.texto.rstrip("*")]

    def __str__(self):
        return f'"{self.texto}"' if " " in self.texto else self.texto


@dataclass(frozen=True)
class Nao:
    filho: object

    def avaliar(self, alvo):
        return not self.filho.avaliar(alvo)

    def termos_positivos(self):
        return []           # termos negados não servem para identificar registros

    def __str__(self):
        return f"NOT {self.filho}"


@dataclass(frozen=True)
class E:
    filhos: tuple

    def avaliar(self, alvo):
        return all(f.avaliar(alvo) for f in self.filhos)

    def termos_positivos(self):
        return [t for f in self.filhos for t in f.termos_positivos()]

    def __str__(self):
        return "(" + " AND ".join(map(str, self.filhos)) + ")"


@dataclass(frozen=True)
class Ou:
    filhos: tuple

    def avaliar(self, alvo):
        return any(f.avaliar(alvo) for f in self.filhos)

    def termos_positivos(self):
        return [t for f in self.filhos for t in f.termos_positivos()]

    def __str__(self):
        return "(" + " OR ".join(map(str, self.filhos)) + ")"


# ─── Parser (descida recursiva) ──────────────────────────────────────────────

def _tokenizar(texto: str) -> list[tuple[str, str]]:
    tokens, pos = [], 0
    texto = texto.strip()
    while pos < len(texto):
        m = _TOKEN.match(texto, pos)
        if not m or m.end() == pos:
            raise ErroConsulta(f"Caractere inesperado na posição {pos}.")
        pos = m.end()
        abre, fecha, frase, palavra = m.groups()
        if abre:
            tokens.append(("(", abre))
        elif fecha:
            tokens.append((")", fecha))
        elif frase is not None:
            if frase.strip():
                tokens.append(("TERMO", frase.strip()))
        elif palavra in OPS:
            tokens.append((OPS[palavra], palavra))
        else:
            tokens.append(("TERMO", palavra))
    return tokens


class _Parser:
    def __init__(self, tokens):
        self.t, self.i = tokens, 0

    def _olhar(self):
        return self.t[self.i][0] if self.i < len(self.t) else None

    def _consumir(self, tipo=None):
        if self._olhar() is None or (tipo and self._olhar() != tipo):
            raise ErroConsulta(f"Esperava {tipo or 'um termo'} e a expressão terminou ou veio outra coisa.")
        tok = self.t[self.i]
        self.i += 1
        return tok

    def expr(self):
        filhos = [self.e()]
        while self._olhar() == "OR":
            self._consumir("OR")
            filhos.append(self.e())
        return filhos[0] if len(filhos) == 1 else Ou(tuple(filhos))

    def e(self):
        filhos = [self.nao()]
        while self._olhar() in ("AND", "NOT", "TERMO", "("):
            if self._olhar() == "AND":
                self._consumir("AND")
            filhos.append(self.nao())
        return filhos[0] if len(filhos) == 1 else E(tuple(filhos))

    def nao(self):
        if self._olhar() == "NOT":
            self._consumir("NOT")
            return Nao(self.nao())
        return self.atomo()

    def atomo(self):
        if self._olhar() == "(":
            self._consumir("(")
            no = self.expr()
            self._consumir(")")
            return no
        return Termo(self._consumir("TERMO")[1])


def parse(texto: str):
    tokens = _tokenizar(texto or "")
    if not tokens:
        raise ErroConsulta("Informe ao menos um termo de busca.")
    p = _Parser(tokens)
    arvore = p.expr()
    if p.i != len(tokens):
        raise ErroConsulta(f"Sobrou '{tokens[p.i][1]}' sem operador — confira parênteses e aspas.")
    if not arvore.termos_positivos():
        raise ErroConsulta("A expressão precisa de ao menos um termo que não seja negado (NOT).")
    return arvore
