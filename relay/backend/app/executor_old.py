"""Workflow execution engine: scheduling, budget tracking, evaluation, adaptation, synthesis.

Strategies (same engine, different policy switches):
  adaptive        LLM planner -> scored agent selection -> topology choice -> adaptation rules enabled
  single          one strong generalist call, no planning
  fixed_pipeline  research_deep -> analyst -> critic for every task, no adaptation (baseline)
"""
from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass

from . import config, evaluator, llm, planner, selector, store, topology
from .agents import Agent, get_agent
from .planner import Node


@dataclass
class NodeResult:
    id: str
    status: str  # done | failed | skipped
    output: str = ""
    score: float = 0.0
    agent_id: str = ""
    attempts: int = 0


class Run:
    def __init__(self, task: str, strategy: str, budget_usd: float, budget_s: float,
                 priority: str, judge: bool) -> None:
        self.id = uuid.uuid4().hex[:8]
        self.task, self.strategy, self.priority, self.judge = task, strategy, priority, judge
        self.budget_usd, self.budget_s = budget_usd, budget_s
        self.created = time.time()
        self.t0 = time.perf_counter()
        self.events: list[dict] = []
        self.status = "running"
        self.finished = False
        self.final: dict | None = None
        self.topology = ""
        self.spent = 0.0
        self.tokens_in = self.tokens_out = self.calls = 0
        self.retries = self.replacements = self.failures = self.skipped = 0

    def elapsed(self) -> float:
        return time.perf_counter() - self.t0

    def emit(self, type_: str, **data) -> None:
        self.events.append({"type": type_, "t": round(self.elapsed(), 2), **data})

    def charge(self, rec: llm.CallRecord, kind: str, label: str = "") -> None:
        self.spent += rec.cost
        self.tokens_in += rec.tokens_in
        self.tokens_out += rec.tokens_out
        self.calls += 1
        self.emit("call", kind=kind, label=label, model=rec.model, tokens_in=rec.tokens_in,
                  tokens_out=rec.tokens_out, cost=round(rec.cost, 6),
                  latency=round(rec.latency, 2), ok=rec.success)


# ---------------------------------------------------------------- preparation
async def _prepare(run: Run) -> tuple[list[Node], dict[str, list[Agent]], bool]:
    if run.strategy == "adaptive":
        plan = await planner.make_plan(run)
        run.emit("plan", category=plan.category, complexity=plan.complexity, source=plan.source,
                 nodes=[n.public() for n in plan.nodes])
        rankings: dict[str, list[Agent]] = {}
        for n in plan.nodes:
            ordered, details = selector.rank(n, run)
            rankings[n.id] = ordered
            run.emit("selection", node_id=n.id,
                     chosen={"id": ordered[0].id, "name": ordered[0].name, "tier": ordered[0].tier},
                     ranking=details, rationale=selector.explain(n, details))
        return plan.nodes, rankings, True

    if run.strategy == "single":
        nodes = [Node("n1", "Answer the task", run.task, ["research"], [], 2)]
        fixed = {"n1": "generalist"}
        reason = "Baseline: one strong generalist handles the whole task."
    else:
        nodes = [
            Node("n1", "Research", run.task + "\n\nGather the key facts and background needed.", ["research"], [], 2),
            Node("n2", "Analyze", run.task + "\n\nAnalyze and reason using the earlier findings.", ["analysis"], ["n1"], 2),
            Node("n3", "Review", "Review the earlier work on this task for errors and gaps:\n" + run.task, ["review"], ["n2"], 2),
        ]
        fixed = {"n1": "research_deep", "n2": "analyst", "n3": "critic"}
        reason = "Baseline: the same three agents run in sequence for every task."
    run.emit("plan", category="fixed", complexity=0, source="fixed", nodes=[n.public() for n in nodes])
    rankings = {}
    for n in nodes:
        a = get_agent(fixed[n.id])
        rankings[n.id] = [a]
        run.emit("selection", node_id=n.id, chosen={"id": a.id, "name": a.name, "tier": a.tier},
                 ranking=[], rationale=reason)
    return nodes, rankings, False


# ------------------------------------------------------------------ node logic
def _next_candidate(ordered: list[Agent], tried: list[str], remaining: float, current: str) -> Agent | None:
    for a in ordered:
        if a.id not in tried and a.id != current and a.cost_hat() <= remaining:
            return a
    return None


async def _run_node(run: Run, node: Node, nodes: dict[str, Node], ordered: list[Agent],
                    results: dict[str, NodeResult], adaptive: bool) -> NodeResult:
    deps = [results[d] for d in node.depends_on if d in results and results[d].status == "done"]

    def skip(reason: str, action: str) -> NodeResult:
        run.skipped += 1
        run.emit("adapt", node_id=node.id, action=action, reason=reason)
        run.emit("node_end", node_id=node.id, status="skipped", output="", score=0.0, agent_id="", note=reason)
        return NodeResult(node.id, "skipped")

    if node.depends_on and not deps:
        return skip("All dependencies failed or were skipped.", "skip")
    if adaptive:
        if run.elapsed() > run.budget_s:
            return skip("Latency budget exhausted before this step started.", "stop")
        if set(node.capabilities) == {"review"} and deps and min(d.score for d in deps) >= config.TAU_HIGH:
            return skip(f"Earlier output scored {min(d.score for d in deps):.2f} (>= {config.TAU_HIGH}); "
                        "a reviewer adds little expected value.", "early_stop")

    context = [(nodes[d.id].title, d.output) for d in deps]
    max_attempts = config.MAX_ATTEMPTS_PER_NODE if adaptive else 1
    agent, tried, attempts, same_retry = ordered[0], [], 0, 0
    best: NodeResult | None = None

    while attempts < max_attempts:
        remaining = run.budget_usd - run.spent
        if adaptive and agent.cost_hat() > remaining:
            alt = _next_candidate(ordered, tried, remaining, agent.id)
            if alt is None:
                if best:
                    break
                return skip(f"Remaining budget ${remaining:.5f} cannot cover any candidate agent.", "skip")
            run.replacements += 1
            run.emit("adapt", node_id=node.id, action="replace",
                     reason=f"Budget: {agent.name} (~${agent.cost_hat():.5f}) exceeds remaining "
                            f"${remaining:.5f}; switching to {alt.name}.")
            agent = alt

        attempts += 1
        run.emit("node_start", node_id=node.id, agent_id=agent.id, agent_name=agent.name,
                 tier=agent.tier, attempt=attempts)
        rec = await agent.run(node.instruction, context)
        run.charge(rec, "agent", f"{agent.name}: {node.title}")

        if not rec.success:
            agent.record(False, 0.0, rec.latency, rec.cost)
            run.failures += 1
            run.emit("attempt", node_id=node.id, agent_id=agent.id, ok=False, score=0.0, error=rec.error)
            if adaptive and same_retry < 1:
                same_retry += 1
                run.retries += 1
                run.emit("adapt", node_id=node.id, action="retry",
                         reason=f"{agent.name} call failed ({rec.error}); retrying once.")
                continue
            tried.append(agent.id)
            nxt = _next_candidate(ordered, tried, run.budget_usd - run.spent, agent.id) if adaptive else None
            if nxt:
                run.replacements += 1
                run.emit("adapt", node_id=node.id, action="replace",
                         reason=f"{agent.name} failed twice; reassigning to {nxt.name}.")
                agent, same_retry = nxt, 0
                continue
            break

        score = evaluator.score(node.instruction, node.capabilities, rec.text)
        agent.record(True, score, rec.latency, rec.cost)
        run.emit("attempt", node_id=node.id, agent_id=agent.id, ok=True, score=score)
        if best is None or score > best.score:
            best = NodeResult(node.id, "done", rec.text, score, agent.id, attempts)
        if not adaptive or score >= config.TAU_LOW:
            break
        tried.append(agent.id)
        nxt = _next_candidate(ordered, tried, run.budget_usd - run.spent, agent.id)
        if nxt is None:
            break
        run.replacements += 1
        run.emit("adapt", node_id=node.id, action="replace",
                 reason=f"{agent.name} output scored {score:.2f} (< {config.TAU_LOW}); trying {nxt.name}.")
        agent, same_retry = nxt, 0

    if best is None:
        run.emit("node_end", node_id=node.id, status="failed", output="", score=0.0, agent_id=agent.id,
                 note="All attempts failed.")
        return NodeResult(node.id, "failed", agent_id=agent.id, attempts=attempts)
    best.attempts = attempts
    run.emit("node_end", node_id=node.id, status="done", output=best.output, score=best.score,
             agent_id=best.agent_id, note="")
    return best


async def _schedule(run: Run, nodes: list[Node], rankings: dict[str, list[Agent]],
                    max_parallel: int, adaptive: bool) -> dict[str, NodeResult]:
    by_id = {n.id: n for n in nodes}
    pending = dict(by_id)
    results: dict[str, NodeResult] = {}
    running: dict[str, asyncio.Task] = {}
    sem = asyncio.Semaphore(max_parallel)

    async def worker(n: Node) -> NodeResult:
        async with sem:
            try:
                return await _run_node(run, n, by_id, rankings[n.id], results, adaptive)
            except Exception as exc:  # never let one node crash the run
                run.failures += 1
                run.emit("node_end", node_id=n.id, status="failed", output="", score=0.0,
                         agent_id="", note=f"{type(exc).__name__}: {exc}")
                return NodeResult(n.id, "failed")

    while pending or running:
        ready = [n for n in pending.values() if all(d in results for d in n.depends_on)]
        for n in ready:
            del pending[n.id]
            running[n.id] = asyncio.create_task(worker(n))
        if not running:
            break
        await asyncio.wait(running.values(), return_when=asyncio.FIRST_COMPLETED)
        for nid in [k for k, t in running.items() if t.done()]:
            results[nid] = running.pop(nid).result()
    return results


# ------------------------------------------------------------------- finalize
async def _synthesize(run: Run, nodes: list[Node], results: dict[str, NodeResult]) -> str:
    done = [(n, results[n.id]) for n in nodes if n.id in results and results[n.id].status == "done"]
    remaining = run.budget_usd - run.spent
    tier = "strong"
    if run.strategy == "adaptive" and llm.est_cost("strong", 1500, 600) > remaining:
        tier = "cheap"
        run.emit("adapt", node_id="synthesis", action="downgrade",
                 reason=f"Remaining budget ${remaining:.5f} is too low for the strong model; synthesising with the cheap model.")
    run.emit("synthesis_start", tier=tier)
    parts = "\n\n".join(f"### {n.title}\n{r.output[:2000]}" for n, r in done)
    prompt = (f"Original task:\n{run.task}\n\nResults from specialist steps:\n{parts}\n\n"
              "Write the final answer to the original task. Merge the results, resolve contradictions, "
              "apply any reviewer corrections, and do not mention the steps or agents.")
    rec = await llm.complete(prompt, "You write clear, accurate final answers.", tier, max_tokens=1000)
    run.charge(rec, "synthesis", "Final synthesis")
    if rec.success and rec.text.strip():
        return rec.text
    return "\n\n".join(r.output for _, r in done)


async def _finalize(run: Run, nodes: list[Node], results: dict[str, NodeResult]) -> None:
    done = [results[n.id] for n in nodes if n.id in results and results[n.id].status == "done"]
    if not done:
        answer = "No answer was produced: every step failed or was skipped. See the event log for details."
    elif len(nodes) == 1:
        answer = done[0].output
    else:
        answer = await _synthesize(run, nodes, results)

    latency = run.elapsed()
    heuristic = evaluator.score(run.task, [], answer)
    judged = await evaluator.judge(run.task, answer) if (run.judge and done) else None
    metrics = {
        "total_latency_s": round(latency, 2), "cost_usd": round(run.spent, 6),
        "tokens_in": run.tokens_in, "tokens_out": run.tokens_out, "agent_calls": run.calls,
        "retries": run.retries, "replacements": run.replacements, "failures": run.failures,
        "skipped_steps": run.skipped, "steps_total": len(nodes), "steps_done": len(done),
        "heuristic_quality": heuristic, "judge_quality": judged, "topology": run.topology,
        "budget_ok": run.spent <= run.budget_usd and latency <= run.budget_s,
        "budget_usd": run.budget_usd, "budget_s": run.budget_s,
    }
    run.final = {"answer": answer, "metrics": metrics}
    run.status = "done" if done else "failed"
    run.emit("final", answer=answer, metrics=metrics)


async def execute(run: Run) -> None:
    try:
        run.emit("run_started", task=run.task, strategy=run.strategy, budget_usd=run.budget_usd,
                 budget_s=run.budget_s, priority=run.priority)
        nodes, rankings, adaptive = await _prepare(run)
        est = {n.id: rankings[n.id][0].latency_hat() for n in nodes}
        force = None if run.strategy == "adaptive" else ("single" if len(nodes) == 1 else "sequential")
        topo = topology.analyze(nodes, est, force)
        run.topology = topo["topology"]
        run.emit("topology", **topo)
        results = await _schedule(run, nodes, rankings, topo["max_parallel"], adaptive)
        await _finalize(run, nodes, results)
    except Exception as exc:
        run.emit("error", message=f"{type(exc).__name__}: {exc}")
        run.status = "failed"
    finally:
        run.finished = True
        try:
            store.save(run)
        except Exception:  # persistence must never break a run
            pass
