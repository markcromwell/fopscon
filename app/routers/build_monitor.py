"""Build-Monitor BFF (Slice 3, the operator-lens core) — watch a program's live forge progress.

Aggregates SOV's live forge state for ONE program into {specs, feed, stalled, idle}: the active specs with
each phase's state, a live loop-activity feed, and any stalled build with its blocker + recommended action.

HONESTY LAW (the same anti-hollow-green, applied to the build view): a FAILED phase/gate is passed through
VERBATIM so the client renders it LOUDLY (red) — this module never smooths a failure to green, never
fabricates an "all passed", and a program with no active build reports an honest `idle`, not a fake. Phase
status IS the gate outcome; we carry it as-is and let the client colour the failure states.

Sources (story BFF contract): the program's specs (/coding/specs?program_id) + per-active-spec phases
(/coding/specs/{id}/phases) + the loop pulse (/pipeline/pulse) + stalled builds (/coding/stalled-specs).
Auth-gated.
"""
from __future__ import annotations

import asyncio

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel  # noqa: F401 (kept for parity; response is a plain dict)

from app.auth import require_user
from app.config import settings

router = APIRouter(prefix="/api", tags=["build-monitor"])

# Spec statuses that represent an in-flight/relevant build (NOT complete/draft/cancelled — those aren't
# "active build"). An unknown status is INCLUDED (fail-open toward showing, so we never hide a live build).
_TERMINAL_OR_PRE = frozenset({"complete", "cancelled", "draft"})

# Phase statuses that are a FAILURE the operator must see loudly. Carried verbatim; the client renders RED.
FAILING_PHASE_STATUSES = frozenset({
    "failed", "push_failed", "needs_human", "error", "blocked", "push_error",
})


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


def _phase_view(p: dict) -> dict:
    status = p.get("status") or "unknown"
    return {
        "seq": p.get("seq"),
        "title": p.get("title") or "",
        "type": p.get("phase_type") or p.get("type") or "",
        "status": status,
        "failing": status in FAILING_PHASE_STATUSES,  # the client renders this RED — honesty, not smoothing
        "provider": p.get("provider_override") or p.get("provider"),
    }


def _feed_from_pulse(pulse: dict) -> list[dict]:
    """Condense the loop pulse into a small live-activity feed so the screen shows motion, honestly."""
    if not isinstance(pulse, dict):
        return []
    feed = []
    status = pulse.get("status")
    if status:
        feed.append({"actor": "pipeline", "event": f"loop status: {status}", "ts": pulse.get("as_of")})
    inflight = pulse.get("workers_in_flight")
    if inflight is not None:
        feed.append({"actor": "workers", "event": f"{inflight} worker(s) in flight", "ts": pulse.get("as_of")})
    age = pulse.get("last_worker_success_age_minutes")
    if age is not None:
        feed.append({"actor": "workers", "event": f"last worker success {age} min ago", "ts": pulse.get("last_worker_success_at")})
    for b in _as_list(pulse.get("blockers")):
        feed.append({
            "actor": "blocker",
            "event": f"phase {b.get('seq')} {b.get('status')}: {(b.get('phase_title') or '')[:60]}",
            "ts": None,
            "spec_id": b.get("spec_id"),
        })
    return feed


@router.get("/programs/{code}/build")
async def program_build(code: str, user: dict = Depends(require_user)) -> dict:
    """Live forge state for one program. `idle` when there is no active build (honest, not a fake)."""
    async with httpx.AsyncClient() as client:
        try:
            prog = await _sov_get(client, f"/coding/programs/{code}")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(exc.response.status_code, f"program {code}: {exc.response.text[:120]}") from exc
        except httpx.HTTPError as exc:
            raise HTTPException(502, f"SOV unavailable: {exc}") from exc
        pid = prog.get("id")

        async def _specs():
            raw = await _sov_get(client, f"/coding/specs?program_id={pid}")
            specs = [s for s in _as_list(raw, "specs", "data") if s.get("program_id") == pid]
            active = [s for s in specs if (s.get("status") or "") not in _TERMINAL_OR_PRE]

            async def _with_phases(s):
                try:
                    ph = await _sov_get(client, f"/coding/specs/{s['id']}/phases")
                    phases = [_phase_view(p) for p in _as_list(ph, "phases")]
                except Exception:  # noqa: BLE001 — a phase-fetch failure omits phases, never crashes the view
                    phases = []
                return {
                    "id": s.get("id"),
                    "title": s.get("title"),
                    "status": s.get("status"),
                    "phases": phases,
                    "has_failure": any(p["failing"] for p in phases),  # roll-up for a loud badge
                }

            return await asyncio.gather(*[_with_phases(s) for s in active])

        async def _stalled():
            try:
                raw = await _sov_get(client, "/coding/stalled-specs")
            except Exception:  # noqa: BLE001
                return []
            # stalled items carry a `program` field → filter to this program only (honest scoping)
            out = []
            for st in _as_list(raw, "stalled"):
                if (st.get("program") or "").upper() == code.upper():
                    out.append({
                        "spec_id": st.get("spec_id"),
                        "title": st.get("title"),
                        "stall_class": st.get("stall_class"),
                        "blocker": st.get("reason"),
                        "recommended_action": st.get("recommended_action"),
                        "since": st.get("status_since"),
                    })
            return out

        async def _feed():
            try:
                return _feed_from_pulse(await _sov_get(client, "/pipeline/pulse"))
            except Exception:  # noqa: BLE001
                return []

        try:
            specs, stalled, feed = await asyncio.gather(_specs(), _stalled(), _feed())
        except httpx.HTTPError as exc:
            raise HTTPException(502, f"SOV unavailable: {exc}") from exc

    return {
        "program": code,
        "specs": specs,
        "feed": feed,
        "stalled": stalled,
        "idle": len(specs) == 0,  # honest idle — no active build, not a fake "all clear"
        "source": "sov_forge_state",
    }
