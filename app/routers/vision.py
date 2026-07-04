"""Idea → Vision BFF (Slice 1, the showpiece — FINALIZED-DESIGN §2 / CoEv2 gui-slice-1-story).

A typed idea becomes a *graded* Vision by proxying the REAL vision-gate: CoEv2 `POST /v1/vision/draft`
(shape the idea → statement + epics + stories) then `POST /v1/grade` (level="vision" → a computed grade
+ the gate's findings). Both council calls are async, so the BFF polls to completion (the SPA shows a
"shaping…" state for the latency).

Trust Strip law, at the Vision level (AC3): the grade is COMPUTED from the council, never asserted here.
A Vision that scores ≥0.60 AND is gate-eligible reads "ready" with its earned number; anything below
honestly reads "not ready yet" and surfaces the gate's specific findings (what's missing). This module
NEVER synthesizes praise — `ready` is derived purely from the council's own score+eligibility, and the
findings are passed straight through. That is the whole point of the screen.

Both endpoints are auth-gated (require_user) — DoS #4: no unauthenticated access to the council.
"""
from __future__ import annotations

import asyncio

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import require_user
from app.config import settings

router = APIRouter(prefix="/api", tags=["vision"])

VISION_GATE_THRESHOLD = 0.60  # the ≥0.60 vision-gate floor (mirrors SOV_VISION_GATE_FLOOR)


class IdeaIn(BaseModel):
    idea: str = Field(min_length=1, max_length=20000)


class StartIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    idea: str = Field(min_length=1, max_length=20000)
    vision: dict = Field(default_factory=dict)  # the drafted vision artifact (statement/epics/stories)


def derive_code(name: str) -> str:
    """A program code from the human name: uppercase alphanumerics, capped. Mirrors how codes are picked
    by hand (FOPSCON ← 'Foundation Operator Console'). Collisions surface as a 409 from SOV for the SPA
    to handle (pick another name) — we don't silently mutate the user's chosen identity."""
    code = "".join(ch for ch in name.upper() if ch.isalnum())[:24]
    return code or "PROGRAM"


async def _council_post(client: httpx.AsyncClient, path: str, payload: dict) -> dict:
    r = await client.post(
        settings.council_base_url + path,
        headers={"Authorization": f"Bearer {settings.council_api_key}"},
        json=payload,
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


async def _sov_post(client: httpx.AsyncClient, path: str, payload: dict) -> dict:
    r = await client.post(
        settings.sov_base_url + path,
        headers={"X-API-Key": settings.sov_api_key},
        json=payload,
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


async def _sov_patch(client: httpx.AsyncClient, path: str, payload: dict) -> dict:
    r = await client.patch(
        settings.sov_base_url + path,
        headers={"X-API-Key": settings.sov_api_key},
        json=payload,
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


async def _council_get(client: httpx.AsyncClient, path: str) -> dict:
    r = await client.get(
        settings.council_base_url + path,
        headers={"Authorization": f"Bearer {settings.council_api_key}"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


async def _poll(client: httpx.AsyncClient, kind: str, job_id: str) -> dict:
    """Poll GET /v1/{kind}/{job_id} until terminal. Returns the completed job, or raises 502/504.

    A failed council job must NEVER be silently treated as a pass (the whole anti-#158 point): a
    non-complete terminal status raises, it does not fall through to a fabricated grade.
    """
    waited = 0.0
    while True:
        job = await _council_get(client, f"/v1/{kind}/{job_id}")
        status = str(job.get("status") or "").lower()
        if status.startswith("complet"):
            return job
        if status in ("failed", "error", "cancelled", "canceled"):
            raise HTTPException(502, f"council {kind} job {status}: {job.get('error_message') or ''}")
        if waited >= settings.council_poll_timeout_s:
            raise HTTPException(504, f"council {kind} job timed out after {int(waited)}s (status={status})")
        await asyncio.sleep(settings.council_poll_interval_s)
        waited += settings.council_poll_interval_s


def _extract_vision(artifact: dict) -> dict:
    """Pull the human-facing statement + epics/stories out of the drafted vision artifact.

    Defensive: the council may phrase the fields slightly differently across modes. We render what's
    there and never invent structure that isn't.
    """
    art = artifact or {}
    statement = (art.get("statement") or art.get("body_text") or "").strip()
    epics = []
    for e in art.get("epics") or []:
        if isinstance(e, dict):
            stories = [
                (s.get("title") if isinstance(s, dict) else s)
                for s in (e.get("stories") or [])
            ]
            epics.append({"title": e.get("title") or e.get("name") or "", "stories": [s for s in stories if s]})
        elif isinstance(e, str) and e.strip():
            epics.append({"title": e.strip(), "stories": []})
    return {"statement": statement, "epics": epics}


def grade_view(grade_job: dict) -> dict:
    """The honest grade view (Trust Strip law). `ready` is COMPUTED from the council's own score +
    eligibility — this function synthesizes NOTHING. Below threshold (or ineligible) → the gate's
    findings ride along so the screen can show *what's missing*, never blanket praise.
    """
    score = grade_job.get("score")
    eligible = bool(grade_job.get("eligible"))
    numeric = isinstance(score, (int, float)) and not isinstance(score, bool)
    ready = eligible and numeric and float(score) >= VISION_GATE_THRESHOLD
    findings = []
    for f in grade_job.get("findings") or []:
        if isinstance(f, dict):
            findings.append({
                "severity": (f.get("severity") or "info"),
                "issue": (f.get("issue") or f.get("why") or "").strip(),
            })
    return {
        "grade": (float(score) if numeric else None),
        "gate": {
            "eligible": eligible,
            "threshold": VISION_GATE_THRESHOLD,
            "ready": ready,
            "findings": findings,
        },
    }


@router.post("/vision/draft")
async def vision_draft(body: IdeaIn, user: dict = Depends(require_user)) -> dict:
    """Shape a typed idea into a graded Vision. Draft (shape) → grade (vision-gate) → honest render.

    Returns {statement, epics:[{title, stories}], grade: number|null, gate:{eligible, threshold, ready,
    findings:[{severity, issue}]}}. A passing grade (ready=true) is the pre-condition the SPA uses to
    offer "Start this program" (AC4).
    """
    pid = settings.vision_sandbox_program_id
    try:
        async with httpx.AsyncClient() as client:
            dj = await _council_post(client, "/v1/vision/draft", {
                "program_id": pid,
                "seed_intent": body.idea,
                "max_cost_usd": settings.council_max_cost_usd,
            })
            draft = await _poll(client, "vision", dj["id"])
            artifact = draft.get("artifact") or {}
            shaped = _extract_vision(artifact)

            gj = await _council_post(client, "/v1/grade", {
                "program_id": pid,
                "level": "vision",
                "artifact": artifact,
                "max_cost_usd": settings.council_max_cost_usd,
            })
            grade = await _poll(client, "grade", gj["id"])
            graded = grade_view(grade)
    except HTTPException:
        raise
    except httpx.HTTPError as exc:  # transport-level: never fabricate a pass
        raise HTTPException(502, f"council unavailable: {exc}") from exc

    return {**shaped, **graded, "assurance_source": "coev2_vision_gate"}


@router.post("/programs")
async def start_program(body: StartIn, user: dict = Depends(require_user)) -> dict:
    """AC4 — "Start this program": stand up a REAL program + Vision from a graded idea, then RE-grade
    under the new program id so it gets its OWN honest, persisted grade (not the sandbox's).

    Same bootstrap path a human uses (POST /coding/programs + PATCH repo_volume_path — the #19 gotcha —
    + POST /planning/visions from the drafted statement). Human-confirmed + passing-grade-gated in the UI;
    the returned grade is the real one computed under the new id, never asserted here.
    """
    code = derive_code(body.name)
    artifact = body.vision or {}
    statement = (artifact.get("statement") or artifact.get("body_text") or body.idea).strip()
    try:
        async with httpx.AsyncClient() as client:
            prog = await _sov_post(client, "/coding/programs", {
                "code": code, "name": body.name, "description": body.idea,
            })
            pid = prog.get("id")
            # #19: create silently drops repo_volume_path → conductor preflight later rejects. Set it now.
            await _sov_patch(client, f"/coding/programs/{code}", {"repo_volume_path": f"/repos/{code.lower()}"})
            # Create the Vision from the drafted statement (the planning-side Vision row).
            try:
                await _sov_post(client, "/planning/visions", {
                    "program_code": code, "title": body.name, "body_text": statement,
                })
            except httpx.HTTPError:
                pass  # program exists even if the Vision row lags; the re-grade below is the honest record
            # RE-grade under the NEW program id — the real, persisted grade for this program.
            gj = await _council_post(client, "/v1/grade", {
                "program_id": pid, "level": "vision", "artifact": artifact,
                "max_cost_usd": settings.council_max_cost_usd,
            })
            grade = await _poll(client, "grade", gj["id"])
            graded = grade_view(grade)
    except HTTPException:
        raise
    except httpx.HTTPStatusError as exc:
        # Bubble a code collision (409) etc. so the SPA can ask for another name — don't mutate identity.
        raise HTTPException(exc.response.status_code, f"program create failed: {exc.response.text[:200]}") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"SOV/council unavailable: {exc}") from exc

    return {"program_id": pid, "code": code, **graded, "assurance_source": "coev2_vision_gate"}
