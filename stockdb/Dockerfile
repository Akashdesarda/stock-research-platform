FROM python:3.13-slim

RUN apt update -y && apt upgrade && \
    apt --no-install-recommends -y install gcc g++ && \
    apt purge -y && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Setting up uv environment
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

# Copy the project into the image
COPY stockdb .

# Sync the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

EXPOSE 8000
CMD ["uv", "run", "main:app", "--host", "0.0.0.0", "--port", "8000"]