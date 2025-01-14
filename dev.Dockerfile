FROM python:3.12-slim
RUN pip install poetry \
    && mkdir -p "/app"

USER 1000
WORKDIR /app
# COPY pyproject.toml poetry.lock ./
# RUN poetry install 
