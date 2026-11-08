from django.db import migrations

CURSOS_FEMA = [
    "Administração",
    "Análise e Desenvolvimento de Sistemas",
    "Ciência da Computação",
    "Ciências Contábeis",
    "Direito",
    "Educação Física",
    "Engenharia Civil",
    "Engenharia de Produção",
    "Fisioterapia",
    "Letras",
    "Medicina Veterinária",
    "Nutrição",
    "Pedagogia",
    "Psicologia",
]


def populate_categorias(apps, schema_editor):
    Categoria = apps.get_model('biblioteca', 'Categoria')
    for nome in CURSOS_FEMA:
        Categoria.objects.get_or_create(nome=nome)


class Migration(migrations.Migration):

    dependencies = [
        ('biblioteca', '0005_livro_categorias_m2m'),
    ]

    operations = [
        migrations.RunPython(populate_categorias, migrations.RunPython.noop),
    ]
