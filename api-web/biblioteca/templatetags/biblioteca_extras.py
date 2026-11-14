from django import template

register = template.Library()


@register.filter
def formatar_chapas(valor):
    """
    Retorna todas as chapas associadas ao livro separadas por vírgula,
    exatamente como estão armazenadas no banco.
    """
    if not valor:
        return "—"
    return str(valor)


@register.simple_tag(takes_context=True)
def url_pagina(context, numero):
    """Querystring atual (busca, filtros, ordenação) com page=numero."""
    params = context["request"].GET.copy()
    params["page"] = numero
    return "?" + params.urlencode()


@register.simple_tag(takes_context=True)
def params_sem_pagina(context):
    """Pares (nome, valor) da querystring atual, exceto page — para campos ocultos."""
    return [(k, v) for k, vs in context["request"].GET.lists() if k != "page" for v in vs]
