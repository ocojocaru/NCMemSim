"""Check the source API baseline without importing optional fitting dependencies.

Run without arguments to compare against the reviewed inventory. Regeneration is
an explicit maintainer operation; it never establishes v1.0 stability by itself.
"""
from __future__ import annotations

import argparse
import ast
import importlib.util
import json
from pathlib import Path
import re

BASELINE_COMMIT = "c0ce4bf108709ca9194c736be4e7e130ef03b48e"


def _expr(node):
    return ast.unparse(node) if node is not None else None


def _call(node):
    positional = list(node.args.posonlyargs) + list(node.args.args)
    defaults = [None] * (len(positional) - len(node.args.defaults)) + list(node.args.defaults)
    params = []
    for i, (arg, default) in enumerate(zip(positional, defaults)):
        params.append({"name": arg.arg, "kind": "positional_only" if i < len(node.args.posonlyargs) else "positional_or_keyword",
            "annotation": _expr(arg.annotation), "required": default is None, "default_expression": _expr(default)})
    if node.args.vararg:
        arg = node.args.vararg
        params.append({"name": arg.arg, "kind": "var_positional", "annotation": _expr(arg.annotation)})
    for arg, default in zip(node.args.kwonlyargs, node.args.kw_defaults):
        params.append({"name": arg.arg, "kind": "keyword_only", "annotation": _expr(arg.annotation),
            "required": default is None, "default_expression": _expr(default)})
    if node.args.kwarg:
        arg = node.args.kwarg
        params.append({"name": arg.arg, "kind": "var_keyword", "annotation": _expr(arg.annotation)})
    return {"parameters": params, "return_annotation": _expr(node.returns),
        "source_signature": "(" + ast.unparse(node.args) + ")" + (" -> " + _expr(node.returns) if node.returns else ""),
        "decorators": [_expr(d) for d in node.decorator_list]}


def _definition(node):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return {"name": node.name, "kind": "function", **_call(node)}
    fields = []
    for member in node.body:
        if isinstance(member, ast.AnnAssign) and isinstance(member.target, ast.Name) and not member.target.id.startswith('_'):
            fields.append({"name": member.target.id, "annotation": _expr(member.annotation),
                "default_expression": _expr(member.value), "required_in_source": member.value is None})
    assignments = [{"names": [t.id for t in member.targets if isinstance(t, ast.Name) and not t.id.startswith('_')],
        "expression": _expr(member.value)} for member in node.body if isinstance(member, ast.Assign)
        and any(isinstance(t, ast.Name) and not t.id.startswith('_') for t in member.targets)]
    return {"name": node.name, "kind": "class", "class_assignments": assignments, "bases": [_expr(b) for b in node.bases],
        "decorators": [_expr(d) for d in node.decorator_list], "declared_fields": fields,
        "constructor": next((_call(m) for m in node.body if isinstance(m, ast.FunctionDef) and m.name == '__init__'), None),
        "methods": [{"name": m.name, **_call(m)} for m in node.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and not m.name.startswith('_')]}


def build_inventory(root: Path):
    modules = []
    for path in sorted((root / 'ncmemsim').rglob('*.py')):
        tree = ast.parse(path.read_text(encoding='utf-8-sig'))
        parts = list(path.relative_to(root).with_suffix('').parts)
        package_file = parts[-1] == '__init__'
        if package_file:
            parts.pop()
        module = '.'.join(parts)
        package = module if package_file else module.rpartition('.')[0]
        exports = None
        aliases = {}
        definitions = []
        constants = []
        for node in tree.body:
            if isinstance(node, (ast.Assign, ast.AugAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                if any(isinstance(t, ast.Name) and t.id == '__all__' for t in targets):
                    values = ast.literal_eval(node.value)
                    if not isinstance(values, (list, tuple)) or any(type(v) is not str for v in values):
                        raise ValueError('Nonliteral export list: ' + module)
                    exports = list(values) if isinstance(node, ast.Assign) else (exports or []) + list(values)
                else:
                    for target in targets:
                        if isinstance(target, ast.Name) and (not target.id.startswith('_') or target.id == '__version__'):
                            expression = _expr(node.value)
                            if target.id == '__version__':
                                # Runtime identity changes in compatible development and
                                # maintenance releases; the literal is not an API signature.
                                expression = "<runtime-version>"
                            constants.append({"name": target.id, "expression": expression})
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and not node.target.id.startswith('_'):
                constants.append({"name": node.target.id, "expression": _expr(node.value), "annotation": _expr(node.annotation)})
            elif isinstance(node, ast.ImportFrom):
                source = importlib.util.resolve_name('.' * node.level + (node.module or ''), package) if node.level else node.module
                for item in node.names:
                    if source and source.startswith('ncmemsim'):
                        aliases[item.asname or item.name] = source + '.' + item.name
            elif isinstance(node, ast.Import):
                for item in node.names:
                    if item.name.startswith('ncmemsim'):
                        aliases[item.asname or item.name.split('.')[0]] = item.name
            elif isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith('_'):
                definitions.append(_definition(node))
        modules.append({"module": module, "source": path.relative_to(root).as_posix(),
            "explicit_exports": exports, "package_import_aliases": dict(sorted(aliases.items())),
            "public_source_definitions": definitions, "public_assignments": constants})
    documented = set()
    for path in [root / 'README.md', *sorted((root / 'docs').rglob('*.md'))]:
        text = path.read_text(encoding='utf-8-sig')
        for code in re.findall(r'```python[^\n]*\n(.*?)```', text, re.S):
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and not node.level and node.module and node.module.startswith('ncmemsim'):
                    documented.update(node.module + '.' + item.name for item in node.names)
                elif isinstance(node, ast.Import):
                    documented.update(item.name for item in node.names if item.name.startswith('ncmemsim'))
    relax_keys = []
    simulator = ast.parse((root / 'ncmemsim/simulator.py').read_text(encoding='utf-8'))
    for node in ast.walk(simulator):
        if isinstance(node, ast.FunctionDef) and node.name == 'relax_voltage':
            for statement in ast.walk(node):
                if isinstance(statement, ast.Return) and isinstance(statement.value, ast.Dict):
                    relax_keys = [ast.literal_eval(key) for key in statement.value.keys]
    return {"result_dictionary_keys": {"ncmemsim.simulator.Simulator.relax_voltage": relax_keys}, "inventory_schema": "source-api-inventory-v1", "baseline_commit": BASELINE_COMMIT,
        "scope": "Every package source module, explicit exports, public source declarations and README/docs Python imports; declarations are not stability approval.",
        "signature_semantics": "Unevaluated source expressions; receiver retained; inherited/generated constructors and fields require base-class/dataclass review.",
        "modules": modules, "documented_imports": sorted(documented)}


def render_inventory(data):
    exported = sum(len(m['explicit_exports'] or []) for m in data['modules'])
    lines = ['# API source inventory', '',
        'Generated from the audited source baseline. [Compatibility preparation](api_compatibility.md)',
        'and [result contracts](api_results.md) distinguish observed behavior from v1.0 approval.', '',
        f"Coverage: {len(data['modules'])} package source modules; {exported} explicit export paths; {len(data['documented_imports'])} distinct documented Python import paths.", '',
        'Source signatures retain `self`/`cls` and unevaluated defaults. Dataclass fields below are',
        'declared fields, not a synthesized inherited constructor. Properties are shown as methods',
        'with their decorators. Public spelling alone does not approve an internal helper.', '',
        'The [JSON inventory](api_inventory.json) includes structured parameters, field defaults,',
        'assignment expressions and documented imports for compatibility review.', '']
    for mod in data['modules']:
        lines.extend(['## ' + mod['module'], '', '`' + mod['source'] + '`', ''])
        lines.extend(['Explicit exports: ' + ', '.join('`' + n + '`' for n in mod['explicit_exports']) if mod['explicit_exports'] is not None else 'No explicit export list; documented entry points need individual approval.', ''])
        for definition in mod['public_source_definitions']:
            if definition['kind'] == 'function':
                lines.extend(['- `' + definition['name'] + definition['source_signature'] + '`'])
            else:
                lines.extend(['### ' + definition['name'], '', 'Bases: ' + (', '.join('`'+b+'`' for b in definition['bases']) or 'none') + '.', ''])
                if definition['decorators']:
                    lines.extend(['Decorators: ' + ', '.join('`'+d+'`' for d in definition['decorators']) + '.', ''])
                if definition['constructor']:
                    lines.extend(['Constructor: `__init__' + definition['constructor']['source_signature'] + '`.', ''])
                for assignment in definition['class_assignments']:
                    lines.extend(['- Assignment `' + ', '.join(assignment['names']) + ' = ' + assignment['expression'] + '`.'])
                for field in definition['declared_fields']:
                    default = 'required declaration' if field['required_in_source'] else 'default expression `' + field['default_expression'] + '`'
                    lines.extend(['- Field `' + field['name'] + ': ' + field['annotation'] + '`; ' + default + '.'])
                for method in definition['methods']:
                    decorators = ('; ' + ', '.join('`'+d+'`' for d in method['decorators'])) if method['decorators'] else ''
                    lines.extend(['- `' + method['name'] + method['source_signature'] + '`' + decorators + '.'])
                lines.append('')
        lines.append('')
    lines.extend(['## Simulator diagnostic dictionary keys', '',
        'Reviewed shapes and units are in [result contracts](api_results.md).', ''])
    lines.extend('- `' + key + '`' for key in data['result_dictionary_keys']['ncmemsim.simulator.Simulator.relax_voltage'])
    return '\n'.join(lines).rstrip() + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--write-baseline', action='store_true', help='Explicitly regenerate the review baseline and its Markdown page.')
    args = parser.parse_args()
    root = args.root.resolve()
    data = build_inventory(root)
    baseline = root / 'docs/api_inventory.json'
    page = root / 'docs/api_inventory.md'
    if args.write_baseline:
        baseline.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        page.write_text(render_inventory(data), encoding='utf-8')
        print('Review inventory regenerated; this does not approve a v1.0 stability guarantee.')
    else:
        if json.loads(baseline.read_text(encoding='utf-8')) != data:
            raise SystemExit('API inventory drift: review imports/signatures/fields/defaults before explicit regeneration.')
        if page.read_text(encoding='utf-8') != render_inventory(data):
            raise SystemExit('Generated API inventory page differs from the baseline.')
        print(f"Source API inventory PASS: {len(data['modules'])} modules, {len(data['documented_imports'])} documented import paths.")


if __name__ == '__main__':
    main()
