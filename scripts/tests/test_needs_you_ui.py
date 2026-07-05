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


def test_needs_routes_dispatch_to_render_needs_and_fetch_bff():
    script = _script()
    assert "function renderNeeds()" in script
    assert 'location.hash === "#/needs"' in script
    assert 'location.hash === "#needs"' in script
    assert 'location.pathname === "/needs"' in script
    assert "renderNeeds()" in script[script.index("function route()") :]
    assert 'authFetch("/api/needs-you")' in script


def test_needs_list_renders_from_response_items_not_a_literal():
    script = _script()
    assert "items:Array.isArray(data.items) ? data.items : []" in script
    assert "needsState.items.forEach(item => list.appendChild(renderNeedsItem(item)))" in script
    assert "renderNeedsItem(item)" in script
    assert 'text:item.program || "Program"' in script
    assert 'text:kindLabel(item.kind)' in script
    assert "text:ageFrom(item.created_at)" in script
    assert 'text:item.ask || ""' in script
    assert "KITH" not in script
    assert "DMI-IPAC" not in script


def test_needs_badge_updates_from_count_and_is_header_visible():
    html = _html()
    script = _script()
    assert '<aside class="side" id="shell-side"></aside>' in html
    assert 'id:"needs-badge"' in script
    assert 'href:"#needs"' in script
    assert "function setNeedsBadge(count)" in script
    assert "badge.textContent = String(n)" in script
    assert 'badge.setAttribute("data-count", String(n))' in script
    assert "shellState.needsCount = Number(count) || 0" in script
    assert "setNeedsBadge(needsState.count)" in script


def test_honest_empty_copy_and_zero_row_branch():
    script = _script()
    empty_branch = script.index("needsState.count === 0")
    rows_branch = script.index("needsState.items.forEach")
    assert empty_branch < rows_branch
    assert "Nothing needs you right now" in script
    assert "The inbox is empty because the BFF returned zero pending items." in script


def test_row_has_single_primary_action_and_44px_touch_target():
    script = _script()
    style = _style()
    collapsed = script[script.index("else box.appendChild") : script.index("function noAssuranceStrip")]
    assert collapsed.count('class:"btn needs-action"') == 1
    assert "primaryActionLabel(item.kind)" in collapsed
    assert ".needs-action{min-height:44px}" in style
