"""Transparent agent-selection policy.

S(a,t) = w_cm*CM + w_q*Q + w_r*R - w_c*(1+2*pressure)*C_norm - w_l*L_norm
 CM  capability coverage, Q shrinkage-estimated quality (penalised for cheap agents on hard subtasks),
 R   success rate, C_norm/L_norm min-max normalised cost and latency among candidates,
 pressure = spent / budget (the cost weight grows as the budget is consumed).
Agents whose estimated cost exceeds the remaining budget are ranked last (hard feasibility filter).
"""
from __future__ import annotations

from . import config
from .agents import AGENTS, Agent, get_agent


def _norm(values: list[float]) -> list[float]:
    lo, hi = min(values), max(values)
    return [0.0 if hi - lo < 1e-12 else (v - lo) / (hi - lo) for v in values]


def rank(node, run) -> tuple[list[Agent], list[dict]]:
    w = config.PRIORITY_WEIGHTS[run.priority]
    flags = getattr(run, "flags", None) or {}
    remaining = run.remaining() if hasattr(run, "remaining") else run.budget_usd - run.spent
    pressure = 0.0 if flags.get("no_budget") else (
        min(1.0, run.spent / run.budget_usd) if run.budget_usd > 0 else 1.0)
    need = set(node.capabilities)

    rows = []
    for a in AGENTS:
        if not a.selectable:
            continue
        cm = len(a.capabilities & need) / max(1, len(need))
        if cm == 0:
            continue
        q = a.quality_hat()
        if a.tier == "cheap":
            q -= config.DIFFICULTY_PENALTY * (node.difficulty - 1)
        rows.append({"agent": a, "cm": cm, "q": max(0.0, q), "r": a.success_hat(),
                     "cost": a.cost_hat(), "lat": a.latency_hat()})
    if not rows:
        g = get_agent("generalist")
        rows.append({"agent": g, "cm": 1.0, "q": g.quality_hat(), "r": g.success_hat(),
                     "cost": g.cost_hat(), "lat": g.latency_hat()})

    if flags.get("static_selection"):
        # ablation: capability match only, ties broken by fixed registry order (no quality/cost/latency)
        for r in rows:
            r["score"], r["feasible"] = r["cm"], True
        rows.sort(key=lambda r: -r["cm"])
    else:
        cn = _norm([r["cost"] for r in rows])
        ln = _norm([r["lat"] for r in rows])
        w_cost = w["cost"] * (1 + 2 * pressure)
        for r, c, l in zip(rows, cn, ln):
            r["score"] = w["cm"] * r["cm"] + w["q"] * r["q"] + w["r"] * r["r"] - w_cost * c - w["lat"] * l
            r["feasible"] = r["cost"] <= remaining
        rows.sort(key=lambda r: (not r["feasible"], -r["score"]))

    details = [{
        "id": r["agent"].id, "name": r["agent"].name, "tier": r["agent"].tier,
        "cm": round(r["cm"], 2), "q": round(r["q"], 3), "r": round(r["r"], 3),
        "cost": round(r["cost"], 6), "lat": round(r["lat"], 2),
        "score": round(r["score"], 3), "feasible": r["feasible"],
    } for r in rows]
    return [r["agent"] for r in rows], details


def explain(node, details: list[dict]) -> str:
    top = details[0]
    text = (f"{top['name']} chosen for '{node.title}': capability match {top['cm']:.0%}, "
            f"estimated quality {top['q']:.2f}, estimated cost ${top['cost']:.5f}, score {top['score']:.3f}")
    if len(details) > 1:
        nxt = details[1]
        text += f". Runner-up {nxt['name']} scored {nxt['score']:.3f}."
    return text
