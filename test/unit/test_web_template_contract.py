from pathlib import Path


def test_web_template_exposes_manual_draft_spec_editor():
    template = Path("web/templates/index.html").read_text(encoding="utf-8")

    assert 'id="draftPanel"' in template
    assert 'id="draftSpecEditor"' in template
    assert "validateDraftSpec()" in template
    assert "/api/text/draft/spec" in template
    assert "Build this cipher from the validated draft?" in template


def test_web_template_exposes_solver_preflight_status():
    template = Path("web/templates/index.html").read_text(encoding="utf-8")

    assert 'id="solverStatus"' in template
    assert "fetchSolverCapabilities" in template
    assert "renderSolverStatus" in template
    assert "/api/solvers" in template
    assert "Solver defaults:" in template
