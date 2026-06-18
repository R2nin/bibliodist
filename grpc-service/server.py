"""
Servidor gRPC — BibliotecaService
Porta padrão: 50051

Uso:
    python server.py

Variáveis de ambiente (opcionais):
    GRPC_PORT       porta do servidor (padrão: 50051)
    RABBITMQ_URL    padrão: amqp://guest:guest@localhost:5672/
    DJANGO_SETTINGS_MODULE (padrão: config.settings)
    DATABASE_URL    (lido pelo settings.py do api-web)
"""

import os
import sys
from concurrent import futures
from pathlib import Path

# ─── Bootstrap do Django ─────────────────────────────────────────────────────
# Aponta para o módulo api-web, que contém os models e settings
BASE_DIR = Path(__file__).resolve().parent.parent / "api-web"
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

# ─── Imports pós-setup ───────────────────────────────────────────────────────
import grpc
from biblioteca.models import Emprestimo, Livro, Leitor
from biblioteca import mq_publisher

import biblioteca_pb2
import biblioteca_pb2_grpc

# ─── Implementação do serviço ────────────────────────────────────────────────

class BibliotecaServicer(biblioteca_pb2_grpc.BibliotecaServiceServicer):

    def VerificarDisponibilidade(self, request, context):
        """Retorna quantos exemplares do livro estão disponíveis."""
        try:
            livro = Livro.objects.get(pk=request.livro_id)
        except Livro.DoesNotExist:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"Livro id={request.livro_id} não encontrado.")
            return biblioteca_pb2.DisponibilidadeResponse()

        disponiveis = livro.exemplares_disponiveis
        return biblioteca_pb2.DisponibilidadeResponse(
            disponivel=disponiveis > 0,
            exemplares_disponiveis=disponiveis,
            titulo=livro.titulo,
        )

    def RegistrarEmprestimo(self, request, context):
        """Cria um Emprestimo e sua Notificacao correspondente."""
        try:
            livro = Livro.objects.get(pk=request.livro_id)
        except Livro.DoesNotExist:
            return biblioteca_pb2.EmprestimoResponse(
                sucesso=False,
                mensagem=f"Livro id={request.livro_id} não encontrado.",
            )

        try:
            leitor = Leitor.objects.get(pk=request.leitor_id)
        except Leitor.DoesNotExist:
            return biblioteca_pb2.EmprestimoResponse(
                sucesso=False,
                mensagem=f"Leitor id={request.leitor_id} não encontrado.",
            )

        if livro.exemplares_disponiveis <= 0:
            return biblioteca_pb2.EmprestimoResponse(
                sucesso=False,
                mensagem=f'Não há exemplares disponíveis de "{livro.titulo}".',
            )

        emp = Emprestimo.objects.create(
            livro=livro,
            leitor=leitor,
            data_prevista=request.data_prevista,
            status="ativo",
        )
        mq_publisher.publicar_emprestimo(
            emprestimo_id=emp.pk,
            livro_titulo=livro.titulo,
            leitor_id=leitor.pk,
            data_prevista=request.data_prevista,
        )

        return biblioteca_pb2.EmprestimoResponse(
            sucesso=True,
            emprestimo_id=emp.pk,
            mensagem=f'Empréstimo #{emp.pk} registrado com sucesso via gRPC.',
        )


# ─── Entry point ─────────────────────────────────────────────────────────────

def serve():
    port = os.environ.get("GRPC_PORT", "50051")
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    biblioteca_pb2_grpc.add_BibliotecaServiceServicer_to_server(BibliotecaServicer(), server)
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    print(f"[gRPC] BibliotecaService rodando na porta {port} ...")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
