import json
import os
import random
import time
from pathlib import Path

import httpx

SEED = 42
RESULTS = Path(__file__).parent / "results"
GATEWAY = os.getenv("GATEWAY_URL", "http://localhost:8080")
LITELLM = os.getenv("LITELLM_URL", "http://localhost:4000")
KEY = os.getenv("EVAL_KEY", "")  # a virtual key from `make keys`
random.seed(SEED)

BODY = {"model": "chat", "max_tokens": 32, "messages": [{"role": "user", "content": "Reply with: ok"}]}


def pct(xs: list[float], p: float) -> float:
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(p / 100 * len(xs)))]


def save(name: str, data: dict) -> Path:
    RESULTS.mkdir(exist_ok=True)
    p = RESULTS / f"{name}_{time.strftime('%Y%m%dT%H%M%S')}.json"
    p.write_text(json.dumps(data, indent=2))
    return p


def headers() -> dict:
    return {"Authorization": f"Bearer {KEY}"}


def client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=60)
