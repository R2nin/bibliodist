from django import template

register = template.Library()


@register.filter
def formatar_chapas(valor):
    """
    Recebe o campo chapa (ex: "1/0234, 2/0056, 789") e retorna
    cada chapa com zeros à esquerda removidos e sem o prefixo "N/".
    Ex: "1/0234, 2/0056" → "234, 56"
    """
    if not valor:
        return "—"
    chapas = []
    for parte in str(valor).split(","):
        parte = parte.strip()
        if "/" in parte:
            parte = parte.split("/", 1)[1]
        parte = parte.lstrip("0") or "0"
        chapas.append(parte)
    return ", ".join(chapas)
