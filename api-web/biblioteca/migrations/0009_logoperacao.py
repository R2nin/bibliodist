from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("biblioteca", "0008_chapa_max_length"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="LogOperacao",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tipo", models.CharField(
                    choices=[
                        ("login", "Login"),
                        ("consulta_livro", "Consulta de Livro"),
                        ("busca", "Busca"),
                        ("emprestimo", "Empréstimo"),
                        ("devolucao", "Devolução"),
                    ],
                    max_length=20,
                )),
                ("descricao", models.TextField()),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                (
                    "usuario",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="logs_operacao",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Log de Operação",
                "verbose_name_plural": "Logs de Operação",
                "ordering": ["-criado_em"],
            },
        ),
    ]
