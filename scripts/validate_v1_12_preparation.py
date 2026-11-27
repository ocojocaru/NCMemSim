# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Check retained v1.11 package sources and the additive Phase U surface."""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def validate_sources(root, review):
    root = Path(root)
    expected = dict(review['published_sources'])
    for name, declaration in review['additions'].items():
        path = name.replace('.', '/') + '.py'
        if path in expected:
            raise ValueError('addition overlaps a published source')
        expected[path] = declaration['sha256']
        tree = ast.parse((root / path).read_text(encoding='utf-8'))
        exports = [ast.literal_eval(node.value) for node in tree.body
                   if isinstance(node, ast.Assign) and any(
                       isinstance(t, ast.Name) and t.id == '__all__' for t in node.targets)]
        if exports != [declaration['exports']]:
            raise ValueError(f'export drift: {path}')
    actual = {p.relative_to(root).as_posix() for p in (root / 'ncmemsim').rglob('*.py')}
    if actual != set(expected):
        raise ValueError('package source membership drift')
    for path, digest in expected.items():
        source = (root / path).read_text(encoding='utf-8')
        if path == 'ncmemsim/_version.py':
            # Only the reviewed version literal may differ from the published source.
            source = source.replace('__version__ = "1.12.0"', '__version__ = "1.11.0"')
        if hashlib.sha256(source.encode('utf-8')).hexdigest() != digest:
            raise ValueError(f'source drift: {path}')
    return {'retained_modules': len(review['published_sources']),
            'additive_modules': len(review['additions']),
            'additive_exports': sum(len(v['exports']) for v in review['additions'].values())}


def validate(root=ROOT):
    root = Path(root)
    review = json.loads((root / 'docs/v1_12_api_review.json').read_text(encoding='utf-8'))
    if (review['baseline_commit'] != '77c4c982084383791511eb45fa128974e26b0044'
            or review['preparation_version'] != '1.11.0' or review['target_release'] != '1.12.0'):
        raise ValueError('preparation identity drift')
    return validate_sources(root, review)


if __name__ == '__main__':
    print('Phase U7 preparation PASS:', validate())
