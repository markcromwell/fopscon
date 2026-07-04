"""The Living Program BFF (Slice 4, the payoff screen — FINALIZED-DESIGN §2 Screen 3).

A shipped program, shown ALIVE: its running URL + health, the features it actually delivered (each tagged
with its earning increment + honest assurance), and the idea→vision→building→living recap.

HONESTY LAW (the whole point of the payoff): show ONLY what is REAL. `running` is true only on real
deployment/health evidence — a program with no live-deployment record shows the honest "not live yet",
NEVER a fabricated URL/health (AC5). Features are the REAL accepted increments with their computed
assurance — never a fabricated count or green (AC2). Vitals are point-in-time from live data; NO trend
line is synthesized (metrics time-series is a known deferred gap — don't fake a sparkline). Auth-gated.

Sources: /coding/programs/{code} (meta + dates) + /coding/programs/{code}/deployments/current +
/health/programs + /coding/programs/{code}/versions + the accepted subjects (with assurance).
"""
from __future__ import annotations

import asyncio

import httpx
from fastapi import APIRouter, Depends, HTTPException

from app.assurance import program_trust_items  # reuse the Slice-0 delivered-increment honesty (on specs)
from app.auth import require_user
from app.config import settings
from app.trust_strip import build_trust_strip

router = APIRouter(prefix="/api", tags=["living"])


async def _sov_get(client: httpx.AsyncClient, path: str):
    r = await client.get(
        settings.sov_base_url + path,
        headers={"X-API-Key": settings.sov_api_key},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


async def _probe_health(client: httpx.AsyncClient, base_url: str) -> tuple[bool, str | None]:
    """Hit the deployed app's REAL health endpoint at read time → (up, status). Never a hardcoded 'ok'.

    This is the guardrail: `running`/`health` come from an actual probe of the running URL, so a program is
    reported alive only if it truly answers — not because a record says so (the canary_caught=True fail-open
    class). A 2xx is up; the status string is the app's own (JSON `status` if present, else 'ok'); anything
    else is honestly 'unreachable'/'error', never green.
    """
    for path in ("/health", "/"):
        try:
            r = await client.get(base_url.rstrip("/") + path, timeout=4)
            if r.status_code // 100 == 2:
                try:
                    status = (r.json() or {}).get("status")
                except Exception:  # noqa: BLE001 — non-JSON 2xx still means it's up
                    status = None
                return True, (status or "ok")
        except Exception:  # noqa: BLE001 — try the next path, then honestly report down
            continue
    return False, "unreachable"


def _as_list(raw, *keys) -> list:
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        for k in keys:
            if isinstance(raw.get(k), list):
                return raw[k]
    return []


def _features_from_trust_items(items: list[dict]) -> list[dict]:
    """Map the Slice-0 delivered-increment trust items ({state, increment_id, title}) → living features.

    Same source that gives the Portfolio Trust Strip — the REAL accepted/delivered increments (via
    program_trust_items on the program's specs), each with its computed assurance `state`. Never a
    fabricated feature or a fake green; an empty result honestly means zero delivered increments.
    """
    return [
        {"name": it.get("title") or f"increment {it.get('increment_id')}",
         "increment": it.get("increment_id"),
         "assurance": it.get("state")}  # two_key|one_key|vacuous|blocked|unknown — computed, honest
        for it in (items or [])
    ]


@router.get("/programs/{code}/living")
async def program_living(code: str, user: dict = Depends(require_user)) -> dict:
    """A program, alive — or an honest 'not live yet'. Never a fabricated URL/health/feature/trend."""
    async with httpx.AsyncClient() as client:
        try:
            prog = await _sov_get(client, f"/coding/programs/{code}")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(exc.response.status_code, f"program {code}: {exc.response.text[:120]}") from exc
        except httpx.HTTPError as exc:
            raise HTTPException(502, f"SOV unavailable: {exc}") from exc

        async def _deploy():
            try:
                d = await _sov_get(client, f"/coding/programs/{code}/deployments/current")
                items = _as_list(d, "deployments", "data")
                return items[0] if items else (d if isinstance(d, dict) and d.get("url") else None)
            except Exception:  # noqa: BLE001 — no deployment record → honest not-live, not a crash
                return None

        async def _health():
            try:
                hp = await _sov_get(client, "/health/programs")
                data = hp.get("data") if isinstance(hp, dict) else None
                if isinstance(data, dict):
                    return data.get(code) or data.get(code.upper()) or data.get(code.lower())
                return None
            except Exception:  # noqa: BLE001
                return None

        async def _version():
            try:
                v = await _sov_get(client, f"/coding/programs/{code}/versions")
                vers = _as_list(v, "versions", "data")
                return (vers[0].get("version") or vers[0].get("tag")) if vers else None
            except Exception:  # noqa: BLE001
                return None

        pid = prog.get("id")

        async def _features():
            # Delivered features = the program's DELIVERED coding-spec increments (the same source that gives
            # the Portfolio Trust Strip its real states — program_trust_items). ?program=code is ignored by
            # SOV; only ?program_id filters (the Slice-0 lesson). Returns (features, raw_trust_items).
            try:
                raw = await _sov_get(client, f"/coding/specs?program_id={pid}")
                specs = [s for s in _as_list(raw, "specs", "data") if s.get("program_id") == pid]
                items = program_trust_items(specs)
                return _features_from_trust_items(items), items
            except Exception:  # noqa: BLE001 — a spec-fetch failure → zero features honestly, not a crash
                return [], []

        deploy, monitor_health, version, feats = await asyncio.gather(
            _deploy(), _health(), _version(), _features())
        features, feature_items = feats

        # Resolve the deployed URL — a recorded deployment, else the program's uat_base_url — and PROBE it
        # LIVE. `running`/`health` come from the actual probe, never from a record asserting it (guardrail).
        deploy_url = (deploy or {}).get("url") or (deploy or {}).get("uat_url") or prog.get("uat_base_url")
        if deploy_url:
            running, health_status = await _probe_health(client, deploy_url)
        else:
            # No known URL → the /health/programs monitor if it tracks this program, else honest not-live.
            m = (monitor_health or {}).get("status") if isinstance(monitor_health, dict) else None
            running, health_status = (m == "ok"), m

    url = deploy_url if (deploy_url and running) else None  # only surface a URL for a program truly serving

    recap = {
        "idea_date": prog.get("created_at"),
        "vision_date": prog.get("vision_created_at") or None,  # present once a Vision exists; else honest null
        "first_alive": (deploy or {}).get("deployed_at") or (deploy or {}).get("created_at"),
        "increments": len(features),
    }

    return {
        "program": code,
        "name": prog.get("name") or code,
        "idea_sentence": (prog.get("description") or "").strip(),
        "running": running,
        "url": url,                          # None → the client shows "not live yet", never a fake URL
        "version": version,
        "health": health_status,             # verbatim from the monitor; None when unmonitored (honest)
        "features": features,                # only REAL delivered increments, each with computed assurance
        # roll the delivered increments' assurance into a strip (raw items already carry `state`); empty →
        # honest "no assurance data yet", never a fabricated green.
        "features_trust_strip": build_trust_strip(feature_items),
        "recap": recap,
        "source": "sov_live_state",
        # NB: no metrics/sparkline field — the time-series store doesn't exist yet; point-in-time only,
        # NEVER a fabricated trend (BUILD-PLAN gap #2, story AC3).
    }
