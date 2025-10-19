FROM python:3.13-slim-bookworm

# RUN apt update -y && \
#     apt --no-install-recommends -y install gcc g++ && \
#     apt clean -y && rm -rf /var/lib/apt/lists/*

# Setting up uv environment
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=./snapshot/uv.lock,target=uv.lock \
    --mount=type=bind,source=./snapshot/pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

COPY ./snapshot/snapshot_data_*.py .

# Keep the image alive when testing but do nothing when used as init source
CMD ["sh", "-c", "echo 'Snapshot image loaded. Use this image to initialize volumes on other systems.' && tail -f /dev/null"]
