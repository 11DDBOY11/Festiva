# Contributing to Festiva AI

Thank you for your interest in contributing to Festiva AI! Festiva AI is an autonomous event planning co-pilot tailored for celebration planning in Mangaluru, India.

## Code of Conduct & Principles

1. **Security First**: Object-level authorization on every endpoint. Always return 404 for resources not owned by the requester to prevent user enumeration.
2. **Hosting Safety**: Never introduce breaking changes to database schemas, environment variable names, or deployment configuration.
3. **Repository Cleanliness**: Keep repository size under 10 MB. Never commit binary media, recordings, virtual environments, or compiled assets to git.

## Local Development Setup

### Backend (Python 3.11+)

```bash
cd backend
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run migrations
alembic upgrade head

# Seed initial vendor dataset
python -m app.db.seed

# Run dev server
uvicorn app.main:app --reload --port 8000
```

### Frontend (Node 20+)

```bash
cd frontend
npm install
npm run dev
```

## Testing & Quality Checks

Run all verification commands before submitting changes:

```bash
# Backend linting & formatting
ruff check app/ tests/
ruff format --check app/ tests/

# Backend unit & integration tests
pytest tests/

# Frontend typecheck & production build
cd frontend
npm run test
npm run build
```
