# Festiva AI — Performance & Efficiency Report

**Version**: 1.0  
**Last Benchmarked**: 2026-10-31  
**Environment**: Local PostgreSQL 16 + FastAPI + Vite Production Build  

---

## 1. Backend Efficiency Optimizations

### In-Memory Rules & Vendor Caching
- **Budget Allocation Rules**: `load_rules()` in `app/domain/budget.py` utilizes `@functools.lru_cache(maxsize=8)` to avoid disk I/O on every calculation.
- **Vendor Directory**: `load_vendor_records()` in `app/domain/vendor_directory.py` caches JSON directory records in memory (`@functools.lru_cache(maxsize=4)`).
- **Dual-Tier Health Check**:
  - `GET /health`: Ultra-lightweight endpoint without database queries for load balancer liveness probes.
  - `GET /health/ready`: Database connectivity check (`SELECT 1`) for readiness verification.
- **Event List Pagination**:
  - `GET /events/`: Supports `limit` (default: 20, max: 100) and `offset` query parameters.

### Concurrency & Latency Benchmarks (10 Concurrent Workers, 20 Requests Each)

| Endpoint | Description | P50 Latency (ms) | P95 Latency (ms) | Reqs |
| :--- | :--- | :--- | :--- | :--- |
| `GET /health` | Liveness check (in-memory) | **150.06 ms** | **211.97 ms** | 20 |
| `GET /health/ready` | Readiness check (DB ping) | **122.51 ms** | **250.40 ms** | 20 |
| `POST /briefs/parse` | Deterministic brief parsing | **118.26 ms** | **154.67 ms** | 20 |
| `POST /auth/login` | Authentication (bcrypt cost 12) | **743.89 ms** | **859.07 ms** | 20 |
| `GET /events/?limit=20` | Paginated user event listing | **165.19 ms** | **274.87 ms** | 20 |
| `GET /events/{id}/plan` | Event plan retrieval & model parse | **167.62 ms** | **302.41 ms** | 20 |

---

## 2. Frontend Efficiency & Bundle Size

### Production Build Footprint
Compiled via Vite + TypeScript (`npm run build`):
- `dist/index.html`: **1.16 kB** (gzip: 0.63 kB)
- `dist/assets/index-BV-TthIe.css`: **47.84 kB** (gzip: 8.28 kB)
- `dist/assets/index-CX6KMwdP.js`: **271.16 kB** (gzip: **72.32 kB**)
- **Total Compressed JS Size**: **72.32 kB** (well under the 150 kB threshold).
