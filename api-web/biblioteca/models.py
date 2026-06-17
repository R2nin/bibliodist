from django.db import models
from django.utils import timezone


class Autor(models.Model):
    nome = models.CharField(max_length=200)

    class Meta:
        verbose_name = "Autor"
        verbose_name_plural = "Autores"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Categoria(models.Model):
    nome = models.CharField(max_length=100)

    class Meta:
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Livro(models.Model):
    titulo = models.CharField(max_length=300)
    isbn = models.CharField(max_length=20, unique=True)
    ano = models.PositiveIntegerField()
    autor = models.ForeignKey(Autor, on_delete=models.PROTECT, related_name="livros")
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name="livros")
    total_exemplares = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = "Livro"
        verbose_name_plural = "Livros"
        ordering = ["titulo"]

    def __str__(self):
        return f"{self.titulo} ({self.ano})"

    @property
    def exemplares_disponiveis(self):
        ativos = self.emprestimos.filter(status="ativo").count()
        return self.total_exemplares - ativos


class Leitor(models.Model):
    nome = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    matricula = models.CharField(max_length=50, unique=True)

    class Meta:
        verbose_name = "Leitor"
        verbose_name_plural = "Leitores"
        ordering = ["nome"]

    def __str__(self):
        return f"{self.nome} ({self.matricula})"


class Emprestimo(models.Model):
    STATUS_CHOICES = [
        ("ativo", "Ativo"),
        ("devolvido", "Devolvido"),
        ("atrasado", "Atrasado"),
    ]

    livro = models.ForeignKey(Livro, on_delete=models.PROTECT, related_name="emprestimos")
    leitor = models.ForeignKey(Leitor, on_delete=models.PROTECT, related_name="emprestimos")
    data_emprestimo = models.DateField(default=timezone.now)
    data_prevista = models.DateField()
    data_devolucao = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="ativo")

    class Meta:
        verbose_name = "Empréstimo"
        verbose_name_plural = "Empréstimos"
        ordering = ["-data_emprestimo"]

    def __str__(self):
        return f"{self.livro} → {self.leitor} ({self.status})"


class Notificacao(models.Model):
    TIPO_CHOICES = [
        ("emprestimo", "Empréstimo Realizado"),
        ("devolucao", "Devolução Registrada"),
        ("atraso", "Atraso Detectado"),
    ]

    leitor = models.ForeignKey(Leitor, on_delete=models.CASCADE, related_name="notificacoes")
    emprestimo = models.ForeignKey(Emprestimo, on_delete=models.CASCADE, related_name="notificacoes")
    tipo = models.CharField(max_length=15, choices=TIPO_CHOICES)
    mensagem = models.TextField()
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Notificação"
        verbose_name_plural = "Notificações"
        ordering = ["-criada_em"]

    def __str__(self):
        return f"[{self.tipo}] {self.leitor} — {self.criada_em:%d/%m/%Y %H:%M}"
