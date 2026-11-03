# ---- build stage ----
FROM python:3.12-slim AS build
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY src ./src
COPY config ./config
COPY demo_bundle ./demo_bundle
COPY models ./models
RUN uv sync --locked --no-dev --no-editable

# ---- runtime stage ----
FROM python:3.12-slim
RUN useradd -m -u 1000 app
WORKDIR /app
COPY --from=build --chown=app:app /app /app
ENV PATH="/app/.venv/bin:$PATH" PORT=8080 ORB_DATA_DIR=/tmp/orbitalis
USER app
EXPOSE 8080
CMD ["sh", "-c", "uvicorn orbitalis.main:app --host 0.0.0.0 --port ${PORT}"]
