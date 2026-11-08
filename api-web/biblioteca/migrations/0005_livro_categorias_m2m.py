from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('biblioteca', '0004_add_tombo_exemplar'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='livro',
            name='categoria',
        ),
        migrations.AddField(
            model_name='livro',
            name='categorias',
            field=models.ManyToManyField(blank=True, related_name='livros', to='biblioteca.categoria'),
        ),
    ]
