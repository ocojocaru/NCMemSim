"""Strict documentation evidence must not close clean distribution validation."""
import json
from pathlib import Path

import pytest

from scripts.validate_strict_documentation_gate import validate

ROOT = Path(__file__).resolve().parents[1]


def test_strict_documentation_gate_recorded_without_candidate_readiness():
    evidence = validate(ROOT)
    assert evidence["status"] == "passed"
    assert "7070 local references" in evidence["observed_result"]
    readiness = json.loads((ROOT / "docs/release_readiness.json").read_text(encoding="utf-8"))
    states = {item["id"]: item["state"] for item in readiness["final_candidate_checks"]}
    assert states["full_local_regression"] == "passed"
    assert states["strict_documentation_audit"] == "passed"
    assert states["clean_installed_distributions"] == "not_run"
    assert states["supported_runtime_ci"] == "passed"
    assert states["remote_documentation"] == "passed"
    assert readiness["ready_for_candidate"] is False


@pytest.mark.parametrize("fault", ["ready", "dist_passed", "docs_notrun", "bad_commit", "missing_result"])
def test_invalid_strict_documentation_gate_states_rejected(tmp_path, fault):
    (tmp_path / "docs").mkdir()
    (tmp_path / "scripts").mkdir()
    (tmp_path / "ncmemsim").mkdir()
    evidence = json.loads((ROOT / "docs/final_candidate_strict_documentation.json").read_text(encoding="utf-8"))
    readiness = json.loads((ROOT / "docs/release_readiness.json").read_text(encoding="utf-8"))
    if fault == "ready":
        readiness["ready_for_candidate"] = True
    elif fault == "dist_passed":
        for check in readiness["final_candidate_checks"]:
            if check["id"] == "clean_installed_distributions":
                check["state"] = "passed"
                check["evidence"] = ["docs/final_candidate_strict_documentation.md"]
    elif fault == "docs_notrun":
        for check in readiness["final_candidate_checks"]:
            if check["id"] == "strict_documentation_audit":
                check["state"] = "not_run"
                check["evidence"] = []
    elif fault == "bad_commit":
        evidence["tested_commit"] = "not-a-commit"
    else:
        evidence["observed_result"] = "MkDocs only"
    (tmp_path / "docs/final_candidate_strict_documentation.json").write_text(json.dumps(evidence), encoding="utf-8")
    (tmp_path / "docs/final_candidate_strict_documentation.md").write_text("strict docs", encoding="utf-8")
    (tmp_path / "docs/release_readiness.json").write_text(json.dumps(readiness), encoding="utf-8")
    (tmp_path / "scripts/validate_documentation.py").write_text("print('ok')\n", encoding="utf-8")
    (tmp_path / "ncmemsim/_version.py").write_text("__version__='0.14.0'\n", encoding="utf-8")
    with pytest.raises(ValueError):
        validate(tmp_path)
