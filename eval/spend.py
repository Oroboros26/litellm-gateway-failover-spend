"""Spend attribution check: for each team, compare LiteLLM-logged cost with an independent
recompute from the logged token counts and a pinned price table. Provider invoices are the
real ground truth; paste invoice totals into INVOICE_USD to compare when available."""
import asyncio
import os
from collections import defaultdict

from eval.common import LITELLM, client, save

MASTER = os.getenv("LITELLM_MASTER_KEY", "")
# USD per 1M tokens (in, out). Placeholders: verify against provider pricing pages before use.
PRICES = {"gpt-4o-mini": (0.15, 0.60), "claude-haiku-5-5": (1.00, 5.00)}
INVOICE_USD: dict[str, float] = {}  # {"openai": 12.34, ...}


async def main() -> None:
    async with client() as c:
        r = await c.get(f"{LITELLM}/spend/logs", headers={"Authorization": f"Bearer {MASTER}"})
    logged, recomputed = defaultdict(float), defaultdict(float)
    for row in r.json():
        team = next((t[5:] for t in row.get("request_tags", []) if t.startswith("team:")), "untagged")
        pin, pout = PRICES.get(row["model"].split("/")[-1], (0, 0))
        logged[team] += row["spend"]
        recomputed[team] += (row["prompt_tokens"] * pin + row["completion_tokens"] * pout) / 1e6
    rows = {t: {"logged_usd": round(logged[t], 4), "recomputed_usd": round(recomputed[t], 4),
                "delta_pct": round(100 * (logged[t] - recomputed[t]) / recomputed[t], 2) if recomputed[t] else None}
            for t in logged}
    print(save("spend", {"teams": rows, "invoice_usd": INVOICE_USD}))


if __name__ == "__main__":
    asyncio.run(main())
