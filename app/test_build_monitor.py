"""Tests for the Build-Monitor BFF (Slice 3) — the honesty law applied to the build view.

Load-bearing: a FAILED phase is carried through as failing (the client renders it RED), never smoothed;
idle is honest (no active build, not a fake); stalled is scoped to the program.
"""
import asyncio

import pytest
from fastapi import HTTPException

import app.routers.build_monitor as bm


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


# ── pure helpers ─────────────────────────────────────────────────────────────
def test_phase_view_flags_failures_loudly():
    for st in ["failed", "push_failed", "needs_human", "blocked"]:
        assert bm._phase_view({"seq": 1, "status": st})["failing"] is True
    for st in ["done", "pending", "implementing"]:
        assert bm._phase_view({"seq": 1, "status": st})["failing"] is False


def test_phase_view_unknown_status_not_failing_but_kept():
    v = bm._phase_view({"seq": 2, "status": "weird_new_state", "title": "x"})
    assert v["status"] == "weird_new_state" and v["failing"] is False


def test_feed_from_pulse_condenses_activity():
    feed = bm._feed_from_pulse({
        "status": "flowing", "as_of": "t", "workers_in_flight": 2,
        "last_worker_success_age_minutes": 3, "last_worker_success_at": "t2",
        "blockers": [{"seq": 1, "status": "needs_human", "phase_title": "schema", "spec_id": 99}],
    })
    events = " ".join(f["event"] for f in feed)
    assert "flowing" in events and "2 worker" in events and "3 min ago" in events and "needs_human" in events


# ── endpoint aggregation ─────────────────────────────────────────────────────
def _stub(monkeypatch, *, program_id=1018, specs=None, phases_by_spec=None, stalled=None, pulse=None):
    async def fake_get(client, path):
        if path.startswith("/coding/programs/"):
            return {"id": program_id, "code": path.rsplit("/", 1)[-1]}
        if path.startswith("/coding/specs?program_id"):
            return {"specs": specs or []}
        if "/phases" in path:
            sid = int(path.split("/coding/specs/")[1].split("/")[0])
            return {"phases": (phases_by_spec or {}).get(sid, [])}
        if path == "/coding/stalled-specs":
            return {"stalled": stalled or []}
        if path == "/pipeline/pulse":
            return pulse or {}
        return {}
    monkeypatch.setattr(bm, "_sov_get", fake_get)


def test_build_aggregates_active_specs_with_phases(monkeypatch):
    _stub(monkeypatch,
          specs=[
              {"id": 10, "program_id": 1018, "status": "active", "title": "A"},
              {"id": 11, "program_id": 1018, "status": "complete", "title": "done"},  # excluded (terminal)
          ],
          phases_by_spec={10: [{"seq": 1, "status": "done"}, {"seq": 2, "status": "implementing"}]})
    out = _run(bm.program_build("FOPSCON", user={"dev": True}))
    assert out["idle"] is False
    assert [s["id"] for s in out["specs"]] == [10]  # complete spec excluded from active build
    assert len(out["specs"][0]["phases"]) == 2
    assert out["specs"][0]["has_failure"] is False


def test_build_failing_phase_is_loud_never_smoothed(monkeypatch):
    _stub(monkeypatch,
          specs=[{"id": 20, "program_id": 1018, "status": "active", "title": "B"}],
          phases_by_spec={20: [{"seq": 1, "status": "done"}, {"seq": 2, "status": "push_failed"}]})
    out = _run(bm.program_build("FOPSCON", user={"dev": True}))
    spec = out["specs"][0]
    assert spec["has_failure"] is True  # roll-up flags the failure loudly
    failing = [p for p in spec["phases"] if p["failing"]]
    assert len(failing) == 1 and failing[0]["status"] == "push_failed"  # carried verbatim, not "green"


def test_build_honest_idle_when_no_active_specs(monkeypatch):
    _stub(monkeypatch, specs=[{"id": 30, "program_id": 1018, "status": "complete", "title": "done"}])
    out = _run(bm.program_build("FOPSCON", user={"dev": True}))
    assert out["idle"] is True and out["specs"] == []


def test_build_stalled_scoped_to_program(monkeypatch):
    _stub(monkeypatch,
          specs=[{"id": 40, "program_id": 1018, "status": "active", "title": "C"}],
          phases_by_spec={40: []},
          stalled=[
              {"spec_id": 1, "program": "FOPSCON", "reason": "gate stuck", "recommended_action": "check gate", "stall_class": "awaiting_uat_gate"},
              {"spec_id": 2, "program": "SOV", "reason": "other prog", "recommended_action": "x"},  # different program → excluded
          ])
    out = _run(bm.program_build("FOPSCON", user={"dev": True}))
    assert len(out["stalled"]) == 1
    assert out["stalled"][0]["spec_id"] == 1 and out["stalled"][0]["blocker"] == "gate stuck"


def test_build_degrades_on_stalled_or_pulse_failure(monkeypatch):
    # a stalled/pulse fetch failure omits that section, never crashes the build view
    async def fake_get(client, path):
        if path.startswith("/coding/programs/"):
            return {"id": 1018}
        if path.startswith("/coding/specs?program_id"):
            return {"specs": [{"id": 50, "program_id": 1018, "status": "active", "title": "D"}]}
        if "/phases" in path:
            return {"phases": [{"seq": 1, "status": "done"}]}
        raise RuntimeError("source down")  # stalled + pulse fail
    monkeypatch.setattr(bm, "_sov_get", fake_get)
    out = _run(bm.program_build("FOPSCON", user={"dev": True}))
    assert len(out["specs"]) == 1 and out["stalled"] == [] and out["feed"] == []
