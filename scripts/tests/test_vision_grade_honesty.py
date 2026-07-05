from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "app" / "static" / "index.html"


def _script():
    html = INDEX.read_text()
    return "\n".join(re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", html, re.S))


def _function(script, name):
    start = script.index(f"function {name}(")
    next_fn = script.find("\nfunction ", start + 1)
    return script[start:] if next_fn == -1 else script[start:next_fn]


def test_grade_uses_bff_threshold_for_ready_boundary():
    script = _script()
    grade = _function(script, "renderGrade")
    vision = _function(script, "renderVision")
    assert "const threshold = v.gate.threshold" in grade
    assert "const ready = v.grade >= threshold" in grade
    assert "const ready = v.grade >= v.gate.threshold" in vision
    assert "v.gate.ready" not in grade
    assert "v.gate.ready" not in vision
    assert 'class:"vgrade " + (ready ? "ready" : "notready")' in grade
    assert "computed by the vision-gate" in grade


def test_ready_start_and_notready_locked_paths_have_no_praise():
    script = _script()
    start = _function(script, "renderStartFlow")
    vision = _function(script, "renderVision")
    assert 'text:"Looks right — start building it"' in start
    assert 'id:"start-program"' in start
    assert 'text:"Start — locked until it clears"' in vision
    assert "What the gate found missing — graded down, not glossed over" in script
    for phrase in ("great idea", "looks good", "excellent", "congratulations"):
        assert phrase not in script.lower()


def test_quoted_wish_epics_and_data_unavailable_are_data_bound():
    script = _script()
    vision = _function(script, "renderVision")
    datafail = _function(script, "renderDataFail")
    unavailable = _function(script, "isDraftReadUnavailable")
    assert "Born from:" in vision
    assert "draftState.idea || v.idea_reason || v.idea" in vision
    assert "v.statement" in vision
    assert "v.epics || []" in vision
    assert "v.degraded === true" in unavailable
    assert "failed" in unavailable
    assert "partial" in unavailable
    assert 'class:"datafail"' in datafail
    assert "source:" in datafail
    assert "green" not in datafail.lower()
    assert "sparkline" not in script.lower()
