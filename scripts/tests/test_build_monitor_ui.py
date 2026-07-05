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


def test_build_route_dispatches_hash_and_pathname_and_portfolio_drills_to_build():
    script = _script()
    route = _function(script, "route")
    assert 'location.hash.match(/^#\\/?program\\/([^/]+)\\/build$/)' in script
    assert 'location.pathname.match(/^\\/program\\/([^/]+)\\/build$/)' in script
    assert "const buildCode = buildRouteCode()" in route
    assert "if(buildCode){ renderBuild(buildCode); return; }" in route
    assert 'location.hash = "#program/" + encodeURIComponent(p.code || p.id || "") + "/build"' in script
    assert "renderBuild(buildCode)" in route


def test_build_fetch_uses_authfetch_bff_and_poll_lifecycle_is_bounded():
    script = _script()
    assert "const BUILD_POLL_MS = 10000" in script
    assert 'authFetch(`/api/programs/${encodeURIComponent(code)}/build`, {signal:controller.signal})' in script
    assert "buildState.poll = setInterval(() => fetchBuild(code), BUILD_POLL_MS)" in script
    stop = _function(script, "stopBuildPolling")
    fetch = _function(script, "fetchBuild")
    route = _function(script, "route")
    assert "clearInterval(buildState.poll)" in stop
    assert "buildState.controller.abort()" in stop
    assert "buildState.seq += 1" in stop
    assert "if(buildState.controller) buildState.controller.abort()" in fetch
    assert "if(seq !== buildState.seq || buildState.program !== code) return;" in fetch
    assert "stopBuildPolling()" in route[route.index("if(buildCode)") :]


def test_build_tree_renders_specs_and_phases_from_response_fields():
    script = _script()
    shell = _function(script, "renderBuildShell")
    spec = _function(script, "renderBuildSpec")
    phase = _function(script, "renderBuildPhase")
    assert "specs.forEach(spec => builds.appendChild(renderBuildSpec(spec)))" in shell
    assert 'text:String(spec.id ?? "spec")' in spec
    assert 'text:spec.title || "Untitled spec"' in spec
    assert 'text:spec.status || "status unknown"' in spec
    assert "(Array.isArray(spec.phases) ? spec.phases : []).forEach" in spec
    assert "phases.appendChild(renderBuildPhase(phase))" in spec
    assert 'text:String(phase.seq ?? "–")' in phase
    assert 'text:phase.title || phase.type || "phase"' in phase
    assert 'text:phase.status || "status unknown"' in phase


def test_build_honesty_classes_use_bff_signals_not_status_guessing():
    script = _script()
    phase_class = _function(script, "phaseClass")
    spec = _function(script, "renderBuildSpec")
    style = _style()
    assert 'phase.failing === true || phase.status_class === "failing"' in phase_class
    assert 'phase.status_class === "unknown"' in phase_class
    assert 'return "ok"' in phase_class
    assert 'class:"spec-badge failure"' in spec
    assert 'class:"spec-badge unknown"' in spec
    assert 'spec.phases_unavailable === true' in spec
    assert "phases unavailable" in spec
    for selector in (".phase.failing", ".gate-chip.failing", ".spec-badge.failure"):
        block = style[style.index(selector) : style.find("}", style.index(selector))]
        assert "var(--blocked)" in block
    unknown = style[style.index(".gate-chip.unknown") : style.find("}", style.index(".gate-chip.unknown"))]
    assert "var(--one-key)" in unknown
    assert "two-key" not in unknown


def test_build_feed_stall_idle_and_degraded_states_are_rendered_honestly():
    script = _script()
    feed = _function(script, "renderBuildFeed")
    stalls = _function(script, "renderStalls")
    degraded = _function(script, "isBuildDegraded")
    shell = _function(script, "renderBuildShell")
    assert "const BUILD_FEED_CAP = 30" in script
    assert ".slice(0, BUILD_FEED_CAP)" in feed
    assert "item.actor" in feed and "item.event" in feed and "item.ts" in feed
    assert "item.blocker" in stalls
    assert "item.recommended_action" in stalls
    assert 'data.idle === true && data.idle_reason !== "genuine"' in degraded
    assert 'data.idle_reason === "unknown"' in degraded
    assert 'degraded.includes("specs")' in degraded
    assert 'data.idle === true && data.idle_reason === "genuine" && !stalled.length' in shell
    assert "Idle — no active build" in script
    assert "Couldn't read build state" in script


def test_build_css_tokened_focusable_and_mobile_scroll_guard():
    html = _html().lower()
    style = _style()
    assert 'rel="stylesheet"' not in html
    assert "@import" not in style
    assert "fonts.googleapis" not in html
    assert ":focus-visible" in style
    assert "prefers-reduced-motion: reduce" in style
    assert "body{margin:0; min-height:100vh; overflow-x:hidden}" in style
    scroll = style[style.index(".phases-scroll") : style.find("}", style.index(".phases-scroll"))]
    assert "overflow-x:auto" in scroll and "max-width:100%" in scroll and "min-width:0" in scroll
    screen_build = style[style.index(".screen-build{") : style.find("}", style.index(".screen-build{"))]
    assert "overflow-x:hidden" in screen_build
    assert "@media (max-width: 390px)" in style
    phone_start = style.index("@media (max-width: 390px)")
    phone_end = style.find("}", style.index(".phase-main{min-width:8rem}", phone_start))
    phone = style[phone_start:phone_end]
    assert ".phases-scroll" in phone and "overflow-x:auto" in phone
    assert ".screen-build" in phone and "overflow-x:hidden" in phone
    for selector in (
        ".builds{",
        ".spec{",
        ".phase{",
        ".gate-chip{",
        ".feed{",
        ".stall{",
        ".mixbar{",
        ".datafail{",
        ".idle{",
    ):
        block = style[style.index(selector) : style.find("}", style.index(selector))]
        assert "var(--" in block


def test_no_static_universal_success_claims_in_build_render_path():
    script = _script().lower()
    start = script.index("function renderbuild")
    end = script.index("function route")
    build_path = script[start:end]
    for phrase in ("all passed", "verified", "green", "guaranteed", "safe to ship"):
        assert phrase not in build_path
