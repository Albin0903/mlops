# etape 1 : construction et dependances
FROM python:3.14-slim-bookworm AS builder

# definition des variables d'environnement pour la construction
ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1 \
  PIP_NO_CACHE_DIR=1 \
  PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /install

# installation des dependances systeme si necessaire (ex: build-essential)
# run apt-get update && apt-get install -y --no-install-recommends gcc g++

COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt

# etape 2 : image finale
FROM python:3.14-slim-bookworm

# securite : definition d'un utilisateur non-root
RUN groupadd -r mlops && useradd -r -g mlops -s /sbin/nologin -d /app mlops

WORKDIR /app

# copie des dependances depuis le builder
COPY --from=builder /install /usr/local

# copie du code de l'application
COPY --chown=mlops:mlops app/ /app/app/

# variables d'environnement pour l'execution
ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1 \
  PYTHONPATH=/app

# passage a l'utilisateur non-root
USER mlops

# metadata
LABEL maintainer="Albin" \
  version="0.1.0" \
  description="api professionnelle d'analyse de code par llm"

# exposition du port
EXPOSE 8000

# healthcheck (verification de sante)
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health/ || exit 1

ENTRYPOINT ["uvicorn", "app.main:app"]
CMD ["--host", "0.0.0.0", "--port", "8000"]
