# ── Backend Flask ──────────────────────────────────────────────────────────
FROM python:3.11-slim

# Evita arquivos .pyc e garante logs em tempo real
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instala dependências do sistema necessárias para psycopg2
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Instala dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do código
COPY . .

EXPOSE 5000

# Roda com gunicorn em produção (mais robusto que flask dev server)
CMD ["python", "-m", "gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]
