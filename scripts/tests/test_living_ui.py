from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "app" / "static" / "index.html"


def _html():
    return INDEX.read_text()


def _script():
    return "\n".join(re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", _html(), re.S))


def _function(script, name):
    start = script.index(f"function {name}")
    next_fn = script.find("\nfunction ", start + 1)
    return script[start:] if next_fn == -1 else script[start:next_fn]


def test_living_route_dispatches_hash_pathname_and_stops_when_leaving():
    script = _script()
    route = _function(script, "route")
    assert 'location.hash.match(/^#\\/?program\\/([^/]+)\\/living$/)' in script
    assert 'location.pathname.match(/^\\/program\\/([^/]+)\\/living$/)' in script
    assert "const livingCode = livingRouteCode()" in route
    assert "if(livingCode){ stopBuildPolling(); renderLiving(livingCode); return; }" in route
    assert "stopLivingPolling()" in route[route.index("if(livingCode)") :]
    assert "renderLiving(livingCode)" in route


def test_living_fetch_uses_authfetch_abortcontroller_seq_guard_and_retry():
    script = _script()
    fetch = _function(script, "fetchLiving")
    stop = _function(script, "stopLivingPolling")
    assert 'authFetch(`/api/programs/${encodeURIComponent(code)}/living`, {signal:controller.signal})' in fetch
    assert "const controller = new AbortController()" in fetch
    assert "if(livingState.controller) livingState.controller.abort()" in fetch
    assert "if(seq !== livingState.seq || livingState.program !== code) return;" in fetch
    assert "if(!res.ok && res.status >= 500)" in fetch
    assert fetch.count('authFetch(`/api/programs/${encodeURIComponent(code)}/living`, {signal:controller.signal})') == 2
    assert "livingState.controller.abort()" in stop
    assert "livingState.seq += 1" in stop


def test_portfolio_card_exposes_living_open_affordance_to_living_hash():
    script = _script()
    card = _function(script, "card")
    created = _function(script, "createdProgramCard")
    assert 'text:"Living / open"' in card
    assert '"data-living-open":codeValue' in card
    assert 'location.hash = "#program/" + encodeURIComponent(codeValue) + "/living"' in card
    assert 'location.hash = "#program/" + encodeURIComponent(p.code || p.id || "") + "/build"' in card
    assert 'text:"Living / open"' in created
    assert 'location.hash = "#program/" + encodeURIComponent(code) + "/living"' in created


def test_not_live_state_has_no_url_or_health_rendering():
    script = _script()
    running = _function(script, "renderLivingRunning")
    notlive = running[running.index("if(data.running !== true)") : running.index('const top = el("div", {class:"living-top"}')]
    assert "Not live yet" in notlive
    assert "data.url" not in notlive
    assert "data.health" not in notlive
    assert "data.version" not in notlive
    assert "no running application URL from the Living BFF yet" in notlive


def test_running_open_it_gated_on_url_and_vitals_rendered_without_sparkline():
    script = _script()
    running = _function(script, "renderLivingRunning")
    assert 'data.running !== true' in running
    assert "data.url ? el(\"span\", {class:\"living-url\", text:data.url}) : null" in running
    assert "if(data.url)" in running
    assert 'href:data.url' in running
    assert 'class:"open-it"' in running
    assert 'text:String(data.health ?? "health unavailable")' in running
    assert 'text:String(data.version ?? "version unavailable")' in running
    assert "sparkline" not in running.lower()
    assert "trend" not in running.lower()


def test_features_render_from_response_assurance_and_cap_without_count_fabrication():
    script = _script()
    features = _function(script, "renderLivingFeatures")
    strip = _function(script, "featureAssuranceStrip")
    assert "const all = Array.isArray(data.features) ? data.features : []" in features
    assert "if(!all.length) return null" in features
    assert ".slice(0, LIVING_FEATURE_CAP)" in features
    assert "data.features_trust_strip" in features
    assert "trustStrip(data.features_trust_strip)" in features
    assert "feature.name" in features
    assert "feature.increment" in features
    assert "trustStrip(featureAssuranceStrip(feature.assurance))" in features
    assert "Showing the first ${LIVING_FEATURE_CAP} delivered features" in features
    assert 'caption:"no assurance data yet"' in strip
    for phrase in ("all passed", "verified", "green", "guaranteed"):
        assert phrase not in features.lower()
        assert phrase not in strip.lower()


def test_recap_renders_known_milestones_and_omits_missing_values():
    script = _script()
    recap = _function(script, "renderLivingRecap")
    shell = _function(script, "renderLivingShell")
    assert "if(recap && recap.idea_date) steps.push" in recap
    assert "if(recap && recap.vision_date) steps.push" in recap
    assert "if(recap && recap.increments != null) steps.push" in recap
    assert "if(recap && recap.first_alive) steps.push" in recap
    assert "if(!steps.length) return null" in recap
    assert "From a sentence to this" in recap
    assert "renderLivingRecap(data.recap || {}, data)" in shell
