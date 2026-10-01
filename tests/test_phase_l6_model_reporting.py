# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

"""Strict nested MODEL archives, complete accounting and deterministic exports."""
import csv
import hashlib
import json
from pathlib import Path
import pytest

from ncmemsim.hashing import canonical_hash
from ncmemsim.ensemble.model_dtco import ModelDTCOStudy, ModelEligibilityResult, ModelParetoAnalysis, evaluate_model_eligibility, analyze_model_pareto
from ncmemsim.ensemble.model_reporting import ModelReportStudy, ModelReport, build_model_report, write_model_report, load_model_report_bundle
from test_phase_l5_model_dtco import linked, objective


def make_report(*, failed=False, pareto=True):
    cases = tuple(evaluate_model_eligibility(linked(i, values, failing=(0,1) if failed else ()))
                  for i, values in enumerate(((1,3),(2,4))))
    result = analyze_model_pareto(cases,(objective(),)) if pareto else None
    return build_model_report('L6 tests',tuple(ModelReportStudy('study-'+str(i),s.study.source,s if pareto else None)
        for i,s in enumerate(cases)),pareto=result,limitations=('synthetic only','no yield or tail convergence'),
        evidence={'audit':{'steps':[16,32]},'note':'archived declaration'})


def rehash(data,key):
    data[key]=canonical_hash({k:v for k,v in data.items() if k != key})


def test_strict_dtco_readers_recompute_all_layers():
    study=linked(0)
    assert ModelDTCOStudy.from_dict(study.to_dict()).study_hash==study.study_hash
    eligibility=evaluate_model_eligibility(study)
    assert ModelEligibilityResult.from_dict(eligibility.to_dict(),study=study).to_dict()==eligibility.to_dict()
    pareto=analyze_model_pareto((eligibility,),(objective(),))
    assert ModelParetoAnalysis.from_json(pareto.to_json()).to_dict()==pareto.to_dict()


@pytest.mark.parametrize('mutate',[
    lambda d:d['points'][0].update(rank=99), lambda d:d.update(fronts=[[1]]),
    lambda d:d.update(ranked_design_count=True),lambda d:d['points'][0]['eligibility'].update(status='ineligible'),
    lambda d:d['points'][0]['objective_values'][0].update(value=99),
    lambda d:d['points'][0]['objective_values'][0].update(denominator=99),
    lambda d:d['sources'][0].update(point_hash='0'*64),
    lambda d:d['sources'][0]['design_point'].update(index=99),
    lambda d:d['sources'][0]['source']['statistics'][0].update(mean=99),
    lambda d:d['objectives'][0].update(scalar_definition_hash='0'*64),
    lambda d:d['objectives'][0]['scalar'].update(schema_version='unknown'),
    lambda d:d.update(extra=1),lambda d:d.update(schema_version='unknown'),
])
def test_rehashed_pareto_tampering_rejected(mutate):
    data=make_report().pareto.to_dict();mutate(data);rehash(data,'analysis_hash')
    with pytest.raises((ValueError,TypeError)):ModelParetoAnalysis.from_dict(data)


@pytest.mark.parametrize('mutate',[
    lambda d:d.update(schema_version='unknown'),lambda d:d.update(extra=1),
    lambda d:d['studies'][0]['population']['counts'].update(assessed_count=99),
    lambda d:d['studies'][0]['population']['fractions']['coverage_fraction'].update(denominator=99),
    lambda d:d['studies'][0]['dtco']['eligibility'].update(study_hash='0'*64),
    lambda d:d['studies'][0]['dtco']['study'].update(source_analysis_hash='0'*64),
    lambda d:d['pareto']['points'][0].update(exclusion_reason='ineligible'),
    lambda d:d['pareto']['sources'].reverse(),
    lambda d:d['studies'].reverse(),lambda d:d.update(evidence=[]),
])
def test_rehashed_report_tampering_rejected(mutate):
    data=make_report().to_dict();mutate(data);rehash(data,'report_hash')
    with pytest.raises((ValueError,TypeError)):ModelReport.from_dict(data)


def test_report_roundtrip_ownership_and_json_strictness():
    report=make_report();original=report.to_json()
    assert ModelReport.from_json(original).to_json()==original
    data=report.to_dict();data['evidence']['audit']['steps'][0]=99
    assert report.to_json()==original
    with pytest.raises(ValueError,match='duplicate'):
        ModelReport.from_json(original.replace('{','{"name":"forged",',1))
    with pytest.raises(ValueError):ModelReport.from_json('{"name":NaN}')


def test_report_links_require_exact_population_and_pareto_order():
    first,second=linked(0),linked(1)
    with pytest.raises(ValueError):ModelReportStudy('x',first.source,evaluate_model_eligibility(second))
    report=make_report()
    with pytest.raises(ValueError):build_model_report('x',report.studies[::-1],pareto=report.pareto)
    with pytest.raises(ValueError):build_model_report('x',(report.studies[0],report.studies[0]))
    with pytest.raises(ValueError):build_model_report('x',())


@pytest.mark.parametrize('failed',[False,True])
def test_complete_population_export_and_deterministic_rebuild(tmp_path,failed):
    report=make_report(failed=failed)
    first=write_model_report(report,tmp_path/'one')
    restored=load_model_report_bundle(first)
    second=write_model_report(restored,tmp_path/'two')
    assert restored.report_hash==report.report_hash
    for path in first.iterdir():assert path.read_bytes()==(second/path.name).read_bytes()
    with (first/'attempts.csv').open(encoding='utf-8',newline='') as handle:rows=list(csv.DictReader(handle))
    assert len(rows)==4
    assert [r['sample_index'] for r in rows]==['0','1','0','1']
    assert all(r['assignments_json'] for r in rows)
    if failed:
        assert all(r['status']=='failed' and r['failure_stage']=='workflow' for r in rows)
        with (first/'statistics.csv').open(encoding='utf-8',newline='') as handle:stats=list(csv.DictReader(handle))
        assert all(r['denominator']=='0' and r['mean']=='' for r in stats)
        assert restored.pareto.to_dict()['excluded_design_count']==2


def test_standalone_report_without_dtco_and_no_rerun(monkeypatch,tmp_path):
    import ncmemsim.ensemble.model_sampling as sampling
    import ncmemsim.ensemble.model_execution as execution
    report=make_report(pareto=False)
    monkeypatch.setattr(sampling,'generate_model_sample_manifest',lambda *a,**k:pytest.fail('resampling'))
    monkeypatch.setattr(execution,'execute_model_sample_manifest',lambda *a,**k:pytest.fail('physics rerun'))
    restored=ModelReport.from_json(report.to_json())
    write_model_report(restored,tmp_path/'standalone')
    assert load_model_report_bundle(tmp_path/'standalone').pareto is None


@pytest.mark.parametrize('filename',['attempts.csv','statistics.csv','designs.csv','report.md','report.json'])
def test_rehashed_bundle_projection_tampering_rejected(tmp_path,filename):
    path=write_model_report(make_report(),tmp_path/'bundle')
    file=path/filename;file.write_bytes(file.read_bytes()+b'forged\n')
    manifest=json.loads((path/'bundle.json').read_text())
    manifest['files'][filename]=hashlib.sha256(file.read_bytes()).hexdigest()
    (path/'bundle.json').write_text(json.dumps(manifest))
    with pytest.raises((ValueError,TypeError)):load_model_report_bundle(path)


@pytest.mark.parametrize('fault',['missing','extra','traversal','version','report_hash'])
def test_bundle_structure_and_manifest_faults(tmp_path,fault):
    path=write_model_report(make_report(),tmp_path/'bundle')
    if fault=='missing':(path/'attempts.csv').unlink()
    elif fault=='extra':(path/'extra.txt').write_text('unexpected')
    else:
        manifest=json.loads((path/'bundle.json').read_text())
        if fault=='traversal':manifest['files']['../escape']='0'*64
        elif fault=='version':manifest['schema_version']='unknown'
        else:manifest['report_hash']='0'*64
        (path/'bundle.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError):load_model_report_bundle(path)


def test_export_refuses_existing_targets(tmp_path):
    report=make_report();target=tmp_path/'existing';target.mkdir();(target/'keep.txt').write_text('keep')
    with pytest.raises(FileExistsError):write_model_report(report,target)
    assert (target/'keep.txt').read_text()=='keep'
    file=tmp_path/'file';file.write_text('keep')
    with pytest.raises(FileExistsError):write_model_report(report,file)
    assert file.read_text()=='keep'


def test_failed_export_cleans_only_its_created_files(monkeypatch,tmp_path):
    report=make_report();original=Path.open
    def failing(self,*args,**kwargs):
        if self.name=='statistics.csv':raise OSError('controlled export failure')
        return original(self,*args,**kwargs)
    monkeypatch.setattr(Path,'open',failing)
    with pytest.raises(OSError,match='controlled'):write_model_report(report,tmp_path/'failed')
    assert not (tmp_path/'failed').exists()


def test_csv_retains_error_messages_and_json_cells(tmp_path):
    # Real errors and assignment tuples must survive ordinary CSV parsing.
    report=make_report(failed=True);path=write_model_report(report,tmp_path/'csv')
    with (path/'attempts.csv').open(encoding='utf-8',newline='') as handle:rows=list(csv.DictReader(handle))
    assert all(r['error_message']=='controlled failure' for r in rows)
    assert all(json.loads(r['assignments_json']) for r in rows)


def test_reference_import_checks_experiment_and_envelope():
    from examples.phase_l6_model_report import report_from_reference
    with pytest.raises(ValueError):report_from_reference({'schema_version':'unknown'})
    # Full real stored L5 restoration is also exercised by the exported L6 example.


def test_mixed_population_retains_failures_and_actual_denominators(tmp_path):
    source=linked(0,failing=(1,)).source
    report=build_model_report('mixed',(ModelReportStudy('mixed',source),))
    path=write_model_report(report,tmp_path/'mixed')
    restored=load_model_report_bundle(path)
    assert restored.studies[0].population.counts['attempted_count']==2
    assert restored.studies[0].population.counts['assessed_count']==1
    assert restored.studies[0].population.counts['failed_count']==1
    with (path/'attempts.csv').open(encoding='utf-8',newline='') as handle:rows=list(csv.DictReader(handle))
    assert [r['status'] for r in rows]==['feasible','failed']
    with (path/'statistics.csv').open(encoding='utf-8',newline='') as handle:stats=list(csv.DictReader(handle))
    assert stats[0]['denominator']=='1'
    assert json.loads(stats[0]['fractions_json'])['coverage_fraction']=={'numerator':1,'denominator':2,'value':.5}


def test_supplemental_evidence_owns_input_and_rejects_non_json():
    source=linked(0).source
    evidence={'grid':[16,32]}
    report=build_model_report('owned',(ModelReportStudy('owned',source),),evidence=evidence)
    evidence['grid'][0]=99
    assert report.to_dict()['evidence']['grid']==[16,32]
    with pytest.raises((ValueError,TypeError)):
        build_model_report('invalid',(ModelReportStudy('x',source),),evidence={'value':float('inf')})
