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
