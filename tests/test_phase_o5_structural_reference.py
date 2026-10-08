# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""O5 mechanism isolation, convergence, conservation and retained outcomes."""
from copy import deepcopy
import math
import numpy as np
import pytest
from examples import phase_o5_structural_reference as ref
from ncmemsim.hashing import canonical_hash
from ncmemsim.materials.temperature import GapKind
from ncmemsim.spectral_absorption import SpectralAbsorptionResult

@pytest.fixture(scope='module')
def reference():
    return ref.run_reference()

def test_reference_acceptance(reference):
    ref.validate_reference(reference)
    assert reference['case_counts']=={'attempted':7,'completed':4,'failed':3}
    assert all(f['status']=='failed' and f['message'] for f in reference['failures'])

def test_separate_mechanisms(reference):
    rows={c['mode']:c['structural_context']['resolved']['layers'][0] for c in reference['cases']}
    for kind in (GapKind.GAMMA.value,GapKind.L.value):
        values={m:r['targets'][kind]['resolved_gap_eV'] for m,r in rows.items()}
        assert values['strain']<values['baseline']<values['confinement']
        assert values['composed']==pytest.approx(values['strain']+values['confinement']-values['baseline'],abs=1e-15)

def test_layer_photon_and_power_conservation(reference):
    for case in reference['cases']:
        for layer in case['optical_layers']:
            restored=SpectralAbsorptionResult.from_dict(layer['absorption'])
            assert restored.to_dict()==layer['absorption']
        for row in case['spectral_audit']:
            s=row['summary']
            for suffix in ('irradiance_W_m2','photon_flux_m2_s'):
                assert s['incident_'+suffix]==pytest.approx(s['absorbed_'+suffix]+s['transmitted_'+suffix],rel=1e-12)
            assert s['passive_absorbed_irradiance_W_m2']==0

def test_threshold_nodes_and_normalization(reference):
    for case in reference['cases']:
        light=ref.TabulatedSpectrum.from_dict(case['source'])
        assert set(reference['threshold_union_nm'])<=set(light.wavelength_nm)
        assert light.in_band_irradiance_W_m2==pytest.approx(ref.POWER_W_M2,rel=1e-14)

def test_geometry_control_includes_electrical_changes(reference):
    small,large=[c for c in reference['controls'] if c['kind']=='diameter']
    assert small['physical_nc_density_m3']/large['physical_nc_density_m3']==pytest.approx(8)
    assert small['charging_energy_J']/large['charging_energy_J']==pytest.approx(2)
    for kind in (GapKind.GAMMA.value,GapKind.L.value):
        a=ref.StructuralOpticalContext.from_dict(small['structural_context']).projection['layers'][0]['targets'][kind]
        b=ref.StructuralOpticalContext.from_dict(large['structural_context']).projection['layers'][0]['targets'][kind]
        assert a['kinetic_confinement_gap_shift_eV']/b['kinetic_confinement_gap_shift_eV']==pytest.approx(4)

def test_multi_fg_and_temperature_controls(reference):
    for c in reference['controls']:
        if c['kind']=='multiple_fg':
            p=np.asarray(c['pulse']['probabilities'])
            assert p.shape==(c['n_fgs'],3,3)
            assert np.max(abs(p.sum(axis=2)-1))<1e-12
            assert len(c['pulse']['absorbed_photon_flux_by_fg_m2_s'])==c['n_fgs']
    a,b=[c for c in reference['controls'] if c['kind']=='temperature']
    assert a['source']==b['source']
    assert a['optical_summary']['fg_absorbed_photon_flux_m2_s']!=b['optical_summary']['fg_absorbed_photon_flux_m2_s']

@pytest.mark.parametrize('target',['counts','criteria','failure','source','controls'])
def test_rehashed_inconsistent_reference_rejected(reference,target):
    raw=deepcopy(reference)
    if target=='counts':raw['case_counts']['completed']=3
    elif target=='criteria':raw['acceptance']['spectral_rtol']=1
    elif target=='failure':raw['failures'].pop()
    elif target=='source':raw['cases'][0]['structural_context_hash']='0'*64
    else:raw['controls']=[]
    raw['reference_hash']=canonical_hash({k:v for k,v in raw.items() if k!='reference_hash'})
    with pytest.raises(ValueError):ref.validate_reference(raw)
