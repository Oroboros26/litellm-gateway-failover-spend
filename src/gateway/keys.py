"""Create teams and per-team virtual keys with budgets and rate limits via the LiteLLM admin API."""
import os

import httpx

# team -> (max_budget USD, budget_duration, rpm, tpm)
TEAMS = {
    "search": (50.0, "30d", 300, 200_000),
    "support-bot": (20.0, "30d", 100, 80_000),
    "sandbox": (1.0, "1d", 10, 10_000),
}


def main() -> None:
    url = os.environ.get("LITELLM_URL", "http://localhost:4000")
    c = httpx.Client(base_url=url, headers={"Authorization": f"Bearer {os.environ['LITELLM_MASTER_KEY']}"})
    for team, (budget, dur, rpm, tpm) in TEAMS.items():
        tid = c.post("/team/new", json={"team_alias": team}).json()["team_id"]
        key = c.post("/key/generate", json={
            "team_id": tid, "key_alias": f"{team}-default", "models": ["chat"],
            "max_budget": budget, "budget_duration": dur, "rpm_limit": rpm, "tpm_limit": tpm,
        }).json()["key"]
        print(f"{team}: {key}")  # shown once; store in the team's secret manager


if __name__ == "__main__":
    main()
