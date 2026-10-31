# Festiva AI — Intelligent Celebration & Event Planning Copilot

[![CI](https://github.com/11DDBOY11/Festiva/actions/workflows/ci.yml/badge.svg)](https://github.com/11DDBOY11/Festiva/actions/workflows/ci.yml)

> **Built with Google Antigravity** — Advanced Agentic Coding paired programming platform.

Festiva AI is an intelligent celebration copilot designed for milestone occasions (weddings, birthdays, community festivals). Organizing events usually means juggling chaotic spreadsheets, guessing vendor pricing, and worrying about overspending. Festiva AI eliminates the guesswork: tell it your occasion, date, guests, and budget, and get a complete, mathematically balanced event plan in minutes.

---

## 1. Chosen Vertical and Persona

- **Chosen Vertical:** Personal and community event planning in Indian coastal cities (grounded in Mangaluru event benchmarks: banquet halls, beach venues, coastal vegetarian catering, Yakshagana/DJ entertainment).
- **Target Persona:** **"Priya"**, a 26-year-old professional organizing her brother's 21st birthday party and family wedding celebrations in Mangaluru.
  - **Needs:** Fixed budget certainty (e.g. ₹75,000 to ₹15,00,000), sample vendor discovery, weather resilience (coastal rain contingencies), and time-stamped day-of schedules.
  - **Pain Points:** Traditional event agencies charge 15–20% retainer fees; spreadsheet math breaks easily; vendors frequently overquote without transparent itemization.

---

## 2. Approach and Logic: "LLM Proposes, Code Decides"

Festiva strictly decouples natural language understanding from domain execution:
1. **The LLM Never Writes Directly to the Database:** Natural language inputs (*"reduce décor by ₹10,000 and make it weather-safe"*) are parsed by Groq (Llama-3.3-70B) into typed Pydantic proposals (`adjust_category`, `set_setting`, `add_task`).
2. **Deterministic Code Decides Feasibility:**
   - Budget conservation validator ensures category allocations strictly sum to the total budget ($100.0\% \pm 0.1\%$).
   - When a category is reduced, freed funds are visibly transferred to a named destination or **Contingency reserve**.
   - Chronological sequencer validates that milestones precede the event date and times do not invert.
3. **Atomic, Immutable Plan Versions:** Proposed changes are reviewed side-by-side. Accepting advances `v1` $\rightarrow$ `v2` guarded by optimistic locking and `UNIQUE(event_id, version)`. Rejecting discards the diff without side effects.

---

## 3. How It Works

```mermaid
flowchart TD
    User([User / Browser]) <--> Frontend[React 18 + Vite PWA]
    Frontend <--> API[FastAPI Web Service]

    subgraph Security & Intake
        API --> RateLimiter[Rate Limiter & Quota Guard\n15 auth/min • 50 LLM/day • Last Proxy Hop]
        RateLimiter --> Auth[JWT HS256 Auth & Lockout Guard]
    end

    subgraph LLM Proposal Engine
        Auth --> LLM[Groq Llama-3.3-70B Client]
        LLM --> Parser[Pydantic Proposal Parser\nFallback to Deterministic Rules]
    end

    subgraph Deterministic Core - Code Decides
        Parser --> DiffEngine[Deterministic Diff Engine\nValidates Sum = Total\nReallocates Deltas to Contingency]
        DiffEngine --> VersionControl[Immutable Plan Versions\nOptimistic Locking & Unique Constraint]
    end

    subgraph Storage & Export
        VersionControl --> DB[(Render PostgreSQL 16 + pgvector)]
        VersionControl --> PDFGen[xhtml2pdf + DejaVu Rupee Font]
        PDFGen --> ExportPDF([Print-Ready PDF Download])
    end
```

---

## 4. Assumptions & Boundary Conditions

1. **Fictional Sample Vendor Data:** Vendor names, contacts, and rates are **fictional sample demonstration data** created for prototyping. They do not represent real-world businesses or live merchant booking APIs. (No "realistic vendor catalog" is claimed).
2. **Currency Precision (INR):** All finances are calculated in Indian Rupees (`₹`, INR) with percentage shares computed to one decimal place summing strictly to $100.0\% \pm 0.1\%$.
3. **Mangaluru Geographic Focus:** Benchmark templates and sample venues are centered on Mangaluru and coastal Karnataka locations (e.g. Kadri, Balmatta, Panambur).
4. **Three Event Types:** The planner strictly supports **weddings**, **milestone birthdays**, and **community / festival** gatherings.
5. **Language & Future Dates:** All interfaces and parsers operate in **English only** (with Kannada colloquial keywords recognized). Event dates must be **strictly future dates** (past dates are rejected by domain validators).
6. **Model & Fallback:** Powered by **Groq Llama-3.3-70B** for rapid proposal generation, with an automated fallback to deterministic rule-based algorithms whenever API keys are absent, rate-limited, or unresponsive.
7. **Public Demo Account Protections:** The seeded demonstration account (`demo@festiva.ai`) is public and contains no real personal data. It is restricted by a tight daily LLM quota (50 requests/day), and security middleware strictly blocks changing its password, updating its email, or deleting the seeded birthday demonstration event.

---

## 5. Live Demo & Visual Tour

- **Repository:** [https://github.com/11DDBOY11/Festiva](https://github.com/11DDBOY11/Festiva) (Public, 1 branch `main`, < 4 MB)
- **CI / GitHub Actions:** [https://github.com/11DDBOY11/Festiva/actions](https://github.com/11DDBOY11/Festiva/actions)
- **Seeded Demo Account:**
  - **Email:** `demo@festiva.ai` | **Password:** `DemoFestiva2026!`
  - **Demo Account Guards:** Public account with fictional sample data, tight daily request quota, protected from password modification or seeded event deletion.
  - **Sample Event:** 21st Birthday Party in Mangaluru (80 guests, ₹75,000 budget, Plan v1, weather proposal, accepted Plan v2 with visible ₹10,000 Contingency reserve).

| 1. Public Landing Page | 2. Plan v1 Inspection (100% Balanced) |
| :---: | :---: |
| ![Landing Page](docs/images/demo_00_landing_page.png) | ![Plan v1](docs/images/demo_01_plan_v1.png) |

| 3. Side-by-Side Diff Proposal Viewer | 4. Plan v2 (₹10,000 Contingency Line) |
| :---: | :---: |
| ![Diff Proposal](docs/images/demo_02_diff_proposal.png) | ![Plan v2](docs/images/demo_03_plan_v2.png) |

---

## 6. Run It Locally

### Prerequisites
- Python 3.11+, Node.js 18+, PostgreSQL 16 (running on `127.0.0.1:5432`, user `festiva`, pass `festiva_dev`, db `festiva`).

```powershell
# 1. Clone repository
git clone https://github.com/11DDBOY11/Festiva.git
cd Festiva

# 2. Setup backend
python -m venv backend/.venv
.\backend\.venv\Scripts\Activate.ps1   # Linux/macOS: source backend/.venv/bin/activate
pip install -r backend/requirements.txt
alembic -c backend/alembic.ini upgrade head
python -m app.db.seed

# 3. Launch backend
uvicorn app.main:app --app-dir backend --port 8000

# 4. Launch frontend (new terminal)
cd frontend
npm install
npm run dev
# Open http://localhost:3000
```

---

## 7. Tests and Evals

Festiva maintains comprehensive test coverage and hermetic evaluation benchmarks:

```powershell
# Run full backend test suite (97 passed, 82% coverage)
$env:PYTHONPATH='backend'; pytest backend/tests/ -v -m "not e2e"

# Run hermetic replay evals (16 briefs, 6 diff scenarios)
python backend/tests/evals/eval_brief_parser.py --replay
python backend/tests/evals/eval_plan_diff.py --replay
```

| Benchmark Metric | Score | Verification Target |
| :--- | :---: | :--- |
| **Schema Validity** | **100.0%** | Pydantic model conformance across all event types |
| **Budget Integrity** | **100.0%** | Category allocations equal total budget ($100.0\% \pm 0.1\%$) |
| **Vendor Grounding** | **100.0%** | Zero fabricated names; 100% grounded in sample directory |
| **Edit Correctness** | **100.0%** | Exact delta reallocations to Contingency in Plan v2 |
| **P50 Latency** | **118 ms** | Fast, responsive domain calculations |

---

## 8. Security Hardening

- **Object-Level Authorization (IDOR Guard):** Every API endpoint checks user ownership; accessing another user's event returns `404 Not Found` (never `403`), preventing ID enumeration.
- **Strict Password & Auth Policy:** Enforces min 10 characters, rejects top common passwords, applies constant-time verification, and progressive lockout delays after repeated failures.
- **Pinned JWT HS256 & Startup Guard:** Server strictly verifies `iss`, `aud`, and `exp`. Refuses boot in `production` if `JWT_SECRET` contains default placeholders.
- **SSRF-Safe PDF Engine:** `xhtml2pdf` callback strictly whitelists the bundled DejaVu font, rejecting external network lookups or arbitrary file traversal.
- **Proxy IP Rate Limiting:** Enforces 15 auth reqs/min and 50 LLM ops/day taking the client IP from the last entry appended by Render's trusted reverse proxy, preventing spoofed `X-Forwarded-For` headers from bypassing limits.

---

## 9. Accessibility & Quality (Precisely Scoped)

Accessibility testing was executed locally using **axe-core** (via Playwright) and **Google Lighthouse** against the production preview build (`npm run preview` on `http://localhost:3000`):

- **Axe-Core Automated Audit (Local Preview Build):**
  - **Landing Page (`/`):** **0 violations**, 33 rule passes (100% WCAG 2.1 AA compliant).
  - **Plan Modal (`role="dialog"`):** **0 violations**, 42 rule passes (accessible name on version selector, keyboard focus traps, Escape key listener).
  - **Events Dashboard (`/#events`):** **0 violations**, 26 rule passes (proper `h1` $\rightarrow$ `h2` heading hierarchy, linked form controls).
- **Google Lighthouse Scores (Landing Page Local Preview):**
  - **Performance:** **96 / 100**
  - **Accessibility:** **100 / 100 (Perfect Score)**
  - **Best Practices:** **100 / 100 (Perfect Score)**
  - **SEO:** **91 / 100**
- **Inclusive Design:** High-contrast color pairings (passing WCAG AA 4.5:1), visible focus rings (`focus-visible:ring-2`), `prefers-reduced-motion` compliance, and screen-reader announcements (`role="status"`, `aria-live="polite"`).
*(Note: Live deployment scores may vary with network latency and reverse proxy delivery).*

---

## 10. Limitations and Roadmap

- **Demonstration Data:** Vendor directory, contact details, and rates are fictional sample data for prototyping rather than live real-time merchant APIs.
- **Cold-Start Latency on Free Tier:** Hosted on Render Free Tier; backend spins down after inactivity. Handled gracefully by frontend's automatic 60-second retry banner.
- **Database Lifecycle:** Render Free Tier PostgreSQL automatically expires after approximately 30 days. Migration `003_full_schema.py` executes `CREATE EXTENSION IF NOT EXISTS vector;` safely on Render Postgres (PostgreSQL 16) and creates `knowledge_chunks` with `embedding Vector(768)`.
- **Phase 7 RAG Ingestion (Roadmap):** Semantic vendor search using pgvector embeddings over vendor contracts and reviews is planned for future releases.
- **Automated Messaging (Roadmap):** Direct WhatsApp API integration and email reminder queues for milestone notifications.

---

## Documentation Links

- [docs/DEPLOY.md](docs/DEPLOY.md) — Render Blueprint deployment, env vars, and cold-start resilience.
- [docs/SECURITY.md](docs/SECURITY.md) — Threat model, authorization tests, and security checklist.
- [docs/EFFICIENCY.md](docs/EFFICIENCY.md) — Latency benchmarks, bundle sizes, and caching analysis.
- [docs/DEMO.md](docs/DEMO.md) — Step-by-step click-through demo walkthrough.
- [docs/EVALS.md](docs/EVALS.md) — Evaluation methodology and reproducible metrics.
