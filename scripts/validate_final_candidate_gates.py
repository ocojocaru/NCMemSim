"""Validate final candidate gate configuration and completed evidence."""
from __future__ import annotations

import ast
import json
from pathlib import Path
import sys


REQUIRED_CHECKS = {
    "full_local_regression",
    "strict_documentation_audit",
    "clean_installed_distributions",
    "supported_runtime_ci",
    "remote_documentation",
}


def _package_version(root: Path) -> str:
    tree = ast.parse((root / "ncmemsim/_version.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__version__":
                    return ast.literal_eval(node.value)
    raise ValueError("missing package version")


def _workflow_branches(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    branches: set[str] = set()
    in_push = False
    for raw in text.splitlines():
        line = raw.strip()
        if line == "push:":
            in_push = True
            continue
        if in_push and raw and not raw.startswith(" ") and not raw.startswith("\t"):
            in_push = False
        if in_push and line.startswith("branches:"):
            _, _, value = line.partition(":")
            value = value.strip()
            if value.startswith("[") and value.endswith("]"):
                for item in value[1:-1].split(","):
                    cleaned = item.strip().strip('"').strip("'")
                    if cleaned:
                        branches.add(cleaned)
            return branches
    return branches


def validate(root: Path) -> dict:
    plan = json.loads((root / "docs/final_candidate_gates.json").read_text(encoding="utf-8"))
    if plan.get("schema_version") != 1:
        raise ValueError("unsupported final gate plan schema")
    if plan.get("status") != "passed":
        raise ValueError("final gate plan must be passed after clean distribution evidence")
    if plan.get("preparation_version") != _package_version(root):
        raise ValueError("final gate preparation version differs from package")
    if plan.get("source_branch") != "prep/v1.0-stability":
        raise ValueError("unexpected final gate source branch")
    checks = {item["id"] for item in plan.get("required_checks", [])}
    if checks != REQUIRED_CHECKS:
        raise ValueError("final gate check inventory changed")
    for item in plan["required_checks"]:
        if item.get("required_state") != "passed" or not item.get("description"):
            raise ValueError("invalid final gate requirement")
    completed = plan.get("completed_evidence", {})
    if set(completed) != REQUIRED_CHECKS or any(not value for value in completed.values()):
        raise ValueError("completed final gate evidence is incomplete")

    config = plan.get("workflow_configuration", {})
    if config.get("ci_push_branch") != "prep/v1.0-stability":
        raise ValueError("CI branch configuration missing from plan")
    if config.get("documentation_push_branch") != "prep/v1.0-stability":
        raise ValueError("Documentation branch configuration missing from plan")
    if "prep/v1.0-stability" not in _workflow_branches(root / ".github/workflows/ci.yml"):
        raise ValueError("CI workflow does not run on prep/v1.0-stability")
    if "prep/v1.0-stability" not in _workflow_branches(root / ".github/workflows/docs.yml"):
        raise ValueError("Documentation workflow does not run on prep/v1.0-stability")

    readiness = json.loads((root / "docs/release_readiness.json").read_text(encoding="utf-8"))
    states = {check["id"]: check for check in readiness["final_candidate_checks"]}
    if set(states) != REQUIRED_CHECKS:
        raise ValueError("final candidate check inventory changed")
    for check_id, item in states.items():
        if item.get("state") != "passed" or not item.get("evidence"):
            raise ValueError(f"final candidate check is not passed with evidence: {check_id}")
    if readiness.get("ready_for_candidate") is not True:
        raise ValueError("candidate readiness must be true after all final gates pass")
    return plan


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    try:
        plan = validate(root)
    except (ValueError, KeyError, TypeError, OSError, StopIteration) as exc:
        print("Final candidate gate plan FAIL:", exc, file=sys.stderr)
        return 1
    print("Final candidate gate plan PASS: " + plan["status"] + "; ready_for_candidate=true.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
