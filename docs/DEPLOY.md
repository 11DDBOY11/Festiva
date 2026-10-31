# Festiva AI — Production Deployment Guide (Render Blueprint)

Festiva AI is configured for one-click deployment on **Render** via Infrastructure-as-Code using the root [`render.yaml`](../render.yaml) Blueprint:
1. **Managed PostgreSQL Database (`festiva-db`)**: Render Postgres Free Tier (PostgreSQL 16 with native `pgvector` support).
2. **Backend Web Service (`festiva-backend`)**: Containerized FastAPI service running as a non-root user (`festiva`, UID 1000) listening on dynamic `$PORT`, with automated migrations, idempotent seed script, and `/health/ready` probe.
3. **Frontend Static Site (`festiva-frontend`)**: CDN-hosted React 18 / Vite SPA with SPA rewrite `/* -> /index.html` and strict HTTP security headers (CSP, HSTS, X-Frame-Options).

---

## 1. Exact First-Deploy Order & Workflow

Because the frontend and backend require each other's live public domain names for CORS and API communication, follow this exact sequence on initial setup:

### Step 1: Create Blueprint
1. Open [dashboard.render.com](https://dashboard.render.com).
2. Click **New +** $\rightarrow$ **Blueprint**.
3. Connect your repository: `https://github.com/11DDBOY11/Festiva` (`main` branch).
4. Render will parse `render.yaml` and provision three resources:
   - `festiva-db` (Database)
   - `festiva-backend` (Docker Web Service)
   - `festiva-frontend` (Static Site)

### Step 2: Note Assigned Service URLs
Once the services are created in your Render dashboard, note their generated URLs:
- **Backend Service URL:** e.g. `https://festiva-backend-xxxx.onrender.com`
- **Frontend Static Site URL:** e.g. `https://festiva-frontend-xxxx.onrender.com`

### Step 3: Configure Environment Variables
Navigate to each service's **Environment** tab:

1. **On `festiva-backend`:**
   - `ENV`: `production`
   - `DATABASE_URL`: Automatically linked via `fromDatabase: festiva-db`
   - `JWT_SECRET`: A secure 32+ character random secret (e.g. `openssl rand -hex 32`). *The server strictly refuses startup if left as default.*
   - `GROQ_API_KEY`: Your Groq API key (`gsk_...`).
   - `DEMO_ACCOUNT_PASSWORD`: Password for the seeded demo user (`DemoFestiva2026!`).
   - `CORS_ORIGINS`: Set to your **Frontend URL** from Step 2 (e.g. `https://festiva-frontend-xxxx.onrender.com`).

2. **On `festiva-frontend`:**
   - `VITE_API_URL`: Set to your **Backend URL** from Step 2 (e.g. `https://festiva-backend-xxxx.onrender.com`).

### Step 4: Redeploy Frontend
Vite bakes `VITE_API_URL` into static assets at build time. After saving `VITE_API_URL`:
- Go to `festiva-frontend` $\rightarrow$ click **Manual Deploy** $\rightarrow$ **Clear build cache & deploy**.
- Once built, your frontend is fully linked to the live backend.

---

## 2. Environment Variables Reference

| Variable | Service | Required | Format / Source | Description |
| :--- | :--- | :---: | :--- | :--- |
| `ENV` | `festiva-backend` | Yes | `production` | Enables production security enforcement, disabling OpenAPI docs and strict JWT checks. |
| `DATABASE_URL` | `festiva-backend` | Yes | `fromDatabase: festiva-db` | Injected automatically by Render Blueprint from the managed Postgres service. |
| `JWT_SECRET` | `festiva-backend` | Yes | 32+ character random string | Key for signing HS256 auth tokens. Server **refuses startup** if set to a dev placeholder in `production`. |
| `GROQ_API_KEY` | `festiva-backend` | Yes | `gsk_...` | API key for Groq Llama-3.3-70B model. If unset or rate-limited, system falls back to deterministic rule engine. |
| `DEMO_ACCOUNT_PASSWORD`| `festiva-backend` | No | `DemoFestiva2026!` | Password for pre-seeded account `demo@festiva.ai`. |
| `CORS_ORIGINS` | `festiva-backend` | Yes | `https://festiva-frontend.onrender.com` | Strict CORS allowlist (comma-separated origins). |
| `VITE_API_URL` | `festiva-frontend` | Yes | `https://festiva-backend.onrender.com` | Backend URL used by frontend API client at build time. |

---

## 3. Database Lifecycle & pgvector Support

### Automated Startup Command
Every backend container deploy automatically runs:
```bash
alembic upgrade head && python -m app.db.seed && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

### Migrations & pgvector
1. **Safe Idempotent Extension Creation:**
   - Schema migration `003_full_schema.py` executes:
     ```sql
     CREATE EXTENSION IF NOT EXISTS vector;
     ```
   - Render PostgreSQL 16 supports `pgvector` natively. Executing `IF NOT EXISTS` ensures migrations apply safely without errors.
   - The migration establishes the `knowledge_chunks` table with column `embedding Vector(768)` for future RAG vector retrieval.
2. **Idempotent Seed Script (`python -m app.db.seed`)**:
   - Populates 15 deterministic budget allocation rules from `data/budget_rules.csv`.
   - Populates 20 sample Mangaluru vendors from `data/vendors.json`.
   - Creates the verified demo account (`demo@festiva.ai`) with Birthday Party Plan v1 and v2 (reduced décor by ₹10,000 to Contingency). If already seeded, gracefully skips.

> [!WARNING]
> **Free Render Postgres 30-Day Expiration:**
> Render's Free Tier PostgreSQL database **expires and is deleted after approximately 30 days**. It is intended for hackathon evaluations, prototyping, and testing. For permanent production data, upgrade to a persistent Render database tier or attach an external managed PostgreSQL instance (e.g. Neon, Supabase) via `DATABASE_URL`.

---

## 4. Free-Tier Cold Starts & Proxy Rate Limiting

1. **Cold Starts:** Render Free Tier spins down web services after 15 minutes of inactivity. When a request arrives, spinning up the container takes ~40–50 seconds.
2. **Frontend Auto-Retry:** `frontend/src/lib/api.ts` intercepts `502`, `503`, and `504` status codes and retries automatically for **up to 60 seconds** (12 attempts $\times$ 5s delay), displaying an accessible top banner with attempt countdown.
3. **Proxy IP Rate Limiting:** Rate limiters in `app/core/rate_limit.py` inspect the **last hop** of `X-Forwarded-For` (appended by Render's trusted reverse proxy), preventing spoofed client headers from evading the 15 req/min auth limit.

---

## 5. Verification Commands

### Checking Health
- **Shallow Health**: `GET /health` $\rightarrow$ `{"status": "ok"}`
- **Readiness Probe**: `GET /health/ready` $\rightarrow$ `{"status": "ready", "database": "connected"}`

### Checking Security Headers
```bash
curl -I https://festiva-frontend-xxxx.onrender.com
```
Expected headers:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`
- `Content-Security-Policy: default-src 'self'; ...`
