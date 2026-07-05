from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "app" / "static" / "index.html"


def _script():
    html = INDEX.read_text()
    return "\n".join(re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", html, re.S))


def _style():
    html = INDEX.read_text()
    return "\n".join(re.findall(r"<style(?:\s[^>]*)?>(.*?)</style>", html, re.S))


def _function(script, name):
    start = script.index(f"function {name}")
    next_fn = script.find("\nfunction ", start + 1)
    return script[start:] if next_fn == -1 else script[start:next_fn]


def test_action_set_is_keyed_by_kind_with_exact_decision_strings():
    action_set = _function(_script(), "actionSet")
    assert 'if(kind === "signoff")' in action_set
    assert '{label:"Accept", decision:"accept"}' in action_set
    assert '{label:"Request changes", decision:"request_changes", danger:true}' in action_set
    assert 'if(kind === "steer") return [{label:"Accept", decision:"accept"}];' in action_set
    steer_branch = action_set[action_set.index('if(kind === "steer"') :]
    assert "request_changes" not in steer_branch
    assert "needs_revision" not in action_set
    assert "reject" not in action_set


def test_resolve_flow_is_open_decide_confirm_at_most_three_interactions():
    script = _script()
    assert "openNeedsItem(item.id)" in script
    assert "selectNeedsDecision(a.decision)" in script
    assert "confirmNeedsResolve(item)" in script
    assert "Tap 1 open · Tap 2 decide · Tap 3 confirm" in script
    render = _function(script, "renderResolveBox")
    assert 'class:"resolve-box"' in render
    assert 'class:"btn decision-option " + (a.danger ? "blocked" : "two-key")' in render
    assert 'el("button", {class:"btn ghost needs-action"' in render


def test_confirm_posts_to_bff_with_verbatim_item_id_and_no_actor():
    confirm = _function(_script(), "confirmNeedsResolve")
    assert 'authFetch(`/api/needs-you/${item.id}/resolve`' in confirm
    assert 'method:"POST"' in confirm
    assert "const body = {decision:needsState.decision};" in confirm
    assert "body.note = needsState.note.trim()" in confirm
    assert "actor" not in confirm
    assert "JSON.stringify(body)" in confirm


def test_confirm_disable_guard_prevents_double_post_and_reenables_on_failure():
    confirm = _function(_script(), "confirmNeedsResolve")
    render = _function(_script(), "renderResolveBox")
    assert "if(needsState.resolving || !needsState.decision) return;" in confirm
    assert "needsState.resolving = true" in confirm
    assert "disabled:needsState.resolving || !selected" in render
    assert 'text:needsState.resolving ? "Confirming…" : "Confirm"' in render
    assert "needsState.resolving = false" in confirm


def test_success_rerenders_from_returned_items_and_updates_badge():
    script = _script()
    confirm = _function(script, "confirmNeedsResolve")
    apply_data = _function(script, "applyNeedsData")
    assert "applyNeedsData(await res.json())" in confirm
    assert "items:Array.isArray(data.items) ? data.items : []" in apply_data
    assert "setNeedsBadge(needsState.count)" in apply_data


def test_resolve_styles_are_dark_tokened_without_hex_literals():
    style = _style()
    for selector in (".resolve-box", ".decision-row", ".needs-action"):
        start = style.index(selector)
        block = style[start : style.find("}", start)]
        assert "var(--" in block
        assert "#" not in block
