FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Systemowe zależności absolutnie niezbędne (np. xmlsec, psycopg2, libmagic – dostosuj do projektu)
RUN apt-get update && apt-get install -y \
    libxmlsec1-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Jeżeli zostajesz przy pipenv:
COPY Pipfile Pipfile.lock ./
RUN pip install --no-cache-dir pipenv \
    && PIPENV_VENV_IN_PROJECT=1 pipenv sync --system --deploy

# Reszta projektu
COPY . .

# Cloud Run nasłuchuje na $PORT
ENV PORT=8080
CMD ["gunicorn", "mcod.wsgi:application", "--bind", "0.0.0.0:8080"]
