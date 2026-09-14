from __future__ import annotations

import numpy as np
import pytest

from ncmemsim.experimental import (
    ExperimentalDatasetMetadata,
    OpticalAbsorptionDataset,
)


def _metadata() -> ExperimentalDatasetMetadata:
    return ExperimentalDatasetMetadata(
        dataset_id="tran2016-ge005-example",
        source="Tran et al. near-edge optical dataset",
        doi="10.1063/1.4943652",
        sample_id="GeSn-x005",
        temperature_description="room temperature",
    )


def _dataset(
    *,
    uncertainty: bool = False,
) -> OpticalAbsorptionDataset:
    kwargs = {}

    if uncertainty:
        kwargs["absorption_uncertainty_m_inv"] = np.array(
            [2.0e4, 2.5e4, 3.0e4],
        )

    return OpticalAbsorptionDataset(
        wavelength_nm=np.array([1500.0, 1750.0, 2000.0]),
        absorption_coefficient_m_inv=np.array(
            [8.0e5, 6.0e5, 4.0e5],
        ),
        sn_fraction=0.05,
        metadata=_metadata(),
        **kwargs,
    )


def test_metadata_preserves_room_temperature_description_without_inventing_value():
    metadata = _metadata()

    assert metadata.temperature_K is None
    assert metadata.temperature_description == "room temperature"


def test_metadata_accepts_explicit_numeric_temperature():
    metadata = ExperimentalDatasetMetadata(
        dataset_id="measured-300k",
        source="laboratory measurement",
        temperature_K=300.0,
    )

    assert metadata.temperature_K == pytest.approx(300.0)


@pytest.mark.parametrize(
    "temperature_K",
    [0.0, -1.0, float("nan"), float("inf")],
)
def test_metadata_rejects_invalid_numeric_temperature(
    temperature_K: float,
):
    with pytest.raises(ValueError):
        ExperimentalDatasetMetadata(
            dataset_id="invalid-temperature",
            source="test",
            temperature_K=temperature_K,
        )


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("dataset_id", ""),
        ("dataset_id", "   "),
        ("source", ""),
        ("source", "   "),
    ],
)
def test_metadata_requires_nonempty_identity_fields(
    field_name: str,
    value: str,
):
    kwargs = {
        "dataset_id": "dataset-1",
        "source": "test source",
    }
    kwargs[field_name] = value

    with pytest.raises(ValueError):
        ExperimentalDatasetMetadata(**kwargs)


def test_dataset_normalizes_to_read_only_float_arrays():
    wavelength_nm = np.array([1500, 1750, 2000], dtype=int)
    alpha = np.array([8, 6, 4], dtype=int) * 1.0e5

    dataset = OpticalAbsorptionDataset(
        wavelength_nm=wavelength_nm,
        absorption_coefficient_m_inv=alpha,
        sn_fraction=0.05,
        metadata=_metadata(),
    )

    assert dataset.wavelength_nm.dtype.kind == "f"
    assert dataset.absorption_coefficient_m_inv.dtype.kind == "f"
    assert not dataset.wavelength_nm.flags.writeable
    assert not dataset.absorption_coefficient_m_inv.flags.writeable

    wavelength_nm[0] = 999
    alpha[0] = 999.0

    assert dataset.wavelength_nm[0] == pytest.approx(1500.0)
    assert dataset.absorption_coefficient_m_inv[0] == pytest.approx(
        8.0e5
    )

    with pytest.raises(ValueError):
        dataset.wavelength_nm[0] = 1600.0


def test_dataset_reports_size_and_uncertainty_presence():
    without_uncertainty = _dataset()
    with_uncertainty = _dataset(uncertainty=True)

    assert without_uncertainty.n_points == 3
    assert without_uncertainty.has_uncertainty is False

    assert with_uncertainty.n_points == 3
    assert with_uncertainty.has_uncertainty is True
    assert not with_uncertainty.absorption_uncertainty_m_inv.flags.writeable


def test_dataset_to_dict_has_explicit_normalized_schema():
    dataset = _dataset(uncertainty=True)

    data = dataset.to_dict()

    assert data["schema_version"] == 1
    assert data["dataset_type"] == "optical_absorption"
    assert data["sn_fraction"] == pytest.approx(0.05)
    assert data["wavelength_nm"] == [1500.0, 1750.0, 2000.0]
    assert data["absorption_coefficient_m_inv"] == [
        8.0e5,
        6.0e5,
        4.0e5,
    ]
    assert data["absorption_uncertainty_m_inv"] == [
        2.0e4,
        2.5e4,
        3.0e4,
    ]
    assert data["metadata"]["dataset_id"] == "tran2016-ge005-example"
    assert data["metadata"]["temperature_K"] is None
    assert (
        data["metadata"]["temperature_description"]
        == "room temperature"
    )


def test_dataset_hash_is_deterministic_for_same_normalized_data():
    dataset_a = _dataset(uncertainty=True)
    dataset_b = _dataset(uncertainty=True)

    assert dataset_a.dataset_hash() == dataset_b.dataset_hash()
    assert len(dataset_a.dataset_hash()) == 64


def test_dataset_hash_changes_when_data_change():
    dataset_a = _dataset()
    dataset_b = OpticalAbsorptionDataset(
        wavelength_nm=np.array([1500.0, 1750.0, 2000.0]),
        absorption_coefficient_m_inv=np.array(
            [8.0e5, 6.0e5, 4.1e5],
        ),
        sn_fraction=0.05,
        metadata=_metadata(),
    )

    assert dataset_a.dataset_hash() != dataset_b.dataset_hash()


@pytest.mark.parametrize(
    "sn_fraction",
    [-0.01, 1.01, float("nan"), float("inf")],
)
def test_dataset_rejects_invalid_sn_fraction(sn_fraction: float):
    with pytest.raises(ValueError):
        OpticalAbsorptionDataset(
            wavelength_nm=np.array([1500.0, 1600.0]),
            absorption_coefficient_m_inv=np.array([1.0e5, 2.0e5]),
            sn_fraction=sn_fraction,
            metadata=_metadata(),
        )


def test_dataset_requires_at_least_two_points():
    with pytest.raises(ValueError):
        OpticalAbsorptionDataset(
            wavelength_nm=np.array([1500.0]),
            absorption_coefficient_m_inv=np.array([1.0e5]),
            sn_fraction=0.05,
            metadata=_metadata(),
        )


def test_dataset_rejects_non_1d_arrays():
    with pytest.raises(ValueError):
        OpticalAbsorptionDataset(
            wavelength_nm=np.array([[1500.0, 1600.0]]),
            absorption_coefficient_m_inv=np.array([1.0e5, 2.0e5]),
            sn_fraction=0.05,
            metadata=_metadata(),
        )


def test_dataset_rejects_mismatched_primary_array_shapes():
    with pytest.raises(ValueError):
        OpticalAbsorptionDataset(
            wavelength_nm=np.array([1500.0, 1600.0]),
            absorption_coefficient_m_inv=np.array(
                [1.0e5, 2.0e5, 3.0e5],
            ),
            sn_fraction=0.05,
            metadata=_metadata(),
        )


@pytest.mark.parametrize(
    "wavelength_nm",
    [
        np.array([0.0, 1600.0]),
        np.array([-1500.0, 1600.0]),
        np.array([1500.0, float("nan")]),
        np.array([1500.0, float("inf")]),
    ],
)
def test_dataset_rejects_invalid_wavelengths(
    wavelength_nm: np.ndarray,
):
    with pytest.raises(ValueError):
        OpticalAbsorptionDataset(
            wavelength_nm=wavelength_nm,
            absorption_coefficient_m_inv=np.array([1.0e5, 2.0e5]),
            sn_fraction=0.05,
            metadata=_metadata(),
        )


@pytest.mark.parametrize(
    "alpha",
    [
        np.array([-1.0, 2.0e5]),
        np.array([1.0e5, float("nan")]),
        np.array([1.0e5, float("inf")]),
    ],
)
def test_dataset_rejects_invalid_absorption_coefficients(
    alpha: np.ndarray,
):
    with pytest.raises(ValueError):
        OpticalAbsorptionDataset(
            wavelength_nm=np.array([1500.0, 1600.0]),
            absorption_coefficient_m_inv=alpha,
            sn_fraction=0.05,
            metadata=_metadata(),
        )


@pytest.mark.parametrize(
    "uncertainty",
    [
        np.array([1.0e4]),
        np.array([0.0, 1.0e4]),
        np.array([-1.0, 1.0e4]),
        np.array([1.0e4, float("nan")]),
        np.array([1.0e4, float("inf")]),
    ],
)
def test_dataset_rejects_invalid_absorption_uncertainties(
    uncertainty: np.ndarray,
):
    with pytest.raises(ValueError):
        OpticalAbsorptionDataset(
            wavelength_nm=np.array([1500.0, 1600.0]),
            absorption_coefficient_m_inv=np.array([1.0e5, 2.0e5]),
            absorption_uncertainty_m_inv=uncertainty,
            sn_fraction=0.05,
            metadata=_metadata(),
        )


def test_dataset_requires_metadata_instance():
    with pytest.raises(TypeError):
        OpticalAbsorptionDataset(
            wavelength_nm=np.array([1500.0, 1600.0]),
            absorption_coefficient_m_inv=np.array([1.0e5, 2.0e5]),
            sn_fraction=0.05,
            metadata={},  # type: ignore[arg-type]
        )
