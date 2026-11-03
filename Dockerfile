FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY clifford ./clifford
COPY alembic.ini ./
COPY migrations ./migrations
COPY scripts ./scripts
RUN uv sync --frozen --no-dev && useradd --uid 10001 --create-home clifford && mkdir -p data && chown -R clifford:clifford /app
USER clifford
EXPOSE 8000
CMD ["sh", "-c", ".venv/bin/alembic upgrade head && exec .venv/bin/uvicorn clifford.api:app --host 0.0.0.0 --port 8000 --workers 1 --ws-max-size 128000 --no-access-log"]
