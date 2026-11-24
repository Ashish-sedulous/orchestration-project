"""Topology selection from DAG structure (pure Python, no LLM)."""
from __future__ import annotations

from . import config

MAX_PARALLEL = 3


def analyze(nodes, est_latency: dict[str, float], force: str | None = None) -> dict:
    by_id = {n.id: n for n in nodes}
    level: dict[str, int] = {}

    def lv(i: str) -> int:
        if i not in level:
            deps = by_id[i].depends_on
            level[i] = 1 + max(lv(d) for d in deps) if deps else 0
        return level[i]

    for n in nodes:
        lv(n.id)
    layers: dict[int, int] = {}
    for l in level.values():
        layers[l] = layers.get(l, 0) + 1
    width = max(layers.values())

    finish: dict[str, float] = {}

    def fin(i: str) -> float:
        if i not in finish:
            deps = by_id[i].depends_on
            finish[i] = est_latency[i] + (max(fin(d) for d in deps) if deps else 0.0)
        return finish[i]

    critical = max(fin(n.id) for n in nodes)
    sequential = sum(est_latency[n.id] for n in nodes)
    saving = sequential - critical

    info = {"width": width, "levels": len(layers), "critical_path_s": round(critical, 2),
            "sequential_s": round(sequential, 2), "saving_s": round(saving, 2)}

    if force:
        topo, reason = force, "Fixed by the selected baseline strategy."
        par = 1
    elif len(nodes) == 1:
        topo, par, reason = "single", 1, "One subtask: no coordination needed."
    elif width == 1:
        topo, par, reason = "sequential", 1, "Every subtask depends on the previous one."
    elif saving > config.PARALLEL_OVERHEAD_S:
        topo = "parallel" if len(layers) == 1 else "hybrid"
        par = min(MAX_PARALLEL, width)
        reason = (f"Independent subtasks exist (width {width}); estimated saving {saving:.1f}s exceeds "
                  f"the {config.PARALLEL_OVERHEAD_S:.1f}s coordination overhead.")
    else:
        topo, par = "sequential", 1
        reason = f"Parallel saving {saving:.1f}s does not beat the coordination overhead."
    return {"topology": topo, "max_parallel": par, "reason": reason, **info}
