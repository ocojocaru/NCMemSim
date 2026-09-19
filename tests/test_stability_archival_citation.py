"""Archival planning approves a plan, not a final deposit."""
import json
from pathlib import Path

import pytest

from scripts.validate_archival_citation import validate
from scripts.validate_release_readiness import validate as validate_readiness


ROOT = Path(__file__).resolve().parents[1]


def test_current_archival_plan_is_approved_without_candidate_readiness():
    plan = validate(ROOT)
    assert plan["status"] == "approved_plan_pending_final_deposit"
    assert plan["doi"] is None
    assert plan["current_citation_version"] == "0.14.0"
    readiness = validate_readiness(ROOT)
    assert {gate["id"]: gate["state"] for gate in readiness["gates"]}["archival_citation"] == "approved"
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
        "invented_doi",
        "selected_archive_service",
        "citation_doi",
        "citation_version",
        "unapproved_gate",
        "premature_ready",
        "local_final_check_passed",
        "remote_final_check_failed",
        "missing_evidence",
    ],
)
def test_archival_plan_rejects_premature_release_claims(tmp_path, fault):
    for name in ["docs", "ncmemsim"]:
        (tmp_path / name).mkdir()
    plan = json.loads((ROOT / "docs/archival_citation.json").read_text(encoding="utf-8"))
    readiness = json.loads((ROOT / "docs/release_readiness.json").read_text(encoding="utf-8"))
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")

    if fault == "invented_doi":
        plan["doi"] = "10.0000/not-real"
    elif fault == "selected_archive_service":
        plan["archive_service"] = "example"
    elif fault == "citation_doi":
        citation += "\ndoi: 10.0000/not-real\n"
    elif fault == "citation_version":
        citation = citation.replace("version: 0.14.0", "version: 1.0.0")
    elif fault == "unapproved_gate":
        next(g for g in readiness["gates"] if g["id"] == "archival_citation")["state"] = "pending"
    elif fault == "premature_ready":
        readiness["ready_for_candidate"] = True
    elif fault == "clean_distribution_check_passed":
        for check in readiness["final_candidate_checks"]:
            if check["id"] == "clean_installed_distributions":
                check["state"] = "passed"
                check["evidence"] = ["docs/final.txt"]
        (tmp_path / "docs/final.txt").write_text("not a real final check", encoding="utf-8")
    elif fault == "remote_final_check_failed":
        for check in readiness["final_candidate_checks"]:
            if check["id"] == "supported_runtime_ci":
                check["state"] = "failed"
    else:
        next(g for g in readiness["gates"] if g["id"] == "archival_citation")["evidence"] = ["CITATION.cff"]

    (tmp_path / "docs/archival_citation.json").write_text(json.dumps(plan), encoding="utf-8")
    (tmp_path / "docs/release_readiness.json").write_text(json.dumps(readiness), encoding="utf-8")
    (tmp_path / "ncmemsim/_version.py").write_text("__version__='0.14.0'\n", encoding="utf-8")
    (tmp_path / "CITATION.cff").write_text(citation, encoding="utf-8")
    (tmp_path / "docs/archival_citation.md").write_text("plan", encoding="utf-8")

    with pytest.raises(ValueError):
        validate(tmp_path)
