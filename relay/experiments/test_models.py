#!/usr/bin/env python3
"""Check that every model in your .env really answers. Run before any experiment.

  python test_models.py                      # tests CHEAP, STRONG, JUDGE and FALLBACK from backend/.env
  python test_models.py gemini/gemini-3.5-flash gemini/gemini-3.6-flash   # test specific candidates
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
import litellm  # noqa: E402
from app import config  # noqa: E402

litellm.suppress_debug_info = True
litellm.drop_params = True


async def probe(label: str, model: str) -> bool:
    try:
        r = await asyncio.wait_for(litellm.acompletion(
            model=model, messages=[{"role": "user", "content": "Reply with the single word OK"}],
            max_tokens=1300, reasoning_effort="low"), timeout=60)
        text = (r.choices[0].message.content or "").strip().replace("\n", " ")[:40]
        print(f"  OK     {label:<9} {model}   reply: {text!r}")
        return True
    except Exception as exc:  # noqa: BLE001
        msg = str(exc).replace("\n", " ")
        print(f"  FAILED {label:<9} {model}\n         {type(exc).__name__}: {msg[:220]}")
        return False


async def main() -> None:
    if len(sys.argv) > 1:
        targets = [(f"cand{i + 1}", m) for i, m in enumerate(sys.argv[1:])]
    else:
        targets = [("cheap", config.MODELS["cheap"]), ("strong", config.MODELS["strong"]),
                   ("judge", config.MODELS["judge"]), ("fallback", config.FALLBACK_MODEL)]
    print("Testing models...")
    results = [await probe(l, m) for l, m in targets]
    print("\nAll good: you can run the experiments." if all(results)
          else "\nFix the FAILED models in backend/.env, then run this test again.")


asyncio.run(main())
