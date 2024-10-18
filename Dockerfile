FROM python:3.11.10-slim AS base-image

ENV PYTHONUNBUFFERED=1 \
  PIP_NO_CACHE_DIR=1 \
  PIP_DISABLE_PIP_VERSION_CHECK=1 \
  POETRY_VERSION=1.8.4 \
  CLOUD_CONNECTOR_SERVICE_NAME=${CLOUD_CONNECTOR_SERVICE_NAME}

WORKDIR /app

COPY poetry.lock pyproject.toml ./
RUN pip install "poetry==$POETRY_VERSION"

# Install all dependencies into /opt/venv
# so that we can copy these resources between
# build stages
RUN poetry config virtualenvs.path /opt/venv

##
## Intermediate image contains build-essential for installing
## google-cloud-profiler's dependencies
##
FROM base-image AS install-image

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY scripts /app/scripts

RUN poetry install --no-interaction --no-ansi --no-cache --no-root --only main

##
## Final image copies dependencies from install-image
##
FROM base-image AS final

COPY --from=install-image /opt/venv /opt/venv

COPY ai_gateway/ ai_gateway/

# Environment variable TRANSFORMERS_CACHE controls where files are downloaded
COPY --from=install-image /app/scripts/bootstrap.py .
RUN poetry run python bootstrap.py

# Opening a default port for running it as a service container in CI/CD pipelines.
EXPOSE 5052

COPY --from=install-image /app/scripts/run.sh .
CMD ["./run.sh"]
