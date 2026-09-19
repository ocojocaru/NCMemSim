"""Remote final gate evidence remains scoped to CI and Documentation only."""
import json
from pathlib import Path

import pytest

from scripts.validate_remote_candidate_gates import validate

ROOT = Path(__file__).resolve().parents[1]


def test_remote_candidate_gates_are_recorded_without_candidate_readiness():
    evidence = validate(ROOT)
    assert evidence["status"] == "passed_pending_evidence_commit_confirmation"
    readiness = json.loads((ROOT / "docs/release_readiness.json").read_text(encoding="utf-8"))
    states = {item["id"]: item["state"] for item in readiness["final_candidate_checks"]}
    assert states["supported_runtime_ci"] == "passed"
    assert states["remote_documentation"] == "passed"
    assert states["full_local_regression"] in {"not_run", "passed"}
    assert states["strict_documentation_audit"] in {"not_run", "passed"}
    assert states["clean_installed_distributions"] == "not_run"
    assert readiness["ready_for_candidate"] is False


@pytest.mark.parametrize("fault", ["ready", "strict_docs_passed", "remote_notrun", "bad_commit"])
def test_invalid_remote_candidate_gate_states_are_rejected(tmp_path, fault):
    (tmp_path / "docs").mkdir()
    (tmp_path / "ncmemsim").mkdir()
    evidence = json.loads((ROOT / "docs/final_candidate_remote_evidence.json").read_text(encoding="utf-8"))
    readiness = json.loads((ROOT / "docs/release_readiness.json").read_text(encoding="utf-8"))
    if fault == "ready":
        readiness["ready_for_candidate"] = True
    elif fault == "strict_docs_passed":
        for check in readiness["final_candidate_checks"]:
            if check["id"] == "clean_installed_distributions":
                check["state"] = "passed"
                check["evidence"] = ["docs/final_candidate_remote_evidence.md"]
    elif fault == "remote_notrun":
        for check in readiness["final_candidate_checks"]:
            if check["id"] == "supported_runtime_ci":
                check["state"] = "not_run"
                check["evidence"] = []
    else:
        evidence["verified_commit"] = "not-a-commit"
    (tmp_path / "docs/final_candidate_remote_evidence.json").write_text(json.dumps(evidence), encoding="utf-8")
    (tmp_path / "docs/final_candidate_remote_evidence.md").write_text("remote evidence", encoding="utf-8")
    (tmp_path / "docs/release_readiness.json").write_text(json.dumps(readiness), encoding="utf-8")
    (tmp_path / "ncmemsim/_version.py").write_text("__version__='0.14.0'\n", encoding="utf-8")
    with pytest.raises(ValueError):
        validate(tmp_path)
