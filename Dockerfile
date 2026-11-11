FROM python:3.14-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY api ./api

# Commit the image was built from; set by CI with --build-arg GIT_SHA=<full sha>
ARG GIT_SHA=unknown
ENV GIT_SHA=$GIT_SHA

ENV PATH="/app/.venv/bin:$PATH"

# Run as a non-root user (numeric UID so Kubernetes can verify it)
RUN useradd --system --uid 10001 --no-create-home app
USER 10001

EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]