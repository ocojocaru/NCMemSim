# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Check the Phase T preparation surface against the published v1.10 commit."""
import importlib
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_v1_10_api_review import validate as validate_v1_10


BASELINE = 'ba1b9ea9563f3786fb4af96215606b103a2925a2'
EXPORTS = {
    'ncmemsim.materials.finite_confinement_contracts': (
        'FiniteConfinementRequest', 'confinement_depth_eV_to_J',
    ),
    'ncmemsim.materials.finite_confinement': (
        'FiniteConfinementResult', 'evaluate_finite_confinement',
    ),
    'ncmemsim.finite_confinement_context': (
        'FiniteConfinementOpticalBinding', 'FiniteConfinementOpticalContext',
    ),
    'ncmemsim.finite_confinement_reporting': (
        'FiniteConfinementStudyReport', 'write_finite_confinement_study_bundle',
        'load_finite_confinement_study_bundle',
    ),
}


def validate():
    """Require the published package sources and the nine reviewed T exports."""
    validate_v1_10(ROOT)
    changes = subprocess.check_output(
        ['git', 'diff', '--no-renames', '--name-status', BASELINE, '--', 'ncmemsim'],
        cwd=ROOT, text=True,
    ).splitlines()
    expected = {f"A\t{name.replace('.', '/')}.py" for name in EXPORTS}
    expected.add('M\tncmemsim/_version.py')
    if set(changes) != expected:
        raise ValueError(f'unexpected runtime source changes since v1.10.0: {changes}')
    for name, expected_exports in EXPORTS.items():
        module = importlib.import_module(name)
        if tuple(module.__all__) != expected_exports or any(
            not hasattr(module, export) for export in expected_exports
        ):
            raise ValueError(f'Phase T export drift in {name}')
    print('v1.11 preparation PASS: retained v1.10 package sources and 9 Phase T exports')


if __name__ == '__main__':
    validate()
