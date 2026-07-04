"""Tests for the assurance adapter (honesty-critical: it must never overstate green)."""
from app.assurance import classify_increment, program_trust_items


def _spec(**kw):
    base = {"status": "complete", "merged_sha": "abc", "uat_gate_passed": True,
            "adversarial_verdict": "approve", "uat_gate_skipped_reason": None}
    base.update(kw)
    return base


def test_two_key_needs_both_uat_and_review():
    assert classify_increment(_spec()) == "two_key"


def test_one_key_when_only_uat_gate():
    assert classify_increment(_spec(adversarial_verdict=None)) == "one_key"


def test_one_key_when_only_review():
    assert classify_increment(_spec(uat_gate_passed=False)) == "one_key"


def test_vacuous_when_required_layer_waived():
    assert classify_increment(_spec(uat_gate_skipped_reason="no_qual_compose")) == "vacuous"


def test_blocked_on_failed_delivery():
    assert classify_increment(_spec(status="push_failed")) == "blocked"
    assert classify_increment(_spec(status="failed")) == "blocked"


def test_complete_but_unmerged_is_not_delivered():
    # the KITH finding: complete != delivered. An unmerged 'complete' spec is NOT an accepted increment.
    assert classify_increment(_spec(merged_sha=None)) is None


def test_in_flight_and_cancelled_are_not_increments():
    for st in ("draft", "active", "negotiating", "cancelled"):
        assert classify_increment(_spec(status=st, merged_sha=None)) is None


def test_program_trust_items_counts_only_delivered():
    specs = [_spec(id=1), _spec(id=2, merged_sha=None), _spec(id=3, status="cancelled", merged_sha=None),
             _spec(id=4, adversarial_verdict=None)]
    items = program_trust_items(specs)
    states = sorted(i["state"] for i in items)
    assert states == ["one_key", "two_key"]  # only the 2 delivered; unmerged + cancelled excluded
