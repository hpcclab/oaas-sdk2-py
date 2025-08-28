## Multi-stage image to install oaas-sdk2-py from source (including Rust ext)

# --- Builder: compiles Rust extension and installs into a virtualenv ---
FROM python:3.12-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH=/root/.local/bin:/root/.cargo/bin:$PATH

RUN set -eux; \
    apt-get update; \
    # Build dependencies for Rust and common native Python deps
            apt-get install -y --no-install-recommends \
                build-essential pkg-config libssl-dev curl ca-certificates git protobuf-compiler; \
    rm -rf /var/lib/apt/lists/*

# Install Rust toolchain (minimal) for maturin builds
RUN set -eux; \
    curl -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal --default-toolchain stable; \
    rustc --version; cargo --version

# Create an isolated venv for the runtime payload
RUN python -m venv /venv

WORKDIR /src
# Copy the project source (keep Docker cache efficient by separating manifests)
COPY pyproject.toml uv.lock README.md /src/
COPY oaas_sdk2_py/ /src/oaas_sdk2_py/
COPY oprc-py/ /src/oprc-py/
COPY deploy/oaas-run.sh /src/deploy/oaas-run.sh

# Build and install from source into /venv
# 1) Install local Rust extension (oprc-py) so the top-level dep constraint is satisfied locally
# 2) Install the top-level package (this repo)
RUN set -eux; \
    /venv/bin/python -m pip install --upgrade pip wheel; \
    /venv/bin/pip install --no-cache-dir ./oprc-py; \
    /venv/bin/pip install --no-cache-dir .


# --- Runtime: slim Python with only the venv and entrypoint ---
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_DIR=/app \
    PATH=/venv/bin:$PATH

# Runtime libs commonly needed by compiled wheels (openssl, certificates)
RUN set -eux; \
        apt-get update; \
        apt-get install -y --no-install-recommends \
            ca-certificates libssl3 libgcc-s1 libstdc++6 zlib1g; \
        rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy entrypoint and the built virtualenv from builder
COPY --from=builder /src/deploy/oaas-run.sh /usr/local/bin/oaas-run
COPY --from=builder /venv /venv

# Non-root user
RUN set -eux; \
    groupadd -g 10001 app; \
    useradd -m -u 10001 -g 10001 -s /bin/sh app; \
    mkdir -p "$APP_DIR"; \
    chown -R app:app "$APP_DIR" /usr/local/bin/oaas-run /venv; \
    chmod +x /usr/local/bin/oaas-run

EXPOSE 8080
USER app
ENTRYPOINT ["/usr/local/bin/oaas-run"]
CMD []
