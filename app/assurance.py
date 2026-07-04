"""Assurance adapter — a program's Trust Strip = the histogram of its ACCEPTED (delivered) Foundation
increments' lock-states, sourced HONESTLY from SOV accept records (design §3 + CoEv2 284461).

There is no per-program assurance endpoint (CoEv2 is stateless; assurance is per-increment). So we map
each of a program's coding_specs to a trust state and count only the ones that are genuinely ACCEPTED —
delivered to master (status == complete AND merged_sha set). A spec that is 'complete' but never merged is
NOT delivered (complete != delivered — the KITH finding) and is honestly excluded, never counted as green.

We never overstate: two_key requires BOTH the delivery/UAT gate AND the adversarial review to have passed
(two independent keys); a single gate is one_key; a waived required layer is vacuous; a failed delivery is
blocked. Programs with no delivered increments yield an empty list -> the Trust Strip reads 'no assurance
data yet'. CoEv2 owns the taxonomy and will refine this mapping on review.
"""
from __future__ import annotations

_APPROVE = {"approve", "approved", "pass", "passed"}


def classify_increment(spec: dict) -> str | None:
    """Map one coding_spec to a trust state, or None if it is not an ACCEPTED (delivered) increment.

    None    — draft/active/negotiating/cancelled, OR complete-but-not-merged (complete != delivered).
    blocked — a failed delivery (status failed / push_failed).
    vacuous — delivered but a required layer was waived (uat_gate_skipped_reason set).
    two_key — delivered AND uat_gate_passed AND adversarial review approved (two independent keys).
    one_key — delivered with only one key evidenced (the mechanical merge at minimum).
    """
    status = (spec.get("status") or "").lower()
    if status in ("failed", "push_failed"):
        return "blocked"
    merged = bool(spec.get("merged_sha"))
    if status != "complete" or not merged:
        return None  # not an accepted/delivered increment (incl. complete-but-unmerged = not delivered)
    if spec.get("uat_gate_skipped_reason"):
        return "vacuous"  # delivered but a required layer was waived
    uat = bool(spec.get("uat_gate_passed"))
    reviewed = str(spec.get("adversarial_verdict") or "").lower() in _APPROVE
    if uat and reviewed:
        return "two_key"  # two independent keys: the delivery/UAT gate + the adversarial review
    return "one_key"  # merged = the mechanical key; the second key is not evidenced


def program_trust_items(specs) -> list[dict]:
    """Trust-strip items (each ``{state, increment_id, title}``) for a program's DELIVERED increments only.

    Non-delivered specs contribute nothing (honest: an in-flight or unmerged increment is not assurance).
    An empty result -> the Trust Strip renders 'no assurance data yet', never a fabricated green.
    """
    items = []
    for s in specs or []:
        st = classify_increment(s)
        if st is not None:
            items.append({"state": st, "increment_id": s.get("id"), "title": s.get("title")})
    return items
