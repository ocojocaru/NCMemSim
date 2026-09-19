"""Validate the final clean installed distribution gate.

The default mode reuses locally available dependency packages to keep the final
preparation check offline. It still builds wheel and source artifacts from the
current source tree, installs those artifacts into separate virtual
environments outside the checkout, and verifies installed-package behavior.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from validate_dtco_distribution import check_archive, check_source_content, create_environment


REQUIRED_CHECKS = {
    "full_local_regression",
    "strict_documentation_audit",
    "clean_installed_distributions",
    "supported_runtime_ci",
    "remote_documentation",
}


def _version(root: Path) -> str:
    tree = ast.parse((root / "ncmemsim/_version.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__version__":
                    return ast.literal_eval(node.value)
    raise ValueError("missing package version")


def _run(*args: str, cwd: Path, env: dict[str, str] | None = None) -> None:
    subprocess.run(args, cwd=cwd, env=env, check=True)


def _offline_dependency_env() -> dict[str, str]:
    env = os.environ.copy()
    candidates = []
    if sys.platform == "win32":
        candidates.append(Path("C:/ProgramData/miniconda3/Lib/site-packages"))
    existing = [str(path) for path in candidates if path.is_dir()]
    if existing:
        current = env.get("PYTHONPATH")
        env["PYTHONPATH"] = os.pathsep.join(existing + ([current] if current else []))
    return env


def validate_evidence(root: Path) -> dict:
    evidence = json.loads((root / "docs/final_candidate_clean_distributions.json").read_text(encoding="utf-8"))
    if evidence.get("schema_version") != 1:
        raise ValueError("unsupported clean distribution evidence schema")
    if evidence.get("preparation_version") != _version(root):
        raise ValueError("clean distribution evidence version differs from package")
    if evidence.get("source_branch") != "prep/v1.0-stability":
        raise ValueError("unexpected clean distribution source branch")
    if evidence.get("status") != "passed":
        raise ValueError("clean distribution evidence must be passed")
    if evidence.get("covered_checks") != ["clean_installed_distributions"]:
        raise ValueError("clean distribution evidence must cover exactly one final check")
    if evidence.get("not_covered") != []:
        raise ValueError("clean distribution evidence should not leave other final gates open")

    readiness = json.loads((root / "docs/release_readiness.json").read_text(encoding="utf-8"))
    states = {item["id"]: item for item in readiness["final_candidate_checks"]}
    if set(states) != REQUIRED_CHECKS:
        raise ValueError("final candidate check inventory changed")
    for check_id, item in states.items():
        if item.get("state") != "passed" or not item.get("evidence"):
            raise ValueError(f"final candidate check is not passed with evidence: {check_id}")
    expected = {
        "docs/final_candidate_clean_distributions.md",
        "docs/final_candidate_clean_distributions.json",
        "scripts/validate_clean_distribution_gate.py",
    }
    if set(states["clean_installed_distributions"]["evidence"]) != expected:
        raise ValueError("clean distribution evidence paths changed")
    if readiness.get("ready_for_candidate") is not True:
        raise ValueError("candidate must be ready only after all final gates pass")
    return evidence


def _build_artifacts(root: Path, work: Path) -> tuple[Path, Path]:
    dist = work / "dist"
    _run(sys.executable, "-m", "build", "--no-isolation", "--outdir", str(dist), cwd=root, env=_offline_dependency_env())
    wheels = sorted(dist.glob("*.whl"))
    sources = sorted(dist.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sources) != 1:
        raise ValueError("expected exactly one wheel and one source distribution")
    return wheels[0], sources[0]


def _installed_probe(root: Path, environment: Path, work: Path) -> str:
    return f'''
import hashlib
import json
from pathlib import Path

root = Path({str(root)!r}).resolve()
environment = Path({str(environment)!r}).resolve()
work = Path({str(work)!r}).resolve()

import ncmemsim
origin = Path(ncmemsim.__file__).resolve()
assert origin.is_relative_to(environment), origin
assert not origin.is_relative_to(root), origin

for name in [
    "ncmemsim.dtco",
    "ncmemsim.dtco.reporting",
    "ncmemsim.dtco.robust_reporting",
    "ncmemsim.workflows",
    "ncmemsim.workflows.evidence",
    "ncmemsim.workflows.application",
    "ncmemsim.workflows.reporting",
    "ncmemsim.transport",
    "ncmemsim.fitting",
]:
    module = __import__(name, fromlist=["*"])
    module_file = Path(module.__file__).resolve()
    assert module_file.is_relative_to(environment), (name, module_file)

from ncmemsim.dtco import DTCOReport, RobustDTCOReport, SampleManifest
from ncmemsim.workflows import DatasetEvidence, WorkflowEvidence, AppliedWorkflowEvidence, WorkflowReport, DataOrigin
assert DataOrigin.SYNTHETIC.value == "synthetic"

fixture_root = work / "archive_fixtures"
inventory = json.loads((fixture_root / "inventory.json").read_text(encoding="utf-8"))
readers = {{
    "dtco": DTCOReport,
    "robust": RobustDTCOReport,
    "workflow": WorkflowReport,
    "dataset_evidence": DatasetEvidence,
    "workflow_evidence": WorkflowEvidence,
    "applied_evidence": AppliedWorkflowEvidence,
    "sample_manifest": SampleManifest,
}}
for entry in inventory["files"]:
    path = fixture_root / entry["file"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]
    text = path.read_text(encoding="utf-8")
    parsed = readers[path.stem].from_json(text)
    assert parsed.to_dict() == json.loads(text)

print("Installed distribution probe PASS:", origin)
'''


def validate_installed_artifacts(root: Path) -> dict:
    with tempfile.TemporaryDirectory(prefix="ncmemsim-clean-dist-") as tmp:
        work = Path(tmp)
        wheel, source = _build_artifacts(root, work)
        source_count = check_source_content(source, root)
        checked = []
        for index, artifact in enumerate((wheel, source)):
            check_archive(artifact)
            environment = work / f"env-{index}"
            python = create_environment(environment, inherit=True)
            _run(
                str(python),
                "-m",
                "pip",
                "install",
                "--no-deps",
                "--no-build-isolation",
                str(artifact) + "[fit]",
                cwd=work,
                env=_offline_dependency_env(),
            )
            shutil.copytree(root / "tests/fixtures/archives/v0_14_0", work / "archive_fixtures", dirs_exist_ok=True)
            probe = work / f"probe-{index}.py"
            probe.write_text(_installed_probe(root, environment, work), encoding="utf-8")
            _run(str(python), "-I", str(probe), cwd=work)
            checked.append(artifact.name)
        return {"artifacts": checked, "audited_source_files": source_count}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata-only", action="store_true", help="Validate retained evidence without rebuilding artifacts.")
    parser.add_argument("--reuse-dependencies", action="store_true", help="Accepted for explicit offline final-gate command readability.")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        evidence = validate_evidence(root)
        result = {"evidence": evidence["status"]}
        if not args.metadata_only:
            result.update(validate_installed_artifacts(root))
    except (ValueError, KeyError, TypeError, OSError, subprocess.CalledProcessError) as exc:
        print("Clean installed distribution gate FAIL:", exc, file=sys.stderr)
        return 1
    print("Clean installed distribution gate PASS: " + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
