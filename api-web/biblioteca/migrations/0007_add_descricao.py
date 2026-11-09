from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('biblioteca', '0006_populate_categorias'),
    ]

    operations = [
        migrations.AddField(
            model_name='livro',
            name='descricao',
            field=models.TextField(blank=True, null=True),
        ),
    ]
