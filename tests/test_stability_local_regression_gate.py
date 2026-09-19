"""Full local regression evidence must not close other local gates."""
import json
from pathlib import Path

import pytest

from scripts.validate_local_regression_gate import validate

ROOT = Path(__file__).resolve().parents[1]


def test_local_regression_gate_recorded_without_candidate_readiness():
    evidence = validate(ROOT)
    assert evidence["status"] == "passed"
    assert "2213 passed" in evidence["observed_result"]
    readiness = json.loads((ROOT / "docs/release_readiness.json").read_text(encoding="utf-8"))
    states = {item["id"]: item["state"] for item in readiness["final_candidate_checks"]}
    assert states["full_local_regression"] == "passed"
    assert states["strict_documentation_audit"] in {"not_run", "passed"}
    assert states["clean_installed_distributions"] == "passed"
    assert readiness["ready_for_candidate"] is True


@pytest.mark.parametrize("fault", ["ready", "regression_notrun", "bad_commit"])
def test_invalid_local_regression_gate_states_rejected(tmp_path, fault):
    (tmp_path / "docs").mkdir()
    (tmp_path / "ncmemsim").mkdir()
    evidence = json.loads((ROOT / "docs/final_candidate_local_regression.json").read_text(encoding="utf-8"))
    readiness = json.loads((ROOT / "docs/release_readiness.json").read_text(encoding="utf-8"))
    if fault == "ready":
        readiness["ready_for_candidate"] = False
    elif fault == "docs_passed":
        for check in readiness["final_candidate_checks"]:
            if check["id"] == "clean_installed_distributions":
                check["state"] = "passed"
                check["evidence"] = ["docs/final_candidate_local_regression.md"]
    elif fault == "dist_passed":
        for check in readiness["final_candidate_checks"]:
            if check["id"] == "clean_installed_distributions":
                check["state"] = "passed"
                check["evidence"] = ["docs/final_candidate_local_regression.md"]
    elif fault == "regression_notrun":
        for check in readiness["final_candidate_checks"]:
            if check["id"] == "full_local_regression":
                check["state"] = "not_run"
                check["evidence"] = []
    else:
        evidence["tested_commit"] = "not-a-commit"
    (tmp_path / "docs/final_candidate_local_regression.json").write_text(json.dumps(evidence), encoding="utf-8")
    (tmp_path / "docs/final_candidate_local_regression.md").write_text("local regression", encoding="utf-8")
    (tmp_path / "docs/final_candidate_remote_evidence.json").write_text("{}", encoding="utf-8")
    (tmp_path / "docs/final_candidate_remote_evidence.md").write_text("remote", encoding="utf-8")
    (tmp_path / "docs/release_readiness.json").write_text(json.dumps(readiness), encoding="utf-8")
    (tmp_path / "ncmemsim/_version.py").write_text("__version__='0.14.0'\n", encoding="utf-8")
    with pytest.raises(ValueError):
        validate(tmp_path)
