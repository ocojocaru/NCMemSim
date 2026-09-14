from __future__ import annotations

import pytest

from ncmemsim.materials.optics import (
    EvaluationDomainStatus,
    OpticalValidationDomain,
    TRAN_2016_NEAR_EDGE_DOMAIN,
)


def test_evaluation_domain_status_values():
    assert (
        EvaluationDomainStatus.WITHIN_VALIDATION_DOMAIN.value
        == "within_validation_domain"
    )
    assert (
        EvaluationDomainStatus.EXTRAPOLATED.value
        == "extrapolated"
    )


def test_tran_2016_domain_metadata():
    domain = TRAN_2016_NEAR_EDGE_DOMAIN

    assert domain.name == "tran-2016-near-edge"
    assert domain.sn_fraction_min == pytest.approx(0.0)
    assert domain.sn_fraction_max == pytest.approx(0.10)
    assert domain.wavelength_min_nm == pytest.approx(1500.0)
    assert domain.wavelength_max_nm == pytest.approx(2500.0)
    assert domain.temperature_note == "room temperature"
    assert domain.doi == "10.1063/1.4943652"


@pytest.mark.parametrize(
    ("sn_fraction", "wavelength_nm"),
    [
        (0.0, 1500.0),
        (0.0, 2500.0),
        (0.10, 1500.0),
        (0.10, 2500.0),
        (0.05, 2000.0),
    ],
)
def test_tran_domain_boundaries_are_inclusive(
    sn_fraction,
    wavelength_nm,
):
    status = TRAN_2016_NEAR_EDGE_DOMAIN.classify(
        sn_fraction=sn_fraction,
        wavelength_nm=wavelength_nm,
    )

    assert (
        status
        is EvaluationDomainStatus.WITHIN_VALIDATION_DOMAIN
    )


@pytest.mark.parametrize(
    ("sn_fraction", "wavelength_nm"),
    [
        (0.100001, 2000.0),
        (0.15, 2000.0),
        (0.05, 1499.0),
        (0.05, 2501.0),
        (0.15, 1000.0),
    ],
)
def test_valid_inputs_outside_tran_domain_are_extrapolated(
    sn_fraction,
    wavelength_nm,
):
    status = TRAN_2016_NEAR_EDGE_DOMAIN.classify(
        sn_fraction=sn_fraction,
        wavelength_nm=wavelength_nm,
    )

    assert status is EvaluationDomainStatus.EXTRAPOLATED


def test_domain_contains_matches_classification():
    domain = TRAN_2016_NEAR_EDGE_DOMAIN

    assert domain.contains(
        sn_fraction=0.05,
        wavelength_nm=2000.0,
    )

    assert not domain.contains(
        sn_fraction=0.15,
        wavelength_nm=2000.0,
    )


@pytest.mark.parametrize(
    "sn_fraction",
    [
        -0.01,
        1.01,
        float("inf"),
        float("-inf"),
        float("nan"),
    ],
)
def test_invalid_composition_is_rejected(sn_fraction):
    with pytest.raises(ValueError):
        TRAN_2016_NEAR_EDGE_DOMAIN.classify(
            sn_fraction=sn_fraction,
            wavelength_nm=2000.0,
        )


@pytest.mark.parametrize(
    "wavelength_nm",
    [
        0.0,
        -1.0,
        float("inf"),
        float("-inf"),
        float("nan"),
    ],
)
def test_invalid_wavelength_is_rejected(wavelength_nm):
    with pytest.raises(ValueError):
        TRAN_2016_NEAR_EDGE_DOMAIN.classify(
            sn_fraction=0.05,
            wavelength_nm=wavelength_nm,
        )


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "sn_fraction_min": -0.01,
            "sn_fraction_max": 0.10,
            "wavelength_min_nm": 1500.0,
            "wavelength_max_nm": 2500.0,
        },
        {
            "sn_fraction_min": 0.20,
            "sn_fraction_max": 0.10,
            "wavelength_min_nm": 1500.0,
            "wavelength_max_nm": 2500.0,
        },
        {
            "sn_fraction_min": 0.0,
            "sn_fraction_max": 1.01,
            "wavelength_min_nm": 1500.0,
            "wavelength_max_nm": 2500.0,
        },
        {
            "sn_fraction_min": 0.0,
            "sn_fraction_max": 0.10,
            "wavelength_min_nm": 0.0,
            "wavelength_max_nm": 2500.0,
        },
        {
            "sn_fraction_min": 0.0,
            "sn_fraction_max": 0.10,
            "wavelength_min_nm": 2500.0,
            "wavelength_max_nm": 1500.0,
        },
    ],
)
def test_invalid_domain_definition_is_rejected(kwargs):
    with pytest.raises(ValueError):
        OpticalValidationDomain(
            name="invalid",
            temperature_note=None,
            doi=None,
            **kwargs,
        )


def test_domain_serialization():
    assert TRAN_2016_NEAR_EDGE_DOMAIN.to_dict() == {
        "name": "tran-2016-near-edge",
        "sn_fraction_min": 0.0,
        "sn_fraction_max": 0.10,
        "wavelength_min_nm": 1500.0,
        "wavelength_max_nm": 2500.0,
        "temperature_note": "room temperature",
        "doi": "10.1063/1.4943652",
    }
