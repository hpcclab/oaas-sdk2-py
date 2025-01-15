FROM python:3.12-slim

RUN pip install poetry \
    && mkdir -p "/app" \
    && mkdir -p "/opt/venvs"

WORKDIR /app
# COPY pyproject.toml poetry.lock ./
# RUN poetry install 
