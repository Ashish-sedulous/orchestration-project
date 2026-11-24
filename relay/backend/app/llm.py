"""Async LLM client: concurrency cap, timeout, retry, model fallback, metrics."""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass

from . import config

log = logging.getLogger("llm")
_sem: asyncio.Semaphore | None = None


def _semaphore() -> asyncio.Semaphore:
    global _sem
    if _sem is None:
        _sem = asyncio.Semaphore(config.MAX_CONCURRENT_CALLS)
    return _sem


@dataclass
class CallRecord:
    model: str
    tier: str
    text: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    cost: float = 0.0
    latency: float = 0.0
    attempts: int = 0
    success: bool = False
    error: str | None = None


def est_cost(tier: str, tokens_in: int, tokens_out: int) -> float:
    pin, pout = config.PRICES[tier]
    return (tokens_in * pin + tokens_out * pout) / 1_000_000


async def complete(
    prompt: str,
    system: str,
    tier: str,
    max_tokens: int = 900,
    temperature: float = 0.3,
) -> CallRecord:
    """Call the model for `tier`; on repeated failure try the fallback model."""
    import litellm  # lazy import so unit tests run without the package

    litellm.drop_params = True
    models = [config.MODELS[tier]]
    if config.FALLBACK_MODEL not in models:
        models.append(config.FALLBACK_MODEL)

    messages = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
    rec = CallRecord(model=models[0], tier=tier)
    start = time.perf_counter()

    for model in models:
        for attempt in range(1, config.CALL_RETRIES + 1):
            rec.attempts += 1
            try:
                async with _semaphore():
                    resp = await asyncio.wait_for(
                        litellm.acompletion(
                            model=model, messages=messages,
                            temperature=temperature,
                            max_tokens=max_tokens + 1200,  # headroom: reasoning models spend tokens thinking
                            reasoning_effort="low",
                        ),
                        timeout=config.CALL_TIMEOUT_S,
                    )
                usage = resp.usage
                rec.model = model
                rec.tokens_in = int(getattr(usage, "prompt_tokens", 0) or 0)
                rec.tokens_out = int(getattr(usage, "completion_tokens", 0) or 0)
                rec.text = resp.choices[0].message.content or ""
                rec.cost = est_cost(tier, rec.tokens_in, rec.tokens_out)
                rec.success, rec.error = True, None
                rec.latency = time.perf_counter() - start
                return rec
            except Exception as exc:  # rate limit, timeout, provider error
                rec.error = f"{type(exc).__name__}: {str(exc)[:200]}"
                log.warning("LLM call failed (%s, attempt %d): %s", model, attempt, rec.error)
                await asyncio.sleep(1.5 * attempt)

    rec.latency = time.perf_counter() - start
    return rec
