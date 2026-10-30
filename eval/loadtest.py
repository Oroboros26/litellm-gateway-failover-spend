"""Load test: gateway vs direct LiteLLM, to measure added latency, plus the cache-on case.
Both paths hit the same mock-friendly model; use a cheap model so cost stays tiny."""
import asyncio
import time

from eval.common import BODY, GATEWAY, LITELLM, client, headers, pct, save

N, CONCURRENCY = 2000, 50


async def run(url: str, unique: bool) -> dict:
    sem, lat, errs = asyncio.Semaphore(CONCURRENCY), [], 0

    async def one(c, i):
        nonlocal errs
        body = dict(BODY, messages=[{"role": "user", "content": f"Reply with: ok {i if unique else 0}"}])
        async with sem:
            t = time.perf_counter()
            r = await c.post(url, json=body, headers=headers())
            lat.append((time.perf_counter() - t) * 1000)
            errs += r.status_code != 200

    t0 = time.perf_counter()
    async with client() as c:
        await asyncio.gather(*(one(c, i) for i in range(N)))
    wall = time.perf_counter() - t0
    return {"req_s": round(N / wall, 1), "p50_ms": round(pct(lat, 50)), "p95_ms": round(pct(lat, 95)),
            "error_rate": errs / N}


async def main() -> None:
    out = {
        "direct_litellm": await run(f"{LITELLM}/chat/completions", unique=True),
        "via_gateway": await run(f"{GATEWAY}/v1/chat/completions", unique=True),
        "via_gateway_cache_hit": await run(f"{GATEWAY}/v1/chat/completions", unique=False),
        "n": N, "concurrency": CONCURRENCY,
    }
    out["added_p95_ms"] = out["via_gateway"]["p95_ms"] - out["direct_litellm"]["p95_ms"]
    print(save("loadtest", out))


if __name__ == "__main__":
    asyncio.run(main())
