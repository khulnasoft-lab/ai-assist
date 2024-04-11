ROOT_DIR := $(shell pwd)
TESTS_DIR := ${ROOT_DIR}/tests
LINTS_DIR := ${ROOT_DIR}/lints
AI_GATEWAY_DIR := ${ROOT_DIR}/ai_gateway

LINT_WORKING_DIR ?= ${AI_GATEWAY_DIR} \
	${ROOT_DIR}/scripts \
	${TESTS_DIR} \
	${LINTS_DIR} \

COMPOSE_FILES := -f docker-compose.dev.yaml
ifneq (,$(wildcard docker-compose.override.yaml))
COMPOSE_FILES += -f docker-compose.override.yaml
endif
COMPOSE := docker-compose $(COMPOSE_FILES)
TEST_PATH_ARG ?= 

.PHONY: develop-local
develop-local:
	$(COMPOSE) up --build --remove-orphans

.PHONY: test-local
test-local:
	$(COMPOSE) run -v "$(ROOT_DIR):/app" api bash -c 'poetry install --with test && poetry run pytest $(TEST_PATH_ARG)'

.PHONY: lint-local
lint-local:
	$(COMPOSE) run -v "$(ROOT_DIR):/app" api bash -c 'poetry install --only lint && poetry run flake8 ai_gateway'

.PHONY: clean
clean:
	$(COMPOSE) rm -s -v -f

.PHONY: install-lint-deps
install-lint-deps:
	@echo "Installing lint dependencies..."
	@poetry install --only lint

.PHONY: black
black: install-lint-deps
	@echo "Running black format..."
	@poetry run black ${LINT_WORKING_DIR}

.PHONY: isort
isort: install-lint-deps
	@echo "Running isort format..."
	@poetry run isort ${LINT_WORKING_DIR}

.PHONY: format
format: black isort

.PHONY: lint
lint: flake8 check-black check-isort check-pylint

.PHONY: flake8
flake8: install-lint-deps
	@echo "Running flake8..."
	@poetry run flake8 ${LINT_WORKING_DIR}

.PHONY: check-black
check-black: install-lint-deps
	@echo "Running black check..."
	@poetry run black --check ${LINT_WORKING_DIR}

.PHONY: check-isort
check-isort: install-lint-deps
	@echo "Running isort check..."
	@poetry run isort --check-only ${LINT_WORKING_DIR}

.PHONY: check-pylint
check-pylint: install-lint-deps
	@echo "Running pylint check..."
	@poetry run pylint ${LINT_WORKING_DIR}

.PHONY: install-test-deps
install-test-deps:
	@echo "Installing test dependencies..."
	@poetry install --with test

.PHONY: test
test: install-test-deps
	@echo "Running tests..."
	@poetry run pytest

.PHONY: test-watch
test-watch: install-test-deps
	@echo "Running tests in watch mode..."
	@poetry run ptw .

.PHONY: test-coverage
test-coverage: install-test-deps
	@echo "Running tests with coverage..."
	@poetry run pytest --cov=ai_gateway --cov=lints --cov-report term --cov-report html

.PHONY: test-coverage-ci
test-coverage-ci: install-test-deps
	@echo "Running tests with coverage on CI..."
	@poetry run pytest --cov=ai_gateway --cov=lints --cov-report term --cov-report xml:.test-reports/coverage.xml --junitxml=".test-reports/tests.xml"
