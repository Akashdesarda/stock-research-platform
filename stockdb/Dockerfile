FROM python:3.13-slim-bookworm

RUN apt update -y && \
    apt --no-install-recommends -y install gcc g++ git && \
    apt clean -y && rm -rf /var/lib/apt/lists/*

WORKDIR /stockdb

# Setting up uv environment
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=./stockdb/uv.lock,target=uv.lock \
    --mount=type=bind,source=./stockdb/pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

# Copy the project into the image
COPY ./stockdb .

# Sync the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

EXPOSE 8000
CMD ["uv", "run","main.py"]