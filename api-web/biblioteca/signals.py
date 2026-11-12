from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver


@receiver(user_logged_in)
def log_login(sender, request, user, **kwargs):
    from .models import LogOperacao
    nome = user.get_full_name() or user.username
    LogOperacao.objects.create(
        usuario=user,
        tipo="login",
        descricao=f'Usuário "{nome}" fez login no sistema.',
    )
