"""
Worker RabbitMQ — BiblioDist (Fase 3)

Consome a fila 'notificacoes' e persiste cada Notificacao no banco Django.

Uso:
    python worker.py

Variáveis de ambiente (opcionais):
    RABBITMQ_URL              padrão: amqp://guest:guest@localhost:5672/
    DJANGO_SETTINGS_MODULE    padrão: config.settings
    DATABASE_URL              lido pelo settings.py do api-web
"""

import json
import logging
import os
import sys
import time
from pathlib import Path

# ─── Bootstrap do Django ─────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent / "api-web"
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

# ─── Imports pós-setup ───────────────────────────────────────────────────────
import pika
from biblioteca.models import Notificacao

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [worker] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
FILA = "notificacoes"
RETRY_DELAY = 5  # segundos entre tentativas de reconexão


# ─── Processamento de mensagens ───────────────────────────────────────────────

def processar(ch, method, properties, body):
    """Callback chamado para cada mensagem recebida."""
    try:
        payload = json.loads(body)
        tipo = payload.get("tipo")
        emp_id = payload.get("emprestimo_id")
        leitor_id = payload.get("leitor_id")
        mensagem = payload.get("mensagem", "")

        if not all([tipo, emp_id, leitor_id]):
            logger.warning("Mensagem inválida (campos faltando): %s", payload)
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        Notificacao.objects.create(
            leitor_id=leitor_id,
            emprestimo_id=emp_id,
            tipo=tipo,
            mensagem=mensagem,
        )
        logger.info("[MQ] Notificação criada: tipo=%s empréstimo=#%s leitor=#%s", tipo, emp_id, leitor_id)
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as exc:
        logger.error("Erro ao processar mensagem: %s — %s", body, exc)
        # nack sem requeue para evitar loop infinito em mensagens corrompidas
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


# ─── Loop principal com reconexão automática ─────────────────────────────────

def conectar_e_consumir():
    params = pika.URLParameters(RABBITMQ_URL)
    conn = pika.BlockingConnection(params)
    ch = conn.channel()
    ch.queue_declare(queue=FILA, durable=True)
    ch.basic_qos(prefetch_count=1)
    ch.basic_consume(queue=FILA, on_message_callback=processar)
    logger.info("Worker conectado. Aguardando mensagens na fila '%s' ...", FILA)
    ch.start_consuming()


def main():
    while True:
        try:
            conectar_e_consumir()
        except pika.exceptions.AMQPConnectionError as exc:
            logger.warning("RabbitMQ indisponível (%s). Reconectando em %ds ...", exc, RETRY_DELAY)
            time.sleep(RETRY_DELAY)
        except KeyboardInterrupt:
            logger.info("Worker encerrado pelo usuário.")
            break


if __name__ == "__main__":
    main()
