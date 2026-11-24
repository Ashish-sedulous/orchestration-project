# Relay: adaptive multi-agent orchestration

Plans a task as a dependency graph, picks the best-value agent for each step with a transparent scoring
policy, chooses a workflow topology (single / sequential / parallel / hybrid), adapts at runtime
(retry, swap agent, early stop, budget downgrade) and streams every decision to a React dashboard.
It orchestrates existing LLMs; no model is trained.

## Run it

### 1. Backend (Python 3.10+)
```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # Windows: copy .env.example .env  (then add your keys)
uvicorn app.main:app --reload --port 8000
```
Check http://localhost:8000/api/health and http://localhost:8000/docs.

### 2. Frontend (Node 18+)
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:5173.

### 3. Offline test (no keys needed)
```bash
cd backend
pip install pytest
pytest -q
```

## Models
Set in `backend/.env`. Cheap tier = Groq `llama-3.1-8b-instant`, strong tier = Gemini Flash. If a call fails
twice, the client falls back to `FALLBACK_MODEL`. If a model name errors, copy a current name from the
Groq or Google AI Studio dashboard. Prices in `app/config.py` are NOTIONAL (free tiers cost $0) so the
cost budget behaves like a paid deployment.

## How the decisions work
| File | Role |
|---|---|
| `planner.py` | LLM decomposes the task into a validated DAG (cycle check, fallback to one node) |
| `selector.py` | `S = w1*match + w2*quality + w3*reliability - w4*cost - w5*latency`; cost weight rises as budget is spent; cold-start shrinkage |
| `topology.py` | Width and critical path from the DAG; parallel only if estimated saving beats coordination overhead |
| `executor.py` | Scheduler, budget tracking, retry / swap agent / early stop / model downgrade, synthesis |
| `evaluator.py` | Deterministic output scoring (length, keyword coverage, code syntax via `ast`) + optional LLM judge |

Strategies: `adaptive` (proposed), `single` and `fixed_pipeline` (baselines). The Compare tab runs all three.

## Limits worth stating in a viva
- Heuristic quality is a proxy; the LLM judge is subjective. Treat results as indicative, not proven.
- Free-tier rate limits can slow parallel runs; concurrency is capped by `MAX_CONCURRENT_CALLS`.
- Hierarchical topology is not implemented separately; the planner-then-delegate flow is the hierarchy.
- CORS is open for local development; restrict origins before deploying.
