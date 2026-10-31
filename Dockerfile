# Plakzicht Mail-server als container (Unraid). Gegevens in /data; poort 8765.
FROM python:3.12-slim

ARG VERSION=ontwikkel
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PLAKZICHT_DOCKER=1 \
    PLAKZICHT_DATA=/data \
    PLAKZICHT_PORT=8765 \
    PLAKZICHT_VERSION=${VERSION} \
    TZ=Europe/Amsterdam

RUN apt-get update && apt-get install -y --no-install-recommends tzdata && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py graph.py mscache.py plakzicht.py ./
COPY ui ./ui

# Unraid: standaard gebruiker nobody:users (99:100), zodat de bestanden in appdata goed staan
RUN mkdir -p /data && chown 99:100 /data
USER 99:100
VOLUME /data
EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8765/health', timeout=4).status == 200 else 1)"

LABEL org.opencontainers.image.title="Plakzicht Mail" \
      org.opencontainers.image.description="Gedeelde mail voor de stickerwinkel, gekoppeld aan Microsoft 365 en Plakzicht" \
      org.opencontainers.image.source="https://github.com/Seipenbusch/plakzicht-mail"

CMD ["python", "app.py", "--server", "--host", "0.0.0.0"]
