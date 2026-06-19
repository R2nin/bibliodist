FROM python:3.12-slim

# worker/worker.py faz: BASE_DIR = Path(__file__).parent.parent / "api-web"
# Logo api-web precisa estar em /app/api-web e worker.py em /app/worker/
WORKDIR /app/worker

COPY worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY worker/ .
COPY api-web/ /app/api-web/

CMD ["python", "worker.py"]
