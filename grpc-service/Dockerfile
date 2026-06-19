FROM python:3.12-slim

# grpc-service/server.py faz: BASE_DIR = Path(__file__).parent.parent / "api-web"
# Logo api-web precisa estar em /app/api-web e server.py em /app/grpc-service/
WORKDIR /app/grpc-service

COPY grpc-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY grpc-service/ .
COPY api-web/ /app/api-web/

CMD ["python", "server.py"]
