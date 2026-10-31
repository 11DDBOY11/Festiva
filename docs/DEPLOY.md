# Festiva AI — Production Deployment Guide (Render Blueprint)

Festiva AI is fully configured for deployment on **Render** via Infrastructure-as-Code using the root [`render.yaml`](../render.yaml) Blueprint:
1. **Managed PostgreSQL Database (`festiva-db`)**: Render Postgres Free Tier (PostgreSQL 16).
2. **Backend Web Service (`festiva-backend`)**: Containerized FastAPI service running as a non-root user (`festiva`, UID 1000) listening on dynamic `$PORT`, with automated migrations, seed script, and `/health/ready` probe.
3. **Frontend Static Site (`festiva-frontend`)**: CDN-hosted React 18 / Vite SPA with SPA rewrite `/* -> /index.html` and strict HTTP security headers (CSP, HSTS, X-Frame-Options).

---

## 1. Quickstart: 1-Click Render Blueprint Deployment

1. **Push to GitHub**: Ensure your latest changes are on `main` in your public repository (`https://github.com/11DDBOY11/Festiva`).
2. **Open Render Dashboard**: Navigate to [dashboard.render.com](https://dashboard.render.com) and click **New +** $\rightarrow$ **Blueprint**.
3. **Connect Repository**: Select `11DDBOY11/Festiva`.
4. **Render Parses `render.yaml`**: Render will detect:
   - `festiva-db` (PostgreSQL Database)
   - `festiva-backend` (Docker Web Service)
   - `festiva-frontend` (Static Site)
5. **Set Required Secrets (`sync: false`)**:
   Render will prompt you to enter values for uncommitted environment variables:
   - `JWT_SECRET`: Generate a secure 32+ character random secret (e.g. `openssl rand -hex 32`).
   - `GROQ_API_KEY`: Your Groq API key (`gsk_...`).
   - `DEMO_ACCOUNT_PASSWORD`: Password for the seeded demo account (`demo@festiva.ai`).
   - `CORS_ORIGINS`: Frontend URL (e.g. `https://festiva-frontend.onrender.com`).
   - `VITE_API_URL`: Backend URL (e.g. `https://festiva-backend.onrender.com`).
6. **Click Apply**: Render provisions the database, builds the container image, executes schema migrations, seeds the initial data, and deploys the static frontend.

---

## 2. Environment Variables Reference

| Variable | Service | Required | Default / Format | Description |
| :--- | :--- | :---: | :--- | :--- |
| `ENV` | `festiva-backend` | Yes | `production` | Enables production security enforcement, disabling OpenAPI docs and strict JWT checks. |
| `DATABASE_URL` | `festiva-backend` | Yes | `fromDatabase(festiva-db)` | Injected automatically by Render Blueprint from the managed Postgres service. |
| `JWT_SECRET` | `festiva-backend` | Yes | *(Secret, sync: false)* | Key for signing HS256 auth tokens. Server **refuses startup** if set to a dev placeholder in `production`. |
| `GROQ_API_KEY` | `festiva-backend` | Yes | *(Secret, sync: false)* | API key for Groq Llama-3.3-70B model. If unset or rate-limited, system falls back to deterministic rule engine. |
| `DEMO_ACCOUNT_PASSWORD`| `festiva-backend` | No | *(Auto-generated or custom)* | Password for pre-seeded account `demo@festiva.ai`. |
| `CORS_ORIGINS` | `festiva-backend` | Yes | `https://festiva-frontend.onrender.com` | Strict CORS allowlist (comma-separated origins). |
| `VITE_API_URL` | `festiva-frontend` | Yes | `https://festiva-backend.onrender.com` | Backend URL used by frontend API client. |

---

## 3. Database & Migrations

### Automated Lifecycle on Every Deploy
The backend container runs this command on start:
```bash
alembic upgrade head && python -m app.db.seed && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```
1. **Alembic Migrations (`alembic upgrade head`)**:
   - `001_initial_schema.py`: Tables `users`, `events`, `plans`, `budget_rules`.
   - `002_add_change_proposals.py`: Table `proposed_changes` for human-in-the-loop review.
   - `003_add_plan_versions.py`: Table `plan_versions` with immutability and version history.
   - `004_add_vendor_directory.py`: Table `vendor_directory` with 20 sample vendors.
2. **Idempotent Seeding (`python -m app.db.seed`)**:
   - Loads 15 deterministic budget allocation rules from `data/budget_rules.csv`.
   - Loads 20 curated Bengaluru vendors from `data/vendors.json`.
   - Creates the verified demo account (`demo@festiva.ai`) with Birthday Party Plan v1 and v2 (reduced décor by ₹10,000 to Contingency). If already seeded, gracefully skips.

### Render Postgres & pgvector Findings
- **Support**: Render PostgreSQL supports `pgvector` on Postgres 13+ via `CREATE EXTENSION IF NOT EXISTS vector;`.
- **Free Tier Constraints**: Render's Free Postgres is designed for ephemeral preview/evaluation and **expires after 30 days** with 1 GB storage limit and 256 MB RAM.
- **Festiva Implementation**: Festiva's core architecture (rules engine, budget calculator, timeline builder, diff engine, vendor matching, and JWT security) operates purely on relational models (`UUID`, `TIMESTAMP`, `DECIMAL`, `JSONB`), requiring zero external vector extensions for production readiness.

---

## 4. Free-Tier Cold Starts & Resilience

Render Free Tier spins down web services after 15 minutes of inactivity. When awoken:
1. **Cold Start Spin-Up**: The first request may take 40–50 seconds while Render boots the container.
2. **Frontend Auto-Retry Banner**:
   - `frontend/src/lib/api.ts` intercepts `502`, `503`, `504` status codes and network disconnects.
   - Retries automatically for up to **60 seconds** (12 attempts $\times$ 5-second interval).
   - Displays an accessible status banner: `Waking up the server... Render free tier spins down after inactivity (attempt X/12, ~60s). Please hold on...`
   - Once connection is established, the banner dismisses and the app resumes seamlessly.
3. **Proxy IP Rate Limiting**:
   - Rate limiters in `app/core/rate_limit.py` inspect `X-Forwarded-For` from Render's reverse proxy so rate limits apply per client IP rather than the Render internal router.

---

## 5. Troubleshooting & Verification

### Checking Health
- **Shallow Health**: `GET /health` $\rightarrow$ `{"status": "ok"}` (Load balancer probe).
- **Readiness Health**: `GET /health/ready` $\rightarrow$ `{"status": "ready", "database": "connected"}` (Verifies live database connection with `SELECT 1`).

### Checking Security Headers
```bash
curl -I https://festiva-frontend.onrender.com
```
Expected headers:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`
- `Content-Security-Policy: default-src 'self'; ...`

### Startup Refusal on Default Secrets
If the service logs report:
```
RuntimeError: JWT_SECRET cannot be a default value in 'production' environment.
```
Update `JWT_SECRET` in the Render Environment tab with a cryptographically secure random string.
