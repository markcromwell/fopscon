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


def test_living_render_path_has_no_static_universal_success_claims():
    script = _script().lower()
    start = script.index("function renderliving")
    end = script.index("function route")
    living_path = script[start:end]
    for phrase in ("all passed", "verified", "green", "guaranteed", "safe to ship"):
        assert phrase not in living_path


def test_living_reads_url_health_features_from_response_and_no_sparkline_or_trend():
    script = _script()
    living_path = script[script.index("function renderLiving") : script.index("function route")]
    assert "data.url" in living_path
    assert "data.health" in living_path
    assert "data.version" in living_path
    assert "data.features" in living_path
    assert "data.features_trust_strip" in living_path
    assert "features:" not in living_path
    assert "url:" not in _function(script, "renderLivingRunning").split("return el", 1)[0]
    assert "sparkline" not in living_path.lower()
    assert "trend" not in living_path.lower()


def test_living_css_tokened_focus_motion_and_no_external_styles():
    html = _html().lower()
    style = _style()
    assert 'rel="stylesheet"' not in html
    assert "@import" not in style
    assert "fonts.googleapis" not in html
    assert ":focus-visible" in style
    assert "prefers-reduced-motion: reduce" in style
    assert "body{margin:0; min-height:100vh; overflow-x:hidden}" in style
    for selector in (
        ".screen-living{",
        ".living-shell{",
        ".living-window{",
        ".running-status{",
        ".vitals{",
        ".living-feature{",
        ".journey{",
        ".notlive{",
    ):
        block = style[style.index(selector) : style.find("}", style.index(selector))]
        assert "var(--" in block


def test_living_single_primary_object_and_phone_scroll_guard():
    script = _script()
    style = _style()
    living_path = script[script.index("function renderLiving") : script.index("function route")]
    assert living_path.count('"data-primary-object":"living-app"') == 2
    shell = _function(script, "renderLivingShell")
    assert "data-primary-object" not in shell
    assert "@media (max-width: 430px)" in style
    phone = style[style.index("@media (max-width: 430px)") : style.find("}", style.index(".vital{min-width:0"))]
    assert ".screen-living{max-width:100%}" in phone
    assert ".open-it{width:100%" in phone
    assert "overflow-x:hidden" in style[style.index(".screen-living{") : style.find("}", style.index(".screen-living{"))]


def test_fopsliving_handle_exposes_route_fetch_render_helpers():
    script = _script()
    assert "window.FOPSLiving = {" in script
    start = script.index("window.FOPSLiving = {")
    handle = script[start : script.index("init();", start)]
    for name in (
        "livingRouteCode",
        "renderLiving",
        "fetchLiving",
        "stopLivingPolling",
        "renderLivingRunning",
        "renderLivingFeatures",
        "renderLivingRecap",
    ):
        assert name in handle


# --- sad-branch teeth ([S4] coverage-gap close — parity with screen-2/3) ---


def test_not_running_renders_notlive_not_fabricated_running():
    # A program that is not live must render the honest .notlive state and MUST NOT
    # emit the running window / Open-it. Bound to data.running, never fabricated.
    fn = _function(_script(), "renderLivingRunning")
    assert "if(data.running !== true){" in fn
    guard = fn.index("if(data.running !== true){")
    notlive = fn.index('class:"notlive"')
    open_it = fn.index('class:"open-it"')
    assert guard < notlive < open_it  # notlive returns BEFORE any running/Open-it markup
    assert "there is nothing to fake" in fn
    assert 'role:"status"' in fn[guard:open_it]
    # the running window + Open-it are url-GATED (no url -> no Open-it), never unconditional
    assert "data.url ?" in fn or "if(data.url)" in fn


def test_feature_assurance_binds_real_state_never_fabricates_two_key():
    script = _script()
    strip = _function(script, "featureAssuranceStrip")
    features = _function(script, "renderLivingFeatures")
    # honest abstain when no assurance — not a fabricated all-clear
    assert 'if(!assurance) return {total:0' in strip
    assert 'caption:"no assurance data yet"' in strip
    # the rendered state is derived from the ARG, not hardcoded
    assert 'String(assurance' in strip
    assert "counts[state] = 1" in strip
    # never fabricates a two-key/all-green manifest inside the strip
    assert "two_key" not in strip
    assert "two-key" not in strip
    # per-feature strip is bound to the REAL feature.assurance value
    assert "trustStrip(featureAssuranceStrip(feature.assurance))" in features
    # a blocked assurance maps to a real (non-green) trust class, not two-key
    assert 'blocked:"blocked"' in script


def test_degraded_living_read_uses_amber_datafail_before_running():
    script = _script()
    style = _style()
    shell = _function(script, "renderLivingShell")
    degraded = _function(script, "renderLivingDegraded")
    is_deg = _function(script, "isLivingDegraded")
    # degraded read is checked BEFORE the running/not-live render (ordering teeth)
    assert "if(isLivingDegraded(data)){" in shell
    assert shell.index("if(isLivingDegraded(data))") < shell.index("renderLivingRunning(data)")
    # a living read error OR a non-empty degraded list -> degraded (not green/not-live)
    assert "livingState.error" in is_deg
    assert "degraded.length > 0" in is_deg
    # the degraded panel is amber datafail, names the source, and is explicitly NOT not-live/running
    assert 'class:"datafail living-datafail"' in degraded
    assert 'role:"alert"' in degraded
    assert 'el("code", {text:source})' in degraded
    assert "not shown as not-live or running" in degraded
    datafail = style[style.index(".datafail{") : style.find("}", style.index(".datafail{"))]
    assert "250,178,25" in datafail  # amber border (§5.11), not green
    assert "var(--two-key)" not in datafail
