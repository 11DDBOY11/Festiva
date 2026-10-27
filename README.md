# Festiva AI

A budget-aware, RAG-powered celebration and event planning copilot for Mangaluru.

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.12+
- Node.js 20+ (frontend, Phase 2)

### Development Setup

1. Clone the repo and create your environment file:

   ```bash
   cp .env.example backend/.env
   # Edit backend/.env with your values
   ```

2. Start infrastructure (Postgres + Redis):

   ```bash
   docker compose up -d
   ```

3. Install backend dependencies:

   ```bash
   cd backend
   pip install -r requirements.txt
   ```

4. Run database migrations:

   ```bash
   make migrate
   ```

5. Start the API server:

   ```bash
   cd backend
   uvicorn app.main:app --reload
   ```

6. Open http://localhost:8000/docs for interactive API docs.

## Commands

| Command       | Description                        |
| ------------- | ---------------------------------- |
| `make dev`    | Start infra + API server           |
| `make test`   | Run pytest                         |
| `make lint`   | Run Ruff linter                    |
| `make migrate`| Apply Alembic migrations           |
| `make demo`   | Run the demo script (Phase 6)      |
| `make eval`   | Run the eval harness (Phase 3)     |

## Architecture

```
React + Vite + Tailwind (PWA shell)
         |  REST / SSE streaming
FastAPI  (auth, events, plans, chat)
         |
  +------+--------------------+--------------------+
  | Planner service           | Deterministic core | Retrieval service  |
  | Function-calling agent,   | budget rules,      | pgvector search +  |
  | structured output         | timeline, checks   | metadata filters   |
  +------+--------------------+--------------------+
         |
  PostgreSQL (+ pgvector)   Redis + RQ (reminders, PDF export)
```

## License

Private — portfolio project.
