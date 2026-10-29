# Festiva AI — Production Deployment Guide

This guide details deploying Festiva AI to cloud infrastructure:
- **Frontend:** Vercel (Vite/React PWA)
- **Backend:** Render or Railway (FastAPI Docker container)
- **Database:** Neon or Supabase (PostgreSQL 16 with pgvector)

---

## 1. Environment Variables Specification

All secrets must be configured via host environment variables in cloud dashboards. **Never commit `.env` files to the repository.**

| Variable | Environment | Example / Format | Purpose |
| :--- | :--- | :--- | :--- |
| `ENV` | Backend | `production` | Enables production security enforcement. |
| `JWT_SECRET` | Backend | `b49f91a0...` (64 hex characters) | Key for signing JWT tokens. Refuses startup if default. |
| `GROQ_API_KEY` | Backend | `gsk_...` | Authentication key for Groq API (Llama-3.3-70B). |
| `DATABASE_URL` | Backend | `postgresql+psycopg2://...` | Connection URI to PostgreSQL instance. |
| `REDIS_URL` | Backend | `redis://...` | Optional connection URI for Redis cache/rate limiting. |
| `CORS_ORIGINS` | Backend | `https://festiva.vercel.app` | Allowed origins for cross-origin frontend requests. |
| `LLM_PROVIDER` | Backend | `groq` | Active LLM client implementation (`groq`, `fake`). |
| `LLM_MODEL` | Backend | `llama-3.3-70b-versatile` | Target LLM model name. |
| `VITE_API_URL` | Frontend | `https://festiva-backend.onrender.com` | Base URL used by frontend API client. |

---

## 2. Backend Deployment on Render

### Using Render Blueprint (`render.yaml`):
1. Log into your Render dashboard.
2. Click **New +** -> **Blueprint**.
3. Connect repository `https://github.com/11DDBOY11/Festiva`.
4. Render automatically parses `render.yaml` and sets up:
   - Web Service: `festiva-backend` using `Dockerfile`.
   - Managed Database: `festiva-db` (Postgres).
5. In the Render service settings, populate the secret `GROQ_API_KEY`.
6. Click **Apply Blueprint**.

### Manual Docker Deployment on Render / Railway:
- **Build Context:** Repository root
- **Dockerfile Path:** `Dockerfile`
- **Exposed Port:** `$PORT` (automatically injected by Render/Railway)
- **Healthcheck Path:** `/health`

---

## 3. Database Initialization & Seeding

After the cloud Postgres instance is running and connected via `DATABASE_URL`:

### Run Alembic Migrations:
```bash
# Apply schema versions 001 through 004
alembic upgrade head
```

### Seed Budget Rules, Sample Vendors & Demo Account:
```bash
# Populates budget_rules, 20 sample vendors, and demo@festiva.ai account with Plan v1 & v2
python app/db/seed.py
```

---

## 4. Frontend Deployment on Vercel

1. Log into Vercel and click **Add New Project**.
2. Select repository `11DDBOY11/Festiva`.
3. In Project Settings:
   - **Framework Preset:** Vite
   - **Root Directory:** `frontend`
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`
4. In **Environment Variables**:
   - `VITE_API_URL`: Your backend URL (e.g. `https://festiva-backend.onrender.com`).
5. Click **Deploy**.
6. Vercel utilizes `frontend/vercel.json` to configure single-page application routing and API proxies.

---

## 5. Security & Rate Limiting Details

- **Default Secret Refusal Guard:** The FastAPI startup lifecycle inspects `JWT_SECRET`. If `ENV=production` and `JWT_SECRET` matches any default development placeholder, the server intentionally refuses to start with `RuntimeError`.
- **IP-Based Auth Rate Limiting:** Endpoint protection allows at most 15 login/register attempts per minute per IP, preventing brute-force password guessing.
- **Per-User Daily LLM Quota:** Each user account is allowed 50 AI requests per calendar day. When the quota is reached, Festiva automatically falls back to deterministic rule-based planning rather than failing requests.

---

## 6. Cold Starts & Free-Tier Expectations

- **Render Free Tier:** Web services spin down after 15 minutes of inactivity. When awoken, expect an initial 30–45 second cold start latency for the first request.
- **Neon / Supabase Serverless Postgres:** Free tier database compute may pause after extended inactivity, incurring a ~2-second warm-up latency on initial connection.
- **Groq Free Tier:** Rate limits of 30 RPM / 14,400 RPD for Llama-3.3-70B. If exceeded, Festiva's automatic fallback immediately engages to ensure uninterrupted planning.
