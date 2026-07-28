import json
import pytest
from ncmemsim import DeviceBuilder, make_ge, make_gesn
from ncmemsim.materials import (
    BarrierModel, CompactOpticalMaterialModel, HFO2,
    MaterialProperty, ParameterStatus, registry,
)
from ncmemsim.reproducibility import build_reproducibility_manifest

@pytest.mark.parametrize("x",[0.0,0.02,0.05,0.10,0.15,0.20])
def test_gesn_model_compositions(x):
    material=make_gesn(x)
    assert material.sn_fraction == pytest.approx(x)
    assert material.eps_r_nc > 0
    assert material.effective_mass_m0 > 0
    assert material.model_name == "GeSnModel"
    assert material.properties["bandgap_eV"].provenance.status is ParameterStatus.ASSUMED

def test_ge_limit_matches_ge_factory():
    ge=make_ge()
    gesn0=make_gesn(0.0)
    assert gesn0.eps_r_nc == pytest.approx(ge.eps_r_nc)
    assert gesn0.bandgap_eV == pytest.approx(ge.bandgap_eV)
    assert gesn0.effective_mass_m0 == pytest.approx(ge.effective_mass_m0)

def test_registry_has_core_materials():
    assert {"ge","gesn","hfo2","sio2","si"}.issubset(registry.available())
    assert registry.create("gesn",sn_fraction=0.10).sn_fraction == pytest.approx(0.10)

def test_affinity_rule_and_calibrated_barrier():
    result=BarrierModel.affinity_rule(make_gesn(0.10),HFO2)
    assert result.conduction_barrier_eV >= 0
    calibrated=BarrierModel.calibrated(1.78)
    assert calibrated.conduction_barrier_eV == pytest.approx(1.78)

def test_compact_optical_threshold():
    model=CompactOpticalMaterialModel()
    m=make_gesn(0.10)
    point=model.evaluate(m,1064.0)
    assert point.photon_energy_eV > 0
    assert point.absorption_coefficient_m_inv >= 0

def test_reproducibility_manifest_is_json_serializable():
    device=DeviceBuilder.v1(n_fgs=1,nc_material=make_gesn(0.10))
    manifest=build_reproducibility_manifest(device)
    encoded=json.dumps(manifest)
    assert "GeSnModel" in encoded
    assert "provenance" in encoded

def test_invalid_material_composition():
    with pytest.raises(ValueError): make_gesn(-0.01)
