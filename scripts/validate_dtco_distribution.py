"""Build and exercise wheel/sdist installations outside the source checkout."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import venv
import zipfile

REQUIRED = {f"ncmemsim/dtco/{name}.py" for name in
            ("__init__", "spec", "binding", "operating", "sweep", "metrics", "pareto", "sensitivity", "reporting", "variation", "sampling", "propagation", "sample_analysis", "robust", "robust_reporting")}

REQUIRED |= {"ncmemsim/workflows/__init__.py", "ncmemsim/workflows/evidence.py", "ncmemsim/workflows/application.py", "ncmemsim/workflows/reporting.py"}

# Every package source module is required, not only the DTCO/workflow subset.
REQUIRED |= {p.relative_to(Path(__file__).resolve().parents[1]).as_posix()
             for p in (Path(__file__).resolve().parents[1] / "ncmemsim").rglob("*.py")}

# Source releases must carry the audited documentation and its build entry points.
SOURCE_REQUIRED = {
    'CITATION.cff',
    'LICENSE',
    'pyproject.toml',
    'assets/banner.svg',
    'docs/NCMemSim_v6_Software_Design_Specification_Rev1.md',
    'docs/Validation_Report.md',
    'docs/api.md',
    'docs/api_compatibility.md',
    'docs/api_inventory.md',
    'docs/api_inventory.json',
    'docs/api_results.md',
    'docs/api_analysis_results.md',
    'docs/api_archives.md',
    'docs/scientific_defaults.md',
    'docs/distribution_contracts.md',
    'docs/release_readiness.md',
    'docs/release_readiness.json',
    'docs/archival_citation.md',
    'docs/archival_citation.json',
    'docs/final_candidate_remote_evidence.json',
    'docs/final_candidate_local_regression.json',
    'docs/final_candidate_local_regression.md',
    'docs/final_candidate_remote_evidence.md',
    'docs/stable_api_proposal.md',
    'docs/stable_api_proposal.json',
    'scripts/validate_stable_api_proposal.py',
    'scripts/validate_release_readiness.py',
    'scripts/validate_archival_citation.py',
    'scripts/validate_remote_candidate_gates.py',
    'scripts/validate_local_regression_gate.py',
    'scripts/validate_clean_distribution_gate.py',
    'scripts/validate_strict_documentation_gate.py',
    'scripts/validate_final_candidate_gates.py',
    'docs/final_candidate_clean_distributions.json',
    'docs/final_candidate_clean_distributions.md',
    'docs/final_candidate_strict_documentation.json',
    'docs/final_candidate_strict_documentation.md',
    'docs/final_candidate_gates.json',
    'docs/final_candidate_gates.md',
    'scripts/validate_api_contract.py',
    'docs/architecture.md',
    'docs/advanced_transport.md',
    'docs/assets/banner.svg',
    'docs/branding.md',
    'docs/calibration.md',
    'docs/developer.md',
    'docs/device_calibration.md',
    'docs/device_model.md',
    'docs/dtco.md',
    'docs/electrostatics.md',
    'docs/glossary.md',
    'docs/index.md',
    'docs/installation.md',
    'docs/materials.md',
    'docs/near_edge_reference.md',
    'docs/optics.md',
    'docs/physics.md',
    'docs/quickstart.md',
    'docs/reproducibility.md',
    'docs/roadmap.md',
    'docs/robust_dtco.md',
    'docs/scientific_scope.md',
    'docs/scientific_workflows.md',
    'docs/transport_retention.md',
    'docs/validation.md',
    'docs/workflows.md',
    'examples/phase_g6_dtco_reference.py',
    'examples/phase_h6_robust_dtco_reference.py',
    'examples/phase_i3_electrical_workflow_reference.py',
    'examples/phase_i4_electro_optical_workflow_reference.py',
    'examples/phase_i6_linked_workflow_report.py',
    'scripts/validate_documentation.py',
    'mkdocs.yml',
    'scripts/validate_dtco_distribution.py',
}
SOURCE_REQUIRED |= {"tests/fixtures/archives/v0_14_0/" + name + ".json" for name in
    ("dtco", "robust", "workflow", "dataset_evidence", "workflow_evidence", "applied_evidence", "sample_manifest", "inventory")}

def check_archive(path: Path) -> None:
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
    else:
        with tarfile.open(path, "r:gz") as archive:
            names = {name.partition("/")[2] for name in archive.getnames()}
    required = REQUIRED if path.suffix == ".whl" else REQUIRED | SOURCE_REQUIRED
    missing = required - names
    if missing:
        raise ValueError(f"{path.name}: missing required release files: {sorted(missing)}")

def check_source_content(path: Path, root: Path) -> int:
    """Compare audited source bytes, including every documentation asset."""
    expected = REQUIRED | SOURCE_REQUIRED | {"README.md", "MANIFEST.in"}
    for directory in ("docs", "assets", "data/reference", "examples", "tests/fixtures/archives"):
        expected.update(p.relative_to(root).as_posix() for p in (root / directory).rglob("*")
                        if p.is_file() and "__pycache__" not in p.parts
                        and p.suffix not in {".pyc", ".pyo"})
    with tarfile.open(path, "r:gz") as archive:
        members = {}
        for member in archive.getmembers():
            name = member.name.partition("/")[2]
            if name in members:
                raise ValueError(f"duplicate source archive member: {name}")
            members[name] = member
        for name in sorted(expected):
            member = members.get(name)
            if member is None or not member.isfile():
                raise ValueError(f"missing source content: {name}")
            with archive.extractfile(member) as stream:
                if stream.read() != (root / name).read_bytes():
                    raise ValueError(f"source content differs: {name}")
    return len(expected)

def run(*args: str, cwd: Path) -> None:
    subprocess.run(args, cwd=cwd, check=True)

def create_environment(path: Path, *, inherit: bool = False) -> Path:
    # Conda's Windows stdlib extensions need its runtime DLL directory even
    # when package dependencies are isolated in a normal venv.
    venv.EnvBuilder(with_pip=False, system_site_packages=inherit).create(path)
    python = path / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    dll_directory = Path(sys.base_prefix) / "Library" / "bin"
    if sys.platform == "win32" and (Path(sys.base_prefix) / "conda-meta").is_dir() and dll_directory.is_dir():
        site_packages = path / "Lib" / "site-packages"
        # Keep the directory handle alive for the lifetime of each interpreter.
        (site_packages / "ncmemsim_conda_runtime.pth").write_text(
            "import os; os._ncmemsim_conda_runtime = os.add_dll_directory("
            + repr(str(dll_directory)) + ")\n", encoding="utf-8")
    run(str(python), "-m", "ensurepip", "--upgrade", cwd=path)
    run(str(python), "-I", "-c", "import pyexpat, ssl; print('Runtime DLL check: PASS')", cwd=path)
    return python

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reuse-dependencies", action="store_true",
                        help="Offline local check: inherit dependencies, but install NCMemSim separately.")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="ncmemsim-g7-") as temporary:
        work = Path(temporary)
        dist = work / "dist"
        if args.reuse_dependencies:
            builder = sys.executable
        else:
            builder = str(create_environment(work / "builder"))
            run(builder, "-m", "pip", "install", "build", "setuptools>=68", "wheel", cwd=work)
        # The builder is a fresh environment in default mode. Build both the
        # sdist and the wheel from that sdist using its freshly installed tools.
        run(builder, "-m", "build", "--no-isolation", "--outdir", str(dist), cwd=root)
        wheels, sources = list(dist.glob("*.whl")), list(dist.glob("*.tar.gz"))
        if len(wheels) != 1 or len(sources) != 1:
            raise ValueError("Expected exactly one wheel and one source distribution")
        source_count = check_source_content(sources[0], root)
        results = []
        for number, artifact in enumerate(wheels + sources):
            check_archive(artifact)
            environment = work / f"env-{number}"
            python = create_environment(environment, inherit=args.reuse_dependencies)
            options = ["--no-deps", "--no-build-isolation"] if args.reuse_dependencies else []
            if not args.reuse_dependencies and artifact.suffix != ".whl":
                run(str(python), "-m", "pip", "install", "setuptools>=68", "wheel", cwd=work)
                options = ["--no-build-isolation"]
            # The integration reference uses the declared optional fit extra.
            run(str(python), "-m", "pip", "install", *options, str(artifact) + "[fit]", cwd=work)
            # Copy only the public reference example, never the source package.
            shutil.copyfile(root / "examples/phase_g6_dtco_reference.py", work / "reference.py")
            shutil.copyfile(root / "examples/phase_h6_robust_dtco_reference.py", work / "robust_reference.py")
            shutil.copyfile(root / "examples/phase_i3_electrical_workflow_reference.py", work / "electrical_workflow_reference.py")
            shutil.copyfile(root / "examples/phase_i4_electro_optical_workflow_reference.py", work / "electro_optical_workflow_reference.py")
            for filename in ('phase_i3_electrical_workflow_reference.py', 'phase_i4_electro_optical_workflow_reference.py', 'phase_i6_linked_workflow_report.py'):
                shutil.copyfile(root / 'examples' / filename, work / filename)
            shutil.copytree(root / "tests/fixtures/archives/v0_14_0",
                            work / "archive_fixtures", dirs_exist_ok=True)
            probe = work / "probe.py"
            probe.write_text(PROBE, encoding="utf-8")
            run(str(python), "-I", str(probe), str(root), str(environment), str(work), cwd=work)
            results.append({"artifact": artifact.name, "installed_workflow": "PASS"})
        print(json.dumps({"distributions": results, "audited_source_files": source_count,
                          "dependency_mode": "inherited" if args.reuse_dependencies else "clean"}, indent=2))

PROBE = r'''import csv
import json
import importlib.util
from pathlib import Path
import sys
import ncmemsim
from ncmemsim.transport import (
    TrapAssistedTransportSpec, TrapParameterStatus, TrapSpecies,
    evaluate_trap_assisted_transport,
)
assert TrapAssistedTransportSpec().enabled is False
assert TrapSpecies.__module__ == "ncmemsim.transport.traps"
_tat_trap = TrapSpecies("installed-smoke", 1.602176634e-19, 0.5, 1e23, 1e-19,
    1e13, TrapParameterStatus.ASSUMED, "synthetic installed check", "conditional rate")
_tat_result = evaluate_trap_assisted_transport(
    TrapAssistedTransportSpec(True, (_tat_trap,)), link_length_m=8e-9,
    electric_field_V_m=2e8, effective_mass_m0=0.2)
assert _tat_result.total_rate_Hz > 0 and len(_tat_result.components) == 1
from ncmemsim.workflows import DataOrigin, DatasetEvidence, WorkflowEvidence, capture_dataset_evidence, build_workflow_evidence
from ncmemsim.workflows import AppliedWorkflowEvidence, WorkflowEvaluator, apply_workflow_parameters
assert DataOrigin.SYNTHETIC.value == "synthetic"
from ncmemsim.dtco import (DTCOReport, write_dtco_report, UniformVariation,
    TruncatedNormalVariation, VariationDefinition, VariationKind, VariationProvenance,
    ParameterBinding, BindingScope)
variation = VariationDefinition("temperature", ParameterBinding(BindingScope.DEVICE,
    ("temperature_K",)), UniformVariation(290,310), "K",
    VariationKind.PARAMETER_ESTIMATION, VariationProvenance("Assumed", "Reference"))
assert len(variation.definition_hash) == 64
assert TruncatedNormalVariation(290,310,300,2).to_dict()["family"] == "truncated_normal"
root, environment, work = map(Path, sys.argv[1:])
origin = Path(ncmemsim.__file__).resolve()
assert origin.is_relative_to(environment.resolve()), origin
assert not origin.is_relative_to(root.resolve()), origin
import ncmemsim.workflows.evidence as workflow_evidence
assert Path(workflow_evidence.__file__).resolve().is_relative_to(environment.resolve())
import ncmemsim.workflows.application as workflow_application
assert Path(workflow_application.__file__).resolve().is_relative_to(environment.resolve())
spec = importlib.util.spec_from_file_location("reference", work / "reference.py")
reference = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reference)
for invalid in (False, True):
    first = reference.build_reference_report(include_invalid_point=invalid)
    second = reference.build_reference_report(include_invalid_point=invalid)
    assert first.report_hash == second.report_hash
    assert DTCOReport.from_json(first.to_json()).report_hash == first.report_hash
    points = first.to_dict()["metric_analysis"]["data"]["points"]
    assert len(points) == (6 if invalid else 4)
    assert sum(p["status"] == "failed" for p in points) == (2 if invalid else 0)
    destination = work / ("failure-report" if invalid else "reference-report")
    # Each distribution gets a fresh export directory.
    destination = environment / destination.name
    write_dtco_report(first, destination)
    assert {p.name for p in destination.iterdir()} == {"manifest.json", "points.csv", "sensitivity.csv", "report.md"}
    assert DTCOReport.from_json((destination / "manifest.json").read_text(encoding="utf-8")).report_hash == first.report_hash
    with (destination / "points.csv").open(newline="", encoding="utf-8") as stream:
        assert len(list(csv.DictReader(stream))) == len(points)
from ncmemsim.dtco import RobustDTCOReport, write_robust_dtco_report
import importlib
for name in ("sampling", "propagation", "sample_analysis", "robust", "robust_reporting"):
    module = importlib.import_module("ncmemsim.dtco." + name)
    assert Path(module.__file__).resolve().is_relative_to(environment.resolve())
spec = importlib.util.spec_from_file_location("robust_reference", work / "robust_reference.py")
robust_reference = importlib.util.module_from_spec(spec)
spec.loader.exec_module(robust_reference)
for failures in (False, True):
    report = robust_reference.build_reference_report(include_failures=failures)
    assert report.report_hash == robust_reference.build_reference_report(include_failures=failures).report_hash
    assert RobustDTCOReport.from_json(report.to_json()).report_hash == report.report_hash
    analyses = report.to_dict()["analyses"]
    assert len(analyses) == 2
    for analysis in analyses:
        points = analysis["data"]["points"]
        assert len(points) == 4
        assert sum(p["status"] == "failed" for p in points) == (3 if failures else 0)
    destination = environment / ("robust-failures" if failures else "robust-reference")
    write_robust_dtco_report(report, destination)
    assert {p.name for p in destination.iterdir()} == {"manifest.json", "samples.csv", "statistics.csv", "nominal.csv", "robust.csv", "report.md"}
    assert RobustDTCOReport.from_json((destination / "manifest.json").read_text(encoding="utf-8")).report_hash == report.report_hash
    with (destination / "samples.csv").open(newline="", encoding="utf-8") as stream:
        assert len(list(csv.DictReader(stream))) == 8
print("Installed Robust DTCO: reproducibility, three failure stages, restoration and six exports PASS")
spec = importlib.util.spec_from_file_location("electrical_workflow_reference", work / "electrical_workflow_reference.py")
electrical_workflow_reference = importlib.util.module_from_spec(spec)
spec.loader.exec_module(electrical_workflow_reference)
for failures in (False, True):
    report = electrical_workflow_reference.build_reference_report(include_failures=failures)
    data = report.to_dict()
    source = WorkflowEvidence.from_json(json.dumps(data['metadata']['source_workflow_evidence']))
    assert source.scientific_status == 'FITTED' and source.qualification_eligible is True
    assert source.to_dict()['fit_dataset']['origin'] == 'synthetic'
    for section in data['analyses']:
        analysis = section['data']
        assert analysis['counts']['total'] == 4 and analysis['counts']['failed'] == (3 if failures else 0)
        applied = AppliedWorkflowEvidence.from_json(json.dumps(
            analysis['source']['study']['evaluation']['parameters']['applied_workflow_evidence']))
        assert applied.evidence_hash == data['metadata']['applied_workflow_evidence_hash']
        assert applied.to_dict()['workflow_evidence'] == source.to_dict()
    assert RobustDTCOReport.from_json(report.to_json()).report_hash == report.report_hash
print('Installed I3 electrical fitting/qualification/application/nominal/sample source links: PASS')
spec = importlib.util.spec_from_file_location("electro_optical_workflow_reference", work / "electro_optical_workflow_reference.py")
electro_optical_workflow_reference = importlib.util.module_from_spec(spec)
spec.loader.exec_module(electro_optical_workflow_reference)
for failures in (False, True):
    report = electro_optical_workflow_reference.build_reference_report(include_failures=failures)
    data = report.to_dict()
    source = WorkflowEvidence.from_json(json.dumps(data['metadata']['source_workflow_evidence']))
    assert source.scientific_status == 'FITTED' and source.qualification_eligible is True
    assert source.to_dict()['fit_dataset']['origin'] == 'synthetic'
    for section in data['analyses']:
        analysis = section['data']
        assert analysis['counts']['total'] == 4 and analysis['counts']['failed'] == (3 if failures else 0)
        applied = AppliedWorkflowEvidence.from_json(json.dumps(
            analysis['source']['study']['evaluation']['parameters']['applied_workflow_evidence']))
        assert applied.evidence_hash == data['metadata']['applied_workflow_evidence_hash']
        assert applied.to_dict()['workflow_evidence'] == source.to_dict()
        context = applied.to_dict()['applied_context']
        assert abs(context['photo_config']['photo_capture_efficiency'] - 2e-7) < 2e-10
    assert RobustDTCOReport.from_json(report.to_json()).report_hash == report.report_hash
print('Installed I4 electro-optical fitting/qualification/application/nominal/sample source links: PASS')
from ncmemsim.workflows import WorkflowReport, build_workflow_report, write_workflow_report
spec = importlib.util.spec_from_file_location('linked_workflow_reference', work / 'phase_i6_linked_workflow_report.py')
linked_workflow_reference = importlib.util.module_from_spec(spec)
spec.loader.exec_module(linked_workflow_reference)
for optical in (False, True):
    for failures in (False, True):
        report = linked_workflow_reference.build_reference_report(optical=optical, include_failures=failures)
        assert WorkflowReport.from_json(report.to_json()).report_hash == report.report_hash
        assert report.to_dict()['scientific_summary']['scientific_status'] == 'FITTED'
        destination = environment / ('workflow-%s-%s' % (optical, failures))
        assert len(write_workflow_report(report, destination)) == 6
        assert WorkflowReport.from_json((destination / 'manifest.json').read_text(encoding='utf-8')).report_hash == report.report_hash
print('Installed I6 linked electrical/optical normal/error sources and six exports: PASS')
# Frozen published-code archives must be readable by the installed package.
import hashlib
from ncmemsim.dtco import SampleManifest
fixture_root = work / 'archive_fixtures'
fixture_inventory = json.loads((fixture_root / 'inventory.json').read_text(encoding='utf-8'))
readers = {'dtco': DTCOReport, 'robust': RobustDTCOReport, 'workflow': WorkflowReport,
    'dataset_evidence': DatasetEvidence, 'workflow_evidence': WorkflowEvidence,
    'applied_evidence': AppliedWorkflowEvidence, 'sample_manifest': SampleManifest}
for entry in fixture_inventory['files']:
    path = fixture_root / entry['file']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == entry['sha256']
    text = path.read_text(encoding='utf-8')
    assert readers[path.stem].from_json(text).to_dict() == json.loads(text)
print('Installed frozen published-v0.14.0 archive readers: PASS')
print("Installed DTCO reference, failure handling, deterministic hashes and exports: PASS", origin)
'''

if __name__ == "__main__":
    main()
