"""Central configuration. Everything tunable lives here."""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # dotenv optional for tests
    pass

MODELS = {
    "cheap": os.getenv("CHEAP_MODEL", "groq/llama-3.1-8b-instant"),
    "strong": os.getenv("STRONG_MODEL", "gemini/gemini-2.5-flash"),
    "judge": os.getenv("JUDGE_MODEL", "groq/llama-3.3-70b-versatile"),
}
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "groq/llama-3.3-70b-versatile")

# Free tiers cost $0, so budgets use NOTIONAL prices (USD per 1M tokens: input, output).
# They let the budget logic behave like a real paid deployment. Edit freely.
PRICES = {"cheap": (0.05, 0.08), "strong": (0.30, 2.50), "judge": (0.59, 0.79)}

MAX_CONCURRENT_CALLS = int(os.getenv("MAX_CONCURRENT_CALLS", "3"))
CALL_TIMEOUT_S = float(os.getenv("CALL_TIMEOUT_S", "60"))
CALL_RETRIES = int(os.getenv("CALL_RETRIES", "2"))

# Policy parameters
MAX_NODES = 6
TAU_LOW = 0.50            # below this score a node is re-assigned to another agent
TAU_HIGH = 0.80           # at/above this a reviewer step is considered unnecessary
MAX_ATTEMPTS_PER_NODE = 3
PARALLEL_OVERHEAD_S = 1.0  # estimated coordination overhead before parallel pays off
SHRINKAGE_K = 3            # prior strength for cold-start estimates
DIFFICULTY_PENALTY = 0.20  # quality penalty per difficulty level for cheap-tier agents

PRIORITY_WEIGHTS = {
    "quality":  {"cm": 0.30, "q": 0.40, "r": 0.15, "cost": 0.05, "lat": 0.05},
    "balanced": {"cm": 0.30, "q": 0.35, "r": 0.15, "cost": 0.12, "lat": 0.08},
    "economy":  {"cm": 0.30, "q": 0.15, "r": 0.15, "cost": 0.30, "lat": 0.15},
}

DB_PATH = os.getenv("DB_PATH", "relay.db")
