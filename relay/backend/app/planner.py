"""Task analysis + decomposition into a validated DAG (the only 'planning' LLM call)."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from . import config, llm
from .agents import CAPABILITIES

PLANNER_SYSTEM = f"""You are a task planner for a multi-agent system. Break the user's task into the FEWEST subtasks needed.
Return ONLY valid JSON in exactly this schema:
{{"category":"qa|research|coding|data_analysis|multi_step","complexity":1,
 "subtasks":[{{"id":"s1","title":"short title, max 6 words","instruction":"self-contained instruction","capabilities":["research"],"depends_on":[],"difficulty":1}}]}}
Rules:
- complexity is 1-5. difficulty is 1-3 (3 = hard reasoning or complex code).
- Allowed capabilities: {", ".join(CAPABILITIES)}.
- A simple question gets exactly ONE subtask.
- At most {config.MAX_NODES} subtasks.
- Subtasks that do not need each other's output must have an empty depends_on so they can run in parallel.
- Use "review" only when verifying a previous subtask clearly adds value.
- Do NOT add a final "combine results" subtask; the system does that.
- Each instruction must contain everything the agent needs (it only sees its own instruction plus dependency outputs).
Output JSON only, no prose."""


@dataclass
class Node:
    id: str
    title: str
    instruction: str
    capabilities: list[str]
    depends_on: list[str] = field(default_factory=list)
    difficulty: int = 2

    def public(self) -> dict:
        return {"id": self.id, "title": self.title, "instruction": self.instruction,
                "capabilities": self.capabilities, "depends_on": self.depends_on,
                "difficulty": self.difficulty}


@dataclass
class Plan:
    category: str
    complexity: int
    nodes: list[Node]
    source: str = "llm"  # llm | fallback


def infer_caps(text: str) -> list[str]:
    t = text.lower()
    if re.search(r"\b(code|function|python|javascript|script|bug|debug|algorithm|program)\b", t):
        return ["coding"]
    if re.search(r"\b(data|analy[sz]e|csv|statistic|compare|calculate|trend|revenue)\b", t):
        return ["analysis"]
    return ["research"]


def fallback_plan(task: str) -> Plan:
    return Plan("qa", 2, [Node("s1", "Answer the task", task, infer_caps(task), [], 2)], "fallback")


def _extract_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("no JSON object found")
    return json.loads(m.group(0))


def _has_cycle(nodes: list[Node]) -> bool:
    indeg = {n.id: len(n.depends_on) for n in nodes}
    children: dict[str, list[str]] = {n.id: [] for n in nodes}
    for n in nodes:
        for d in n.depends_on:
            children[d].append(n.id)
    queue = [i for i, d in indeg.items() if d == 0]
    seen = 0
    while queue:
        cur = queue.pop()
        seen += 1
        for c in children[cur]:
            indeg[c] -= 1
            if indeg[c] == 0:
                queue.append(c)
    return seen != len(nodes)


def validate(raw: dict, task: str) -> Plan:
    subs = raw.get("subtasks") or []
    nodes: list[Node] = []
    used: set[str] = set()
    for i, s in enumerate(subs[: config.MAX_NODES], start=1):
        nid = str(s.get("id") or f"s{i}")
        if nid in used:
            nid = f"s{i}"
        used.add(nid)
        caps = [c for c in (s.get("capabilities") or []) if c in CAPABILITIES] or infer_caps(
            str(s.get("instruction", task)))
        try:
            diff = max(1, min(3, int(s.get("difficulty", 2))))
        except (TypeError, ValueError):
            diff = 2
        nodes.append(Node(nid, str(s.get("title") or f"Step {i}")[:60],
                          str(s.get("instruction") or task), caps,
                          [str(d) for d in (s.get("depends_on") or [])], diff))
    if not nodes:
        raise ValueError("empty plan")
    ids = {n.id for n in nodes}
    for n in nodes:
        n.depends_on = [d for d in dict.fromkeys(n.depends_on) if d in ids and d != n.id]
    if _has_cycle(nodes):  # repair: turn into a simple chain in given order
        for i, n in enumerate(nodes):
            n.depends_on = [nodes[i - 1].id] if i else []
    try:
        complexity = max(1, min(5, int(raw.get("complexity", 2))))
    except (TypeError, ValueError):
        complexity = 2
    return Plan(str(raw.get("category", "multi_step")), complexity, nodes)


async def make_plan(run) -> Plan:
    """Ask the cheap model first; retry once with the strong model; else fall back to one node."""
    for tier in ("cheap", "strong"):
        rec = await llm.complete(f"Task:\n{run.task}", PLANNER_SYSTEM, tier, max_tokens=900, temperature=0.1)
        run.charge(rec, "planner", "Task analysis and decomposition")
        if not rec.success:
            continue
        try:
            return validate(_extract_json(rec.text), run.task)
        except (ValueError, json.JSONDecodeError, AttributeError, TypeError):
            continue
    return fallback_plan(run.task)
