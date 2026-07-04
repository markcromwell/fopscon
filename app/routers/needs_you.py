"""Needs-You BFF (Slice 2, the PO heart / DoS #1) — the one genuinely-new backend piece.

Aggregates everything that needs a human DECISION across all programs into a single prioritized inbox,
so the PO resolves one in ≤3 taps. This is the highest-value screen after the door, and the aggregation
here also feeds #155 (notification/pause-and-ask).

HONESTY DISCIPLINE (the whole point): SOV's `/accept/reviewable` returns *every* subject in *every*
status (draft, complete, cancelled, …). Showing all of them would fabricate urgency. This module filters
to the states that genuinely await a human RIGHT NOW (waiting_po_review, waiting_definition_approval, …)
and honestly omits sources that aren't wired yet — it never invents a pending item. Empty → an honest
"nothing needs you", never a fake.

Sources aggregated (what's wired today):
  - GET /accept/reviewable   → MVP/story sign-offs waiting on the PO   → resolve POST /accept/{id}/programmer-decision
  - GET /coding/phases/needs-human → phases blocked needing a human    → resolve POST /coding/phases/{id}/approve
(PO-comms / clarifications: not wired yet → omitted honestly, per the story's guidance.)

Auth-gated (require_user).
"""
from __future__ import annotations

import asyncio

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import require_user
from app.config import settings

router = APIRouter(prefix="/api", tags=["needs-you"])

# Accept-subject statuses that genuinely need a human decision NOW. Everything else (draft, complete,
# accepted, cancelled, active, implementing) is NOT awaiting the PO and must not appear in the inbox.
PO_PENDING_STATUSES = frozenset({
    "waiting_po_review",
    "waiting_definition_approval",
    "needs_revision",
    "po_review",
    "waiting_review",
})

# Priority order for the inbox (lower = shown first). The PO's sign-off is the sharpest call.
_KIND_PRIORITY = {"signoff": 0, "clarify": 1, "prioritize": 2, "steer": 3}


class ResolveIn(BaseModel):
    decision: str = Field(..., min_length=1, max_length=40)  # e.g. accept | request_changes
    note: str | None = Field(default=None, max_length=4000)
    option: str | None = Field(default=None, max_length=200)


async def _sov_get(client: httpx.AsyncClient, path: str):
    r = await client.get(
        settings.sov_base_url + path,
        headers={"X-API-Key": settings.sov_api_key},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


async def _sov_post(client: httpx.AsyncClient, path: str, payload: dict):
    r = await client.post(
        settings.sov_base_url + path,
        headers={"X-API-Key": settings.sov_api_key},
        json=payload,
        timeout=20,
    )
    r.raise_for_status()
    return r.json()


def _accept_items(reviewable: dict, filtered_out: dict | None = None) -> list[dict]:
    """Map PO-pending accept subjects → NeedsItem. Filters to states awaiting a human (honesty).

    Observability (CoEv2 advisory #1): a genuinely-pending status we forgot to allowlist would make a real
    PO item silently invisible. So we tally every EXCLUDED status into `filtered_out` — an unexpected new
    status shows up as a non-zero count instead of vanishing (honest-partial applied to the filter itself).
    """
    out = []
    for s in (reviewable or {}).get("subjects", []):
        status = s.get("status")
        if status not in PO_PENDING_STATUSES:
            if filtered_out is not None:
                filtered_out[status] = filtered_out.get(status, 0) + 1
            continue
        sid = s.get("id")
        out.append({
            "id": f"accept:{sid}",
            "program": s.get("program_code") or "",
            "kind": "signoff",
            "ask": s.get("title") or f"{s.get('kind','')} #{sid}",
            "status": s.get("status"),
            "created_at": s.get("created_at") or s.get("updated_at"),
            "assurance": None,  # a TrustStrip rides here once the subject carries an assurance manifest
            "resolve": {"method": "POST", "url": f"/accept/{sid}/programmer-decision"},
        })
    return out


def _phase_items(phases) -> list[dict]:
    """Map needs-human phases → NeedsItem. These are blocked phases a human must clear."""
    items = phases if isinstance(phases, list) else (phases or {}).get("phases", [])
    out = []
    for p in items:
        pid = p.get("id")
        out.append({
            "id": f"phase:{pid}",
            "program": p.get("program_code") or (f"spec {p.get('spec_id')}" if p.get("spec_id") else ""),
            "kind": "steer",
            "ask": p.get("title") or f"phase #{pid} needs a human",
            "status": p.get("status") or "needs_human",
            "created_at": p.get("updated_at") or p.get("created_at"),
            "assurance": None,
            "resolve": {"method": "POST", "url": f"/coding/phases/{pid}/approve"},
        })
    return out


@router.get("/needs-you")
async def needs_you(user: dict = Depends(require_user)) -> dict:
    """One cross-program prioritized inbox of pending human decisions. Honest empty when nothing pends.

    A per-source fetch failure degrades to omitting THAT source (honest partial), never a crash and never
    a fabricated item — the PO sees what actually needs them, or an honest empty.
    """
    filtered_out: dict = {}
    degraded: list[str] = []
    async with httpx.AsyncClient() as client:
        async def _accepts():
            try:
                return _accept_items(await _sov_get(client, "/accept/reviewable"), filtered_out)
            except Exception:  # noqa: BLE001 — omit this source honestly, don't crash the inbox
                degraded.append("accept")
                return []

        async def _phases():
            try:
                return _phase_items(await _sov_get(client, "/coding/phases/needs-human"))
            except Exception:  # noqa: BLE001
                degraded.append("phases")
                return []

        accepts, phases = await asyncio.gather(_accepts(), _phases())

    items = accepts + phases
    items.sort(key=lambda i: (_KIND_PRIORITY.get(i["kind"], 9), str(i.get("created_at") or "")))
    # `filtered_out` = which STATUSES were excluded (an unlisted-but-pending status shows as a count, not a
    # silent drop — advisory #1). `degraded` = which SOURCES could not be reached (CoEv2 honesty catch): an
    # empty inbox with a non-empty `degraded` is NOT a confirmed all-clear — the client MUST render
    # "couldn't reach some sources" over that empty, never the reassuring "Nothing needs you". A broken
    # inbox must not read as green. Both are diagnostics, not inbox content.
    return {
        "items": items,
        "count": len(items),
        "source": "sov_live_aggregation",
        "filtered_out": filtered_out,
        "degraded": degraded,
    }


@router.post("/needs-you/{item_id}/resolve")
async def resolve(item_id: str, body: ResolveIn, user: dict = Depends(require_user)) -> dict:
    """Resolve one item (≤3 taps): route to the real SOV endpoint for its kind, then return the fresh list.

    The item_id encodes its source (`accept:{n}` / `phase:{n}`) so we proxy to the correct resolve endpoint.
    The action is real — no local mutation — so the item genuinely drops off the next fetch.
    """
    try:
        source, _, raw = item_id.partition(":")
        sid = int(raw)
    except (ValueError, AttributeError):
        raise HTTPException(400, f"bad item id: {item_id!r}")

    async with httpx.AsyncClient() as client:
        try:
            if source == "accept":
                # SOV's ProgrammerDecision REQUIRES actor + uses `notes` (not `note`), and accepts ONLY
                # decision ∈ {accept, request_changes} (422 otherwise). Send the resolver's identity as
                # actor so the sign-off is attributed to the real human, not anonymous.
                if body.decision not in ("accept", "request_changes"):
                    raise HTTPException(422, "sign-off decision must be 'accept' or 'request_changes'")
                payload = {
                    "actor": user.get("email") or "fopscon-po",
                    "decision": body.decision,
                    "notes": body.note or "",
                }
                await _sov_post(client, f"/accept/{sid}/programmer-decision", payload)
            elif source == "phase":
                # accept clears the phase; request_changes on a phase isn't a simple endpoint yet → reject
                if body.decision not in ("accept", "approve"):
                    raise HTTPException(422, "phase items support 'accept' (approve) only for now")
                await _sov_post(client, f"/coding/phases/{sid}/approve", {})
            else:
                raise HTTPException(400, f"unknown item source: {source!r}")
        except HTTPException:
            raise
        except httpx.HTTPStatusError as exc:
            raise HTTPException(exc.response.status_code, f"resolve failed: {exc.response.text[:200]}") from exc
        except httpx.HTTPError as exc:
            raise HTTPException(502, f"SOV unavailable: {exc}") from exc

    return await needs_you(user=user)
