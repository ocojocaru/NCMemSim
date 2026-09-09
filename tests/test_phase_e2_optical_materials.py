import math

import pytest

from ncmemsim import make_ge, make_gesn
from ncmemsim.materials.optics.models import (
    CompactOpticalMaterialModel,
    GeSnOpticalParameterSet,
    direct_gap_gesn_eV,
    photon_energy_eV,
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


def test_direct_gap_property_has_provenance():
    material = make_gesn(0.10)
    model = CompactOpticalMaterialModel()

    prop = model.direct_gap_property(material)

    assert prop.unit == "eV"
    assert prop.provenance.parameter_set == "gesn-optical-provisional-v1"