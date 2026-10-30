"""Edge service in front of LiteLLM: custom auth, PII redaction, request tagging, clean errors."""
import os

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from gateway.pii import redact_messages

LITELLM_URL = os.getenv("LITELLM_URL", "http://localhost:4000")
FEATURES = set(filter(None, os.getenv("ALLOWED_FEATURES", "").split(",")))  # empty = any

app = FastAPI(title="ai-gateway-edge")
client = httpx.AsyncClient(base_url=LITELLM_URL, timeout=60)
_team_cache: dict[str, str] = {}  # Limitation: no TTL, restart on key rotation; add TTL if keys churn


def err(status: int, type_: str, msg: str) -> JSONResponse:
    return JSONResponse({"error": {"type": type_, "message": msg}}, status_code=status)


def normalize(status: int, body: dict) -> tuple[int, dict]:
    """LiteLLM reports an exhausted budget as HTTP 400; surface it as a clean 429."""
    e = body.get("error") or {}
    if status == 400 and (e.get("type") == "budget_exceeded" or "budget" in str(e.get("message", "")).lower()):
        return 429, {"error": {"type": "budget_exceeded", "message": "Team budget exhausted for this period."}}
    return status, body


async def team_of(key: str) -> str | None:
    if key not in _team_cache:
        r = await client.get("/key/info", headers={"Authorization": f"Bearer {key}"})
        if r.status_code != 200:
            return None
        info = r.json().get("info", {})
        _team_cache[key] = info.get("team_alias") or info.get("team_id") or "unassigned"
    return _team_cache[key]


@app.get("/healthz")
async def healthz():
    return {"ok": True}


@app.post("/v1/chat/completions")
async def chat(req: Request):
    key = req.headers.get("authorization", "").removeprefix("Bearer ").strip()
    if not key:
        return err(401, "auth", "Missing virtual key.")
    team = await team_of(key)
    if team is None:
        return err(401, "auth", "Invalid virtual key.")
    feature = req.headers.get("x-feature", "default")
    if FEATURES and feature not in FEATURES:
        return err(403, "feature", f"Unknown feature '{feature}'.")

    body = await req.json()
    if body.get("stream"):  # Limitation: no SSE passthrough yet, add when a client needs it
        return err(400, "unsupported", "stream=true not supported by the edge yet.")
    redactions = redact_messages(body.get("messages", []))
    body.setdefault("metadata", {})["tags"] = [f"team:{team}", f"feature:{feature}"]

    r = await client.post("/chat/completions", json=body, headers={"Authorization": f"Bearer {key}"})
    status, payload = normalize(r.status_code, r.json())
    return JSONResponse(payload, status_code=status, headers={"x-pii-redactions": str(redactions)})
