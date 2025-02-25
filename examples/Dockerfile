FROM ghcr.io/astral-sh/uv:python3.13-bookworm
ARG APP_DIR
ENV APP_MODULE=${APP_DIR}


RUN mkdir -p "/opt/app"
WORKDIR /opt/app
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project 
COPY  . .

# Sync the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --compile-bytecode

EXPOSE 8080

ENTRYPOINT uv run python -m ${APP_MODULE}
