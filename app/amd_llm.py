"""AMD TokenFactory (Radeon Cloud) client — OpenAI-compatible chat completions.

Stdlib only. Reads configuration from environment variables; NEVER hardcode keys.

  AMD_API_KEY     key ("rc-...") from the AMD TokenFactory console   (required to enable)
  AMD_BASE_URL    default https://developer.amd.com.cn/radeon/api/v1
  AMD_MODEL       default DeepSeek-V4-Flash (any model listed by GET /models)

If AMD_API_KEY is unset or a call fails, callers fall back to the offline
deterministic path and the API response says so (`llm.used == false`).
Nothing is reported as running on AMD unless a real call succeeded.
"""

from __future__ import annotations

import json
import os
import urllib.request

DEFAULT_BASE = "https://developer.amd.com.cn/radeon/api/v1"
DEFAULT_MODEL = "DeepSeek-V4-Flash"


def configured() -> bool:
    return bool(os.environ.get("AMD_API_KEY"))


def settings() -> dict:
    return {
        "base_url": os.environ.get("AMD_BASE_URL", DEFAULT_BASE).rstrip("/"),
        "model": os.environ.get("AMD_MODEL", DEFAULT_MODEL),
        "configured": configured(),
    }


def chat(messages: list[dict], max_tokens: int = 400, temperature: float = 0.2, timeout: int = 40) -> str:
    """POST /chat/completions on AMD-hosted model. Raises on any failure."""
    s = settings()
    body = json.dumps(
        {"model": s["model"], "messages": messages, "max_tokens": max_tokens, "temperature": temperature}
    ).encode()
    req = urllib.request.Request(
        s["base_url"] + "/chat/completions",
        data=body,
        headers={
            "Authorization": "Bearer " + os.environ["AMD_API_KEY"],
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode())
    return data["choices"][0]["message"]["content"].strip()


SYSTEM = (
    "You are ShelfSense, a shopping assistant for a skincare catalogue. Answer ONLY from the "
    "evidence provided. Cite evidence ids like [E1]. If evidence is insufficient, say so. "
    "Max 3 sentences."
)


def grounded_answer(question: str, recs: list[dict], citations: list[dict]) -> str:
    ev = []
    for i, c in enumerate(citations, 1):
        ev.append(f"[E{i}] ({c['type']} {c['sku']}) {c['snippet']}")
    rec_lines = [f"{r['sku']} {r['title']} (${r.get('price_usd')})" for r in recs[:3]]
    user = (
        f"Question: {question}\nRanked candidates: {'; '.join(rec_lines)}\nEvidence:\n"
        + "\n".join(ev)
    )
    return chat([{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}])


def extract_attributes(title: str, description: str, reviews: list[str]) -> dict:
    """Ask the AMD-hosted LLM to fill skin_type / concerns as JSON."""
    prompt = (
        "From this product text return ONLY JSON {\"skin_type\":[...],\"concerns\":[...]} using "
        "short lowercase terms; use [] when unsupported.\n"
        f"Title: {title}\nDescription: {description}\nReviews: {' | '.join(reviews)[:800]}"
    )
    out = chat([{"role": "user", "content": prompt}], max_tokens=150, temperature=0)
    s, e = out.find("{"), out.rfind("}")
    return json.loads(out[s : e + 1])
