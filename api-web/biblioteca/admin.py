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
    list_display = ("titulo", "autor", "categoria", "ano", "isbn", "total_exemplares")
    list_filter = ("categoria", "autor")
    search_fields = ("titulo", "isbn")


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
