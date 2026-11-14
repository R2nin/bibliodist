import datetime
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db.models import F
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .decorators import staff_required
from .models import Autor, Categoria, Emprestimo, Leitor, Livro, LogOperacao, Notificacao
from . import grpc_client
from . import isbn as isbn_lookup
from . import mq_publisher


def _log(request, tipo, descricao):
    usuario = request.user if request.user.is_authenticated else None
    LogOperacao.objects.create(usuario=usuario, tipo=tipo, descricao=descricao)


@staff_required
def logs(request):
    qs = LogOperacao.objects.select_related("usuario").order_by("-criado_em")
    tipo = request.GET.get("tipo", "")
    if tipo:
        qs = qs.filter(tipo=tipo)
    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "biblioteca/logs.html", {"page_obj": page, "tipo": tipo})


@staff_required
def livro_buscar_isbn(request):
    isbn = isbn_lookup.normalizar_isbn(request.GET.get("isbn", ""))
    if not isbn:
        return JsonResponse({"erro": "ISBN não informado."}, status=400)
    if len(isbn) not in (10, 13):
        return JsonResponse({"erro": "ISBN inválido: deve ter 10 ou 13 dígitos."}, status=400)

    avisos = []
    dados = isbn_lookup.buscar(isbn, avisos)
    if not dados:
        erro = "Nenhum resultado encontrado para este ISBN."
        if avisos:
            erro += " Atenção: " + "; ".join(dict.fromkeys(avisos)) + "."
        return JsonResponse({"erro": erro}, status=404)
    return JsonResponse(dados)


# ─── Home ────────────────────────────────────────────────────────────────────

@login_required
def home(request):
    from .models import Livro, Leitor, Emprestimo
    ctx = {
        "total_livros": Livro.objects.count(),
        "total_exemplares": sum(Livro.objects.values_list("total_exemplares", flat=True)),
        "total_leitores": Leitor.objects.count(),
        "emprestimos_ativos": Emprestimo.objects.filter(status="ativo").count(),
        "emprestimos_atrasados": Emprestimo.objects.filter(status="atrasado").count(),
    }
    return render(request, "home.html", ctx)


# ─── Autores ─────────────────────────────────────────────────────────────────

@login_required
def autor_list(request):
    qs = Autor.objects.all()
    paginator = Paginator(qs, 10)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "biblioteca/autor_list.html", {"page_obj": page})


@staff_required
def autor_create(request):
    if request.method == "POST":
        nome = request.POST.get("nome", "").strip()
        if nome:
            Autor.objects.create(nome=nome)
            messages.success(request, "Autor criado com sucesso.")
            return redirect("autor_list")
        messages.error(request, "Nome é obrigatório.")
    nome_sugerido = request.GET.get("nome", "")
    return render(request, "biblioteca/autor_form.html", {"titulo": "Novo Autor", "nome_sugerido": nome_sugerido})


@staff_required
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


@staff_required
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

@login_required
def categoria_list(request):
    qs = Categoria.objects.all()
    paginator = Paginator(qs, 10)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "biblioteca/categoria_list.html", {"page_obj": page})


@staff_required
def categoria_create(request):
    if request.method == "POST":
        nome = request.POST.get("nome", "").strip()
        if nome:
            Categoria.objects.create(nome=nome)
            messages.success(request, "Categoria criada com sucesso.")
            return redirect("categoria_list")
        messages.error(request, "Nome é obrigatório.")
    return render(request, "biblioteca/categoria_form.html", {"titulo": "Nova Categoria"})


@staff_required
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


@staff_required
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

@login_required
def livro_list(request):
    q = request.GET.get("q", "").strip()
    sort = request.GET.get("sort", "titulo")
    direcao = request.GET.get("dir", "asc")

    CAMPOS_VALIDOS = {
        "titulo", "chapa", "data_aquisicao", "tombo_inicial",
        "tombo_exemplar", "classificacao_cdd", "total_exemplares",
    }
    if sort not in CAMPOS_VALIDOS:
        sort = "titulo"
    if direcao not in ("asc", "desc"):
        direcao = "asc"

    order_field = f"-{sort}" if direcao == "desc" else sort

    qs = Livro.objects.select_related("autor").prefetch_related("categorias")
    if q:
        qs = qs.filter(
            titulo__icontains=q
        ) | qs.filter(
            chapa__icontains=q
        ) | qs.filter(
            tombo_inicial__icontains=q
        ) | qs.filter(
            tombo_exemplar__icontains=q
        )
        qs = qs.distinct()
        nome = request.user.get_full_name() or request.user.username
        _log(request, "busca", f'Usuário "{nome}" buscou por "{q}".')
    qs = qs.order_by(order_field)

    paginator = Paginator(qs, 10)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "biblioteca/livro_list.html", {
        "page_obj": page,
        "q": q,
        "sort": sort,
        "dir": direcao,
    })


@login_required
def livro_detail(request, pk):
    livro = get_object_or_404(
        Livro.objects.select_related("autor").prefetch_related("categorias"),
        pk=pk,
    )
    nome = request.user.get_full_name() or request.user.username
    _log(request, "consulta_livro", f'Usuário "{nome}" consultou o livro "{livro.titulo}".')
    return render(request, "biblioteca/livro_detail.html", {"livro": livro})


def _metadados_livro(post):
    """Campos vindos da busca por ISBN (editora, data, capa, nota)."""
    from decimal import Decimal, InvalidOperation
    nota = post.get("nota", "").strip().replace(",", ".")
    try:
        nota = Decimal(nota) if nota else None
        if nota is not None and not (0 <= nota <= 5):
            nota = None
    except InvalidOperation:
        nota = None
    qtd = post.get("nota_qtd", "").strip()
    capa = post.get("capa_url", "").strip()
    return {
        "editora": post.get("editora", "").strip()[:200],
        "data_publicacao": post.get("data_publicacao", "").strip()[:20],
        "capa_url": capa[:500] if capa.startswith(("http://", "https://")) else "",
        "nota": nota,
        "nota_qtd": int(qtd) if qtd.isdigit() else None,
    }


@staff_required
def livro_create(request):
    autores = Autor.objects.all()
    categorias = Categoria.objects.all()
    if request.method == "POST":
        erros = []
        titulo = request.POST.get("titulo", "").strip()
        isbn = request.POST.get("isbn", "").strip()
        ano = request.POST.get("ano", "").strip()
        autor_id = request.POST.get("autor")
        categorias_ids = request.POST.getlist("categorias")
        total = request.POST.get("total_exemplares", "1").strip()
        descricao = request.POST.get("descricao", "").strip()

        if not titulo:
            erros.append("Título é obrigatório.")
        if isbn and Livro.objects.filter(isbn=isbn).exists():
            erros.append("Já existe um livro com este ISBN.")

        if erros:
            for e in erros:
                messages.error(request, e)
        else:
            livro = Livro.objects.create(
                titulo=titulo,
                isbn=isbn or None,
                ano=int(ano) if ano.isdigit() else None,
                autor_id=autor_id or None,
                total_exemplares=int(total) if total.isdigit() else 1,
                descricao=descricao or None,
                **_metadados_livro(request.POST),
            )
            livro.categorias.set(categorias_ids)
            messages.success(request, "Livro criado com sucesso.")
            return redirect("livro_list")

    return render(request, "biblioteca/livro_form.html", {
        "titulo_pag": "Novo Livro",
        "autores": autores,
        "categorias": categorias,
    })


@staff_required
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
        livro.descricao = request.POST.get("descricao", "").strip() or None
        for campo, valor in _metadados_livro(request.POST).items():
            setattr(livro, campo, valor)
        total = request.POST.get("total_exemplares", "").strip()
        if total.isdigit():
            livro.total_exemplares = int(total)
        livro.save()
        livro.categorias.set(request.POST.getlist("categorias"))
        messages.success(request, "Livro atualizado.")
        return redirect("livro_list")
    return render(request, "biblioteca/livro_form.html", {
        "titulo_pag": "Editar Livro",
        "obj": livro,
        "autores": autores,
        "categorias": categorias,
    })


@staff_required
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

@login_required
def leitor_list(request):
    qs = Leitor.objects.all()
    paginator = Paginator(qs, 10)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "biblioteca/leitor_list.html", {"page_obj": page})


@staff_required
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


@staff_required
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


@staff_required
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


@login_required
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


@staff_required
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
            nome_op = request.user.get_full_name() or request.user.username
            _log(request, "emprestimo", f'Usuário "{nome_op}" registrou empréstimo de "{livro.titulo}" para {emp.leitor.nome} (modo local, gRPC indisponível).')
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
                return redirect("emprestimo_list")
        except ConnectionError:
            messages.error(request, "Serviço gRPC ficou indisponível durante o registro. Tente novamente.")
            return render(request, "biblioteca/emprestimo_form.html", {
                "livros": livros,
                "leitores": leitores,
            })
        nome_op = request.user.get_full_name() or request.user.username
        livro_emp = get_object_or_404(Livro, pk=livro_id)
        leitor_emp = get_object_or_404(Leitor, pk=leitor_id)
        _log(request, "emprestimo", f'Usuário "{nome_op}" registrou empréstimo de "{livro_emp.titulo}" para {leitor_emp.nome}.')
        return redirect("emprestimo_list")

    return render(request, "biblioteca/emprestimo_form.html", {
        "livros": livros,
        "leitores": leitores,
    })


@staff_required
def emprestimo_devolver(request, pk):
    emp = get_object_or_404(Emprestimo, pk=pk)
    if emp.status == "devolvido":
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
        nome_op = request.user.get_full_name() or request.user.username
        _log(request, "devolucao", f'Usuário "{nome_op}" registrou devolução de "{emp.livro.titulo}" por {emp.leitor.nome}.')
        messages.success(request, "Devolução registrada com sucesso.")
        return redirect("emprestimo_list")
    return render(request, "biblioteca/emprestimo_devolver.html", {"emp": emp})


# ─── Empréstimos em atraso: renovação e cobrança por e-mail ──────────────────

def _texto_cobranca(emp):
    hoje = timezone.now().date()
    dias = (hoje - emp.data_prevista).days
    assunto = f'BiblioDist — devolução em atraso: "{emp.livro.titulo}"'
    corpo = (
        f"Olá, {emp.leitor.nome}.\n\n"
        f'Consta em nosso sistema que o livro "{emp.livro.titulo}", emprestado em '
        f"{emp.data_emprestimo:%d/%m/%Y}, deveria ter sido devolvido em "
        f"{emp.data_prevista:%d/%m/%Y} ({dias} dia{'s' if dias != 1 else ''} de atraso).\n\n"
        "Por favor, devolva o livro na biblioteca o quanto antes ou entre em contato "
        "para solicitar a renovação do empréstimo.\n\n"
        "Atenciosamente,\nBiblioteca — BiblioDist"
    )
    return assunto, corpo


@staff_required
def emprestimo_renovar(request, pk):
    _atualizar_atrasos()
    emp = get_object_or_404(Emprestimo.objects.select_related("livro", "leitor"), pk=pk)
    if emp.status != "atrasado":
        messages.warning(request, "Só é possível renovar empréstimos em atraso.")
        return redirect("emprestimo_list")

    hoje = timezone.now().date()
    sugestao = hoje + datetime.timedelta(days=7)
    if request.method == "POST":
        bruto = request.POST.get("nova_data", "").strip()
        try:
            nova_data = datetime.date.fromisoformat(bruto)
        except ValueError:
            nova_data = None
        if not nova_data:
            messages.error(request, "Informe uma data válida.")
        elif nova_data <= hoje:
            messages.error(request, "A nova data de devolução deve ser posterior a hoje.")
        else:
            anterior = emp.data_prevista
            emp.data_prevista = nova_data
            emp.status = "ativo"
            emp.save(update_fields=["data_prevista", "status"])
            mq_publisher.publicar_evento(
                tipo="renovacao",
                emprestimo_id=emp.pk,
                livro_titulo=emp.livro.titulo,
                leitor_id=emp.leitor.pk,
                mensagem=(
                    f'Empréstimo do livro "{emp.livro.titulo}" renovado. '
                    f"Nova data de devolução: {nova_data:%d/%m/%Y}."
                ),
            )
            nome_op = request.user.get_full_name() or request.user.username
            _log(request, "renovacao",
                 f'Usuário "{nome_op}" renovou o empréstimo de "{emp.livro.titulo}" para '
                 f"{emp.leitor.nome}: de {anterior:%d/%m/%Y} para {nova_data:%d/%m/%Y}.")
            messages.success(request, f"Empréstimo renovado até {nova_data:%d/%m/%Y}.")
            return redirect("emprestimo_list")
        sugestao = nova_data or sugestao

    return render(request, "biblioteca/emprestimo_renovar.html", {
        "emp": emp,
        "hoje": hoje,
        "minimo": hoje + datetime.timedelta(days=1),
        "sugestao": sugestao,
    })


@staff_required
def emprestimo_cobrar(request, pk):
    _atualizar_atrasos()
    emp = get_object_or_404(Emprestimo.objects.select_related("livro", "leitor"), pk=pk)
    if emp.status != "atrasado":
        messages.warning(request, "Só é possível enviar cobrança de empréstimos em atraso.")
        return redirect("emprestimo_list")

    smtp_configurado = bool(settings.EMAIL_HOST)
    assunto, corpo = _texto_cobranca(emp)
    if request.method == "POST":
        assunto = request.POST.get("assunto", "").strip() or assunto
        corpo = request.POST.get("corpo", "").strip() or corpo
        try:
            send_mail(assunto, corpo, settings.DEFAULT_FROM_EMAIL, [emp.leitor.email])
        except Exception as exc:
            logging.getLogger(__name__).exception("Falha ao enviar e-mail de cobrança")
            messages.error(request, f"Não foi possível enviar o e-mail: {exc}")
        else:
            # F() evita perder contagem se dois envios ocorrerem ao mesmo tempo
            Emprestimo.objects.filter(pk=emp.pk).update(
                cobrancas=F("cobrancas") + 1, ultima_cobranca=timezone.now(),
            )
            emp.refresh_from_db(fields=["cobrancas", "ultima_cobranca"])
            vezes = f"{emp.cobrancas}ª cobrança"
            mq_publisher.publicar_evento(
                tipo="atraso",
                emprestimo_id=emp.pk,
                livro_titulo=emp.livro.titulo,
                leitor_id=emp.leitor.pk,
                mensagem=f'E-mail de cobrança enviado para {emp.leitor.email} sobre "{emp.livro.titulo}".',
            )
            nome_op = request.user.get_full_name() or request.user.username
            _log(request, "cobranca",
                 f'Usuário "{nome_op}" enviou e-mail de cobrança para {emp.leitor.nome} '
                 f'<{emp.leitor.email}> sobre "{emp.livro.titulo}" (previsto para {emp.data_prevista:%d/%m/%Y}) — {vezes}.')
            if smtp_configurado:
                messages.success(request, f"E-mail de cobrança enviado para {emp.leitor.email} ({vezes}).")
            else:
                messages.warning(request, f"SMTP não configurado: o e-mail foi gerado apenas no log do servidor ({vezes}).")
            return redirect("emprestimo_list")

    return render(request, "biblioteca/emprestimo_cobrar.html", {
        "emp": emp,
        "assunto": assunto,
        "corpo": corpo,
        "dias_atraso": (timezone.now().date() - emp.data_prevista).days,
        "smtp_configurado": smtp_configurado,
    })
