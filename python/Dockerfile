FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.10.10 /uv /usr/local/bin/uv
WORKDIR /app
COPY python/pyproject.toml python/uv.lock ./
RUN uv sync --frozen --no-dev
COPY python/ ./
ENV PYTHONPATH=/app
USER 65532:65532
ENTRYPOINT ["/app/.venv/bin/python", "labs/06/main.py"]
