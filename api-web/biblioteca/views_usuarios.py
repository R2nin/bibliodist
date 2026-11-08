from django.contrib import messages
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render

from .decorators import superuser_required


@superuser_required
def usuario_list(request):
    usuarios = User.objects.all().order_by("username")
    return render(request, "usuarios/usuario_list.html", {"usuarios": usuarios})


@superuser_required
def usuario_create(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        primeiro_nome = request.POST.get("primeiro_nome", "").strip()
        senha = request.POST.get("senha", "")
        senha2 = request.POST.get("senha2", "")
        papel = request.POST.get("papel", "normal")

        erros = []
        if not username:
            erros.append("Nome de usuário é obrigatório.")
        elif User.objects.filter(username=username).exists():
            erros.append("Já existe um usuário com este nome.")
        if not senha:
            erros.append("Senha é obrigatória.")
        elif senha != senha2:
            erros.append("As senhas não conferem.")
        elif len(senha) < 8:
            erros.append("A senha deve ter pelo menos 8 caracteres.")

        if erros:
            for e in erros:
                messages.error(request, e)
        else:
            user = User.objects.create_user(
                username=username,
                password=senha,
                first_name=primeiro_nome,
            )
            if papel == "admin":
                user.is_staff = True
                user.save()
            messages.success(request, f'Usuário "{username}" criado com sucesso.')
            return redirect("usuario_list")

    return render(request, "usuarios/usuario_form.html")


@superuser_required
def usuario_reset_senha(request, pk):
    usuario = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        senha = request.POST.get("senha", "")
        senha2 = request.POST.get("senha2", "")
        erros = []
        if not senha:
            erros.append("Senha é obrigatória.")
        elif senha != senha2:
            erros.append("As senhas não conferem.")
        elif len(senha) < 8:
            erros.append("A senha deve ter pelo menos 8 caracteres.")

        if erros:
            for e in erros:
                messages.error(request, e)
        else:
            usuario.set_password(senha)
            usuario.save()
            messages.success(request, f'Senha de "{usuario.username}" redefinida com sucesso.')
            return redirect("usuario_list")

    return render(request, "usuarios/usuario_reset_senha.html", {"usuario": usuario})
