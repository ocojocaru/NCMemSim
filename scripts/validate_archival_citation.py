"""Validate archival/citation planning without claiming a final deposit."""
from __future__ import annotations

import ast
import json
from pathlib import Path
import sys


def _package_version(root: Path) -> str:
    tree = ast.parse((root / "ncmemsim/_version.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__version__":
                    return ast.literal_eval(node.value)
    raise ValueError("missing package version")


def _citation_version(citation_text: str) -> str:
    for line in citation_text.splitlines():
        if line.startswith("version:"):
            return line.split(":", 1)[1].strip()
    raise ValueError("missing citation version")


LOCAL_FINAL_CHECKS = {"full_local_regression", "strict_documentation_audit", "clean_installed_distributions"}
REMOTE_FINAL_CHECKS = {"supported_runtime_ci", "remote_documentation"}


def validate(root: Path) -> dict:
    plan = json.loads((root / "docs/archival_citation.json").read_text(encoding="utf-8"))
    expected_keys = {
        "schema_version",
        "name",
        "preparation_version",
        "status",
        "repository_code",
        "current_citation_file",
        "current_citation_version",
        "final_release_version",
        "doi",
        "archive_service",
        "approved_scope",
        "not_approved",
        "final_candidate_evidence_required",
    }
    if set(plan) != expected_keys or plan["schema_version"] != 1:
        raise ValueError("unsupported archival citation plan schema")
    if plan["status"] != "approved_plan_pending_final_deposit":
        raise ValueError("unexpected archival citation status")
    if plan["doi"] is not None:
        raise ValueError("DOI must remain null until an external deposit exists")
    if plan["archive_service"] != "to_be_selected_before_final_release":
        raise ValueError("archive service must remain unresolved before final release")
    if plan["final_release_version"] != "1.0.0":
        raise ValueError("final release version must be 1.0.0")

    package_version = _package_version(root)
    citation_text = (root / "CITATION.cff").read_text(encoding="utf-8")
    if "doi:" in citation_text.lower():
        raise ValueError("CITATION.cff must not claim a DOI before deposit verification")
    if _citation_version(citation_text) != package_version:
        raise ValueError("current citation version must match package version")
    if plan["preparation_version"] != package_version:
        raise ValueError("plan preparation version must match package version")
    if plan["current_citation_version"] != package_version:
        raise ValueError("plan citation version must match current citation file")

    readiness = json.loads((root / "docs/release_readiness.json").read_text(encoding="utf-8"))
    gates = {gate["id"]: gate["state"] for gate in readiness["gates"]}
    if gates.get("archival_citation") != "approved":
        raise ValueError("archival citation gate must be approved after plan review")
    if readiness["ready_for_candidate"] is not False:
        raise ValueError("candidate must remain not ready until final checks pass")
    final_states = {check["id"]: check["state"] for check in readiness["final_candidate_checks"]}
    if any(final_states[name] != "not_run" for name in LOCAL_FINAL_CHECKS):
        raise ValueError("local final candidate checks must remain not_run during planning")
    if any(final_states[name] not in {"not_run", "passed"} for name in REMOTE_FINAL_CHECKS):
        raise ValueError("remote final candidate checks must be not_run or passed")

    evidence = set()
    for gate in readiness["gates"]:
        if gate["id"] == "archival_citation":
            evidence = set(gate["evidence"])
    required = {"CITATION.cff", "docs/archival_citation.md", "docs/archival_citation.json"}
    if not required <= evidence:
        raise ValueError("archival citation evidence is incomplete")
    return plan


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    try:
        plan = validate(root)
    except (ValueError, KeyError, TypeError, OSError, StopIteration) as exc:
        print("Archival citation plan FAIL:", exc, file=sys.stderr)
        return 1
    print(
        "Archival citation plan PASS: "
        + plan["status"]
        + "; DOI/deposit remain final-release work."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
