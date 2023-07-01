FROM python:3.9.16-slim AS base-image

ENV PYTHONUNBUFFERED=1 \
  PIP_NO_CACHE_DIR=1 \
  PIP_DISABLE_PIP_VERSION_CHECK=1 \
  POETRY_VERSION=1.5.1

WORKDIR /app

COPY ./scripts/ /scripts/

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

RUN apt-get update
RUN apt-get install -y build-essential git curl
RUN curl -sL https://deb.nodesource.com/setup_16.x | bash -
RUN apt-get update
RUN apt-get install -y nodejs

COPY poetry.lock pyproject.toml ./
COPY ./scripts /scripts/

RUN poetry install --no-interaction --no-ansi --no-cache --no-root --only main

# Build tree-sitter library for the grammars supported
COPY --from=base-image /scripts/ /tmp
RUN poetry run python /tmp/prepare-tokenizer.py
RUN poetry run python /tmp/build-tree-sitter-lib.py

## 
## Final image copies dependencies from install-image
## 
FROM base-image as final

COPY --from=install-image /opt/venv /opt/venv
COPY --from=install-image lib/*.so ./lib/

COPY poetry.lock pyproject.toml ./
COPY codesuggestions/ codesuggestions/

CMD ["poetry", "run", "codesuggestions"]
