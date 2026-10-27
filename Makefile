.PHONY: dev test lint migrate demo eval

dev:
	docker compose up -d
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	cd backend && python -m pytest tests/ -v

lint:
	cd backend && ruff check app/ tests/

format:
	cd backend && ruff format app/ tests/

migrate:
	cd backend && alembic upgrade head

demo:
	@echo "Demo script not yet implemented (Phase 6)"

eval:
	python backend/tests/evals/eval_brief_parser.py --replay

eval-live:
	python backend/tests/evals/eval_brief_parser.py --live

