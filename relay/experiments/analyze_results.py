#!/usr/bin/env python3
"""Turn results/results.jsonl into paper-ready tables (results/tables.md, results/summary.csv, figure).

Usage: python analyze_results.py [path/to/results.jsonl]
Uses only the standard library; the figure needs `pip install matplotlib` (optional).
"""
from __future__ import annotations

import csv
import json
import random
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "results" / "results.jsonl"
OUT = HERE / "results"
rows = [json.loads(l) for l in open(SRC)]
ORDER = ["single", "fixed_pipeline", "adaptive", "abl_no_adapt", "abl_no_early_stop", "abl_no_parallel",
         "abl_no_budget", "abl_static_selection", "abl_no_learning"]
CATS = ["qa", "research", "coding", "data", "multi"]


def mean(x): return sum(x) / len(x) if x else float("nan")
def sd(x): return st.stdev(x) if len(x) > 1 else 0.0
def pct(x, p):
    if not x: return float("nan")
    x = sorted(x); k = (len(x) - 1) * p / 100; f = int(k); c = min(f + 1, len(x) - 1)
    return x[f] + (x[c] - x[f]) * (k - f)
def f(v, d=2): return "n/a" if v != v else f"{v:.{d}f}"


def group(rs, key): 
    g = defaultdict(list)
    for r in rs: g[key(r)].append(r)
    return g


def summarize(rs):
    judge = [r["judge"] for r in rs if r["judge"] is not None]
    lat = [r["latency_s"] for r in rs]
    return {
        "n": len(rs), "success": mean([1.0 if r["passed"] else 0.0 for r in rs]) * 100,
        "check": mean([r["check_score"] for r in rs]), "judge": mean(judge), "judge_sd": sd(judge),
        "heur": mean([r["heuristic"] for r in rs if r["heuristic"] is not None]),
        "lat_med": pct(lat, 50), "lat_p95": pct(lat, 95), "lat_mean": mean(lat),
        "cost": mean([r["cost_usd"] for r in rs]), "tokens": mean([r["tokens"] for r in rs]),
        "calls": mean([r["calls"] for r in rs]), "retries": mean([r["retries"] for r in rs]),
        "swaps": mean([r["replacements"] for r in rs]), "skipped": mean([r["skipped"] for r in rs]),
        "fail": mean([1.0 if r["status"] != "done" else 0.0 for r in rs]) * 100,
        "budget_ok": mean([1.0 if r["budget_ok"] else 0.0 for r in rs]) * 100,
    }


def table(header, body):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in body]
    return "\n".join(out) + "\n"


def overall(rs, conds):
    body = []
    for c in conds:
        s = summarize([r for r in rs if r["condition"] == c])
        if s["n"] == 0: continue
        body.append([c, s["n"], f(s["success"], 1), f(s["check"]), f"{f(s['judge'])} +/- {f(s['judge_sd'])}",
                     f(s["lat_med"], 1), f(s["lat_p95"], 1), f"${s['cost']:.5f}", f(s["tokens"], 0),
                     f(s["calls"], 1), f(s["retries"]), f(s["swaps"]), f(s["skipped"]), f(s["budget_ok"], 0)])
    return table(["Condition", "Runs", "Success %", "Check score", "Judge (0-1) mean +/- sd", "Median lat (s)",
                  "P95 lat (s)", "Mean cost", "Tokens", "Calls", "Retries", "Swaps", "Skipped", "Within budget %"], body)


def paired(rs, a, b, metric, scale=1.0, n_boot=3000):
    def per_task(c):
        d = defaultdict(list)
        for r in rs:
            if r["condition"] == c and r[metric] is not None:
                d[r["task_id"]].append(float(r[metric]) * scale)
        return {k: mean(v) for k, v in d.items()}
    A, B = per_task(a), per_task(b)
    ids = sorted(set(A) & set(B))
    if len(ids) < 3: return None
    diffs = [A[i] - B[i] for i in ids]
    rnd = random.Random(1)
    boots = sorted(mean([rnd.choice(diffs) for _ in diffs]) for _ in range(n_boot))
    return mean(diffs), boots[int(.025 * n_boot)], boots[int(.975 * n_boot)], len(ids)


md = [f"# Results tables (source: {SRC.name}, {len(rows)} runs)\n"]
models = rows[0].get("model_cfg") if rows else {}
md.append(f"Models used: {models}\n")
for budget in ("loose", "tight"):
    rs = [r for r in rows if r["budget"] == budget]
    if not rs: continue
    md.append(f"## Overall comparison, {budget} budget\n")
    md.append(overall(rs, [c for c in ORDER if c in ("single", "fixed_pipeline", "adaptive")]))
    abl = [c for c in ORDER if c.startswith("abl_") and any(r["condition"] == c for r in rs)]
    if abl:
        md.append(f"## Ablations, {budget} budget (compare with the 'adaptive' row)\n")
        md.append(overall(rs, ["adaptive"] + abl))
    md.append(f"## Success % and mean cost by task category, {budget} budget\n")
    body = []
    for c in [x for x in ORDER if x in ("single", "fixed_pipeline", "adaptive")]:
        row = [c]
        for cat in CATS:
            s = [r for r in rs if r["condition"] == c and r["category"] == cat]
            row.append("n/a" if not s else f"{mean([1.0 if r['passed'] else 0.0 for r in s]) * 100:.0f}% / ${mean([r['cost_usd'] for r in s]):.4f}")
        body.append(row)
    md.append(table(["Condition"] + CATS, body))
    md.append(f"## Paired differences, adaptive minus baseline ({budget} budget, per-task means, 95% bootstrap CI)\n")
    body = []
    for base in ("single", "fixed_pipeline"):
        for metric, label, scale in (("check_score", "check score", 1), ("judge", "judge quality", 1),
                                     ("latency_s", "latency (s)", 1), ("cost_usd", "cost ($)", 1), ("calls", "agent calls", 1)):
            res = paired(rs, "adaptive", base, metric, scale)
            if res: body.append([f"adaptive - {base}", label, f"{res[0]:+.4f}", f"[{res[1]:+.4f}, {res[2]:+.4f}]", res[3]])
    md.append(table(["Comparison", "Metric", "Mean diff", "95% CI", "Tasks"], body))
    ad = [r for r in rs if r["condition"] == "adaptive"]
    if ad:
        counts = defaultdict(int)
        for r in ad:
            for a in r["adapts"]: counts[a] += 1
        topo = defaultdict(int)
        for r in ad: topo[r["topology"]] += 1
        md.append(f"## Adaptive behaviour, {budget} budget\n")
        md.append("Adaptation events: " + (", ".join(f"{k}={v}" for k, v in sorted(counts.items())) or "none") + "\n")
        md.append("Topologies chosen: " + ", ".join(f"{k}={v}" for k, v in sorted(topo.items())) + "\n")
        pick = defaultdict(int)
        for r in ad:
            for _, aid in r["selections"]: pick[aid] += 1
        md.append("Agents selected: " + ", ".join(f"{k}={v}" for k, v in sorted(pick.items(), key=lambda kv: -kv[1])) + "\n")

(OUT / "tables.md").write_text("\n".join(md))
with open(OUT / "summary.csv", "w", newline="") as fh:
    w = csv.writer(fh); keys = None
    for budget in ("loose", "tight"):
        for c in ORDER:
            rs = [r for r in rows if r["budget"] == budget and r["condition"] == c]
            if not rs: continue
            s = summarize(rs)
            if keys is None:
                keys = list(s); w.writerow(["budget", "condition"] + keys)
            w.writerow([budget, c] + [round(s[k], 5) for k in keys])
print("Wrote", OUT / "tables.md", "and", OUT / "summary.csv")

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(5.5, 4))
    for c in ("single", "fixed_pipeline", "adaptive"):
        rs = [r for r in rows if r["budget"] == "loose" and r["condition"] == c]
        if rs:
            s = summarize(rs)
            ax.scatter(s["cost"], s["success"], s=90, label=c)
    ax.set_xlabel("Mean cost per task (notional USD)"); ax.set_ylabel("Success rate (%)")
    ax.legend(); ax.grid(alpha=.3); fig.tight_layout(); fig.savefig(OUT / "quality_vs_cost.png", dpi=200)
    print("Wrote", OUT / "quality_vs_cost.png")
except ImportError:
    print("matplotlib not installed; skipped the figure (pip install matplotlib)")
