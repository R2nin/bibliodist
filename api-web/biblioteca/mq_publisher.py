"""
Publicador RabbitMQ para notificações assíncronas.

Publica na fila 'notificacoes' um JSON com os dados de cada evento
(empréstimo ou devolução). O worker consome e persiste a Notificacao.

Se o RabbitMQ estiver offline, o erro é logado e a notificação é criada
diretamente no banco (fallback síncrono), garantindo que nada se perca.
"""

import json
import logging
import os

logger = logging.getLogger(__name__)

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
FILA = "notificacoes"


def _publicar(payload: dict) -> None:
    """Abre conexão, publica e fecha. Simples e sem estado persistente."""
    import pika  # importação local — opcional no Django quando MQ está offline

    params = pika.URLParameters(RABBITMQ_URL)
    conn = pika.BlockingConnection(params)
    ch = conn.channel()
    ch.queue_declare(queue=FILA, durable=True)
    ch.basic_publish(
        exchange="",
        routing_key=FILA,
        body=json.dumps(payload, ensure_ascii=False),
        properties=pika.BasicProperties(delivery_mode=2),  # persistente
    )
    conn.close()


def publicar_emprestimo(emprestimo_id: int, livro_titulo: str,
                        leitor_id: int, data_prevista: str) -> bool:
    """
    Publica evento de empréstimo na fila.
    Retorna True se publicou com sucesso, False se fallback síncrono foi usado.
    """
    payload = {
        "tipo": "emprestimo",
        "emprestimo_id": emprestimo_id,
        "livro_titulo": livro_titulo,
        "leitor_id": leitor_id,
        "mensagem": (
            f'Empréstimo do livro "{livro_titulo}" realizado. '
            f"Devolver até {data_prevista}."
        ),
    }
    try:
        _publicar(payload)
        logger.info("[MQ] Evento empréstimo #%s publicado.", emprestimo_id)
        return True
    except Exception as exc:
        logger.warning("[MQ] RabbitMQ indisponível (%s). Criando notificação localmente.", exc)
        _fallback_sincrono(payload)
        return False


def publicar_devolucao(emprestimo_id: int, livro_titulo: str,
                       leitor_id: int, data_devolucao: str) -> bool:
    """
    Publica evento de devolução na fila.
    Retorna True se publicou com sucesso, False se fallback síncrono foi usado.
    """
    payload = {
        "tipo": "devolucao",
        "emprestimo_id": emprestimo_id,
        "livro_titulo": livro_titulo,
        "leitor_id": leitor_id,
        "mensagem": f'Livro "{livro_titulo}" devolvido em {data_devolucao}.',
    }
    try:
        _publicar(payload)
        logger.info("[MQ] Evento devolução #%s publicado.", emprestimo_id)
        return True
    except Exception as exc:
        logger.warning("[MQ] RabbitMQ indisponível (%s). Criando notificação localmente.", exc)
        _fallback_sincrono(payload)
        return False


def _fallback_sincrono(payload: dict) -> None:
    """Cria Notificacao diretamente no banco quando o MQ está offline."""
    from .models import Notificacao  # importação local para evitar circular import
    Notificacao.objects.create(
        leitor_id=payload["leitor_id"],
        emprestimo_id=payload["emprestimo_id"],
        tipo=payload["tipo"],
        mensagem=payload["mensagem"],
    )
