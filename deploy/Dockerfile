# Single-file runner for oaas-sdk2-py (minimal layers, no embedded scripts)
FROM python:3.12-slim

# Optionally pin SDK version at build time: --build-arg OAAS_SDK2_PY_VERSION=0.1.0
ARG OAAS_SDK2_PY_VERSION

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_DIR=/app

WORKDIR /app

# Copy entrypoint (kept as a separate file, not embedded in Dockerfile)
COPY oaas-run.sh /usr/local/bin/oaas-run

# Single RUN to reduce layers: create non-root user, set permissions, install SDK
RUN set -eux; \
    groupadd -g 10001 app; \
    useradd -m -u 10001 -g 10001 -s /bin/sh app; \
    mkdir -p "$APP_DIR"; \
    chown -R app:app "$APP_DIR" /usr/local/bin/oaas-run; \
    chmod +x /usr/local/bin/oaas-run; \
    python -m pip install --upgrade pip; \
    python -m pip install --no-cache-dir "oaas-sdk2-py${OAAS_SDK2_PY_VERSION:+==${OAAS_SDK2_PY_VERSION}}"

EXPOSE 8080
USER app
ENTRYPOINT ["/usr/local/bin/oaas-run"]
CMD []
