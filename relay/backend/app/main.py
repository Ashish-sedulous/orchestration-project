"""FastAPI app: start runs, stream events (SSE), history, agent registry."""
from __future__ import annotations

import asyncio
import json
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from . import config, store
from .agents import AGENTS
from .executor import Run, execute

app = FastAPI(title="Relay - adaptive multi-agent orchestration")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

RUNS: dict[str, Run] = {}
TASKS: set[asyncio.Task] = set()


class RunRequest(BaseModel):
    task: str = Field(min_length=3, max_length=4000)
    strategy: Literal["adaptive", "single", "fixed_pipeline"] = "adaptive"
    budget_usd: float = Field(default=0.02, ge=0.0005, le=1.0)
    budget_s: float = Field(default=90, ge=5, le=600)
    priority: Literal["quality", "balanced", "economy"] = "balanced"
    judge: bool = True


@app.get("/api/health")
def health():
    return {"ok": True, "models": config.MODELS, "fallback": config.FALLBACK_MODEL}


@app.post("/api/run")
async def start_run(req: RunRequest):
    run = Run(req.task.strip(), req.strategy, req.budget_usd, req.budget_s, req.priority, req.judge)
    RUNS[run.id] = run
    t = asyncio.create_task(execute(run))
    TASKS.add(t)
    t.add_done_callback(TASKS.discard)
    return {"run_id": run.id}


@app.get("/api/runs/{run_id}/events")
async def events(run_id: str):
    run = RUNS.get(run_id)
    stored = None if run else store.get_events(run_id)
    if run is None and stored is None:
        raise HTTPException(404, "Run not found")

    async def gen():
        i = 0
        while True:
            evs = run.events if run else stored
            while i < len(evs):
                yield f"data: {json.dumps(evs[i])}\n\n"
                i += 1
            if run is None or run.finished:
                if i >= len(evs):
                    break
            await asyncio.sleep(0.15)
        yield "event: end\ndata: {}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/runs")
def runs():
    return store.list_runs()


@app.get("/api/agents")
def agents():
    return [a.public() for a in AGENTS]
