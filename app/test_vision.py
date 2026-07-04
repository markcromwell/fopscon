"""Tests for the Idea→Vision BFF (Slice 1) — the Trust-Strip-law invariants that make the grade HONEST.

Pure helpers (grade_view / _extract_vision / derive_code) are tested directly. The async endpoints are
driven with stubbed council/SOV helpers so we assert the proxy's *logic* (shape → grade → honest render,
and the no-fabricated-pass rule) without a live council call.
"""
import asyncio

import pytest
from fastapi import HTTPException

import app.routers.vision as v


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


# ── pure: grade_view (the honesty core) ─────────────────────────────────────
def test_grade_view_ready_when_eligible_and_over_threshold():
    out = v.grade_view({"score": 0.837, "eligible": True, "findings": []})
    assert out["grade"] == 0.837
    assert out["gate"]["ready"] is True
    assert out["gate"]["threshold"] == 0.60


def test_grade_view_not_ready_below_threshold_surfaces_findings():
    # THE honesty-negative: a thin idea scores low → NOT ready, and the gate's findings ride along.
    out = v.grade_view({
        "score": 0.42, "eligible": True,
        "findings": [{"severity": "high", "issue": "no measurable success criteria", "why": "x"}],
    })
    assert out["gate"]["ready"] is False
    assert out["grade"] == 0.42
    assert out["gate"]["findings"][0]["severity"] == "high"
    assert "measurable" in out["gate"]["findings"][0]["issue"]


def test_grade_view_not_ready_when_score_high_but_ineligible():
    # score over the floor is NOT enough — the council can still rule it ineligible (real case: 0.737/False).
    out = v.grade_view({"score": 0.737, "eligible": False, "findings": []})
    assert out["gate"]["ready"] is False


def test_grade_view_never_fabricates_ready_on_missing_score():
    out = v.grade_view({"eligible": True, "findings": []})
    assert out["grade"] is None
    assert out["gate"]["ready"] is False


def test_grade_view_bool_is_not_a_numeric_score():
    # guard: score=True must not be read as 1.0 ≥ 0.60
    out = v.grade_view({"score": True, "eligible": True, "findings": []})
    assert out["grade"] is None
    assert out["gate"]["ready"] is False


# ── pure: extraction + code derivation ──────────────────────────────────────
def test_extract_vision_statement_and_epics():
    art = {"statement": "A clear north star.",
           "epics": [{"title": "E1", "stories": ["s1", {"title": "s2"}]}, "E2"]}
    out = v._extract_vision(art)
    assert out["statement"] == "A clear north star."
    assert out["epics"][0]["title"] == "E1"
    assert out["epics"][0]["stories"] == ["s1", "s2"]
    assert out["epics"][1] == {"title": "E2", "stories": []}


def test_extract_vision_falls_back_to_body_text():
    assert v._extract_vision({"body_text": "bt"})["statement"] == "bt"
    assert v._extract_vision({})["statement"] == ""


def test_derive_code():
    assert v.derive_code("Foundation Operator Console") == "FOUNDATIONOPERATORCONSOLE"[:24]
    assert v.derive_code("my-idea!") == "MYIDEA"
    assert v.derive_code("   ") == "PROGRAM"


# ── async: the draft proxy (shape → grade → honest render) ───────────────────
def _stub_council(monkeypatch, *, vision_status="complete", grade_job=None, artifact=None):
    posts = []

    async def fake_post(client, path, payload):
        posts.append((path, payload))
        return {"id": "job-" + path.rsplit("/", 1)[-1]}

    async def fake_poll(client, kind, job_id):
        if kind == "vision":
            return {"status": vision_status, "artifact": artifact or {"statement": "S", "epics": []}}
        return grade_job or {"status": "complete", "score": 0.80, "eligible": True, "findings": []}

    monkeypatch.setattr(v, "_council_post", fake_post)
    monkeypatch.setattr(v, "_poll", fake_poll)
    return posts


def test_vision_draft_happy_path(monkeypatch):
    posts = _stub_council(monkeypatch,
                          artifact={"statement": "North star", "epics": [{"title": "E", "stories": ["s"]}]},
                          grade_job={"status": "complete", "score": 0.83, "eligible": True, "findings": []})
    out = _run(v.vision_draft(v.IdeaIn(idea="a strong idea"), user={"dev": True}))
    assert out["statement"] == "North star"
    assert out["epics"][0]["stories"] == ["s"]
    assert out["gate"]["ready"] is True
    # draft called with the sandbox program id + the typed idea as seed_intent
    draft_call = [p for p in posts if p[0].endswith("/vision/draft")][0]
    assert draft_call[1]["program_id"] == v.settings.vision_sandbox_program_id
    assert draft_call[1]["seed_intent"] == "a strong idea"


def test_vision_draft_honesty_negative(monkeypatch):
    _stub_council(monkeypatch,
                  grade_job={"status": "complete", "score": 0.40, "eligible": True,
                             "findings": [{"severity": "high", "issue": "too thin"}]})
    out = _run(v.vision_draft(v.IdeaIn(idea="a thin idea"), user={"dev": True}))
    assert out["gate"]["ready"] is False
    assert out["gate"]["findings"][0]["issue"] == "too thin"


def test_poll_raises_on_failed_job_never_fabricates_pass(monkeypatch):
    async def fake_get(client, path):
        return {"status": "failed", "error_message": "council boom"}
    monkeypatch.setattr(v, "_council_get", fake_get)
    with pytest.raises(HTTPException) as e:
        _run(v._poll(client=None, kind="grade", job_id="x"))
    assert e.value.status_code == 502


# ── async: /start (create + re-grade under the new id) ───────────────────────
def test_start_program_creates_and_regrades(monkeypatch):
    sov_calls = []

    async def fake_sov_post(client, path, payload):
        sov_calls.append(("POST", path, payload))
        if path == "/coding/programs":
            return {"id": 4242, "code": payload["code"]}
        return {}

    async def fake_sov_patch(client, path, payload):
        sov_calls.append(("PATCH", path, payload))
        return {}

    async def fake_council_post(client, path, payload):
        sov_calls.append(("CPOST", path, payload))
        return {"id": "g1"}

    async def fake_poll(client, kind, job_id):
        return {"status": "complete", "score": 0.71, "eligible": True, "findings": []}

    monkeypatch.setattr(v, "_sov_post", fake_sov_post)
    monkeypatch.setattr(v, "_sov_patch", fake_sov_patch)
    monkeypatch.setattr(v, "_council_post", fake_council_post)
    monkeypatch.setattr(v, "_poll", fake_poll)

    out = _run(v.start_program(
        v.StartIn(name="Cool Thing", idea="an idea", vision={"statement": "S", "epics": []}),
        user={"dev": True},
    ))
    assert out["program_id"] == 4242
    assert out["code"] == "COOLTHING"
    assert out["gate"]["ready"] is True  # re-graded 0.71 under the NEW id
    # re-grade was posted under the NEW program id, not the sandbox
    regrade = [c for c in sov_calls if c[0] == "CPOST"][0]
    assert regrade[2]["program_id"] == 4242
    assert regrade[2]["level"] == "vision"
