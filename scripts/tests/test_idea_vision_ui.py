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


def test_new_route_door_has_single_primary_input_and_sample_chips():
    script = _script()
    assert 'href:"#/new"' in script
    assert 'data-primary-object":"idea-input"' in script
    assert 'el("textarea"' in script
    assert 'id:inputId' in script
    assert "samples = [" in script
    assert script.count('"data-sample-idea":sample') == 1
    assert len([line for line in script.splitlines() if line.strip().startswith('"A ')]) == 3


def test_chip_click_fills_the_idea_input():
    script = _script()
    assert "function onSampleClick" in script
    assert 'getAttribute("data-sample-idea")' in script
    assert "input.value = sample" in script
    assert "draftState.idea = sample" in script


def test_empty_submit_guard_prevents_vision_draft_request():
    script = _script()
    guard = script.index("if(!idea){")
    draft_call = script.index('authFetch("/api/vision/draft"')
    assert guard < draft_call
    assert "Enter an idea before shaping it." in script
    assert 'JSON.stringify({idea})' in script


def test_submit_lifecycle_disables_button_persists_idea_and_restores_it():
    script = _script()
    assert "disabled:draftState.inFlight" in script
    assert 'text:draftState.inFlight ? "Shaping…"' in script
    assert "setStored(IDEA_KEY, idea)" in script
    assert "getStored(IDEA_KEY)" in script
    assert "new AbortController()" in script
    assert "setTimeout(() => controller.abort(), DRAFT_TIMEOUT_MS)" in script
    assert "Retry shaping" in script


def test_ready_and_not_ready_render_paths_are_honest():
    script = _script()
    assert 'v.gate.ready === true' in script
    assert 'text:ready ? "Ready to start" : "Not ready yet"' in script
    assert 'id:"start-program"' in script
    assert "if(v.gate.ready === true) container.appendChild(renderStartFlow(v));" in script
    assert "v.gate.findings || []" in script
    forbidden_praise = ["great idea", "looks good", "excellent", "congratulations"]
    lower = script.lower()
    for phrase in forbidden_praise:
        assert phrase not in lower


def test_vision_render_uses_response_body_and_handles_bad_or_oversized_payloads():
    script = _script()
    assert "typeof v.statement === \"string\"" in script
    assert "Array.isArray(v.epics)" in script
    assert "v.gate && typeof v.gate === \"object\"" in script
    assert "v.statement" in script
    assert "epic.title || epic.name" in script
    assert "STORY_CAP" in script
    assert "console.warn" in script
    assert "rendering was truncated" in script


def test_start_program_requires_confirm_and_posts_created_program_payload_once():
    script = _script()
    start = script.index("function renderStartFlow")
    post = script.index('authFetch("/api/programs"')
    assert start < post
    assert 'id:"confirm-start"' in script
    assert "if(draftState.starting) return;" in script
    assert "draftState.starting = true" in script
    assert "const body = {name:programName(vision, draftState.idea), idea:draftState.idea, vision};" in script
    assert "draftState.created = await res.json()" in script
    assert "Re-graded" in script


def test_css_uses_d1_tokens_focus_visible_reduced_motion_and_mobile_scroll_guard():
    html = _html().lower()
    assert 'rel="stylesheet"' not in html
    assert "rel='stylesheet'" not in html
    style = _style()
    assert "@import" not in style
    assert "overflow-x:hidden" in style
    assert ":focus-visible" in style
    assert "prefers-reduced-motion: reduce" in style
    assert "letter-spacing:-" not in style
    for token in ("--bg", "--surface", "--ink", "--accent", "--two-key", "--vacuous", "--r-sm", "--t-16"):
        assert f"var({token})" in style
