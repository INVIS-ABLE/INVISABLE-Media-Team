# INVISABLE® AI Media Agency OS — developer shortcuts
.PHONY: help install test lint fmt run up up-all down logs demo

help:
	@echo "INVISABLE OS"
	@echo "  make install   install the core package (dev extras)"
	@echo "  make test      run the test suite"
	@echo "  make lint      ruff + mypy"
	@echo "  make run       run the API locally (uvicorn --reload)"
	@echo "  make demo      run a tournament from the CLI"
	@echo "  make up        bring up the minimal stack (core+postgres+chroma)"
	@echo "  make up-all    bring up the full stack (all profiles)"
	@echo "  make down      stop the stack"

install:
	cd core && pip install -e ".[dev]"

test:
	cd core && pytest -q

lint:
	cd core && ruff check invisable_os tests && mypy invisable_os || true

fmt:
	cd core && ruff check --fix invisable_os tests

run:
	cd core && uvicorn invisable_os.main:app --reload --port 8080

demo:
	cd core && python -m invisable_os.demo

up:
	docker compose up -d core postgres chroma

up-all:
	docker compose --profile llm --profile media --profile publish --profile ops up -d

down:
	docker compose down

logs:
	docker compose logs -f core
