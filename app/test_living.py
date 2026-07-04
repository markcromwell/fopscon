"""Tests for the Living Program BFF (Slice 4) — the honesty invariants of the payoff screen.

Load-bearing: `running`/`health` come from a REAL probe (never a hardcoded green), features are the REAL
delivered increments (never fabricated), and an undeployed program is honestly not-live.
"""
import asyncio

import pytest

import app.routers.living as lv


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


# ── pure: features from delivered-increment trust items ──────────────────────
def test_features_from_trust_items_maps_real_state():
    items = [{"state": "two_key", "increment_id": 10, "title": "Reach out"},
             {"state": "one_key", "increment_id": 11, "title": "Draft"}]
    feats = lv._features_from_trust_items(items)
    assert feats[0] == {"name": "Reach out", "increment": 10, "assurance": "two_key"}
    assert feats[1]["assurance"] == "one_key"


def test_features_empty_is_honest_zero():
    assert lv._features_from_trust_items([]) == []  # zero delivered → zero features, never fabricated


# ── real health probe: up only on a real 2xx, never hardcoded ────────────────
class _Resp:
    def __init__(self, code, body=None):
        self.status_code = code
        self._body = body or {}
    def json(self):
        return self._body


def test_probe_up_on_2xx_with_real_status(monkeypatch):
    class _Client:
        async def get(self, url, timeout=None):
            return _Resp(200, {"status": "ok"})
    up, status = _run(lv._probe_health(_Client(), "http://kith-uat:8000"))
    assert up is True and status == "ok"


def test_probe_down_when_unreachable(monkeypatch):
    class _Client:
        async def get(self, url, timeout=None):
            raise RuntimeError("connection refused")
    up, status = _run(lv._probe_health(_Client(), "http://nope:9999"))
    assert up is False and status == "unreachable"  # honest down, NEVER a hardcoded 'ok'


# ── endpoint: real-probe running + honest not-live ───────────────────────────
def _stub(monkeypatch, *, prog, specs=None, probe=None, monitor=None):
    async def fake_sov(client, path):
        if path.startswith("/coding/programs/") and "/" not in path.split("/coding/programs/")[1]:
            return prog
        if path.startswith("/coding/programs/") and path.endswith("/deployments/current"):
            return []
        if path == "/health/programs":
            return {"data": monitor or {}}
        if "/versions" in path:
            return {"versions": []}
        if path.startswith("/coding/specs?program_id"):
            return {"specs": specs or []}
        return {}
    monkeypatch.setattr(lv, "_sov_get", fake_sov)
    if probe is not None:
        async def fake_probe(client, base):
            return probe
        monkeypatch.setattr(lv, "_probe_health", fake_probe)


def test_living_running_from_real_probe(monkeypatch):
    # KITH-like: uat_base_url present + probe says up → running True + real health, features from specs
    _stub(monkeypatch,
          prog={"id": 1018, "name": "KITH", "uat_base_url": "http://kith-uat:8000", "description": "CRM"},
          specs=[{"id": 1, "program_id": 1018, "status": "complete", "merged_sha": "abc",
                  "uat_gate_passed": True, "adversarial_review": {"verdict": "approved"}, "title": "F1"}],
          probe=(True, "ok"))
    out = _run(lv.program_living("KITH", user={"dev": True}))
    assert out["running"] is True and out["url"] == "http://kith-uat:8000" and out["health"] == "ok"
    assert len(out["features"]) >= 1


def test_living_honest_not_live_when_no_url(monkeypatch):
    # undeployed: no uat_base_url, nothing in the monitor → running False, url None (never a fake URL)
    _stub(monkeypatch, prog={"id": 99, "name": "FOPSCON", "description": "console"}, specs=[])
    out = _run(lv.program_living("FOPSCON", user={"dev": True}))
    assert out["running"] is False and out["url"] is None and out["health"] is None


def test_living_probe_down_is_not_running(monkeypatch):
    # url present but the probe says DOWN → running False + url None (a recorded URL that doesn't answer is
    # NOT alive — the anti-fail-open guardrail)
    _stub(monkeypatch, prog={"id": 5, "name": "X", "uat_base_url": "http://x:8000"}, specs=[],
          probe=(False, "unreachable"))
    out = _run(lv.program_living("X", user={"dev": True}))
    assert out["running"] is False and out["url"] is None
    assert "sparkline" not in out and "trend" not in out  # no fabricated time-series
