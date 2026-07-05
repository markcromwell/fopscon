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


def test_assurance_uses_existing_trust_strip_or_hatched_no_data_branch():
    script = _script()
    render_item = _function(script, "renderNeedsItem")
    no_data = _function(script, "noAssuranceStrip")
    assert "item.kind === \"signoff\"" in render_item
    assert "item.assurance === null ? noAssuranceStrip() : trustStrip(item.assurance || {})" in render_item
    assert 'class:"assurance-empty"' in no_data
    assert 'class:"hatch"' in no_data
    assert "no assurance data yet" in no_data
    assert "two-key" not in no_data


def test_phone_first_overflow_badge_and_width_guards():
    style = _style()
    html = _html()
    assert "overflow-x:hidden" in style
    assert ".screen-needs{max-width:520px}" in style
    assert "max-width:100%" in style
    assert '<aside class="side" id="shell-side"></aside>' in html
    assert 'id:"needs-badge"' in _script()


def test_tokened_no_external_styles_focus_visible_and_reduced_motion():
    html = _html().lower()
    style = _style()
    assert 'rel="stylesheet"' not in html
    assert "@import" not in style
    assert "fonts.googleapis" not in html
    assert ":focus-visible" in style
    assert "prefers-reduced-motion: reduce" in style
    for selector in (".needs-item", ".program-pill", ".resolve-box", ".empty-state"):
        block = style[style.index(selector) : style.find("}", style.index(selector))]
        assert "var(--" in block


def test_no_static_universal_trust_claims_in_needs_render_path():
    script = _script().lower()
    start = script.index("function renderneeds")
    end = script.index("function rendernew")
    needs_path = script[start:end]
    forbidden = [
        "verified",
        "guaranteed",
        "safe to ship",
        "all tests passed",
        "green",
        "trusted",
    ]
    for phrase in forbidden:
        assert phrase not in needs_path


def test_single_primary_object_and_focusable_action_controls():
    script = _script()
    style = _style()
    assert 'data-primary-object":"needs-list"' in script
    assert 'el("button"' in _function(script, "renderNeedsItem")
    assert 'el("button"' in _function(script, "renderResolveBox")
    assert ".decision-row .btn{min-height:44px}" in style
    assert ".needs-action{min-height:44px}" in style
