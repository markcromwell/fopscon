"""Portfolio home BFF endpoint (design §8 Slice 0).

Aggregates LIVE SOV program state into the FINALIZED-DESIGN card shape: every program as a card with
its idea-sentence, lifecycle stage, health, and a Trust Strip. The Trust Strip is COMPUTED from the
program's assurance data — and where that data is not yet wired (the governance/assurance endpoint is
a known, specific gap), the strip is honestly 'unknown', never a fabricated green (the Trust Strip law).
"""
from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException

from app.config import settings
from app.trust_strip import build_trust_strip

router = APIRouter(prefix="/api", tags=["portfolio"])


def _lifecycle_stage(prog: dict) -> str:
    """Coarse idea → vision → building → living stage derived from SOV program state."""
    if prog.get("is_topic"):
        return "topic"
    deploy = prog.get("deploy_type") or (prog.get("deploy_config") or {}).get("type")
    if deploy:
        return "living"
    if prog.get("clone_status") == "ready" or prog.get("repo_url"):
        return "building"
    return "idea"


def _idea_sentence(prog: dict) -> str:
    return (prog.get("description") or "").strip() or prog.get("name") or prog.get("code") or ""


async def _sov_get(client: httpx.AsyncClient, path: str):
    r = await client.get(
        settings.sov_base_url + path,
        headers={"X-API-Key": settings.sov_api_key},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


@router.get("/portfolio")
async def portfolio() -> dict:
    """Every deliverable program as a card with a data-computed Trust Strip.

    Assurance-source honesty: the per-program assurance manifests are a known gap
    (`/governance/summary` currently errors), so each card's Trust Strip resolves to 'no assurance
    data yet' — the console shows the truth (unknown), never asserts green. When the assurance endpoint
    lands, feed its per-feature items into ``build_trust_strip`` and the mixbar reflects real data with
    zero change to this shape.
    """
    try:
        async with httpx.AsyncClient() as client:
            raw = await _sov_get(client, "/coding/programs")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"SOV /coding/programs unavailable: {exc}") from exc

    progs = raw.get("programs") if isinstance(raw, dict) else raw
    progs = progs or []
    cards = []
    for p in progs:
        if p.get("is_topic"):
            continue  # topics are containers, not deliverable programs
        assurance_items: list = []  # gap: per-program assurance not yet wired -> honest 'unknown'
        cards.append({
            "id": p.get("id"),
            "code": p.get("code"),
            "name": p.get("name"),
            "idea_sentence": _idea_sentence(p),
            "lifecycle_stage": _lifecycle_stage(p),
            "health": {"clone_status": p.get("clone_status"), "active": p.get("active")},
            "trust_strip": build_trust_strip(assurance_items),
            "repo_url": p.get("repo_url"),
        })
    return {
        "programs": cards,
        "count": len(cards),
        "portfolio_trust_strip": build_trust_strip([]),
        # honest gap disclosure — surfaced so the UI can show "assurance pending" not a false green
        "assurance_source": "unavailable",
    }
