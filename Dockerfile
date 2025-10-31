# Dockerfile ottimizzato per Google Cloud Run
# Usa un'immagine Python ufficiale come base
FROM python:3.11-slim as builder

# Imposta variabili d'ambiente per Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Installa Poetry
RUN pip install poetry

# Configura Poetry per non creare un ambiente virtuale
ENV POETRY_VENV_IN_PROJECT=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Imposta la directory di lavoro
WORKDIR /app

# Copia i file di configurazione Poetry e README
COPY pyproject.toml poetry.lock* README.md ./

# Installa le dipendenze
RUN poetry install --only=main && rm -rf $POETRY_CACHE_DIR

# Stage di produzione
FROM python:3.11-slim as production

# Imposta variabili d'ambiente
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

# Crea un utente non-root per sicurezza
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Imposta la directory di lavoro
WORKDIR /app

# Copia l'ambiente virtuale dal builder
COPY --from=builder /app/.venv /app/.venv

# Copia il codice dell'applicazione
COPY app/ ./app/
COPY .env.example ./.env

# Cambia proprietario dei file all'utente appuser
RUN chown -R appuser:appuser /app

# Cambia all'utente non-root
USER appuser

# Esponi la porta (Cloud Run usa la variabile PORT)
EXPOSE 8080

# Comando per avviare l'applicazione
# Cloud Run imposta automaticamente la variabile PORT
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]