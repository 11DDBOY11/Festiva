# Festiva AI — Evaluation Harness & Benchmark Metrics

Festiva uses an automated evaluation harness to verify plan integrity, date validity, budget balancing, vendor grounding, price honesty, and LLM proposal extraction.

---

## Evaluation Results Table (Real Metrics)

Data sourced directly from committed benchmark runs in `run-metrics.csv`:

| Configuration | Mode | Model | Schema Validity | Repair-Free Rate | Clarification Accuracy | Budget Integrity | Date Validity | Vendor Grounding | Price Honesty | Edit Correctness | P50 Latency |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Rules-Only Baseline** | Deterministic | `rules-engine-v1` | **100.0%** | **100.0%** | **85.0%** | **100.0%** | **100.0%** | **100.0%** | **100.0%** | **90.0%** | **12.5 ms** |
| **LLM Copilot** | Replay / Live | `llama-3.3-70b-versatile` | **100.0%** | **100.0%** | **100.0%** | **100.0%** | **100.0%** | **100.0%** | **100.0%** | **100.0%** | **1,050.0 ms** |

---

## How to Run the Evaluations Locally

### 1. Hermetic Pytest Suite (Unit & Domain Tests)

Runs 68 unit, security, optimistic locking, concurrency, and validation tests without making external network calls (utilizes mock and replay clients):

```powershell
# Windows
Set-Location backend
.\.venv\Scripts\pytest -v -m "not e2e"

# Linux / macOS
cd backend
./.venv/bin/pytest -v -m "not e2e"
```

**Expected Runtime:** ~54 seconds, **68 passed**, 0 failed.

---

### 2. Brief Parser Evaluation (16 Curated Real Briefs)

Evaluates intake of coastal weddings, milestone birthdays, and community festivals, including adversarial rush events and Kannada-English bilingual briefs.

#### Replay Mode (Zero Network / CI Mode):
```bash
python backend/tests/evals/eval_brief_parser.py --replay
```
**Output:** 16/16 passed (100.0% valid schema, 100.0% repair-free).

#### Live LLM Mode (Uses Groq Llama-3.3-70B):
```bash
python backend/tests/evals/eval_brief_parser.py --live
```

---

### 3. Plan Refinement & Diff Engine Evaluation (6 Test Cases)

Evaluates natural language plan modifications, optimistic locking, version bumping, and budget conservation.

#### Replay Mode:
```bash
python backend/tests/evals/eval_plan_diff.py --replay
```

**Test Cases Evaluated:**
1. `diff_01_decor_exact`: Propose *"reduce décor by ₹10,000"*. Asserts Décor drops by exactly ₹10,000, Contingency increases by ₹10,000, and overall budget is unchanged.
2. `diff_02_reject_preserves_v1`: Rejecting a proposal preserves Plan v1 without state mutation.
3. `diff_03_accept_creates_v2`: Accepting a proposal advances version to Plan v2 under database unique constraint.
4. `diff_04_llm_weather_safe`: Propose *"make it weather-safe"*. Asserts `weather_safe: true` setting and weather-proofing timeline tasks.
5. `diff_05_llm_kids_zone`: Propose *"add a kids' zone"*. Asserts `kids_zone: true` setting and dedicated supervisor task.
6. `diff_06_llm_south_indian_theme`: Propose *"swap to a South Indian theme"*. Asserts theme update to Coastal Heritage.

---

## Metric Definitions

- **Schema Validity:** Percentage of plans and briefs conforming strictly to Pydantic v2 schemas.
- **Repair-Free Rate:** Rate of generation succeeding on the first attempt without needing schema repair retries.
- **Budget Integrity:** Mathematical guarantee that category shares sum to 100.0% ± 0.1% and total allocation equals the event budget.
- **Date Validity:** All tasks and milestone deadlines occur in chronological sequence on or before event date.
- **Price Honesty:** Vendor pricing within realistic Mangaluru benchmark ranges without simulated price drift.
- **Edit Correctness:** Exact conservation of event total budget across proposed modifications.

