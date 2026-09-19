"""Final gate configuration must not silently mark candidate checks passed."""
import json
from pathlib import Path

import pytest

from scripts.validate_final_candidate_gates import validate


ROOT = Path(__file__).resolve().parents[1]


def test_final_gate_plan_is_configured_without_readiness():
    plan = validate(ROOT)
    assert plan["status"] == "configured_not_run"
    assert plan["source_branch"] == "prep/v1.0-stability"
    readiness = json.loads((ROOT / "docs/release_readiness.json").read_text(encoding="utf-8"))
    assert readiness["ready_for_candidate"] is False
    states = {check["id"]: check["state"] for check in readiness["final_candidate_checks"]}
    assert states["full_local_regression"] in {"not_run", "passed"}
    assert states["strict_documentation_audit"] in {"not_run", "passed"}
    assert states["clean_installed_distributions"] == "not_run"
    assert states["supported_runtime_ci"] in {"not_run", "passed"}
    assert states["remote_documentation"] in {"not_run", "passed"}


@pytest.mark.parametrize(
    "fault",
    [
        "wrong_status",
        "wrong_branch",
        "missing_check",
        "clean_distribution_check_passed",
        "failed_remote_check",
        "premature_ready",
        "ci_branch_missing",
        "docs_branch_missing",
    ],
)
def test_invalid_final_gate_configuration_is_rejected(tmp_path, fault):
    (tmp_path / "docs").mkdir()
    (tmp_path / "ncmemsim").mkdir()
    (tmp_path / ".github/workflows").mkdir(parents=True)
    plan = json.loads((ROOT / "docs/final_candidate_gates.json").read_text(encoding="utf-8"))
    readiness = json.loads((ROOT / "docs/release_readiness.json").read_text(encoding="utf-8"))
    ci_text = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    docs_text = (ROOT / ".github/workflows/docs.yml").read_text(encoding="utf-8")

    if fault == "wrong_status":
        plan["status"] = "passed"
    elif fault == "wrong_branch":
        plan["source_branch"] = "main"
    elif fault == "missing_check":
        plan["required_checks"].pop()
    elif fault == "clean_distribution_check_passed":
        for check in readiness["final_candidate_checks"]:
            if check["id"] == "clean_installed_distributions":
                check["state"] = "passed"
                check["evidence"] = ["docs/final.txt"]
        (tmp_path / "docs/final.txt").write_text("not real final evidence", encoding="utf-8")
    elif fault == "failed_remote_check":
        for check in readiness["final_candidate_checks"]:
            if check["id"] == "supported_runtime_ci":
                check["state"] = "failed"
    elif fault == "premature_ready":
        readiness["ready_for_candidate"] = True
    elif fault == "ci_branch_missing":
        ci_text = ci_text.replace('branches: ["prep/v1.0-stability"]', 'branches: ["main"]')
    else:
        docs_text = docs_text.replace('branches: ["prep/v1.0-stability"]', 'branches: ["main"]')

    (tmp_path / "docs/final_candidate_gates.json").write_text(json.dumps(plan), encoding="utf-8")
    (tmp_path / "docs/release_readiness.json").write_text(json.dumps(readiness), encoding="utf-8")
    (tmp_path / "ncmemsim/_version.py").write_text("__version__='0.14.0'\n", encoding="utf-8")
    (tmp_path / ".github/workflows/ci.yml").write_text(ci_text, encoding="utf-8")
    (tmp_path / ".github/workflows/docs.yml").write_text(docs_text, encoding="utf-8")

    with pytest.raises(ValueError):
        validate(tmp_path)
