# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
import hashlib
import json
import pytest
from examples.phase_o6_structural_report import run_reference
from ncmemsim.hashing import canonical_hash
from ncmemsim.structural_reporting import (StructuralReport,StructuralReportStudy,build_structural_report,
    write_structural_report,load_structural_report_bundle)
from ncmemsim.spectral_sources import _canonical


@pytest.fixture(scope='module')
def report():return run_reference()


def test_complete_sources_states_failures_and_undefined_values(report):
    assert report.summary['counts']=={'attempted':4,'completed':2,'failed':2}
    assert report.summary['pulse_delta_vfb_V']['estimated_count']==1
    pulse=report.studies[1].to_dict()
    assert len(pulse['source']['spectral_run']['initial_state']['floating_gates'])==1
    assert pulse['summary']['scalar_effective_alpha_m_inv_by_fg']==[None]
    assert len(pulse['source']['spectral_run']['runtime'])==4
    assert StructuralReport.from_json(report.to_json())==report


def test_all_failed_statistics_are_undefined(report):
    r=build_structural_report('all failed',report.studies[2:],limitations=report.limitations)
    assert r.summary['counts']=={'attempted':2,'completed':0,'failed':2}
    assert r.summary['pulse_delta_vfb_V']['mean'] is None
    assert r.summary['pulse_delta_vfb_V']['estimated_count']==0
    assert StructuralReport.from_dict(r.to_dict())==r


def test_restore_without_optical_solver_or_rng_replay(report,monkeypatch):
    from ncmemsim.simulator import Simulator
    from ncmemsim.materials.optics.models import CompositeGeSnAbsorptionModel
    import numpy as np
    def forbidden(*args,**kwargs):raise AssertionError('no replay')
    monkeypatch.setattr(Simulator,'relax_voltage',forbidden)
    monkeypatch.setattr(CompositeGeSnAbsorptionModel,'evaluate',forbidden)
    from ncmemsim.structural_optical_context import _StructuralOpticalModel
    monkeypatch.setattr(_StructuralOpticalModel,'evaluate',forbidden)
    monkeypatch.setattr(np.random,'default_rng',forbidden)
    assert StructuralReport.from_json(report.to_json())==report


@pytest.mark.parametrize('fault',['summary','state','read','photo_rate','flux','protocol','nested_projection','extra','failure'])
def test_coherently_rehashed_inconsistent_sources_rejected(report,fault):
    raw=deepcopy(report.to_dict());study=raw['studies'][1];source=study['source']['spectral_run']
    if fault=='summary':raw['summary']['counts']['completed']=3
    elif fault=='state':source['observations']['programmed_state']['floating_gates'][0]['P0'][0]=.5
    elif fault=='read':source['observations']['read_state']['time_s']+=1
    elif fault=='photo_rate':source['observations']['photo_transition_rate_by_fg_s'][0]*=2
    elif fault=='flux':source['observations']['absorbed_photon_flux_by_fg_m2_s'][0]*=2
    elif fault=='protocol':source['protocol']['read_semantics']='illuminated'
    elif fault=='nested_projection':source['context']['optical_result']['projection']['summary']['absorbed_irradiance_W_m2']+=1
    elif fault=='extra':source['unreviewed']=True
    else:raw['studies'][2]['source']['request']=[]
    for s in raw['studies']:s['source_hash']=canonical_hash(s['source'])
    payload={k:v for k,v in raw.items() if k!='report_hash'};raw['report_hash']=canonical_hash(payload)
    with pytest.raises(ValueError):StructuralReport.from_dict(raw)


def test_deterministic_seven_file_bundle_and_no_overwrite(report,tmp_path):
    a=write_structural_report(report,tmp_path/'a');b=write_structural_report(report,tmp_path/'b')
    assert len(list(a.iterdir()))==7
    assert {p.name:p.read_bytes() for p in a.iterdir()}=={p.name:p.read_bytes() for p in b.iterdir()}
    assert load_structural_report_bundle(a)==report
    with pytest.raises(FileExistsError):write_structural_report(report,a)


@pytest.mark.parametrize('fault',['csv','structural_csv','markdown','missing','extra','manifest','json_projection'])
def test_bundle_rejects_even_coherently_rehashed_bad_projections(report,tmp_path,fault):
    d=write_structural_report(report,tmp_path/'bundle')
    manifest=json.loads((d/'bundle.json').read_text(encoding='utf-8'))
    if fault in ('csv','structural_csv','markdown'):
        name={'csv':'layers.csv','structural_csv':'structural.csv','markdown':'report.md'}[fault]
        (d/name).write_bytes((d/name).read_bytes()+b'forged\n')
        manifest['files'][name]=hashlib.sha256((d/name).read_bytes()).hexdigest()
    elif fault=='missing':(d/'sources.csv').unlink()
    elif fault=='extra':(d/'extra.txt').write_text('extra')
    elif fault=='manifest':manifest['report_hash']='0'*64
    else:
        raw=json.loads((d/'report.json').read_text(encoding='utf-8'));raw['studies'][0]['summary']['status']='failed'
        raw['report_hash']=canonical_hash({k:v for k,v in raw.items() if k!='report_hash'})
        (d/'report.json').write_text(json.dumps(raw),encoding='utf-8')
        manifest['report_hash']=raw['report_hash'];manifest['files']['report.json']=hashlib.sha256((d/'report.json').read_bytes()).hexdigest()
    (d/'bundle.json').write_text(json.dumps(manifest),encoding='utf-8')
    with pytest.raises(ValueError):load_structural_report_bundle(d)


def test_labels_limits_and_duplicate_json_keys_rejected(report):
    with pytest.raises(ValueError):build_structural_report('bad',(report.studies[0],report.studies[0]),limitations=report.limitations)
    with pytest.raises(ValueError):build_structural_report('bad',report.studies,limitations=())
    with pytest.raises(ValueError):StructuralReport.from_json(report.to_json().replace('{','{"name":"duplicate",',1))


def test_failed_request_preserves_invalid_inputs_without_inventing_success(report):
    source=report.studies[2].to_dict()['source']
    assert source['request']['requested_override']=={'trace':.02}
    assert len(source['request']['baseline_context']['bindings'][0]['strain_profiles'])==2
    assert report.studies[2].summary['status']=='failed'
    assert 'observations' not in source


def test_all_failed_bundle_has_no_invented_layer_or_pulse_statistics(report,tmp_path):
    failed=build_structural_report('all failed export',report.studies[2:],limitations=report.limitations)
    folder=write_structural_report(failed,tmp_path/'failed')
    assert load_structural_report_bundle(folder)==failed
    assert len((folder/'layers.csv').read_text(encoding='utf-8').splitlines())==1
    raw=json.loads((folder/'report.json').read_text(encoding='utf-8'))
    assert raw['summary']['pulse_delta_vfb_V']['mean'] is None


def test_numeric_observation_types_and_unknown_state_fields_rejected(report):
    from ncmemsim.structural_reporting import StructuralRunEvidence
    raw=deepcopy(report.studies[1].to_dict()['source'])
    raw['spectral_run']['observations']['photo_transition_rate_by_fg_s'][0]=True
    with pytest.raises(ValueError):StructuralRunEvidence.from_dict(raw)
    raw=deepcopy(report.studies[1].to_dict()['source'])
    raw['spectral_run']['initial_state']['unreviewed']=True
    with pytest.raises(ValueError):StructuralRunEvidence.from_dict(raw)


@pytest.mark.parametrize('n',[2,3])
def test_multifg_pulse_states_charge_and_optical_provenance_restore(n):
    from examples.phase_o5_structural_reference import structural_context,source,spectral
    from ncmemsim.structural_optical_context import run_structural_spectral_program_pulse_read
    from ncmemsim.spectral_context import SpectralPulseProtocol
    from ncmemsim.program_protocol import ProgramPulseReadProtocol
    from ncmemsim.photo import PhotoTransitionWeights,PhotoTransitionConfig
    from ncmemsim.structural_reporting import build_structural_run_evidence,StructuralRunEvidence
    context=spectral(structural_context('composed',n),source(3,()))
    protocol=SpectralPulseProtocol(ProgramPulseReadProtocol(2,1e-7,0,1e-7/8),PhotoTransitionWeights())
    evidence=build_structural_run_evidence(run_structural_spectral_program_pulse_read(context,protocol,photo_config=PhotoTransitionConfig(.1)))
    restored=StructuralRunEvidence.from_json(evidence.to_json())
    assert len(restored.to_dict()['spectral_run']['observations']['programmed_state']['floating_gates'])==n
    assert restored==evidence


def test_structural_inputs_and_separate_contributions_retained(report):
    raw=report.to_dict()['studies'][1]['source']
    owner=raw['context']['structural_context']
    assert len(owner['bindings'][0]['strain_profiles'])==2
    assert len(owner['bindings'][0]['confinement_profiles'])==2
    rows=report.studies[1].summary['structural_projection']['layers']
    for value in rows[0]['targets'].values():
        assert value['strain_gap_shift_eV']<0
        assert value['kinetic_confinement_gap_shift_eV']>0
        assert value['resolved_gap_eV']==pytest.approx(value['thermal_baseline_gap_eV']+value['strain_gap_shift_eV']+value['kinetic_confinement_gap_shift_eV'])


@pytest.mark.parametrize('fault',['radius','trace','composition','owner_swap','schema','duplicate'])
def test_structural_source_tampering_rejected(report,fault):
    raw=deepcopy(report.to_dict());study=raw['studies'][1];context=study['source']['context']
    owner=context['structural_context']
    if fault=='radius':owner['resolved']['layers'][0]['radius_m_from_device']*=2
    elif fault=='trace':owner['bindings'][0]['trace_strain']*=2
    elif fault=='composition':owner['resolved']['layers'][0]['targets']['optical_gamma_gap']['resolved_gap_eV']+=.01
    elif fault=='owner_swap':study['source']['spectral_run']['context']=report.studies[0].to_dict()['source']['spectral_context'];context['structural_context']['bindings']=[]
    elif fault=='schema':study['source']['schema_version']='structural-run-evidence-v2'
    else:raw['studies'].append(raw['studies'][0])
    for s in raw['studies']:s['source_hash']=canonical_hash(s['source'])
    raw['report_hash']=canonical_hash({k:v for k,v in raw.items() if k!='report_hash'})
    with pytest.raises(ValueError):StructuralReport.from_dict(raw)


def test_json_duplicate_keys_and_nonfinite_rejected(report):
    with pytest.raises(ValueError):StructuralReport.from_json('{"name":"a","name":"b"}')
    with pytest.raises(ValueError):StructuralReport.from_json(report.to_json().replace('0.005','NaN',1))


def test_disabled_source_retains_zero_optical_budgets():
    from dataclasses import replace
    from examples.phase_o5_structural_reference import structural_context,source,spectral
    context=spectral(structural_context('composed'),replace(source(3,()),enabled=False))
    study=StructuralReportStudy('disabled source','optical',context.to_json())
    restored=StructuralReportStudy.from_json(study.to_json())
    assert restored.summary['optical_summary']['incident_irradiance_W_m2']==0
    layers=context.spectral_context.optical_result.projection['layers']
    assert all(x['absorption']['summary']['absorbed_irradiance_W_m2']==0 for x in layers)
    assert restored.summary['optical_summary']['fg_absorbed_photon_flux_m2_s']==0


def test_freezer_rejects_workflow_identities_and_missing_initial_state():
    from examples.phase_o5_structural_reference import structural_context,source,spectral
    from ncmemsim.structural_optical_context import run_structural_spectral_program_pulse_read
    from ncmemsim.spectral_context import SpectralPulseProtocol
    from ncmemsim.program_protocol import ProgramPulseReadProtocol
    from ncmemsim.photo import PhotoTransitionWeights,PhotoTransitionConfig
    from ncmemsim.structural_reporting import build_structural_run_evidence
    context=spectral(structural_context('composed'),source(3,()))
    protocol=SpectralPulseProtocol(ProgramPulseReadProtocol(2,1e-8,0,1e-8),PhotoTransitionWeights())
    workflow=run_structural_spectral_program_pulse_read(context,protocol,photo_config=PhotoTransitionConfig(.1))
    for fault in ('context','structural','nested','initial','extra'):
        raw=deepcopy(workflow)
        if fault=='context':raw['context_hash']='0'*64
        elif fault=='structural':raw['structural_context_hash']='0'*64
        elif fault=='nested':raw['spectral_run']['context_hash']='0'*64
        elif fault=='initial':del raw['spectral_run']['initial_state']
        else:raw['extra']=True
        with pytest.raises(ValueError):build_structural_run_evidence(raw)
