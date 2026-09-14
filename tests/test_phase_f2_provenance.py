from __future__ import annotations

import pytest

from ncmemsim.materials.provenance import (
    ParameterProvenance,
    ParameterStatus,
)


def test_parameter_status_supports_literature_fitted():
    assert ParameterStatus.LITERATURE_FITTED.value == "literature_fitted"


def test_parameter_status_supports_derived():
    assert ParameterStatus.DERIVED.value == "derived"


def test_existing_provenance_serialization_remains_backward_compatible():
    provenance = ParameterProvenance(
        source="legacy source",
        status=ParameterStatus.LITERATURE,
        doi=None,
        notes=None,
        parameter_set="legacy-v1",
    )

    assert provenance.to_dict() == {
        "source": "legacy source",
        "status": "literature",
        "doi": None,
        "notes": None,
        "parameter_set": "legacy-v1",
    }


def test_reported_uncertainty_is_serialized_when_defined():
    provenance = ParameterProvenance(
        source="Tran et al. 2016",
        status=ParameterStatus.LITERATURE_FITTED,
        doi="10.1063/1.4943652",
        notes="Direct-absorption prefactor.",
        parameter_set="gesn-near-edge-tran2016-v1",
        reported_uncertainty=0.86e6,
        uncertainty_unit="m^-1 eV^(1/2)",
    )

    assert provenance.to_dict() == {
        "source": "Tran et al. 2016",
        "status": "literature_fitted",
        "doi": "10.1063/1.4943652",
        "notes": "Direct-absorption prefactor.",
        "parameter_set": "gesn-near-edge-tran2016-v1",
        "reported_uncertainty": 0.86e6,
        "uncertainty_unit": "m^-1 eV^(1/2)",
    }


def test_uncertainty_fields_are_omitted_when_not_defined():
    provenance = ParameterProvenance(
        source="derived relation",
        status=ParameterStatus.DERIVED,
        parameter_set="derived-v1",
    )

    data = provenance.to_dict()

    assert "reported_uncertainty" not in data
    assert "uncertainty_unit" not in data


@pytest.mark.parametrize(
    "uncertainty",
    [
        -1.0,
        float("inf"),
        float("-inf"),
        float("nan"),
    ],
)
def test_invalid_reported_uncertainty_is_rejected(uncertainty):
    with pytest.raises(ValueError):
        ParameterProvenance(
            source="invalid uncertainty",
            status=ParameterStatus.LITERATURE_FITTED,
            reported_uncertainty=uncertainty,
            uncertainty_unit="eV",
        )


def test_empty_uncertainty_unit_is_rejected():
    with pytest.raises(ValueError):
        ParameterProvenance(
            source="invalid uncertainty unit",
            status=ParameterStatus.LITERATURE_FITTED,
            reported_uncertainty=0.1,
            uncertainty_unit="",
        )


def test_uncertainty_unit_without_uncertainty_is_rejected():
    with pytest.raises(ValueError):
        ParameterProvenance(
            source="orphan uncertainty unit",
            status=ParameterStatus.LITERATURE,
            uncertainty_unit="eV",
        )
