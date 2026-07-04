"""Tests for the Needs-You aggregation BFF (Slice 2) — the honest-inbox invariants.

The load-bearing property: the inbox shows ONLY items genuinely awaiting a human (filtered), never the
whole reviewable set, and never a fabricated item; empty is honest. Plus resolve routes each item to the
real SOV endpoint for its source.
"""
import asyncio

import pytest
from fastapi import HTTPException

import app.routers.needs_you as ny


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


# ── honest filtering ─────────────────────────────────────────────────────────
def test_accept_items_filters_to_po_pending_only():
    reviewable = {"subjects": [
        {"kind": "mvp", "id": 21, "title": "W2000 UAT review", "program_code": "DMI-IPAC", "status": "waiting_po_review"},
        {"kind": "mvp", "id": 20, "title": "draft mvp", "program_code": "SOV", "status": "draft"},          # not pending
        {"kind": "story", "id": 9, "title": "done story", "program_code": "SOV", "status": "complete"},       # not pending
        {"kind": "mvp", "id": 19, "title": "needs def", "program_code": "SOV", "status": "waiting_definition_approval"},
        {"kind": "mvp", "id": 5, "title": "cancelled", "program_code": "X", "status": "cancelled"},           # not pending
    ]}
    items = ny._accept_items(reviewable)
    ids = {i["id"] for i in items}
    assert ids == {"accept:21", "accept:19"}  # ONLY the two PO-pending states, not the 5 total
    it = next(i for i in items if i["id"] == "accept:21")
    assert it["program"] == "DMI-IPAC" and it["kind"] == "signoff"
    assert it["resolve"] == {"method": "POST", "url": "/accept/21/programmer-decision"}


def test_accept_items_empty_when_nothing_pending():
    reviewable = {"subjects": [{"id": 1, "status": "complete"}, {"id": 2, "status": "cancelled"}]}
    assert ny._accept_items(reviewable) == []


def test_phase_items_maps_needs_human_phases():
    phases = [{"id": 3566, "spec_id": 1596, "title": "job_expectations schema", "status": "needs_human"}]
    items = ny._phase_items(phases)
    assert items[0]["id"] == "phase:3566"
    assert items[0]["kind"] == "steer"
    assert items[0]["resolve"]["url"] == "/coding/phases/3566/approve"


# ── aggregation endpoint ─────────────────────────────────────────────────────
def _stub(monkeypatch, reviewable=None, phases=None, fail=None):
    async def fake_get(client, path):
        if fail == path:
            raise RuntimeError("source down")
        if path == "/accept/reviewable":
            return reviewable if reviewable is not None else {"subjects": []}
        if path == "/coding/phases/needs-human":
            return phases if phases is not None else []
        return {}
    monkeypatch.setattr(ny, "_sov_get", fake_get)


def test_needs_you_aggregates_and_prioritizes(monkeypatch):
    _stub(monkeypatch,
          reviewable={"subjects": [{"id": 21, "title": "signoff", "program_code": "P", "status": "waiting_po_review"}]},
          phases=[{"id": 3566, "title": "steer me", "status": "needs_human", "program_code": "Q"}])
    out = _run(ny.needs_you(user={"dev": True}))
    assert out["count"] == 2
    # signoff (priority 0) before steer (priority 3)
    assert out["items"][0]["id"] == "accept:21"
    assert out["items"][1]["id"] == "phase:3566"


def test_needs_you_honest_empty(monkeypatch):
    _stub(monkeypatch)
    out = _run(ny.needs_you(user={"dev": True}))
    assert out["count"] == 0 and out["items"] == []


def test_needs_you_degrades_on_source_failure_not_crash(monkeypatch):
    # accept source down → omit it honestly, still return the phase items (no crash, no fabrication),
    # AND flag the failed source in `degraded` so the empty/partial isn't read as a confirmed clear.
    _stub(monkeypatch, phases=[{"id": 3566, "title": "x", "status": "needs_human"}], fail="/accept/reviewable")
    out = _run(ny.needs_you(user={"dev": True}))
    assert out["count"] == 1 and out["items"][0]["id"] == "phase:3566"
    assert out["degraded"] == ["accept"]


def test_needs_you_both_sources_down_is_degraded_not_false_all_clear(monkeypatch):
    # THE honesty inversion CoEv2 caught: both sources down → count=0, but `degraded` names both so the
    # client renders "couldn't reach some sources", NEVER the reassuring "Nothing needs you".
    async def fake_get(client, path):
        raise RuntimeError("source down")
    monkeypatch.setattr(ny, "_sov_get", fake_get)
    out = _run(ny.needs_you(user={"dev": True}))
    assert out["count"] == 0
    assert set(out["degraded"]) == {"accept", "phases"}  # empty-because-degraded, not empty-because-zero


def test_needs_you_healthy_empty_has_no_degraded(monkeypatch):
    # a genuine zero → empty `degraded`, so the client CAN show the honest "Nothing needs you"
    _stub(monkeypatch)
    out = _run(ny.needs_you(user={"dev": True}))
    assert out["count"] == 0 and out["degraded"] == []


# ── resolve routing ──────────────────────────────────────────────────────────
def test_resolve_accept_routes_to_programmer_decision(monkeypatch):
    calls = []
    async def fake_post(client, path, payload):
        calls.append((path, payload)); return {}
    _stub(monkeypatch)
    monkeypatch.setattr(ny, "_sov_post", fake_post)
    _run(ny.resolve("accept:21", ny.ResolveIn(decision="accept", note="lgtm"), user={"email": "mark@x.com"}))
    assert calls[0][0] == "/accept/21/programmer-decision"
    # SOV's ProgrammerDecision requires actor + uses `notes` (not `note`)
    assert calls[0][1] == {"actor": "mark@x.com", "decision": "accept", "notes": "lgtm"}


def test_resolve_accept_rejects_invalid_decision(monkeypatch):
    _stub(monkeypatch)
    async def fake_post(client, path, payload):
        return {}
    monkeypatch.setattr(ny, "_sov_post", fake_post)
    with pytest.raises(HTTPException) as e:
        _run(ny.resolve("accept:21", ny.ResolveIn(decision="looks_good"), user={"dev": True}))
    assert e.value.status_code == 422  # only accept | request_changes are valid


def test_needs_you_reports_filtered_out_statuses(monkeypatch):
    # observability: excluded statuses are tallied so an unlisted-but-pending status is visible
    _stub(monkeypatch, reviewable={"subjects": [
        {"id": 1, "status": "draft"}, {"id": 2, "status": "draft"}, {"id": 3, "status": "cancelled"},
        {"id": 4, "status": "waiting_po_review", "title": "real", "program_code": "P"},
    ]})
    out = _run(ny.needs_you(user={"dev": True}))
    assert out["count"] == 1  # only the waiting_po_review item is inbox content
    assert out["filtered_out"] == {"draft": 2, "cancelled": 1}


def test_resolve_phase_accept_routes_to_approve(monkeypatch):
    calls = []
    async def fake_post(client, path, payload):
        calls.append(path); return {}
    _stub(monkeypatch)
    monkeypatch.setattr(ny, "_sov_post", fake_post)
    _run(ny.resolve("phase:3566", ny.ResolveIn(decision="accept"), user={"dev": True}))
    assert calls[0] == "/coding/phases/3566/approve"


def test_resolve_phase_request_changes_rejected(monkeypatch):
    _stub(monkeypatch)
    async def fake_post(client, path, payload):
        return {}
    monkeypatch.setattr(ny, "_sov_post", fake_post)
    with pytest.raises(HTTPException) as e:
        _run(ny.resolve("phase:3566", ny.ResolveIn(decision="request_changes"), user={"dev": True}))
    assert e.value.status_code == 422


def test_resolve_bad_id_400(monkeypatch):
    _stub(monkeypatch)
    with pytest.raises(HTTPException) as e:
        _run(ny.resolve("garbage", ny.ResolveIn(decision="accept"), user={"dev": True}))
    assert e.value.status_code == 400
