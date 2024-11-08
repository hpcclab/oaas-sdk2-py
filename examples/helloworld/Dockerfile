FROM python:3.12-slim
ARG APP_DIR
ENV APP_MODULE=${APP_DIR}

RUN pip install poetry \
    && mkdir -p "/opt/app"
WORKDIR /opt/app
COPY pyproject.toml poetry.lock ./
RUN poetry install \
    && poetry cache clear --all .
COPY  ./${APP_MODULE} ./${APP_MODULE}

EXPOSE 8080

ENTRYPOINT poetry run python -m ${APP_MODULE}
