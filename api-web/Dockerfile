FROM python:3.12-slim

WORKDIR /app

COPY api-web/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api-web/ .

# Coleta estáticos (whitenoise) — sem acesso ao banco, usa SECRET_KEY padrão
RUN python manage.py collectstatic --noinput || true

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2"]
