"""Offline end-to-end test with a fake LLM (no API keys, no network)."""
import asyncio
import json
import os

os.environ["DB_PATH"] = ":memory:"

from app import llm, executor  # noqa: E402

PLAN = {"category": "multi_step", "complexity": 4, "subtasks": [
    {"id": "s1", "title": "Collect revenue facts", "instruction": "Collect revenue facts about the company", "capabilities": ["research"], "depends_on": [], "difficulty": 1},
    {"id": "s2", "title": "Collect cost facts", "instruction": "Collect cost facts about the company", "capabilities": ["research"], "depends_on": [], "difficulty": 3},
    {"id": "s3", "title": "Verify figures", "instruction": "Verify the figures", "capabilities": ["review"], "depends_on": ["s1", "s2"], "difficulty": 1},
]}
GOOD = ("Revenue and cost facts about the company are summarised here. The company reported revenue growth. "
        "- Revenue rose steadily over the period.\n- Costs were controlled and the figures were verified carefully.\n"
        "Overall the figures about revenue and cost look consistent.")


async def fake_complete(prompt, system, tier, max_tokens=900, temperature=0.3):
    if "task planner" in system:
        text = json.dumps(PLAN)
    elif "grade answers" in system:
        text = '{"score": 8}'
    else:
        text = GOOD
    await asyncio.sleep(0.01)
    return llm.CallRecord(model="fake", tier=tier, text=text, tokens_in=300, tokens_out=200,
                          cost=llm.est_cost(tier, 300, 200), latency=0.01, attempts=1, success=True)


def run_strategy(strategy):
    llm.complete = fake_complete
    run = executor.Run("Analyze the company revenue and costs", strategy, 0.05, 60, "balanced", True)
    asyncio.run(executor.execute(run))
    return run


def test_adaptive_hybrid_and_early_stop():
    run = run_strategy("adaptive")
    types = [e["type"] for e in run.events]
    topo = next(e for e in run.events if e["type"] == "topology")
    assert topo["topology"] == "hybrid" and topo["max_parallel"] >= 2
    assert any(e["type"] == "adapt" and e["action"] == "early_stop" for e in run.events)
    assert "synthesis_start" in types and run.status == "done"
    assert run.final["metrics"]["cost_usd"] > 0 and run.final["metrics"]["budget_ok"]


def test_single_baseline_one_call():
    run = run_strategy("single")
    assert run.final["metrics"]["agent_calls"] == 1


def test_fixed_pipeline_runs_all_three():
    run = run_strategy("fixed_pipeline")
    assert run.final["metrics"]["steps_done"] == 3
