"""Agent definitions, capability metadata and the registry with learned statistics."""
from __future__ import annotations

from dataclasses import dataclass, field

from . import config, llm

CAPABILITIES = ["research", "analysis", "coding", "writing", "review"]
_K = config.SHRINKAGE_K


def _default_cost(tier: str) -> float:
    return llm.est_cost(tier, 600, 500)


@dataclass
class Agent:
    id: str
    name: str
    description: str
    capabilities: frozenset
    tier: str
    system: str
    prior_quality: float
    prior_success: float
    prior_latency: float
    selectable: bool = True
    # running statistics (learned during use)
    calls: int = 0
    ok: int = 0
    n: int = 0
    q_sum: float = 0.0
    lat_sum: float = 0.0
    cost_sum: float = 0.0

    # --- shrinkage estimators: (observed_sum + K * prior) / (count + K) ---
    def quality_hat(self) -> float:
        return (self.q_sum + _K * self.prior_quality) / (self.n + _K)

    def success_hat(self) -> float:
        return (self.ok + _K * self.prior_success) / (self.calls + _K)

    def latency_hat(self) -> float:
        return (self.lat_sum + _K * self.prior_latency) / (self.n + _K)

    def cost_hat(self) -> float:
        return (self.cost_sum + _K * _default_cost(self.tier)) / (self.n + _K)

    def record(self, success: bool, score: float, latency: float, cost: float) -> None:
        self.calls += 1
        if success:
            self.ok += 1
            self.n += 1
            self.q_sum += score
            self.lat_sum += latency
            self.cost_sum += cost

    async def run(self, instruction: str, context: list[tuple[str, str]]) -> llm.CallRecord:
        ctx = "\n\n".join(f"[{title}]\n{out[:1500]}" for title, out in context)
        prompt = instruction + (f"\n\nContext from earlier steps:\n{ctx}" if ctx else "")
        return await llm.complete(prompt, self.system, self.tier, max_tokens=800)

    def public(self) -> dict:
        return {
            "id": self.id, "name": self.name, "description": self.description,
            "capabilities": sorted(self.capabilities), "tier": self.tier,
            "model": config.MODELS[self.tier], "selectable": self.selectable,
            "est_quality": round(self.quality_hat(), 3),
            "est_success": round(self.success_hat(), 3),
            "est_latency_s": round(self.latency_hat(), 2),
            "est_cost": round(self.cost_hat(), 6),
            "calls": self.calls, "observations": self.n,
        }


_STYLE = " Be accurate and concise (under 300 words unless code is required). No filler."

AGENTS: list[Agent] = [
    Agent("research_fast", "Research (fast)", "Quick factual lookup and summaries on a small model.",
          frozenset({"research", "writing"}), "cheap",
          "You are a research assistant. Give clear, factual, well-organised findings." + _STYLE,
          0.60, 0.90, 2.5),
    Agent("research_deep", "Research (deep)", "Thorough research and reasoning on a strong model.",
          frozenset({"research", "analysis", "writing"}), "strong",
          "You are a senior researcher. Give thorough, nuanced, well-structured findings and state uncertainty." + _STYLE,
          0.88, 0.93, 6.0),
    Agent("analyst", "Data analyst", "Quantitative reasoning, comparisons and structured analysis.",
          frozenset({"analysis", "writing"}), "strong",
          "You are a data analyst. Reason step by step with numbers, tables or lists where useful, and state assumptions." + _STYLE,
          0.89, 0.93, 6.0),
    Agent("coder_fast", "Coder (fast)", "Small scripts and simple code fixes on a small model.",
          frozenset({"coding"}), "cheap",
          "You are a programmer. Return correct, runnable code in a fenced code block plus a one-paragraph explanation." + _STYLE,
          0.60, 0.90, 2.5),
    Agent("coder_deep", "Coder (deep)", "Complex code, debugging and algorithms on a strong model.",
          frozenset({"coding"}), "strong",
          "You are a senior software engineer. Return correct, tested-by-reasoning code in a fenced block, handle edge cases, then explain briefly." + _STYLE,
          0.88, 0.93, 6.5),
    Agent("critic", "Reviewer", "Checks earlier outputs for errors, gaps and inconsistencies.",
          frozenset({"review"}), "cheap",
          "You are a strict reviewer. List concrete errors, gaps or contradictions in the given material, then give corrected key points." + _STYLE,
          0.70, 0.92, 2.5),
    Agent("generalist", "Generalist", "Single-agent baseline: one strong model for everything.",
          frozenset(CAPABILITIES), "strong",
          "You are a capable assistant. Answer the task fully and accurately." + _STYLE,
          0.85, 0.93, 6.0, selectable=False),
]


def get_agent(agent_id: str) -> Agent:
    return next(a for a in AGENTS if a.id == agent_id)
