"""Deterministic output evaluator (no LLM calls) + optional LLM judge for final answers."""
from __future__ import annotations

import ast
import re

from . import llm

REFUSAL = ("as an ai", "i cannot", "i can't", "i'm unable", "i am unable", "i don't have access")
STOP = set(
    "the and for with that this from into your have will about which their there what when where using use each "
    "also should would could than then them they been being over under more most such only some any can may our "
    "out are was were not but you his her its who how why give make write explain please".split()
)


def _keywords(text: str, limit: int = 10) -> list[str]:
    seen: list[str] = []
    for w in re.findall(r"[a-zA-Z][a-zA-Z\-]{3,}", text.lower()):
        if w not in STOP and w not in seen:
            seen.append(w)
    return seen[:limit]


def _structure(caps: list[str], text: str) -> float:
    if "coding" in caps:
        blocks = re.findall(r"```(\w*)\n(.*?)```", text, re.S)
        if not blocks:
            return 0.2
        best = 0.5
        for lang, body in blocks:
            if lang.lower() in ("python", "py", ""):
                try:
                    ast.parse(body)  # syntax check only, never executes code
                    best = max(best, 1.0)
                except SyntaxError:
                    best = max(best, 0.4)
            else:
                best = max(best, 0.8)
        return best
    has_sentences = len(re.findall(r"[.!?]", text)) >= 2
    has_list = bool(re.search(r"^\s*([-*]|\d+\.)\s", text, re.M))
    return 1.0 if (has_sentences and has_list) else (0.8 if has_sentences else 0.5)


def score(instruction: str, caps: list[str], text: str) -> float:
    """Heuristic quality proxy in [0,1]: length, keyword coverage, structure, refusal/truncation checks."""
    t = (text or "").strip()
    if not t:
        return 0.0
    words = len(t.split())
    length = min(1.0, words / (30 if "coding" in caps else 60))
    kws = _keywords(instruction)
    coverage = (sum(1 for k in kws if k in t.lower()) / len(kws)) if kws else 0.7
    coverage = min(1.0, coverage / 0.6)  # 60% keyword coverage earns full marks
    s = 0.3 * length + 0.4 * coverage + 0.3 * _structure(caps, t)
    if any(p in t.lower()[:200] for p in REFUSAL):
        s -= 0.3
    if not re.search(r"[.!?`)\]}:]\s*$", t):  # likely cut off by the token limit
        s -= 0.1
    return round(max(0.0, min(1.0, s)), 3)


async def judge(task: str, answer: str) -> float | None:
    """LLM-as-judge on the final answer, 1-10 mapped to 0-1. Evaluation overhead is NOT charged to the run."""
    rec = await llm.complete(
        f"Task:\n{task}\n\nAnswer:\n{answer[:3500]}",
        'You grade answers for correctness, completeness and clarity. Reply with JSON only: {"score": <integer 1-10>}',
        "judge", max_tokens=30, temperature=0.0,
    )
    if not rec.success:
        return None
    m = re.search(r"\d+", rec.text)
    if not m:
        return None
    return round(max(1, min(10, int(m.group(0)))) / 10, 2)
