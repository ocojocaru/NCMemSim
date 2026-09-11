import math

import pytest

from ncmemsim import make_ge, make_gesn
from ncmemsim.materials.provenance import ParameterStatus
from ncmemsim.materials.optics.models import (
    CompactOpticalMaterialModel,
    GeSnOpticalParameterSet,
    CompositeGeSnAbsorptionModel,
    GeSnAbsorptionParameterSet,
    direct_gap_gesn_eV,
    indirect_gap_gesn_eV,
    photon_energy_eV,
    direct_absorption_m_inv,
    indirect_absorption_m_inv,
    phonon_occupation,
    urbach_absorption_m_inv,
)


def test_photon_energy_at_1550_nm():
    energy = photon_energy_eV(1550.0)

    assert math.isclose(
        energy,
        0.80,
        rel_tol=1e-2,
    )


def test_ge_direct_gap_endpoint():
    gap = direct_gap_gesn_eV(0.0)

    assert math.isclose(
        gap,
        GeSnOpticalParameterSet().ge_direct_gap_eV,
        rel_tol=0.0,
        abs_tol=1e-15,
    )


def test_direct_gap_decreases_with_sn():
    gap_ge = direct_gap_gesn_eV(0.0)
    gap_gesn = direct_gap_gesn_eV(0.10)

    assert gap_gesn < gap_ge


def test_invalid_sn_fraction_rejected():
    with pytest.raises(ValueError):
        direct_gap_gesn_eV(1.1)


def test_absorption_zero_below_direct_edge():
    material = make_ge()
    model = CompactOpticalMaterialModel()

    point = model.evaluate(
        material,
        wavelength_nm=2000.0,
    )

    assert point.photon_energy_eV < point.direct_gap_eV
    assert point.absorption_coefficient_m_inv == 0.0


def test_absorption_positive_above_direct_edge():
    material = make_ge()
    model = CompactOpticalMaterialModel()

    point = model.evaluate(
        material,
        wavelength_nm=1000.0,
    )

    assert point.photon_energy_eV > point.direct_gap_eV
    assert point.absorption_coefficient_m_inv > 0.0


def test_gesn_extends_compact_absorption_to_longer_wavelength():
    ge = make_ge()
    gesn = make_gesn(0.10)

    model = CompactOpticalMaterialModel()

    ge_point = model.evaluate(ge, 1700.0)
    gesn_point = model.evaluate(gesn, 1700.0)

    assert gesn_point.direct_gap_eV < ge_point.direct_gap_eV
    assert (
        gesn_point.absorption_coefficient_m_inv
        >= ge_point.absorption_coefficient_m_inv
    )


def test_direct_gap_property_has_literature_provenance():
    material = make_gesn(0.10)
    model = CompactOpticalMaterialModel()

    prop = model.direct_gap_property(material)

    assert prop.unit == "eV"
    assert prop.provenance.status == ParameterStatus.LITERATURE
    assert prop.provenance.doi == "10.1039/D2NR07107J"
    assert prop.provenance.parameter_set == "gesn-optical-300K-v1"
    
def test_direct_gap_10pct_sn_literature_parameterization():
    gap = direct_gap_gesn_eV(0.10)

    expected = (
        0.90 * 0.7985
        + 0.10 * (-0.413)
        - 2.89 * 0.10 * 0.90
    )

    assert math.isclose(
        gap,
        expected,
        rel_tol=0.0,
        abs_tol=1e-12,
    )

def test_ge_indirect_gap_endpoint():
    gap = indirect_gap_gesn_eV(0.0)

    assert math.isclose(
        gap,
        GeSnOpticalParameterSet().ge_indirect_gap_eV,
        rel_tol=0.0,
        abs_tol=1e-15,
    )


def test_alpha_sn_indirect_gap_endpoint():
    gap = indirect_gap_gesn_eV(1.0)

    assert math.isclose(
        gap,
        GeSnOpticalParameterSet().alpha_sn_indirect_gap_eV,
        rel_tol=0.0,
        abs_tol=1e-15,
    )


def test_indirect_gap_10pct_sn():
    gap = indirect_gap_gesn_eV(0.10)

    expected = (
        0.90 * 0.664
        + 0.10 * 0.092
        - 0.89 * 0.10 * 0.90
    )

    assert math.isclose(
        gap,
        expected,
        rel_tol=0.0,
        abs_tol=1e-12,
    )


def test_indirect_gap_property_has_literature_provenance():
    material = make_gesn(0.10)
    model = CompactOpticalMaterialModel()

    prop = model.indirect_gap_property(material)

    assert prop.unit == "eV"
    assert prop.symbol == "E_g^L"
    assert prop.provenance.status == ParameterStatus.LITERATURE
    assert prop.provenance.parameter_set == "gesn-optical-300K-v1"


def test_direct_gap_crosses_indirect_gap_with_sn():
    gap_gamma_ge = direct_gap_gesn_eV(0.0)
    gap_l_ge = indirect_gap_gesn_eV(0.0)

    gap_gamma_10 = direct_gap_gesn_eV(0.10)
    gap_l_10 = indirect_gap_gesn_eV(0.10)

    assert gap_gamma_ge > gap_l_ge
    assert gap_gamma_10 < gap_l_10
    
def test_direct_absorption_zero_below_gamma():
    ps = GeSnAbsorptionParameterSet()

    alpha = direct_absorption_m_inv(
        photon_energy_eV=0.7,
        direct_gap_eV=0.8,
        parameters=ps,
    )

    assert alpha == 0.0


def test_direct_absorption_positive_above_gamma():
    ps = GeSnAbsorptionParameterSet()

    alpha = direct_absorption_m_inv(
        photon_energy_eV=1.0,
        direct_gap_eV=0.8,
        parameters=ps,
    )

    assert alpha > 0.0


def test_indirect_absorption_zero_far_below_l_edge():
    ps = GeSnAbsorptionParameterSet()

    alpha = indirect_absorption_m_inv(
        photon_energy_eV=0.5,
        indirect_gap_eV=0.7,
        parameters=ps,
    )

    assert alpha == 0.0


def test_indirect_absorption_positive_above_l_edge():
    ps = GeSnAbsorptionParameterSet()

    alpha = indirect_absorption_m_inv(
        photon_energy_eV=0.8,
        indirect_gap_eV=0.7,
        parameters=ps,
    )

    assert alpha > 0.0


def test_urbach_positive_below_gamma_edge():
    ps = GeSnAbsorptionParameterSet()

    alpha = urbach_absorption_m_inv(
        photon_energy_eV=0.79,
        direct_gap_eV=0.8,
        parameters=ps,
    )

    assert alpha > 0.0


def test_urbach_zero_above_gamma_edge():
    ps = GeSnAbsorptionParameterSet()

    alpha = urbach_absorption_m_inv(
        photon_energy_eV=0.81,
        direct_gap_eV=0.8,
        parameters=ps,
    )

    assert alpha == 0.0


def test_composite_absorption_is_sum_of_components():
    material = make_gesn(0.08)
    model = CompositeGeSnAbsorptionModel()

    point = model.evaluate(material, 2000.0)

    expected = (
        point.alpha_direct_m_inv
        + point.alpha_indirect_m_inv
        + point.alpha_urbach_m_inv
    )

    assert math.isclose(
        point.absorption_coefficient_m_inv,
        expected,
        rel_tol=1e-14,
    )


def test_composite_model_reports_both_band_edges():
    material = make_gesn(0.08)
    model = CompositeGeSnAbsorptionModel()

    point = model.evaluate(material, 2000.0)

    assert point.direct_gap_eV is not None
    assert point.indirect_gap_eV is not None
    
def test_optics_public_api_exports_composite_model():
    from ncmemsim.materials.optics import (
        CompositeGeSnAbsorptionModel,
        GeSnAbsorptionParameterSet,
        GeSnOpticalParameterSet,
    )

    assert CompositeGeSnAbsorptionModel is not None
    assert GeSnAbsorptionParameterSet is not None
    assert GeSnOpticalParameterSet is not None
    
def test_composite_absorption_reports_provenance():
    material = make_gesn(0.08)
    model = CompositeGeSnAbsorptionModel()

    point = model.evaluate(material, 2000.0)

    assert point.provenance is not None
    assert point.provenance["model_form"].status == ParameterStatus.LITERATURE
    assert point.provenance["coefficients"].status == ParameterStatus.ASSUMED
    
def test_phonon_occupation_at_300k():
    n = phonon_occupation(0.027, 300.0)

    assert n == pytest.approx(0.543, rel=0.02)


def test_phonon_occupation_increases_with_temperature():
    low = phonon_occupation(0.027, 100.0)
    high = phonon_occupation(0.027, 300.0)

    assert high > low


def test_phonon_occupation_approaches_zero_at_low_temperature():
    n = phonon_occupation(0.027, 10.0)

    assert n < 1.0e-10


def test_invalid_phonon_temperature_rejected():
    with pytest.raises(ValueError):
        phonon_occupation(0.027, 0.0)


def test_invalid_phonon_energy_rejected():
    with pytest.raises(ValueError):
        phonon_occupation(0.0, 300.0)


def test_indirect_absorption_is_temperature_dependent():
    cold = GeSnAbsorptionParameterSet(temperature_K=100.0)
    warm = GeSnAbsorptionParameterSet(temperature_K=300.0)

    alpha_cold = indirect_absorption_m_inv(
        photon_energy_eV=0.60,
        indirect_gap_eV=0.55,
        parameters=cold,
    )

    alpha_warm = indirect_absorption_m_inv(
        photon_energy_eV=0.60,
        indirect_gap_eV=0.55,
        parameters=warm,
    )

    assert alpha_warm > alpha_cold