.PHONY: dev test lint format migrate demo eval eval-live eval-plan

ifeq ($(OS),Windows_NT)
    PYTHON ?= $(if $(wildcard backend/.venv/Scripts/python.exe),backend/.venv/Scripts/python.exe,python)
    RUFF ?= $(if $(wildcard backend/.venv/Scripts/ruff.exe),backend/.venv/Scripts/ruff.exe,ruff)
    ALEMBIC ?= $(if $(wildcard backend/.venv/Scripts/alembic.exe),backend/.venv/Scripts/alembic.exe,alembic)
    UVICORN ?= $(if $(wildcard backend/.venv/Scripts/uvicorn.exe),backend/.venv/Scripts/uvicorn.exe,uvicorn)
else
    PYTHON ?= $(if $(wildcard backend/.venv/bin/python),backend/.venv/bin/python,python3)
    RUFF ?= $(if $(wildcard backend/.venv/bin/ruff),backend/.venv/bin/ruff,ruff)
    ALEMBIC ?= $(if $(wildcard backend/.venv/bin/alembic),backend/.venv/bin/alembic,alembic)
    UVICORN ?= $(if $(wildcard backend/.venv/bin/uvicorn),backend/.venv/bin/uvicorn,uvicorn)
endif

dev:
	docker compose up -d
	cd backend && $(UVICORN) app.main:app --reload --host 0.0.0.0 --port 8000

test:
	$(PYTHON) -m pytest backend/tests/ -v

lint:
	$(RUFF) check backend/app/ backend/tests/

format:
	$(RUFF) format backend/app/ backend/tests/

migrate:
	cd backend && $(ALEMBIC) upgrade head

demo:
	@echo "Demo script not yet implemented (Phase 6)"

eval:
	$(PYTHON) backend/tests/evals/eval_brief_parser.py --replay
	$(PYTHON) backend/tests/evals/eval_plan_generator.py --replay

eval-live:
	$(PYTHON) backend/tests/evals/eval_brief_parser.py --live
	$(PYTHON) backend/tests/evals/eval_plan_generator.py

eval-plan:
	$(PYTHON) backend/tests/evals/eval_plan_generator.py --replay
