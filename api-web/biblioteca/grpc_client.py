"""
Cliente gRPC para o BibliotecaService.

Uso nas views:
    from .grpc_client import verificar_disponibilidade, registrar_emprestimo
"""

import os

import grpc

from .grpc_generated import biblioteca_pb2, biblioteca_pb2_grpc

GRPC_HOST = os.environ.get("GRPC_HOST", "localhost")
GRPC_PORT = os.environ.get("GRPC_PORT", "50051")
_ADDR = f"{GRPC_HOST}:{GRPC_PORT}"

_TIMEOUT = 5  # segundos


def _get_stub():
    channel = grpc.insecure_channel(_ADDR)
    return biblioteca_pb2_grpc.BibliotecaServiceStub(channel)


def verificar_disponibilidade(livro_id: int) -> dict:
    """
    Retorna dict com chaves:
        disponivel (bool), exemplares_disponiveis (int), titulo (str)
    Lança ConnectionError se o serviço gRPC não estiver acessível.
    """
    try:
        stub = _get_stub()
        resp = stub.VerificarDisponibilidade(
            biblioteca_pb2.VerificarRequest(livro_id=livro_id),
            timeout=_TIMEOUT,
        )
        return {
            "disponivel": resp.disponivel,
            "exemplares_disponiveis": resp.exemplares_disponiveis,
            "titulo": resp.titulo,
        }
    except grpc.RpcError as exc:
        raise ConnectionError(f"gRPC indisponível: {exc.details()}") from exc


def registrar_emprestimo(livro_id: int, leitor_id: int, data_prevista: str) -> dict:
    """
    Retorna dict com chaves:
        sucesso (bool), emprestimo_id (int), mensagem (str)
    Lança ConnectionError se o serviço gRPC não estiver acessível.
    """
    try:
        stub = _get_stub()
        resp = stub.RegistrarEmprestimo(
            biblioteca_pb2.EmprestimoRequest(
                livro_id=livro_id,
                leitor_id=leitor_id,
                data_prevista=data_prevista,
            ),
            timeout=_TIMEOUT,
        )
        return {
            "sucesso": resp.sucesso,
            "emprestimo_id": resp.emprestimo_id,
            "mensagem": resp.mensagem,
        }
    except grpc.RpcError as exc:
        raise ConnectionError(f"gRPC indisponível: {exc.details()}") from exc
