from django.contrib import admin
from django.urls import path

from biblioteca import views

urlpatterns = [
    path("", views.home, name="home"),
    path("admin/", admin.site.urls),

    # Autores
    path("autores/", views.autor_list, name="autor_list"),
    path("autores/novo/", views.autor_create, name="autor_create"),
    path("autores/<int:pk>/editar/", views.autor_edit, name="autor_edit"),
    path("autores/<int:pk>/excluir/", views.autor_delete, name="autor_delete"),

    # Categorias
    path("categorias/", views.categoria_list, name="categoria_list"),
    path("categorias/nova/", views.categoria_create, name="categoria_create"),
    path("categorias/<int:pk>/editar/", views.categoria_edit, name="categoria_edit"),
    path("categorias/<int:pk>/excluir/", views.categoria_delete, name="categoria_delete"),

    # Livros
    path("livros/", views.livro_list, name="livro_list"),
    path("livros/novo/", views.livro_create, name="livro_create"),
    path("livros/<int:pk>/editar/", views.livro_edit, name="livro_edit"),
    path("livros/<int:pk>/excluir/", views.livro_delete, name="livro_delete"),

    # Leitores
    path("leitores/", views.leitor_list, name="leitor_list"),
    path("leitores/novo/", views.leitor_create, name="leitor_create"),
    path("leitores/<int:pk>/editar/", views.leitor_edit, name="leitor_edit"),
    path("leitores/<int:pk>/excluir/", views.leitor_delete, name="leitor_delete"),

    # Empréstimos
    path("emprestimos/", views.emprestimo_list, name="emprestimo_list"),
    path("emprestimos/novo/", views.emprestimo_create, name="emprestimo_create"),
    path("emprestimos/<int:pk>/devolver/", views.emprestimo_devolver, name="emprestimo_devolver"),
]
