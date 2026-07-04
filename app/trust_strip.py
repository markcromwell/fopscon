"""The Trust Strip — the load-bearing principle of the console (design §3).

> No trust claim may appear at any altitude unless it is COMPUTED from the manifests below it, and
> every fold must leave a truthful one-line summary at the surface.

This is the same anti-fail-open doctrine as #158, expressed in data: a caption is only ever a
data-computed sentence, never a static universal ("all earned"). An absent/empty manifest yields an
honest 'no assurance data yet' — NEVER a green claim. Rendered at every aggregation level (portfolio
card, build hero, recap row, Maintain rows, Needs-You lede).
"""
from __future__ import annotations

# two-key green / one-key amber / vacuous orange / blocked red (design §3) + the honest UNKNOWN
# state (no manifest yet — must never be read as green).
TRUST_STATES = ("two_key", "one_key", "vacuous", "blocked", "unknown")

# worst-first ordering for the honest headline colour (a strip is only as green as its weakest link).
_WORST_FIRST = ("blocked", "vacuous", "one_key", "unknown", "two_key")


def build_trust_strip(items) -> dict:
    """Compute a Trust Strip mixbar + a DATA-COMPUTED caption from a list of assurance items.

    Each item is a mapping with a ``state`` in TRUST_STATES (anything else counts as ``unknown`` —
    fail-honest, never fail-green). Returns ``{counts, total, caption, worst}``. Zero items => a
    truthful 'no assurance data yet' caption (the whole point: we never assert green without evidence).
    """
    counts = {s: 0 for s in TRUST_STATES}
    for it in items or []:
        st = (it or {}).get("state")
        counts[st if st in counts else "unknown"] += 1
    total = sum(counts.values())
    if total == 0:
        return {"counts": counts, "total": 0, "caption": "no assurance data yet", "worst": "unknown"}
    worst = next((st for st in _WORST_FIRST if counts[st]), "unknown")
    parts = [
        f"{counts['two_key']} two-key",
        f"{counts['one_key']} one-key",
        f"{counts['vacuous']} vacuous",
        f"{counts['blocked']} blocked",
    ]
    if counts["unknown"]:
        parts.append(f"{counts['unknown']} unknown")
    caption = f"{total} feature{'s' if total != 1 else ''} · " + " · ".join(parts)
    return {"counts": counts, "total": total, "caption": caption, "worst": worst}
