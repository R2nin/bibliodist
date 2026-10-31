import json
import re
from datetime import date
from collections import defaultdict

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from biblioteca.models import Livro


P_TOMBO = re.compile(
    r'Tombo Inicial:\s*(\d+)\s*\|?\s*Tombo Exemplar:\s*(\d+)\s*\|?\s*Título:\s*(.+?)(?:\s*\||\s*$)',
    re.IGNORECASE,
)
P_NOVO = re.compile(
    r'[Tt][íi]tulo:\s*(.*?)\s*/\s*C:\s*([A-Za-z]?[\d.\s]+?)\s*/\s*T:\s*([\d.]+)',
    re.IGNORECASE,
)
P_SIMPLES = re.compile(r'^(.+?)\s+-\s*([A-ZÁÉÍÓÚ].+)$')


def _parse(registro):
    """
    Retorna dict com: titulo, tombo_inicial, cdd, data_aquisicao
    ou None se não for possível extrair.
    """
    desc = registro['DESCRICAO'].strip()
    data_aq = registro.get('DATAAQUISICAO', '')
    data_aq = date.fromisoformat(data_aq[:10]) if data_aq else None

    m = P_TOMBO.search(desc)
    if m:
        return {
            'titulo': m.group(3).strip(),
            'tombo_inicial': m.group(1).strip(),
            'cdd': None,
            'data_aquisicao': data_aq,
            'key': f'T_{m.group(1).strip()}',
        }

    m = P_NOVO.search(desc)
    if m:
        titulo = m.group(1).strip()
        tombo = m.group(3).strip().replace('.', '')  # ex: "35.749" → "35749"
        return {
            'titulo': titulo,
            'tombo_inicial': tombo,
            'cdd': m.group(2).strip(),
            'data_aquisicao': data_aq,
            'key': f'N_{titulo.upper()}',
        }

    m = P_SIMPLES.match(desc)
    if m:
        titulo = m.group(1).strip()
        return {
            'titulo': titulo,
            'tombo_inicial': None,
            'cdd': None,
            'data_aquisicao': data_aq,
            'key': f'S_{titulo.upper()}',
        }

    return None


class Command(BaseCommand):
    help = 'Importa o acervo bibliográfico exportado do portal de transparência (JSON).'

    def add_arguments(self, parser):
        parser.add_argument('arquivo', help='Caminho para o arquivo JSON exportado.')
        parser.add_argument(
            '--limpar',
            action='store_true',
            help='Remove todos os livros sem empréstimos antes de importar.',
        )

    def handle(self, *args, **options):
        caminho = options['arquivo']

        try:
            with open(caminho, encoding='utf-8') as f:
                dados = json.load(f)
        except FileNotFoundError:
            raise CommandError(f'Arquivo não encontrado: {caminho}')
        except json.JSONDecodeError as e:
            raise CommandError(f'JSON inválido: {e}')

        if options['limpar']:
            sem_emprestimo = Livro.objects.filter(emprestimos__isnull=True)
            total_rem = sem_emprestimo.count()
            sem_emprestimo.delete()
            self.stdout.write(f'  {total_rem} livros sem empréstimos removidos.')

        # Filtrar só bibliográficos
        bibliograficos = [r for r in dados if 'BIBLIOGRÁFICOS' in r.get('TIPO', '')]
        self.stdout.write(f'Registros bibliográficos no arquivo: {len(bibliograficos):,}')

        # Agrupar por livro (chave única)
        livros: dict[str, dict] = {}
        sem_parse = 0

        for reg in bibliograficos:
            parsed = _parse(reg)
            if parsed is None:
                sem_parse += 1
                continue
            key = parsed['key']
            if key not in livros:
                livros[key] = {
                    'titulo': parsed['titulo'],
                    'tombo_inicial': parsed['tombo_inicial'],
                    'classificacao_cdd': parsed['cdd'],
                    'data_aquisicao': parsed['data_aquisicao'],
                    'total_exemplares': 0,
                }
            livros[key]['total_exemplares'] += 1

        self.stdout.write(f'Títulos únicos identificados: {len(livros):,}')
        if sem_parse:
            self.stdout.write(self.style.WARNING(f'  Registros não parseados: {sem_parse}'))

        # Descobrir quais tombos já existem no banco
        tombos_existentes = set(
            Livro.objects.exclude(tombo_inicial=None)
            .values_list('tombo_inicial', flat=True)
        )
        titulos_existentes = set(
            Livro.objects.filter(tombo_inicial=None)
            .values_list('titulo', flat=True)
        )

        novos = []
        ignorados = 0

        for info in livros.values():
            if info['tombo_inicial'] and info['tombo_inicial'] in tombos_existentes:
                ignorados += 1
                continue
            if not info['tombo_inicial'] and info['titulo'] in titulos_existentes:
                ignorados += 1
                continue

            novos.append(Livro(
                titulo=info['titulo'][:500],
                tombo_inicial=info['tombo_inicial'],
                classificacao_cdd=info['classificacao_cdd'],
                data_aquisicao=info['data_aquisicao'],
                total_exemplares=info['total_exemplares'],
            ))

        if ignorados:
            self.stdout.write(f'  Já existiam no banco (ignorados): {ignorados:,}')

        self.stdout.write(f'Novos livros a inserir: {len(novos):,}')

        if not novos:
            self.stdout.write(self.style.SUCCESS('Nada a inserir. Banco já está atualizado.'))
            return

        # Inserir em lotes de 500
        LOTE = 500
        total_inserido = 0
        with transaction.atomic():
            for i in range(0, len(novos), LOTE):
                lote = novos[i:i + LOTE]
                Livro.objects.bulk_create(lote, ignore_conflicts=True)
                total_inserido += len(lote)
                self.stdout.write(f'  {total_inserido:,} / {len(novos):,}', ending='\r')
                self.stdout.flush()

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Importação concluída: {total_inserido:,} livros inseridos.'
        ))
