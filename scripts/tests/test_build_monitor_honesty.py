from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "app" / "static" / "index.html"


def _html():
    return INDEX.read_text()


def _script():
    return "\n".join(re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", _html(), re.S))


def _style():
    return "\n".join(re.findall(r"<style(?:\s[^>]*)?>(.*?)</style>", _html(), re.S))


def _function(script, name):
    start = script.index(f"function {name}")
    next_fn = script.find("\nfunction ", start + 1)
    return script[start:] if next_fn == -1 else script[start:next_fn]


def test_spec_status_blocked_maps_to_blocked_not_green():
    script = _script()
    spec_status = _function(script, "specStatusClass")
    spec = _function(script, "renderBuildSpec")
    style = _style()
    assert 's === "blocked"' in spec_status
    assert 'return "st-blocked"' in spec_status
    assert 's === "failed"' in spec_status
    assert 'return "st-done"' in spec_status
    assert 'return "st-building"' in spec_status
    assert 'class:"spec-status " + specStatusClass(spec.status)' in spec
    blocked = style[style.index(".spec-status.st-blocked") : style.find("}", style.index(".spec-status.st-blocked"))]
    building = style[style.index(".spec-status.st-building") : style.find("}", style.index(".spec-status.st-building"))]
    assert "var(--blocked)" in blocked
    assert "var(--two-key)" not in blocked
    assert "var(--accent-text)" in building
    assert "var(--two-key)" not in building


def test_mixbar_reflects_real_phase_counts_not_fabricated_trend():
    script = _script()
    spec = _function(script, "renderBuildSpec")
    counts = _function(script, "buildPhaseMixCounts")
    mixbar = _function(script, "renderBuildMixbar")
    assert "phase.failing === true || phase.status_class === \"failing\"" in counts
    assert "phase.status_class === \"unknown\"" in counts
    assert "renderBuildMixbar(phaseList)" in spec
    assert "seg.style.flex = String(n)" in mixbar
    assert "Math.random" not in mixbar
    assert "sparkline" not in script.lower()
    assert "trend" not in mixbar.lower()


def test_degraded_uses_datafail_before_idle_and_names_source():
    script = _script()
    shell = _function(script, "renderBuildShell")
    degraded = _function(script, "renderBuildDegraded")
    assert "if(isBuildDegraded(data))" in shell
    assert shell.index("if(isBuildDegraded(data))") < shell.index('data.idle_reason === "genuine"')
    assert 'class:"datafail build-datafail"' in degraded
    assert "Couldn't read build state" in degraded
    assert "el(\"code\", {text:sources})" in degraded
    assert "not shown as idle or complete" in degraded


def test_stalls_surface_blocker_and_recommendation_in_crit_family():
    script = _script()
    stalls = _function(script, "renderStalls")
    style = _style()
    assert "item.blocker" in stalls
    assert "item.recommended_action" in stalls
    assert 'class:"stall-blocker"' in stalls
    assert 'class:"stall-recommendation"' in stalls
    blocker = style[style.index(".stall-blocker") : style.find("}", style.index(".stall-blocker"))]
    assert "var(--crit)" in blocker


def test_no_static_universal_success_claims_in_build_render_path():
    script = _script().lower()
    start = script.index("function renderbuild")
    end = script.index("function renderliving")
    build_path = script[start:end]
    for phrase in ("all passed", "verified", "guaranteed", "safe to ship", "build complete"):
        assert phrase not in build_path