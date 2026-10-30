"""Failover drill: send 1 req/s, then `docker pause` the primary provider stand-in.
Recovery time = first failed/slow request -> first fast success on the fallback.

Providers are real APIs, so we simulate an outage by pointing the OpenAI deployment at a
blackhole via LiteLLM's /model/update (or by blocking egress). Pass the command to run as
KILL_CMD, e.g. KILL_CMD="docker compose exec litellm sh -c 'echo 0.0.0.0 api.openai.com >> /etc/hosts'".
"""
import asyncio
import os
import subprocess
import time

from eval.common import BODY, GATEWAY, client, headers, save

DURATION_S, KILL_AT_S, SLOW_MS = 60, 15, 3000


async def main() -> None:
    log, killed_at = [], None
    t0 = time.perf_counter()
    async with client() as c:
        while (now := time.perf_counter() - t0) < DURATION_S:
            if killed_at is None and now >= KILL_AT_S:
                await asyncio.to_thread(subprocess.run, os.environ["KILL_CMD"], shell=True, check=True)
                killed_at = now
            t = time.perf_counter()
            r = await c.post(f"{GATEWAY}/v1/chat/completions", json=BODY, headers=headers())
            ms = (time.perf_counter() - t) * 1000
            log.append({"t": round(now, 1), "status": r.status_code, "ms": round(ms),
                        "model": r.json().get("model")})
            await asyncio.sleep(max(0, 1 - ms / 1000))

    bad = [x for x in log if x["t"] >= killed_at and (x["status"] != 200 or x["ms"] > SLOW_MS)]
    first_bad = bad[0]["t"] if bad else None
    ok_after = [x for x in log if first_bad and x["t"] > bad[-1]["t"] and x["status"] == 200]
    recovery = round(ok_after[0]["t"] - first_bad, 1) if ok_after else None
    print(save("failover", {"kill_at_s": killed_at, "failed_or_slow": len(bad),
                            "recovery_s": recovery, "log": log}))


if __name__ == "__main__":
    asyncio.run(main())
