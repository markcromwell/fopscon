from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "app" / "static" / "index.html"


def _script():
    html = INDEX.read_text()
    return "\n".join(re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", html, re.S))


def _function(script, name):
    start = script.index(f"function {name}")
    next_fn = script.find("\nfunction ", start + 1)
    return script[start:] if next_fn == -1 else script[start:next_fn]


def test_heartbeat_defaults_to_honest_quiet_without_timestamp():
    script = _script()
    heartbeat = _function(script, "renderLoopHeartbeat")
    assert "if(!stamp)" in heartbeat
    assert 'class:"loopline quiet"' in heartbeat
    assert "loop quiet · no recent increment" in heartbeat
    assert "console.warn" in heartbeat
    assert "12m" not in heartbeat
    assert "Nm ago" not in heartbeat


def test_freshness_is_computed_only_from_real_timestamp():
    script = _script()
    heartbeat = _function(script, "renderLoopHeartbeat")
    update = _function(script, "updateShellSignals")
    assert "const age = freshnessLabel(stamp)" in heartbeat
    assert "last increment ${age} ago" in heartbeat
    assert "firstTimestamp(data" in update
    assert "if(stamp) shellState.lastIncrementAt = stamp" in update
    assert "function freshnessLabel(value)" in script


def test_guide_badge_and_live_pill_are_data_bound():
    script = _script()
    shell = _function(script, "renderShellChrome")
    badge = _function(script, "setNeedsBadge")
    pill = _function(script, "livePill")
    assert 'step.id === "guide" && shellState.needsCount > 0' in shell
    assert "shellState.needsCount = Number(count) || 0" in badge
    assert "String(shellState.needsCount)" in shell
    assert "if(shellState.loopLive !== true) return null" in pill
    assert "Loop live" in pill
