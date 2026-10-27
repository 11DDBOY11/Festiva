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
| `make eval`   | Run the eval harness (Phase 3/6)   |

## Implementation Roadmap (12 Phases)

| Phase | Focus | Key Deliverables & Exit Criteria |
| :--- | :--- | :--- |
| **Phase 1** | Foundation & Auth | Monorepo, Postgres + pgvector, FastAPI, JWT auth with token rotation, events CRUD, React PWA shell, CI with lint and tests, LLMClient interface. |
| **Phase 2** | Full Schema & Seed | Full schema migrations, budget rules engine (wedding/birthday/community), 20 sample Mangaluru vendors, Pydantic models & validators. |
| **Phase 3** | Brief Parser & Evals | Structured brief parser, clarifying-question loop, plan JSON schema, 10 eval briefs (live + replay), UI brief intake. |
| **Phase 4** | Plan Generation & UI | Deterministic budget engine, timeline generator, vendor category checklist, full plan viewer UI. |
| **Phase 5** | Plan Versioning & MVP | Immutable plan_versions, proposed_changes diff viewer (accept/reject), chat refinement, PDF export. MVP Birthday demo runs end-to-end. |
| **Phase 6** | Evaluation Harness | Complete 25-brief eval suite with accuracy/repair metrics; CI regression harness. |
| **Phase 7** | RAG Ingestion Pipeline| Chunking & embedding pipeline, CLI ingestion, pgvector index, metadata-filtered retrieval, 50+ vendors loaded. recall@5 >= 80%. |
| **Phase 8** | Vendor Features | Vendor shortlist & comparison UI, grounding validators, price honesty verification. Grounding = 100%. |
| **Phase 9** | Operations & Guests | Operational tracking: expenses, tasks with owners, guests & RSVP tracking, vendor message drafting. |
| **Phase 10**| Background Jobs | Email reminders for due tasks, read-only share link for family, RBAC. |
| **Phase 11**| Hardening & Security | Rate limits, input sanitizing, prompt-injection tests, error states, cost tracking. |
| **Phase 12**| Production & Demo | Public deployment, seed data, final demo video, architecture documentation, before/after eval report. |

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
