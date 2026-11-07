"""Aba "Revisão PRISMA" — revisão sistemática sobre o Acervo Digital da FEMA."""
import csv
from datetime import date

from django.http import HttpResponse
from django.shortcuts import render

from .prisma import acervo_fema
from .prisma.consulta import ErroConsulta
from .prisma.pipeline import Criterios, executar

EXEMPLOS = [
    "blockchain",
    'blockchain OR "contrato inteligente" OR "smart contract"',
    "(inteligencia OR machine OR neural) AND saude",
    "seguranca AND (rede OR redes) NOT jogo",
    "educa* AND (aplicativo OR mobile)",
]


def _int_ou_none(valor):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def _criterios(get) -> Criterios:
    return Criterios(
        expressao=get.get("q", "").strip(),
        tipo=get.get("tipo", "TCC") or "TCC",
        curso=get.get("curso", "BCC") or "BCC",
        ano_inicio=_int_ou_none(get.get("ano_inicio")),
        ano_fim=_int_ou_none(get.get("ano_fim")),
        exigir_pdf=get.get("exigir_pdf") == "on",
        exigir_resumo=get.get("exigir_resumo") == "on",
        modo_amplo=get.get("modo_amplo") == "on",
    )


def prisma_busca(request):
    g = request.GET
    primeira_visita = "q" not in g
    crit = _criterios(g)
    if primeira_visita:
        crit.exigir_pdf = True          # padrão do formulário

    ctx = {
        "crit": crit,
        "cursos": acervo_fema.listar_cursos(),
        "tipos": acervo_fema.listar_tipos(),
        "exemplos": EXEMPLOS,
        "ano_atual": date.today().year,
        "pagina_publica": acervo_fema.PAGINA_PUBLICA,
        "querystring": g.urlencode(),
    }

    if not primeira_visita:
        try:
            res = executar(crit)
        except ErroConsulta as exc:
            ctx["erro"] = f"Expressão inválida: {exc}"
        except acervo_fema.AcervoIndisponivel:
            ctx["erro"] = ("Não foi possível acessar o Acervo Digital da FEMA agora. "
                           "Verifique a conexão com a internet e tente novamente.")
        else:
            ctx["res"] = res
            ctx["grafico_anos"] = res.por_ano()
            ctx["grafico_kw"] = res.top_palavras_chave(12)

    return render(request, "biblioteca/prisma.html", ctx)


def prisma_exportar_csv(request):
    crit = _criterios(request.GET)
    try:
        res = executar(crit)
    except (ErroConsulta, acervo_fema.AcervoIndisponivel) as exc:
        return HttpResponse(f"Erro: {exc}", status=400, content_type="text/plain; charset=utf-8")

    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="prisma_fema_{date.today():%Y%m%d}.csv"'
    resp.write("﻿")   # BOM para o Excel reconhecer UTF-8
    w = csv.writer(resp, delimiter=";")
    campos = ["situacao", "etapa", "motivo", "id", "titulo", "ano", "curso", "tipo",
              "autores", "orientadores", "palavras_chave", "resumo", "url_pdf"]
    w.writerow(campos)
    for t in res.incluidos:
        d = t.as_dict()
        w.writerow(["incluido", "Inclusão", ""] + [d[c] for c in campos[3:]])
    for ex in res.excluidos:
        d = ex.trabalho.as_dict()
        w.writerow(["excluido", ex.etapa, ex.motivo] + [d[c] for c in campos[3:]])
    return resp
