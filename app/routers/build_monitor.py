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
    "failed", "push_failed", "push_error", "needs_human", "error", "blocked",
})

# Phase statuses that are EXPLICITLY benign — normal flow / in-progress / success. On a "a failure is
# impossible to miss" screen, GREEN REQUIRES EXPLICIT SUCCESS (CoEv2 honesty catch): only these render
# calm. Anything that is neither failing NOR explicitly-ok is classed "unknown" and the client renders it
# DISTINCTLY (neutral/amber), never green-by-default — a novel/unrecognized status must not read as fine.
KNOWN_OK_PHASE_STATUSES = frozenset({
    "pending", "queued", "running", "implementing", "dispatched",
    "reviewing", "in_review", "waiting_approval",
    "done", "complete", "merged", "passed",
})


def status_class(status: str) -> str:
    """failing → RED · ok → calm · unknown → neutral/distinct (never green-by-default)."""
    if status in FAILING_PHASE_STATUSES:
        return "failing"
    if status in KNOWN_OK_PHASE_STATUSES:
        return "ok"
    return "unknown"


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
    cls = status_class(status)
    return {
        "seq": p.get("seq"),
        "title": p.get("title") or "",
        "type": p.get("phase_type") or p.get("type") or "",
        "status": status,
        "status_class": cls,             # ok | failing | unknown — the client colours from this
        "failing": cls == "failing",     # the client renders this RED — honesty, not smoothing
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
        degraded: list[str] = []

        async def _specs():
            raw = await _sov_get(client, f"/coding/specs?program_id={pid}")
            # A 200 with an UNRECOGNIZED shape must NOT read as "no active build" (the Slice-2 inversion,
            # applied here): _as_list would return [] either way, so we detect a malformed read explicitly
            # and flag `degraded` — the client then renders "couldn't read build state", not a reassuring idle.
            recognizable = isinstance(raw, list) or (
                isinstance(raw, dict) and any(isinstance(raw.get(k), list) for k in ("specs", "data"))
            )
            if not recognizable:
                degraded.append("specs")
                return []
            specs = [s for s in _as_list(raw, "specs", "data") if s.get("program_id") == pid]
            active = [s for s in specs if (s.get("status") or "") not in _TERMINAL_OR_PRE]

            async def _with_phases(s):
                phases_unavailable = False
                try:
                    ph = await _sov_get(client, f"/coding/specs/{s['id']}/phases")
                    phases = [_phase_view(p) for p in _as_list(ph, "phases")]
                except Exception:  # noqa: BLE001 — a phase-fetch failure marks the spec, never a quiet green
                    phases, phases_unavailable = [], True
                return {
                    "id": s.get("id"),
                    "title": s.get("title"),
                    "status": s.get("status"),
                    "phases": phases,
                    "phases_unavailable": phases_unavailable,  # don't let an unread phase-set read as benign
                    "has_failure": any(p["failing"] for p in phases),          # roll-up: loud red badge
                    "has_unknown": any(p["status_class"] == "unknown" for p in phases),  # novel status → distinct
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

    # idle is only HONEST when the specs read succeeded and returned zero active. If the read was degraded
    # (malformed shape), it's idle_reason="unknown" and the client must render "couldn't read build state",
    # NOT the reassuring "no active build" (CoEv2 honesty note #1 — the same broken-read-reads-as-clear class).
    specs_ok = "specs" not in degraded
    idle = len(specs) == 0
    if not idle:
        idle_reason = ""
    elif specs_ok:
        idle_reason = "genuine"      # read OK, genuinely no active build → honest "idle"
    else:
        idle_reason = "unknown"      # couldn't read → NOT a confirmed idle
    return {
        "program": code,
        "specs": specs,
        "feed": feed,
        "stalled": stalled,
        "idle": idle,
        "idle_reason": idle_reason,
        "degraded": degraded,
        "source": "sov_forge_state",
    }
