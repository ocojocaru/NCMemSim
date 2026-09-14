from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from ncmemsim.experimental import (
    ExperimentalDatasetMetadata,
    OpticalAbsorptionDataset,
)
from ncmemsim.io import load_optical_absorption_csv


def _metadata() -> ExperimentalDatasetMetadata:
    return ExperimentalDatasetMetadata(
        dataset_id="optical-csv-test",
        source="synthetic optical absorption test dataset",
        sample_id="sample-a",
        temperature_description="room temperature",
    )


def _write_csv(
    path: Path,
    text: str,
    *,
    encoding: str = "utf-8",
) -> Path:
    path.write_text(text, encoding=encoding)
    return path


def test_load_two_column_optical_absorption_csv(tmp_path: Path):
    path = _write_csv(
        tmp_path / "optical.csv",
        (
            "wavelength_nm,absorption_coefficient_m_inv\n"
            "1500,800000\n"
            "1750,600000\n"
            "2000,400000\n"
        ),
    )

    dataset = load_optical_absorption_csv(
        path,
        sn_fraction=0.05,
        metadata=_metadata(),
    )

    assert isinstance(dataset, OpticalAbsorptionDataset)
    assert dataset.n_points == 3
    assert dataset.sn_fraction == pytest.approx(0.05)
    assert dataset.has_uncertainty is False
    assert dataset.wavelength_nm.tolist() == [
        1500.0,
        1750.0,
        2000.0,
    ]
    assert dataset.absorption_coefficient_m_inv.tolist() == [
        8.0e5,
        6.0e5,
        4.0e5,
    ]


def test_load_three_column_csv_preserves_uncertainty(tmp_path: Path):
    path = _write_csv(
        tmp_path / "optical_uncertainty.csv",
        (
            "wavelength_nm,absorption_coefficient_m_inv,"
            "absorption_uncertainty_m_inv\n"
            "1500,800000,20000\n"
            "1750,600000,25000\n"
            "2000,400000,30000\n"
        ),
    )

    dataset = load_optical_absorption_csv(
        path,
        sn_fraction=0.05,
        metadata=_metadata(),
    )

    assert dataset.has_uncertainty is True
    assert dataset.absorption_uncertainty_m_inv is not None
    assert dataset.absorption_uncertainty_m_inv.tolist() == [
        2.0e4,
        2.5e4,
        3.0e4,
    ]


def test_loader_preserves_metadata(tmp_path: Path):
    metadata = _metadata()

    path = _write_csv(
        tmp_path / "metadata.csv",
        (
            "wavelength_nm,absorption_coefficient_m_inv\n"
            "1500,800000\n"
            "1600,700000\n"
        ),
    )

    dataset = load_optical_absorption_csv(
        path,
        sn_fraction=0.03,
        metadata=metadata,
    )

    assert dataset.metadata is metadata
    assert dataset.metadata.dataset_id == "optical-csv-test"


def test_loaded_dataset_hash_matches_direct_normalized_dataset(
    tmp_path: Path,
):
    metadata = _metadata()

    path = _write_csv(
        tmp_path / "hash.csv",
        (
            "wavelength_nm,absorption_coefficient_m_inv\n"
            "1500,800000\n"
            "1750,600000\n"
            "2000,400000\n"
        ),
    )

    loaded = load_optical_absorption_csv(
        path,
        sn_fraction=0.05,
        metadata=metadata,
    )

    direct = OpticalAbsorptionDataset(
        wavelength_nm=np.array([1500.0, 1750.0, 2000.0]),
        absorption_coefficient_m_inv=np.array(
            [8.0e5, 6.0e5, 4.0e5],
        ),
        sn_fraction=0.05,
        metadata=metadata,
    )

    assert loaded.dataset_hash() == direct.dataset_hash()


def test_loader_accepts_utf8_bom(tmp_path: Path):
    path = _write_csv(
        tmp_path / "bom.csv",
        (
            "wavelength_nm,absorption_coefficient_m_inv\n"
            "1500,800000\n"
            "1600,700000\n"
        ),
        encoding="utf-8-sig",
    )

    dataset = load_optical_absorption_csv(
        path,
        sn_fraction=0.05,
        metadata=_metadata(),
    )

    assert dataset.n_points == 2


def test_loader_ignores_completely_blank_data_rows(tmp_path: Path):
    path = _write_csv(
        tmp_path / "blank_rows.csv",
        (
            "wavelength_nm,absorption_coefficient_m_inv\n"
            "\n"
            "1500,800000\n"
            "   ,   \n"
            "1600,700000\n"
            "\n"
        ),
    )

    dataset = load_optical_absorption_csv(
        path,
        sn_fraction=0.05,
        metadata=_metadata(),
    )

    assert dataset.n_points == 2


@pytest.mark.parametrize(
    "header",
    [
        "wavelength_nm,alpha_m_inv",
        "absorption_coefficient_m_inv,wavelength_nm",
        (
            "wavelength_nm,absorption_coefficient_m_inv,"
            "unexpected_column"
        ),
        "wavelength_nm,absorption_coefficient_m_inv,",
        " wavelength_nm,absorption_coefficient_m_inv",
    ],
)
def test_loader_rejects_unsupported_headers(
    tmp_path: Path,
    header: str,
):
    path = _write_csv(
        tmp_path / "bad_header.csv",
        f"{header}\n1500,800000\n1600,700000\n",
    )

    with pytest.raises(
        ValueError,
        match="Unsupported optical absorption CSV header",
    ):
        load_optical_absorption_csv(
            path,
            sn_fraction=0.05,
            metadata=_metadata(),
        )


def test_loader_rejects_empty_file(tmp_path: Path):
    path = _write_csv(tmp_path / "empty.csv", "")

    with pytest.raises(ValueError, match="CSV file is empty"):
        load_optical_absorption_csv(
            path,
            sn_fraction=0.05,
            metadata=_metadata(),
        )


def test_loader_rejects_header_only_file(tmp_path: Path):
    path = _write_csv(
        tmp_path / "header_only.csv",
        "wavelength_nm,absorption_coefficient_m_inv\n",
    )

    with pytest.raises(
        ValueError,
        match="at least two data rows",
    ):
        load_optical_absorption_csv(
            path,
            sn_fraction=0.05,
            metadata=_metadata(),
        )


def test_loader_rejects_single_data_row(tmp_path: Path):
    path = _write_csv(
        tmp_path / "one_row.csv",
        (
            "wavelength_nm,absorption_coefficient_m_inv\n"
            "1500,800000\n"
        ),
    )

    with pytest.raises(
        ValueError,
        match="at least two data rows",
    ):
        load_optical_absorption_csv(
            path,
            sn_fraction=0.05,
            metadata=_metadata(),
        )


@pytest.mark.parametrize(
    "bad_row",
    [
        "1500\n",
        "1500,800000,unexpected\n",
    ],
)
def test_loader_rejects_wrong_number_of_fields(
    tmp_path: Path,
    bad_row: str,
):
    path = _write_csv(
        tmp_path / "bad_fields.csv",
        (
            "wavelength_nm,absorption_coefficient_m_inv\n"
            f"{bad_row}"
            "1600,700000\n"
        ),
    )

    with pytest.raises(ValueError, match="CSV line 2"):
        load_optical_absorption_csv(
            path,
            sn_fraction=0.05,
            metadata=_metadata(),
        )


@pytest.mark.parametrize(
    ("bad_row", "field_name"),
    [
        ("not-a-number,800000\n", "wavelength_nm"),
        ("1500,not-a-number\n", "absorption_coefficient_m_inv"),
        ("1500,\n", "absorption_coefficient_m_inv"),
    ],
)
def test_loader_rejects_missing_or_non_numeric_primary_values(
    tmp_path: Path,
    bad_row: str,
    field_name: str,
):
    path = _write_csv(
        tmp_path / "bad_numeric.csv",
        (
            "wavelength_nm,absorption_coefficient_m_inv\n"
            f"{bad_row}"
            "1600,700000\n"
        ),
    )

    with pytest.raises(ValueError, match=field_name):
        load_optical_absorption_csv(
            path,
            sn_fraction=0.05,
            metadata=_metadata(),
        )


@pytest.mark.parametrize(
    "bad_value",
    ["", "not-a-number"],
)
def test_loader_rejects_missing_or_non_numeric_uncertainty(
    tmp_path: Path,
    bad_value: str,
):
    path = _write_csv(
        tmp_path / "bad_uncertainty.csv",
        (
            "wavelength_nm,absorption_coefficient_m_inv,"
            "absorption_uncertainty_m_inv\n"
            f"1500,800000,{bad_value}\n"
            "1600,700000,20000\n"
        ),
    )

    with pytest.raises(
        ValueError,
        match="absorption_uncertainty_m_inv",
    ):
        load_optical_absorption_csv(
            path,
            sn_fraction=0.05,
            metadata=_metadata(),
        )


@pytest.mark.parametrize(
    "rows",
    [
        "0,800000\n1600,700000\n",
        "-1500,800000\n1600,700000\n",
        "1500,-1\n1600,700000\n",
        "1500,nan\n1600,700000\n",
        "1500,inf\n1600,700000\n",
    ],
)
def test_loader_delegates_physical_validation_to_dataset(
    tmp_path: Path,
    rows: str,
):
    path = _write_csv(
        tmp_path / "invalid_physics.csv",
        (
            "wavelength_nm,absorption_coefficient_m_inv\n"
            f"{rows}"
        ),
    )

    with pytest.raises(ValueError):
        load_optical_absorption_csv(
            path,
            sn_fraction=0.05,
            metadata=_metadata(),
        )


@pytest.mark.parametrize(
    "uncertainty_rows",
    [
        "1500,800000,0\n1600,700000,20000\n",
        "1500,800000,-1\n1600,700000,20000\n",
        "1500,800000,nan\n1600,700000,20000\n",
        "1500,800000,inf\n1600,700000,20000\n",
    ],
)
def test_loader_delegates_uncertainty_validation_to_dataset(
    tmp_path: Path,
    uncertainty_rows: str,
):
    path = _write_csv(
        tmp_path / "invalid_uncertainty.csv",
        (
            "wavelength_nm,absorption_coefficient_m_inv,"
            "absorption_uncertainty_m_inv\n"
            f"{uncertainty_rows}"
        ),
    )

    with pytest.raises(ValueError):
        load_optical_absorption_csv(
            path,
            sn_fraction=0.05,
            metadata=_metadata(),
        )


def test_loader_delegates_sn_fraction_validation_to_dataset(
    tmp_path: Path,
):
    path = _write_csv(
        tmp_path / "bad_sn.csv",
        (
            "wavelength_nm,absorption_coefficient_m_inv\n"
            "1500,800000\n"
            "1600,700000\n"
        ),
    )

    with pytest.raises(ValueError, match="sn_fraction"):
        load_optical_absorption_csv(
            path,
            sn_fraction=1.1,
            metadata=_metadata(),
        )


def test_loader_requires_metadata_instance(tmp_path: Path):
    path = _write_csv(
        tmp_path / "bad_metadata.csv",
        (
            "wavelength_nm,absorption_coefficient_m_inv\n"
            "1500,800000\n"
            "1600,700000\n"
        ),
    )

    with pytest.raises(TypeError, match="metadata"):
        load_optical_absorption_csv(
            path,
            sn_fraction=0.05,
            metadata={},  # type: ignore[arg-type]
        )


def test_loader_preserves_file_not_found_error(tmp_path: Path):
    missing = tmp_path / "missing.csv"

    with pytest.raises(FileNotFoundError):
        load_optical_absorption_csv(
            missing,
            sn_fraction=0.05,
            metadata=_metadata(),
        )
