# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
import hashlib
import json
import pytest
from examples.phase_n6_spectral_report import run_reference
from ncmemsim.hashing import canonical_hash
from ncmemsim.spectral_reporting import (SpectralReport,SpectralReportStudy,build_spectral_report,
    write_spectral_report,load_spectral_report_bundle)
from ncmemsim.spectral_sources import _canonical


@pytest.fixture(scope='module')
def report():return run_reference()


def test_complete_sources_states_failures_and_undefined_values(report):
    assert report.summary['counts']=={'attempted':4,'completed':2,'failed':2}
    assert report.summary['pulse_delta_vfb_V']['estimated_count']==1
    pulse=report.studies[1].to_dict()
    assert len(pulse['source']['initial_state']['floating_gates'])==1
    assert pulse['summary']['scalar_effective_alpha_m_inv_by_fg']==[None]
    assert len(pulse['source']['runtime'])==4
    assert SpectralReport.from_json(report.to_json())==report


def test_all_failed_statistics_are_undefined(report):
    r=build_spectral_report('all failed',report.studies[2:],limitations=report.limitations)
    assert r.summary['counts']=={'attempted':2,'completed':0,'failed':2}
    assert r.summary['pulse_delta_vfb_V']['mean'] is None
    assert r.summary['pulse_delta_vfb_V']['estimated_count']==0
    assert SpectralReport.from_dict(r.to_dict())==r


def test_restore_without_optical_solver_or_rng_replay(report,monkeypatch):
    from ncmemsim.simulator import Simulator
    from ncmemsim.materials.optics.models import CompositeGeSnAbsorptionModel
    import numpy as np
    def forbidden(*args,**kwargs):raise AssertionError('no replay')
    monkeypatch.setattr(Simulator,'relax_voltage',forbidden)
    monkeypatch.setattr(CompositeGeSnAbsorptionModel,'evaluate',forbidden)
    monkeypatch.setattr(np.random,'default_rng',forbidden)
    assert SpectralReport.from_json(report.to_json())==report


@pytest.mark.parametrize('fault',['summary','state','read','photo_rate','flux','protocol','nested_projection','extra','failure'])
def test_coherently_rehashed_inconsistent_sources_rejected(report,fault):
    raw=deepcopy(report.to_dict());study=raw['studies'][1];source=study['source']
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
    with pytest.raises(ValueError):SpectralReport.from_dict(raw)


def test_deterministic_six_file_bundle_and_no_overwrite(report,tmp_path):
    a=write_spectral_report(report,tmp_path/'a');b=write_spectral_report(report,tmp_path/'b')
    assert len(list(a.iterdir()))==6
    assert {p.name:p.read_bytes() for p in a.iterdir()}=={p.name:p.read_bytes() for p in b.iterdir()}
    assert load_spectral_report_bundle(a)==report
    with pytest.raises(FileExistsError):write_spectral_report(report,a)


@pytest.mark.parametrize('fault',['csv','markdown','missing','extra','manifest','json_projection'])
def test_bundle_rejects_even_coherently_rehashed_bad_projections(report,tmp_path,fault):
    d=write_spectral_report(report,tmp_path/'bundle')
    manifest=json.loads((d/'bundle.json').read_text(encoding='utf-8'))
    if fault in ('csv','markdown'):
        name='layers.csv' if fault=='csv' else 'report.md'
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
    with pytest.raises(ValueError):load_spectral_report_bundle(d)


def test_labels_limits_and_duplicate_json_keys_rejected(report):
    with pytest.raises(ValueError):build_spectral_report('bad',(report.studies[0],report.studies[0]),limitations=report.limitations)
    with pytest.raises(ValueError):build_spectral_report('bad',report.studies,limitations=())
    with pytest.raises(ValueError):SpectralReport.from_json(report.to_json().replace('{','{"name":"duplicate",',1))


def test_failed_request_preserves_invalid_inputs_without_inventing_success(report):
    source=report.studies[2].to_dict()['source']
    assert source['request']['source']['wavelength_nm']==[1499.]
    assert report.studies[2].summary['status']=='failed'
    assert 'observations' not in source


def test_all_failed_bundle_has_no_invented_layer_or_pulse_statistics(report,tmp_path):
    failed=build_spectral_report('all failed export',report.studies[2:],limitations=report.limitations)
    folder=write_spectral_report(failed,tmp_path/'failed')
    assert load_spectral_report_bundle(folder)==failed
    assert len((folder/'layers.csv').read_text(encoding='utf-8').splitlines())==1
    raw=json.loads((folder/'report.json').read_text(encoding='utf-8'))
    assert raw['summary']['pulse_delta_vfb_V']['mean'] is None


def test_numeric_observation_types_and_unknown_state_fields_rejected(report):
    from ncmemsim.spectral_reporting import SpectralRunEvidence
    raw=deepcopy(report.studies[1].to_dict()['source'])
    raw['observations']['photo_transition_rate_by_fg_s'][0]=True
    with pytest.raises(ValueError):SpectralRunEvidence.from_dict(raw)
    raw=deepcopy(report.studies[1].to_dict()['source'])
    raw['initial_state']['unreviewed']=True
    with pytest.raises(ValueError):SpectralRunEvidence.from_dict(raw)


@pytest.mark.parametrize('n',[2,3])
def test_multifg_pulse_states_charge_and_optical_provenance_restore(n):
    from examples.phase_n5_broadband_reference import build_resolution,make_source,build_context
    from ncmemsim.spectral_context import SpectralPulseProtocol,run_spectral_program_pulse_read
    from ncmemsim.program_protocol import ProgramPulseReadProtocol
    from ncmemsim.photo import PhotoTransitionWeights,PhotoTransitionConfig
    from ncmemsim.spectral_reporting import build_spectral_run_evidence,SpectralRunEvidence
    context=build_context(build_resolution(n),make_source('multispectral'))
    protocol=SpectralPulseProtocol(ProgramPulseReadProtocol(2,1e-7,0,1e-7/16),PhotoTransitionWeights())
    evidence=build_spectral_run_evidence(run_spectral_program_pulse_read(context,protocol,photo_config=PhotoTransitionConfig(.1)))
    restored=SpectralRunEvidence.from_json(evidence.to_json())
    assert len(restored.to_dict()['observations']['programmed_state']['floating_gates'])==n
    assert restored==evidence
