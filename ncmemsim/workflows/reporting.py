"""Linked scientific workflow archives; restoration performs no fitting or physics."""
from __future__ import annotations
import csv
from dataclasses import dataclass
from io import StringIO
import json
from pathlib import Path
from ..hashing import canonical_hash
from ..dtco import RobustDTCOReport, BindingScope, ParameterBinding, apply_device_bindings
from ..dtco.spec import _device_definition_payload, _operating_definition_payload, _canonical_binding_unit
from ..dtco.sweep import _json_snapshot
from .evidence import WorkflowEvidence, _load, _label
from .application import AppliedWorkflowEvidence, _restore_device, _restore_protocol


def _summary(source):
    raw = source.to_dict()
    return {'scientific_status': source.scientific_status,
        'fit_data_origin': raw['fit_dataset']['origin'],
        'validation_data_origin': None if raw['validation_dataset'] is None else raw['validation_dataset']['origin'],
        'qualification_eligible': source.qualification_eligible}


def _check(raw):
    if set(raw) != {'schema_version', 'name', 'ncmemsim_version', 'metadata',
        'workflow_evidence', 'applied_workflow_evidence', 'robust_report', 'device_variants', 'scientific_summary'} or raw['schema_version'] != 'scientific-workflow-report-v1':
        raise ValueError('unsupported or incomplete workflow report schema')
    _label(raw['name'], 'report name'); _label(raw['ncmemsim_version'], 'package version')
    if type(raw['metadata']) is not dict:
        raise ValueError('report metadata must be an object')
    try:
        source = WorkflowEvidence.from_json(_json_snapshot(raw['workflow_evidence']))
        applied = AppliedWorkflowEvidence.from_json(_json_snapshot(raw['applied_workflow_evidence']))
        report = RobustDTCOReport.from_json(_json_snapshot(raw['robust_report']))
        context = applied.to_dict()
        if context['workflow_evidence'] != source.to_dict():
            raise ValueError('workflow/application source mismatch')
        if _json_snapshot(raw['scientific_summary']) != _json_snapshot(_summary(source)):
            raise ValueError('scientific status/origin/qualification mismatch')
        if raw['ncmemsim_version'] != context['runtime']['ncmemsim'] or report.to_dict()['ncmemsim_version'] != raw['ncmemsim_version']:
            raise ValueError('report package provenance mismatch')
        studies = report.to_dict()['analyses']
        if type(raw['device_variants']) is not list or len(raw['device_variants']) != len(studies):
            raise ValueError('device variant order/count mismatch')
        base = _restore_device(context['applied_context']['device'])
        operating = _operating_definition_payload(_restore_protocol(context['operating']))
        for variant, section in zip(raw['device_variants'], studies):
            if type(variant) is not list:
                raise ValueError('device variant assignments must be lists')
            assignments = []
            for item in variant:
                if type(item) is not dict or set(item) != {'binding', 'value', 'unit'}:
                    raise ValueError('invalid device variant assignment')
                binding = item['binding']
                if type(binding) is not dict or set(binding) != {'scope', 'path'} or type(binding['path']) is not list:
                    raise ValueError('invalid device variant binding')
                parsed = ParameterBinding(BindingScope(binding['scope']), tuple(binding['path']))
                if parsed.scope is not BindingScope.DEVICE or item['unit'] != _canonical_binding_unit(parsed):
                    raise ValueError('device variant scope/unit mismatch')
                assignments.append((parsed, item['value']))
            candidate = apply_device_bindings(base, assignments)
            study = section['data']['source']['study']
            evaluation = study['evaluation']
            if evaluation['id'] != context['evaluation_id'] or evaluation['parameters'].get('applied_workflow_evidence') != applied.to_dict():
                raise ValueError('study/application evaluator source mismatch')
            if study['runtime'] != context['runtime']:
                raise ValueError('study/application runtime mismatch')
            if study['nominal']['device'] != _device_definition_payload(candidate):
                raise ValueError('undeclared nominal device variant')
            if study['nominal']['operating'] != operating:
                raise ValueError('study/application operating mismatch')
        # Metadata never substitutes for the authoritative typed sources. If
        # retained H references declare these links, they must agree as well.
        metadata = report.to_dict()['metadata']
        for key, expected in (('source_workflow_evidence', source.to_dict()),
            ('applied_workflow_evidence_hash', applied.evidence_hash)):
            if key in metadata and metadata[key] != expected:
                raise ValueError('legacy report metadata source mismatch')
    except (KeyError, TypeError, IndexError, AttributeError) as error:
        raise ValueError('incomplete workflow report structure') from error


@dataclass(frozen=True)
class WorkflowReport:
    """One source/application linked to ordered H studies and explicit DEVICE variants.

    Integrity is consistency, not authenticity or experimental qualification.
    Runtime provenance is archived without requiring this machine's runtime.
    """
    payload_json: str

    def __post_init__(self):
        raw = _load(self.payload_json)
        _check(raw)
        object.__setattr__(self, 'payload_json', _json_snapshot(raw))

    @property
    def report_hash(self):
        return canonical_hash(json.loads(self.payload_json))

    def to_dict(self):
        return {**json.loads(self.payload_json), 'report_hash': self.report_hash}

    def to_json(self):
        return _json_snapshot(self.to_dict())

    @classmethod
    def from_json(cls, value):
        raw = _load(value)
        expected = raw.pop('report_hash', None)
        if expected != canonical_hash(raw):
            raise ValueError('workflow report integrity mismatch')
        return cls(_json_snapshot(raw))

    def _csv(self, method):
        raw = self.to_dict()
        robust = RobustDTCOReport.from_json(_json_snapshot(raw['robust_report']))
        rows = list(csv.reader(StringIO(getattr(robust, method)())))
        prefix = ['workflow_report_hash', 'workflow_evidence_hash', 'applied_workflow_evidence_hash',
            'scientific_status', 'fit_data_origin', 'validation_data_origin', 'qualification_eligible']
        summary = raw['scientific_summary']
        values = [self.report_hash, raw['workflow_evidence']['evidence_hash'],
            raw['applied_workflow_evidence']['evidence_hash'], summary['scientific_status'],
            summary['fit_data_origin'], summary['validation_data_origin'], summary['qualification_eligible']]
        stream = StringIO(newline='')
        writer = csv.writer(stream, lineterminator='\n')
        writer.writerow(prefix + rows[0])
        for row in rows[1:]: writer.writerow(values + row)
        return stream.getvalue()

    def samples_csv(self): return self._csv('samples_csv')
    def statistics_csv(self): return self._csv('statistics_csv')
    def nominal_csv(self): return self._csv('nominal_csv')
    def robust_csv(self): return self._csv('robust_csv')

    def to_markdown(self):
        raw = self.to_dict(); summary = raw['scientific_summary']
        source = raw['workflow_evidence']
        lines = ['# Scientific workflow report', '', raw['name'], '',
            f"Report hash: `{self.report_hash}`",
            f"Workflow evidence hash: `{source['evidence_hash']}`",
            f"Applied context evidence hash: `{raw['applied_workflow_evidence']['evidence_hash']}`", '',
            f"Scientific status: **{summary['scientific_status']}**",
            f"Fit data origin: **{summary['fit_data_origin']}**",
            f"Validation data origin: **{summary['validation_data_origin']}**",
            f"Qualification eligible: `{summary['qualification_eligible']}`", '',
            'Qualification eligibility is not promotion to experimental calibration or manufacturing yield.',
            'Integrity hashes establish consistency, not authenticity. Declared DEVICE variants retain order.', '',
            'Source and applicability declarations:', '']
        for key in ('fit_dataset', 'validation_dataset'):
            dataset = source[key]
            if dataset is not None:
                lines += [f"- {key}: {json.dumps(dataset['source'], ensure_ascii=False)}; applicability: {json.dumps(dataset['applicability'], ensure_ascii=False)}"]
        robust = RobustDTCOReport.from_json(_json_snapshot(raw['robust_report']))
        return '\n'.join(lines) + '\n\n' + robust.to_markdown()


def build_workflow_report(workflow_evidence, applied_workflow_evidence, robust_report, *, name,
        device_variants, metadata=None):
    """Require explicit DEVICE assignments for each ordered nominal study.

    An empty assignment tuple declares an unchanged applied device. Arbitrary
    device changes cannot be justified by free metadata or matching hashes.
    """
    if not isinstance(workflow_evidence, WorkflowEvidence) or not isinstance(applied_workflow_evidence, AppliedWorkflowEvidence) or not isinstance(robust_report, RobustDTCOReport):
        raise TypeError('typed workflow/application/Robust DTCO sources required')
    variants = []
    for assignments in device_variants:
        values = []
        for binding, value in assignments:
            if not isinstance(binding, ParameterBinding) or binding.scope is not BindingScope.DEVICE:
                raise TypeError('device variants require DEVICE ParameterBinding assignments')
            values.append({'binding': binding.to_dict(), 'value': value, 'unit': _canonical_binding_unit(binding)})
        variants.append(values)
    return WorkflowReport(_json_snapshot({'schema_version': 'scientific-workflow-report-v1',
        'name': name, 'ncmemsim_version': applied_workflow_evidence.to_dict()['runtime']['ncmemsim'],
        'metadata': {} if metadata is None else metadata, 'workflow_evidence': workflow_evidence.to_dict(),
        'applied_workflow_evidence': applied_workflow_evidence.to_dict(), 'robust_report': robust_report.to_dict(),
        'device_variants': variants, 'scientific_summary': _summary(workflow_evidence)}))


def write_workflow_report(report, output_dir):
    """Write six portable artifacts; preflight all existing targets before writing."""
    if not isinstance(report, WorkflowReport): raise TypeError('WorkflowReport required')
    contents = [('manifest.json', report.to_json() + '\n'), ('samples.csv', report.samples_csv()),
        ('statistics.csv', report.statistics_csv()), ('nominal.csv', report.nominal_csv()),
        ('robust.csv', report.robust_csv()), ('report.md', report.to_markdown())]
    directory = Path(output_dir).resolve()
    targets = tuple(directory / name for name, _ in contents)
    if any(target.exists() or target.is_symlink() for target in targets):
        raise FileExistsError('workflow report target already exists')
    directory.mkdir(parents=True, exist_ok=True)
    for target, (_, content) in zip(targets, contents):
        with target.open('x', encoding='utf-8', newline='\n') as stream: stream.write(content)
    return targets


__all__ = ['WorkflowReport', 'build_workflow_report', 'write_workflow_report']
