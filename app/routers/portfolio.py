"""Portfolio home BFF endpoint (design §8 Slice 0).

Aggregates LIVE SOV program state into the FINALIZED-DESIGN card shape: every program as a card with
its idea-sentence, lifecycle stage, health, and a Trust Strip COMPUTED from the histogram of that
program's ACCEPTED (delivered) increments' lock-states (app/assurance.py). Most programs are pre-Foundation
with no accepted increments -> the strip honestly reads 'no assurance data yet'; only Foundation-run
programs (e.g. KITH, FOPSCON) light up. Never a fabricated green (the Trust Strip law).
"""
from __future__ import annotations

import asyncio

import httpx
from fastapi import APIRouter, HTTPException

from app.assurance import program_trust_items
from app.config import settings
from app.trust_strip import build_trust_strip

router = APIRouter(prefix="/api", tags=["portfolio"])


def _lifecycle_stage(prog: dict) -> str:
    """Coarse idea -> vision -> building -> living stage derived from SOV program state."""
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


def _as_list(raw, *keys) -> list:
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        for k in keys:
            if isinstance(raw.get(k), list):
                return raw[k]
    return []


@router.get("/portfolio")
async def portfolio() -> dict:
    """Every deliverable program as a card with a Trust Strip computed from its accepted increments."""
    try:
        async with httpx.AsyncClient() as client:
            raw = await _sov_get(client, "/coding/programs")
            progs = _as_list(raw, "programs", "data")
            deliverable = [p for p in progs if not p.get("is_topic")]

            async def _items_for(p):
                pid = p.get("id")
                if pid is None:
                    return []
                try:
                    # NB: ?program=<code> is IGNORED by the API (returns a global recent set) — only
                    # ?program_id=<id> filters correctly. Wrong attribution would fabricate every card's
                    # Trust Strip, exactly the dishonesty the strip must never do.
                    specs = _as_list(await _sov_get(client, f"/coding/specs?program_id={pid}"), "specs", "data")
                    specs = [s for s in specs if s.get("program_id") == pid]  # defensive: only this program's
                    return program_trust_items(specs)
                except Exception:  # noqa: BLE001 — a per-program fetch failure -> honest 'no data', not a crash
                    return []

            items_per = await asyncio.gather(*[_items_for(p) for p in deliverable])
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"SOV unavailable: {exc}") from exc

    cards = []
    all_items: list = []
    for p, items in zip(deliverable, items_per):
        all_items.extend(items)
        cards.append({
            "id": p.get("id"),
            "code": p.get("code"),
            "name": p.get("name"),
            "idea_sentence": _idea_sentence(p),
            "lifecycle_stage": _lifecycle_stage(p),
            "health": {"clone_status": p.get("clone_status"), "active": p.get("active")},
            "trust_strip": build_trust_strip(items),
            "repo_url": p.get("repo_url"),
        })
    return {
        "programs": cards,
        "count": len(cards),
        "portfolio_trust_strip": build_trust_strip(all_items),
        "assurance_source": "sov_accept_records",  # histogram of accepted-increment lock-states
    }
