from pathlib import Path


def test_web_template_exposes_manual_draft_spec_editor():
    template = Path("web/templates/index.html").read_text(encoding="utf-8")

    assert 'id="draftPanel"' in template
    assert 'id="draftSpecEditor"' in template
    # Build validates the edited draft in-line (via /api/text/draft/spec) before
    # building, so a separate Validate button is intentionally not present.
    assert "confirmCipherDraft()" in template
    assert "/api/text/draft/spec" in template
    assert "Build this cipher from the validated draft?" in template


def test_web_template_exposes_solver_preflight_status():
    template = Path("web/templates/index.html").read_text(encoding="utf-8")

    # The dedicated "Check Solvers" button and its #solverStatus side-panel were removed
    # in the control-panel redesign. Solver preflight capabilities are still fetched and
    # surfaced - now inline in the run-confirmation dialog as "Solver defaults:".
    assert 'id="solverStatus"' not in template
    assert "fetchSolverCapabilities" in template
    assert "renderSolverStatus" in template
    assert "/api/solvers" in template
    assert "Solver defaults:" in template
