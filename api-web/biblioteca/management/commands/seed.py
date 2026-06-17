"""
Comando: python manage.py seed
Popula o banco com dados de exemplo para desenvolvimento/demonstração.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from biblioteca.models import Autor, Categoria, Emprestimo, Leitor, Livro


class Command(BaseCommand):
    help = "Popula o banco com dados de exemplo (autores, categorias, livros, leitores)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limpar",
            action="store_true",
            help="Remove todos os registros antes de popular.",
        )

    def handle(self, *args, **options):
        if options["limpar"]:
            Emprestimo.objects.all().delete()
            Livro.objects.all().delete()
            Autor.objects.all().delete()
            Categoria.objects.all().delete()
            Leitor.objects.all().delete()
            self.stdout.write(self.style.WARNING("Banco limpo."))

        # ── Categorias ────────────────────────────────────────────────────────
        categorias_data = [
            "Ciência da Computação",
            "Matemática",
            "Engenharia",
            "Literatura Brasileira",
            "Física",
            "Redes e Sistemas Distribuídos",
        ]
        categorias = {}
        for nome in categorias_data:
            obj, created = Categoria.objects.get_or_create(nome=nome)
            categorias[nome] = obj
            if created:
                self.stdout.write(f"  Categoria criada: {nome}")

        # ── Autores ───────────────────────────────────────────────────────────
        autores_data = [
            "Andrew S. Tanenbaum",
            "Donald E. Knuth",
            "Martin Fowler",
            "Machado de Assis",
            "Clarice Lispector",
            "Bjarne Stroustrup",
        ]
        autores = {}
        for nome in autores_data:
            obj, created = Autor.objects.get_or_create(nome=nome)
            autores[nome] = obj
            if created:
                self.stdout.write(f"  Autor criado: {nome}")

        # ── Livros ────────────────────────────────────────────────────────────
        livros_data = [
            {
                "titulo": "Sistemas Distribuídos: Princípios e Paradigmas",
                "isbn": "978-85-7606-191-2",
                "ano": 2007,
                "autor": "Andrew S. Tanenbaum",
                "categoria": "Redes e Sistemas Distribuídos",
                "total_exemplares": 3,
            },
            {
                "titulo": "Redes de Computadores",
                "isbn": "978-85-7606-168-4",
                "ano": 2011,
                "autor": "Andrew S. Tanenbaum",
                "categoria": "Redes e Sistemas Distribuídos",
                "total_exemplares": 2,
            },
            {
                "titulo": "The Art of Computer Programming, Vol. 1",
                "isbn": "978-0-201-89683-1",
                "ano": 1997,
                "autor": "Donald E. Knuth",
                "categoria": "Ciência da Computação",
                "total_exemplares": 2,
            },
            {
                "titulo": "Refactoring: Improving the Design of Existing Code",
                "isbn": "978-0-201-48567-7",
                "ano": 1999,
                "autor": "Martin Fowler",
                "categoria": "Ciência da Computação",
                "total_exemplares": 4,
            },
            {
                "titulo": "Dom Casmurro",
                "isbn": "978-85-359-0277-7",
                "ano": 1899,
                "autor": "Machado de Assis",
                "categoria": "Literatura Brasileira",
                "total_exemplares": 5,
            },
            {
                "titulo": "A Paixão Segundo G.H.",
                "isbn": "978-85-220-0581-5",
                "ano": 1964,
                "autor": "Clarice Lispector",
                "categoria": "Literatura Brasileira",
                "total_exemplares": 3,
            },
            {
                "titulo": "The C++ Programming Language",
                "isbn": "978-0-321-56384-2",
                "ano": 2013,
                "autor": "Bjarne Stroustrup",
                "categoria": "Ciência da Computação",
                "total_exemplares": 2,
            },
        ]
        livros = {}
        for d in livros_data:
            obj, created = Livro.objects.get_or_create(
                isbn=d["isbn"],
                defaults={
                    "titulo": d["titulo"],
                    "ano": d["ano"],
                    "autor": autores[d["autor"]],
                    "categoria": categorias[d["categoria"]],
                    "total_exemplares": d["total_exemplares"],
                },
            )
            livros[d["isbn"]] = obj
            if created:
                self.stdout.write(f"  Livro criado: {d['titulo']}")

        # ── Leitores ─────────────────────────────────────────────────────────
        leitores_data = [
            {"nome": "Ana Paula Silva", "email": "ana.silva@fema.edu.br", "matricula": "2311600001"},
            {"nome": "Bruno Costa Lima", "email": "bruno.lima@fema.edu.br", "matricula": "2311600002"},
            {"nome": "Carlos Eduardo Souza", "email": "carlos.souza@fema.edu.br", "matricula": "2311600003"},
            {"nome": "Daniela Ferreira Rocha", "email": "daniela.rocha@fema.edu.br", "matricula": "2311600004"},
            {"nome": "Eduardo Alves Neto", "email": "eduardo.neto@fema.edu.br", "matricula": "2311600005"},
        ]
        leitores = {}
        for d in leitores_data:
            obj, created = Leitor.objects.get_or_create(
                matricula=d["matricula"],
                defaults={"nome": d["nome"], "email": d["email"]},
            )
            leitores[d["matricula"]] = obj
            if created:
                self.stdout.write(f"  Leitor criado: {d['nome']}")

        self.stdout.write(self.style.SUCCESS("\nSeed concluído com sucesso!"))
        self.stdout.write(f"  {Autor.objects.count()} autores")
        self.stdout.write(f"  {Categoria.objects.count()} categorias")
        self.stdout.write(f"  {Livro.objects.count()} livros")
        self.stdout.write(f"  {Leitor.objects.count()} leitores")
