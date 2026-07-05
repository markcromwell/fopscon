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


def test_dark_tokens_and_no_raw_hex_outside_root():
    style = _style()
    root = re.search(r":root\{(.*?)\n  \}", style, re.S).group(1)
    outside_root = style.replace(root, "")
    assert "--bg:#0c0c0e" in root
    assert "--surface:#16161a" in root
    assert "--accent:#3987e5" in root
    assert "body{margin:0; min-height:100vh; overflow-x:hidden}" in style
    assert "body{background:var(--bg); color:var(--ink); font:14px/1.5 var(--sans);" in style
    assert "::selection" in style
    assert ":focus-visible" in style
    assert "prefers-reduced-motion: reduce" in style
    assert not re.findall(r"#[0-9a-fA-F]{3,8}", outside_root)


def test_every_css_var_usage_resolves_against_root():
    style = _style()
    root = re.search(r":root\{(.*?)\n  \}", style, re.S).group(1)
    defined = set(re.findall(r"(--[\w-]+)\s*:", root))
    used = set(re.findall(r"var\((--[\w-]+)", style))
    assert used
    assert not (used - defined)


def test_shell_rail_is_generated_from_five_steps_and_active_route():
    html = _html()
    script = _script()
    style = _style()
    steps = script[script.index("const STEPS = [") : script.index("];", script.index("const STEPS = ["))]
    assert '<aside class="side" id="shell-side"></aside>' in html
    assert "const STEPS = [" in script
    assert steps.count('label:"') == 5
    for label in ("Idea → Vision", "Vision → Program", "The Living Program", "Guide", "Maintain"):
        assert label in script
    assert 'href:"#/new"' in script
    assert 'href:"#needs"' in script
    assert 'function currentStepId()' in script
    assert 'return "idea";' in script
    assert 'if(isOn) link.setAttribute("aria-current", "page");' in script
    assert '@media (max-width:880px)' in style
    assert '.app-shell{grid-template-columns:1fr}' in style
