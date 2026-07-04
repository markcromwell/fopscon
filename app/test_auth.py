"""Tests for the sign-in gate — the fail-CLOSED cases the live 401 test misses (CoEv2 [P] finding)."""
import asyncio

import pytest
from fastapi import HTTPException

import app.auth as auth


class _FakeReq:
    def __init__(self, token=None, cookie=None):
        self.headers = {"authorization": f"Bearer {token}"} if token else {}
        self.cookies = {"fops_idtoken": cookie} if cookie else {}


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


def _valid(email="anyone@gmail.com"):
    return {"email": email, "email_verified": True, "iss": "accounts.google.com"}


def test_dev_bypass_when_auth_off(monkeypatch):
    monkeypatch.setattr(auth.settings, "auth_enabled", False)
    user = _run(auth.require_user(_FakeReq()))
    assert user["dev"] is True


def test_empty_allowlist_DENIES_valid_token(monkeypatch):
    # THE hole: auth on + empty allowlist must deny a perfectly valid Google token, not admit it.
    monkeypatch.setattr(auth.settings, "auth_enabled", True)
    monkeypatch.setattr(auth.settings, "allowed_emails", "")  # empty
    monkeypatch.setattr(auth, "verify_google_id_token", lambda t: _valid())
    with pytest.raises(HTTPException) as e:
        _run(auth.require_user(_FakeReq(token="valid.shaped.token")))
    assert e.value.status_code == 403


def test_allowlisted_email_admitted(monkeypatch):
    monkeypatch.setattr(auth.settings, "auth_enabled", True)
    monkeypatch.setattr(auth.settings, "allowed_emails", "markcromwell@gmail.com")
    monkeypatch.setattr(auth, "verify_google_id_token", lambda t: _valid("markcromwell@gmail.com"))
    user = _run(auth.require_user(_FakeReq(token="valid.shaped.token")))
    assert user["email"] == "markcromwell@gmail.com"


def test_non_allowlisted_email_denied(monkeypatch):
    monkeypatch.setattr(auth.settings, "auth_enabled", True)
    monkeypatch.setattr(auth.settings, "allowed_emails", "markcromwell@gmail.com")
    monkeypatch.setattr(auth, "verify_google_id_token", lambda t: _valid("intruder@gmail.com"))
    with pytest.raises(HTTPException) as e:
        _run(auth.require_user(_FakeReq(token="valid.shaped.token")))
    assert e.value.status_code == 403


def test_no_token_401(monkeypatch):
    monkeypatch.setattr(auth.settings, "auth_enabled", True)
    monkeypatch.setattr(auth.settings, "allowed_emails", "markcromwell@gmail.com")
    with pytest.raises(HTTPException) as e:
        _run(auth.require_user(_FakeReq()))
    assert e.value.status_code == 401


def test_startup_refuses_boot_with_empty_allowlist(monkeypatch):
    monkeypatch.setattr(auth.settings, "auth_enabled", True)
    monkeypatch.setattr(auth.settings, "allowed_emails", "")
    import app as pkg
    with pytest.raises(RuntimeError):
        pkg.create_app()
