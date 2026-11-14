from django.contrib import admin

from .models import Autor, Categoria, Emprestimo, Leitor, Livro, Notificacao


@admin.register(Autor)
class AutorAdmin(admin.ModelAdmin):
    list_display = ("nome",)
    search_fields = ("nome",)


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nome",)
    search_fields = ("nome",)


@admin.register(Livro)
class LivroAdmin(admin.ModelAdmin):
    list_display = ("titulo", "autor", "ano", "isbn", "total_exemplares")
    list_filter = ("categorias", "autor")
    search_fields = ("titulo", "isbn")
    filter_horizontal = ("categorias",)


@admin.register(Leitor)
class LeitorAdmin(admin.ModelAdmin):
    list_display = ("nome", "email", "matricula")
    search_fields = ("nome", "email", "matricula")


@admin.register(Emprestimo)
class EmprestimoAdmin(admin.ModelAdmin):
    list_display = ("livro", "leitor", "data_emprestimo", "data_prevista", "data_devolucao", "status")
    list_filter = ("status",)
    search_fields = ("livro__titulo", "leitor__nome")
    date_hierarchy = "data_emprestimo"


@admin.register(Notificacao)
class NotificacaoAdmin(admin.ModelAdmin):
    list_display = ("leitor", "emprestimo", "tipo", "criada_em")
    list_filter = ("tipo",)
    readonly_fields = ("criada_em",)


# ─── Usuários: admins gerenciam tudo, exceto contas de superadmin ────────────

from django.contrib.auth.admin import UserAdmin as _BaseUserAdmin
from django.contrib.auth.models import User

admin.site.unregister(User)


@admin.register(User)
class UserAdmin(_BaseUserAdmin):
    """Admins (não-superusuários) não veem/alteram superadmins nem se promovem."""

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            qs = qs.filter(is_superuser=False)
        return qs

    def get_readonly_fields(self, request, obj=None):
        campos = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser:
            campos += ["is_superuser", "groups", "user_permissions"]
        return campos
