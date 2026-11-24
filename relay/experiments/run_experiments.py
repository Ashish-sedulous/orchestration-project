#!/usr/bin/env python3
"""Run the benchmark suite under several strategies/ablations and append results to results/results.jsonl.

Examples (from the `experiments` folder, backend venv active):
  python run_experiments.py --fake --per-category 1 --reps 1          # offline smoke test, no API calls
  python run_experiments.py --conditions single,fixed_pipeline,adaptive --reps 2 --budget loose
  python run_experiments.py --conditions abl_no_adapt,abl_no_early_stop --per-category 2 --budget loose
The script is resumable: finished (condition, task, rep, budget) combinations are skipped.

SAFETY: coding tasks execute model-written Python on your machine (isolated mode, 8 s timeout, temp dir,
empty environment). The tasks are simple functions; still, skim results/results.jsonl if you are unsure.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "backend"))
RESULTS = HERE / "results"
RESULTS.mkdir(exist_ok=True)
os.environ["DB_PATH"] = str(RESULTS / "experiment_runs.db")  # keep app history clean

from app import executor, llm  # noqa: E402
from app.agents import AGENTS  # noqa: E402

CONDITIONS = {
    "single": ("single", {}),
    "fixed_pipeline": ("fixed_pipeline", {}),
    "adaptive": ("adaptive", {}),
    "abl_no_adapt": ("adaptive", {"no_adapt": True}),
    "abl_no_early_stop": ("adaptive", {"no_early_stop": True}),
    "abl_no_parallel": ("adaptive", {"no_parallel": True}),
    "abl_no_budget": ("adaptive", {"no_budget": True}),
    "abl_static_selection": ("adaptive", {"static_selection": True}),
    "abl_no_learning": ("adaptive", {"no_learning": True}),
}
BUDGETS = {"loose": (0.05, 120.0), "tight": (0.003, 60.0)}  # (notional USD, seconds)


# ------------------------------------------------------------------ checking
def _run_code_tests(answer: str, tests: str) -> float:
    blocks = re.findall(r"```(?:python|py)?[ \t]*\n(.*?)```", answer, re.S)
    code = next((b for b in blocks if "def " in b), None)
    if not code:
        return 0.0
    program = code + "\n\n" + tests + "\n"
    with tempfile.TemporaryDirectory() as tmp:
        try:
            res = subprocess.run([sys.executable, "-I", "-c", program], cwd=tmp, capture_output=True,
                                 timeout=8, env={"PATH": os.environ.get("PATH", "")})
        except subprocess.TimeoutExpired:
            return 0.0
    return 1.0 if res.returncode == 0 else 0.0


def check_answer(task: dict, answer: str) -> tuple[float, bool]:
    chk = task["check"]
    if not answer.strip():
        return 0.0, False
    if chk["type"] == "code":
        score = _run_code_tests(answer, chk["tests"])
    else:
        groups = chk["groups"]
        hit = sum(1 for g in groups if any(re.search(p, answer, re.I) for p in g))
        score = hit / len(groups)
    return round(score, 3), score >= task.get("pass_threshold", 1.0)


# ------------------------------------------------------------------- running
def reset_stats() -> None:
    for a in AGENTS:
        a.calls = a.ok = a.n = 0
        a.q_sum = a.lat_sum = a.cost_sum = 0.0


async def fake_complete(prompt, system, tier, max_tokens=900, temperature=0.3):
    await asyncio.sleep(0.01)
    if "task planner" in system:
        text = json.dumps({"category": "multi_step", "complexity": 3, "subtasks": [
            {"id": "s1", "title": "Part one", "instruction": prompt[:200], "capabilities": ["research"], "depends_on": [], "difficulty": 1},
            {"id": "s2", "title": "Part two", "instruction": prompt[:200], "capabilities": ["analysis"], "depends_on": [], "difficulty": 2}]})
    elif "grade answers" in system:
        text = '{"score": 7}'
    else:
        text = "Here is a reasonable answer. - First point.\n- Second point about the task.\n```python\ndef f():\n    return 1\n```\nDone."
    return llm.CallRecord(model="fake", tier=tier, text=text, tokens_in=300, tokens_out=200,
                          cost=llm.est_cost(tier, 300, 200), latency=0.01, attempts=1, success=True)


async def run_one(condition: str, task: dict, rep: int, budget_name: str) -> dict:
    strategy, flags = CONDITIONS[condition]
    usd, secs = BUDGETS[budget_name]
    run = executor.Run(task["prompt"], strategy, usd, secs, "balanced", True, flags=dict(flags))
    await executor.execute(run)
    final = run.final or {"answer": "", "metrics": {}}
    answer = final["answer"] if run.status == "done" else ""
    check_score, passed = check_answer(task, answer)
    m = final.get("metrics", {})
    return {
        "condition": condition, "budget": budget_name, "task_id": task["id"], "category": task["category"],
        "rep": rep, "status": run.status, "check_score": check_score, "passed": passed,
        "judge": m.get("judge_quality"), "heuristic": m.get("heuristic_quality"),
        "latency_s": m.get("total_latency_s", round(run.elapsed(), 2)), "cost_usd": m.get("cost_usd", run.spent),
        "tokens": m.get("tokens_in", 0) + m.get("tokens_out", 0), "calls": m.get("agent_calls", run.calls),
        "retries": m.get("retries", 0), "replacements": m.get("replacements", 0),
        "skipped": m.get("skipped_steps", 0), "failures": m.get("failures", 0),
        "budget_ok": m.get("budget_ok"), "topology": m.get("topology", run.topology),
        "steps_total": m.get("steps_total"), "steps_done": m.get("steps_done"),
        "selections": [(e["node_id"], e["chosen"]["id"]) for e in run.events if e["type"] == "selection"],
        "adapts": [e["action"] for e in run.events if e["type"] == "adapt"],
        "answer": answer[:4000], "model_cfg": dict(executor.config.MODELS), "timestamp": time.time(),
        # calls answered by a model other than the configured tiers (i.e. the fallback). Should be 0.
        "fallback_calls": sum(1 for e in run.events if e["type"] == "call"
                              and e["model"] not in executor.config.MODELS.values()),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--conditions", default="single,fixed_pipeline,adaptive")
    ap.add_argument("--budget", default="loose", choices=list(BUDGETS))
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--per-category", type=int, default=0, help="use only the first N tasks of each category")
    ap.add_argument("--pause", type=float, default=2.0, help="seconds to wait between runs (rate limits)")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--fake", action="store_true", help="offline mode with a fake LLM")
    ap.add_argument("--out", default=str(RESULTS / "results.jsonl"))
    args = ap.parse_args()

    if args.fake:
        llm.complete = fake_complete
        args.out = str(RESULTS / "results_fake.jsonl")
        args.pause = 0
    tasks = json.load(open(HERE / "tasks.json"))
    if args.per_category:
        seen: dict[str, int] = {}
        keep = []
        for t in tasks:
            seen[t["category"]] = seen.get(t["category"], 0) + 1
            if seen[t["category"]] <= args.per_category:
                keep.append(t)
        tasks = keep
    conds = [c.strip() for c in args.conditions.split(",") if c.strip()]
    for c in conds:
        if c not in CONDITIONS:
            sys.exit(f"Unknown condition {c}. Choose from: {', '.join(CONDITIONS)}")

    done = set()
    if os.path.exists(args.out):
        for line in open(args.out):
            r = json.loads(line)
            done.add((r["condition"], r["task_id"], r["rep"], r["budget"]))

    total = len(conds) * len(tasks) * args.reps
    i = 0
    print(f"Models: {dict(executor.config.MODELS)}  fallback={executor.config.FALLBACK_MODEL}")
    for cond in conds:
        for rep in range(args.reps):
            reset_stats()  # every (condition, rep) pass starts cold, learning accumulates across its tasks
            order = tasks[:]
            random.Random(args.seed + rep).shuffle(order)
            for task in order:
                i += 1
                if (cond, task["id"], rep, args.budget) in done:
                    print(f"[{i}/{total}] skip (already done) {cond} {task['id']} rep{rep}")
                    continue
                rec = asyncio.run(run_one(cond, task, rep, args.budget))
                with open(args.out, "a") as f:
                    f.write(json.dumps(rec) + "\n")
                print(f"[{i}/{total}] {cond:<20} {task['id']:<4} rep{rep} {args.budget} -> "
                      f"pass={rec['passed']} check={rec['check_score']} judge={rec['judge']} "
                      f"t={rec['latency_s']}s cost=${rec['cost_usd']:.5f} calls={rec['calls']} status={rec['status']}"
                      + (f"  WARNING: {rec['fallback_calls']} call(s) used the fallback model" if rec["fallback_calls"] else ""))
                time.sleep(args.pause)
    print("Done. Results:", args.out)


if __name__ == "__main__":
    main()
