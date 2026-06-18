from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import Autor, Categoria, Emprestimo, Leitor, Livro, Notificacao
from . import grpc_client
from . import mq_publisher


# ─── Home ────────────────────────────────────────────────────────────────────

def home(request):
    return render(request, "home.html")


# ─── Autores ─────────────────────────────────────────────────────────────────

def autor_list(request):
    qs = Autor.objects.all()
    paginator = Paginator(qs, 10)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "biblioteca/autor_list.html", {"page_obj": page})


def autor_create(request):
    if request.method == "POST":
        nome = request.POST.get("nome", "").strip()
        if nome:
            Autor.objects.create(nome=nome)
            messages.success(request, "Autor criado com sucesso.")
            return redirect("autor_list")
        messages.error(request, "Nome é obrigatório.")
    return render(request, "biblioteca/autor_form.html", {"titulo": "Novo Autor"})


def autor_edit(request, pk):
    autor = get_object_or_404(Autor, pk=pk)
    if request.method == "POST":
        nome = request.POST.get("nome", "").strip()
        if nome:
            autor.nome = nome
            autor.save()
            messages.success(request, "Autor atualizado.")
            return redirect("autor_list")
        messages.error(request, "Nome é obrigatório.")
    return render(request, "biblioteca/autor_form.html", {"titulo": "Editar Autor", "obj": autor})


def autor_delete(request, pk):
    autor = get_object_or_404(Autor, pk=pk)
    if request.method == "POST":
        try:
            autor.delete()
            messages.success(request, "Autor removido.")
        except Exception:
            messages.error(request, "Não é possível remover: existem livros vinculados.")
        return redirect("autor_list")
    return render(request, "biblioteca/confirm_delete.html", {"obj": autor, "cancelar_url": "autor_list"})


# ─── Categorias ──────────────────────────────────────────────────────────────

def categoria_list(request):
    qs = Categoria.objects.all()
    paginator = Paginator(qs, 10)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "biblioteca/categoria_list.html", {"page_obj": page})


def categoria_create(request):
    if request.method == "POST":
        nome = request.POST.get("nome", "").strip()
        if nome:
            Categoria.objects.create(nome=nome)
            messages.success(request, "Categoria criada com sucesso.")
            return redirect("categoria_list")
        messages.error(request, "Nome é obrigatório.")
    return render(request, "biblioteca/categoria_form.html", {"titulo": "Nova Categoria"})


def categoria_edit(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    if request.method == "POST":
        nome = request.POST.get("nome", "").strip()
        if nome:
            categoria.nome = nome
            categoria.save()
            messages.success(request, "Categoria atualizada.")
            return redirect("categoria_list")
        messages.error(request, "Nome é obrigatório.")
    return render(request, "biblioteca/categoria_form.html", {"titulo": "Editar Categoria", "obj": categoria})


def categoria_delete(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    if request.method == "POST":
        try:
            categoria.delete()
            messages.success(request, "Categoria removida.")
        except Exception:
            messages.error(request, "Não é possível remover: existem livros vinculados.")
        return redirect("categoria_list")
    return render(request, "biblioteca/confirm_delete.html", {"obj": categoria, "cancelar_url": "categoria_list"})


# ─── Livros ──────────────────────────────────────────────────────────────────

def livro_list(request):
    q = request.GET.get("q", "").strip()
    qs = Livro.objects.select_related("autor", "categoria")
    if q:
        qs = qs.filter(titulo__icontains=q)
    paginator = Paginator(qs, 10)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "biblioteca/livro_list.html", {"page_obj": page, "q": q})


def livro_create(request):
    autores = Autor.objects.all()
    categorias = Categoria.objects.all()
    if request.method == "POST":
        erros = []
        titulo = request.POST.get("titulo", "").strip()
        isbn = request.POST.get("isbn", "").strip()
        ano = request.POST.get("ano", "").strip()
        autor_id = request.POST.get("autor")
        categoria_id = request.POST.get("categoria")
        total = request.POST.get("total_exemplares", "1").strip()

        if not titulo:
            erros.append("Título é obrigatório.")
        if not isbn:
            erros.append("ISBN é obrigatório.")
        if not ano or not ano.isdigit():
            erros.append("Ano inválido.")
        if not autor_id:
            erros.append("Autor é obrigatório.")
        if not categoria_id:
            erros.append("Categoria é obrigatória.")

        if not erros:
            if Livro.objects.filter(isbn=isbn).exists():
                erros.append("Já existe um livro com este ISBN.")

        if erros:
            for e in erros:
                messages.error(request, e)
        else:
            Livro.objects.create(
                titulo=titulo,
                isbn=isbn,
                ano=int(ano),
                autor_id=autor_id,
                categoria_id=categoria_id,
                total_exemplares=int(total) if total.isdigit() else 1,
            )
            messages.success(request, "Livro criado com sucesso.")
            return redirect("livro_list")

    return render(request, "biblioteca/livro_form.html", {
        "titulo_pag": "Novo Livro",
        "autores": autores,
        "categorias": categorias,
    })


def livro_edit(request, pk):
    livro = get_object_or_404(Livro, pk=pk)
    autores = Autor.objects.all()
    categorias = Categoria.objects.all()
    if request.method == "POST":
        livro.titulo = request.POST.get("titulo", livro.titulo).strip()
        livro.isbn = request.POST.get("isbn", livro.isbn).strip()
        ano = request.POST.get("ano", "").strip()
        if ano.isdigit():
            livro.ano = int(ano)
        livro.autor_id = request.POST.get("autor", livro.autor_id)
        livro.categoria_id = request.POST.get("categoria", livro.categoria_id)
        total = request.POST.get("total_exemplares", "").strip()
        if total.isdigit():
            livro.total_exemplares = int(total)
        livro.save()
        messages.success(request, "Livro atualizado.")
        return redirect("livro_list")
    return render(request, "biblioteca/livro_form.html", {
        "titulo_pag": "Editar Livro",
        "obj": livro,
        "autores": autores,
        "categorias": categorias,
    })


def livro_delete(request, pk):
    livro = get_object_or_404(Livro, pk=pk)
    if request.method == "POST":
        try:
            livro.delete()
            messages.success(request, "Livro removido.")
        except Exception:
            messages.error(request, "Não é possível remover: existem empréstimos vinculados.")
        return redirect("livro_list")
    return render(request, "biblioteca/confirm_delete.html", {"obj": livro, "cancelar_url": "livro_list"})


# ─── Leitores ────────────────────────────────────────────────────────────────

def leitor_list(request):
    qs = Leitor.objects.all()
    paginator = Paginator(qs, 10)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "biblioteca/leitor_list.html", {"page_obj": page})


def leitor_create(request):
    if request.method == "POST":
        nome = request.POST.get("nome", "").strip()
        email = request.POST.get("email", "").strip()
        matricula = request.POST.get("matricula", "").strip()
        erros = []
        if not nome:
            erros.append("Nome é obrigatório.")
        if not email:
            erros.append("E-mail é obrigatório.")
        if not matricula:
            erros.append("Matrícula é obrigatória.")
        if not erros:
            if Leitor.objects.filter(email=email).exists():
                erros.append("Já existe um leitor com este e-mail.")
            if Leitor.objects.filter(matricula=matricula).exists():
                erros.append("Já existe um leitor com esta matrícula.")
        if erros:
            for e in erros:
                messages.error(request, e)
        else:
            Leitor.objects.create(nome=nome, email=email, matricula=matricula)
            messages.success(request, "Leitor criado com sucesso.")
            return redirect("leitor_list")
    return render(request, "biblioteca/leitor_form.html", {"titulo": "Novo Leitor"})


def leitor_edit(request, pk):
    leitor = get_object_or_404(Leitor, pk=pk)
    if request.method == "POST":
        leitor.nome = request.POST.get("nome", leitor.nome).strip()
        leitor.email = request.POST.get("email", leitor.email).strip()
        leitor.matricula = request.POST.get("matricula", leitor.matricula).strip()
        leitor.save()
        messages.success(request, "Leitor atualizado.")
        return redirect("leitor_list")
    return render(request, "biblioteca/leitor_form.html", {"titulo": "Editar Leitor", "obj": leitor})


def leitor_delete(request, pk):
    leitor = get_object_or_404(Leitor, pk=pk)
    if request.method == "POST":
        try:
            leitor.delete()
            messages.success(request, "Leitor removido.")
        except Exception:
            messages.error(request, "Não é possível remover: existem empréstimos vinculados.")
        return redirect("leitor_list")
    return render(request, "biblioteca/confirm_delete.html", {"obj": leitor, "cancelar_url": "leitor_list"})


# ─── Empréstimos ─────────────────────────────────────────────────────────────

def _atualizar_atrasos():
    """Marca como 'atrasado' todo empréstimo ativo cuja data prevista já passou."""
    hoje = timezone.now().date()
    Emprestimo.objects.filter(status="ativo", data_prevista__lt=hoje).update(status="atrasado")


def emprestimo_list(request):
    _atualizar_atrasos()
    qs = Emprestimo.objects.select_related("livro", "leitor")
    status_filtro = request.GET.get("status", "")
    if status_filtro:
        qs = qs.filter(status=status_filtro)
    paginator = Paginator(qs, 10)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "biblioteca/emprestimo_list.html", {
        "page_obj": page,
        "status_filtro": status_filtro,
    })


def emprestimo_create(request):
    _atualizar_atrasos()
    livros = Livro.objects.select_related("autor").order_by("titulo")
    leitores = Leitor.objects.order_by("nome")
    if request.method == "POST":
        livro_id = request.POST.get("livro")
        leitor_id = request.POST.get("leitor")
        data_prevista = request.POST.get("data_prevista", "").strip()
        erros = []
        if not livro_id:
            erros.append("Livro é obrigatório.")
        if not leitor_id:
            erros.append("Leitor é obrigatório.")
        if not data_prevista:
            erros.append("Data prevista de devolução é obrigatória.")

        if erros:
            for e in erros:
                messages.error(request, e)
            return render(request, "biblioteca/emprestimo_form.html", {
                "livros": livros,
                "leitores": leitores,
            })

        # ── Verifica disponibilidade via gRPC ─────────────────────────────
        grpc_offline = False
        try:
            disp = grpc_client.verificar_disponibilidade(int(livro_id))
            if not disp["disponivel"]:
                messages.error(
                    request,
                    f'[gRPC] Não há exemplares disponíveis de "{disp["titulo"]}".',
                )
                return render(request, "biblioteca/emprestimo_form.html", {
                    "livros": livros,
                    "leitores": leitores,
                })
        except ConnectionError:
            grpc_offline = True
            livro = get_object_or_404(Livro, pk=livro_id)
            if livro.exemplares_disponiveis <= 0:
                messages.error(request, f'Não há exemplares disponíveis de "{livro.titulo}".')
                return render(request, "biblioteca/emprestimo_form.html", {
                    "livros": livros,
                    "leitores": leitores,
                })

        # ── Registra o empréstimo via gRPC (ou localmente se offline) ─────
        if grpc_offline:
            livro = get_object_or_404(Livro, pk=livro_id)
            emp = Emprestimo.objects.create(
                livro=livro,
                leitor_id=leitor_id,
                data_prevista=data_prevista,
                status="ativo",
            )
            mq_publisher.publicar_emprestimo(
                emprestimo_id=emp.pk,
                livro_titulo=livro.titulo,
                leitor_id=int(leitor_id),
                data_prevista=data_prevista,
            )
            messages.success(request, f"Empréstimo #{emp.pk} registrado com sucesso (serviço gRPC indisponível, modo local).")
            return redirect("emprestimo_list")

        try:
            resultado = grpc_client.registrar_emprestimo(
                livro_id=int(livro_id),
                leitor_id=int(leitor_id),
                data_prevista=data_prevista,
            )
            if resultado["sucesso"]:
                messages.success(request, resultado["mensagem"])
            else:
                messages.error(request, f'[gRPC] {resultado["mensagem"]}')
        except ConnectionError:
            messages.error(request, "Serviço gRPC ficou indisponível durante o registro. Tente novamente.")
            return render(request, "biblioteca/emprestimo_form.html", {
                "livros": livros,
                "leitores": leitores,
            })
        return redirect("emprestimo_list")

    return render(request, "biblioteca/emprestimo_form.html", {
        "livros": livros,
        "leitores": leitores,
    })


def emprestimo_devolver(request, pk):
    emp = get_object_or_404(Emprestimo, pk=pk)
    if emp.status != "ativo":
        messages.warning(request, "Este empréstimo já foi encerrado.")
        return redirect("emprestimo_list")
    if request.method == "POST":
        hoje = timezone.now().date()
        emp.data_devolucao = hoje
        emp.status = "devolvido"
        emp.save()
        mq_publisher.publicar_devolucao(
            emprestimo_id=emp.pk,
            livro_titulo=emp.livro.titulo,
            leitor_id=emp.leitor.pk,
            data_devolucao=hoje.strftime("%d/%m/%Y"),
        )
        messages.success(request, "Devolução registrada com sucesso.")
        return redirect("emprestimo_list")
    return render(request, "biblioteca/emprestimo_devolver.html", {"emp": emp})
