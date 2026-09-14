from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from ncmemsim.experimental import (
    ExperimentalDatasetMetadata,
)
from ncmemsim.io import (
    load_optical_absorption_csv,
)


REFERENCE_DIR = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "reference"
    / "tran2016"
)

METADATA_PATH = (
    REFERENCE_DIR
    / "tran2016_sampleA_fig6a_metadata.json"
)

ALL_PATH = (
    REFERENCE_DIR
    / "tran2016_sampleA_fig6a_near_edge_all.csv"
)

FIT_PATH = (
    REFERENCE_DIR
    / "tran2016_sampleA_fig6a_fit.csv"
)

VALIDATION_PATH = (
    REFERENCE_DIR
    / "tran2016_sampleA_fig6a_validation.csv"
)

AUDIT_PATH = (
    REFERENCE_DIR
    / "tran2016_sampleA_fig6a_digitization_audit.csv"
)

OVERLAY_PATH = (
    REFERENCE_DIR
    / "tran2016_sampleA_fig6a_overlay.png"
)

README_PATH = (
    REFERENCE_DIR
    / "README.md"
)


EXPECTED_LOADER_HEADER = [
    "wavelength_nm",
    "absorption_coefficient_m_inv",
    "absorption_uncertainty_m_inv",
]


def _metadata() -> dict:
    with METADATA_PATH.open(
        encoding="utf-8"
    ) as file_handle:
        return json.load(file_handle)


def _dataset_metadata(
    *,
    dataset_id: str,
    notes: str,
) -> ExperimentalDatasetMetadata:
    metadata = _metadata()

    return ExperimentalDatasetMetadata(
        dataset_id=dataset_id,
        source=metadata["source"]["citation"],
        doi=metadata["source"]["doi"],
        sample_id=metadata["source"]["sample"],
        temperature_description=(
            metadata["sample_metadata"][
                "temperature_description"
            ]
        ),
        notes=notes,
    )


def _load_dataset(
    path: Path,
    *,
    dataset_id: str,
    notes: str,
):
    return load_optical_absorption_csv(
        path,
        sn_fraction=0.0,
        metadata=_dataset_metadata(
            dataset_id=dataset_id,
            notes=notes,
        ),
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file_handle:
        for chunk in iter(
            lambda: file_handle.read(
                1024 * 1024
            ),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def _read_csv_rows(
    path: Path,
) -> list[dict[str, str]]:
    with path.open(
        newline="",
        encoding="utf-8",
    ) as file_handle:
        return list(
            csv.DictReader(file_handle)
        )


def test_reference_package_contains_expected_files():
    expected_paths = (
        METADATA_PATH,
        ALL_PATH,
        FIT_PATH,
        VALIDATION_PATH,
        AUDIT_PATH,
        OVERLAY_PATH,
        README_PATH,
    )

    for path in expected_paths:
        assert path.is_file(), path


def test_reference_metadata_schema_and_classification():
    metadata = _metadata()

    assert metadata["schema_version"] == 1
    assert (
        metadata["dataset_family"]
        == "tran2016_sampleA_fig6a"
    )
    assert (
        metadata["classification"]
        == "DIGITIZED_MODEL_DERIVED_EXPERIMENTAL_DATA"
    )


def test_reference_source_identity_is_tran_2016():
    source = _metadata()["source"]

    assert source["doi"] == "10.1063/1.4943652"
    assert source["figure"] == "Figure 6(a)"
    assert source["pdf_page"] == 8
    assert source["sample"] == "A"
    assert len(source["source_pdf_sha256"]) == 64


def test_sample_metadata_describe_unstrained_pure_ge():
    sample = _metadata()["sample_metadata"]

    assert sample["material"] == "Ge"
    assert sample["sn_fraction"] == pytest.approx(
        0.0
    )
    assert (
        sample[
            "in_plane_compressive_strain_percent"
        ]
        == pytest.approx(0.0)
    )
    assert sample["film_thickness_nm"] == pytest.approx(
        300.0
    )
    assert (
        sample["temperature_description"]
        == "room temperature"
    )


def test_reported_sample_a_direct_gap_is_metadata_only():
    sample = _metadata()["sample_metadata"]

    assert (
        sample["reported_direct_gap_eV"]
        == pytest.approx(0.805)
    )
    assert (
        sample[
            "reported_direct_gap_uncertainty_eV"
        ]
        == pytest.approx(0.037)
    )


def test_data_lineage_preserves_model_derived_origin():
    lineage = _metadata()["data_lineage"]

    assert (
        "spectroscopic ellipsometry measurement"
        in lineage
    )
    assert any(
        "Johs-Herzinger" in entry
        for entry in lineage
    )
    assert any(
        "published Figure 6(a)" in entry
        for entry in lineage
    )
    assert any(
        "digitization" in entry
        for entry in lineage
    )


def test_digitization_uncertainty_is_explicitly_not_experimental():
    digitization = _metadata()["digitization"]

    assert (
        digitization[
            "assigned_relative_alpha_uncertainty"
        ]
        == pytest.approx(0.05)
    )

    uncertainty_note = digitization[
        "uncertainty_interpretation"
    ].lower()

    assert "digitization" in uncertainty_note
    assert "not" in uncertainty_note
    assert "experimental" in uncertainty_note


@pytest.mark.parametrize(
    "path",
    [
        ALL_PATH,
        FIT_PATH,
        VALIDATION_PATH,
    ],
)
def test_loader_ready_csv_headers_are_exact(
    path: Path,
):
    with path.open(
        newline="",
        encoding="utf-8",
    ) as file_handle:
        reader = csv.reader(file_handle)
        header = next(reader)

    assert header == EXPECTED_LOADER_HEADER


def test_all_selected_dataset_loads_with_existing_loader():
    dataset = _load_dataset(
        ALL_PATH,
        dataset_id=(
            "tran2016-sampleA-fig6a-all"
        ),
        notes=(
            "All selected near-edge points "
            "digitized from Tran 2016 Fig. 6(a)."
        ),
    )

    assert dataset.n_points == 8
    assert dataset.sn_fraction == pytest.approx(
        0.0
    )
    assert dataset.has_uncertainty is True
    assert np.all(
        dataset.wavelength_nm > 0.0
    )
    assert np.all(
        dataset.absorption_coefficient_m_inv
        >= 0.0
    )
    assert np.all(
        dataset.absorption_uncertainty_m_inv
        > 0.0
    )


def test_fit_and_validation_subsets_load_with_existing_loader():
    fit_dataset = _load_dataset(
        FIT_PATH,
        dataset_id=(
            "tran2016-sampleA-fig6a-fit"
        ),
        notes=(
            "Alternating-point fitting subset."
        ),
    )
    validation_dataset = _load_dataset(
        VALIDATION_PATH,
        dataset_id=(
            "tran2016-sampleA-fig6a-validation"
        ),
        notes=(
            "Alternating-point holdout subset."
        ),
    )

    assert fit_dataset.n_points == 4
    assert validation_dataset.n_points == 4
    assert fit_dataset.has_uncertainty is True
    assert validation_dataset.has_uncertainty is True


def test_fit_and_validation_subsets_are_disjoint():
    fit_rows = _read_csv_rows(
        FIT_PATH
    )
    validation_rows = _read_csv_rows(
        VALIDATION_PATH
    )

    fit_wavelengths = {
        row["wavelength_nm"]
        for row in fit_rows
    }
    validation_wavelengths = {
        row["wavelength_nm"]
        for row in validation_rows
    }

    assert fit_wavelengths.isdisjoint(
        validation_wavelengths
    )


def test_fit_and_validation_subsets_reconstruct_all_points():
    all_rows = _read_csv_rows(
        ALL_PATH
    )
    fit_rows = _read_csv_rows(
        FIT_PATH
    )
    validation_rows = _read_csv_rows(
        VALIDATION_PATH
    )

    all_triplets = {
        tuple(row[column] for column in EXPECTED_LOADER_HEADER)
        for row in all_rows
    }
    split_triplets = {
        tuple(row[column] for column in EXPECTED_LOADER_HEADER)
        for row in (
            fit_rows
            + validation_rows
        )
    }

    assert split_triplets == all_triplets


def test_split_policy_is_holdout_not_independent_experiment():
    split_policy = _metadata()["split_policy"]

    assert (
        split_policy["type"]
        == "holdout_from_same_published_curve"
    )
    assert (
        split_policy["independent_experiment"]
        is False
    )

    warning = split_policy["warning"].lower()

    assert "same published curve" in warning
    assert "not independent experiments" in warning


def test_split_point_ids_are_explicit_and_disjoint():
    split_policy = _metadata()["split_policy"]

    fit_ids = set(
        split_policy["fit_point_ids"]
    )
    validation_ids = set(
        split_policy[
            "validation_point_ids"
        ]
    )

    assert fit_ids == {
        "P02",
        "P04",
        "P06",
        "P08",
    }
    assert validation_ids == {
        "P01",
        "P03",
        "P05",
        "P07",
    }
    assert fit_ids.isdisjoint(
        validation_ids
    )


def test_audit_contains_selected_and_excluded_points():
    rows = _read_csv_rows(
        AUDIT_PATH
    )

    selected = [
        row
        for row in rows
        if row["selected_near_edge"] == "True"
    ]
    excluded = [
        row
        for row in rows
        if row["selected_near_edge"] == "False"
    ]

    assert len(selected) == 8
    assert len(excluded) == 3

    assert {
        row["split"]
        for row in excluded
    } == {
        "excluded_indirect_region"
    }


def test_selected_energy_and_wavelength_ranges_match_metadata():
    metadata = _metadata()
    rows = [
        row
        for row in _read_csv_rows(
            AUDIT_PATH
        )
        if row["selected_near_edge"] == "True"
    ]

    energies = np.array(
        [
            float(
                row["photon_energy_eV"]
            )
            for row in rows
        ]
    )
    wavelengths = np.array(
        [
            float(row["wavelength_nm"])
            for row in rows
        ]
    )

    expected_energy_range = (
        metadata["selection"][
            "selected_energy_range_eV"
        ]
    )
    expected_wavelength_range = (
        metadata["selection"][
            "selected_wavelength_range_nm"
        ]
    )

    assert energies.min() == pytest.approx(
        expected_energy_range[0],
        abs=1.0e-8,
    )
    assert energies.max() == pytest.approx(
        expected_energy_range[1],
        abs=1.0e-8,
    )

    assert wavelengths.min() == pytest.approx(
        expected_wavelength_range[0],
        abs=1.0e-5,
    )
    assert wavelengths.max() == pytest.approx(
        expected_wavelength_range[1],
        abs=1.0e-5,
    )


def test_boundary_level_digitization_note_is_preserved():
    selection = _metadata()["selection"]

    assert (
        selection[
            "selected_wavelength_range_nm"
        ][0]
        < 1500.0
    )

    note = selection[
        "upper_boundary_note"
    ].lower()

    assert "digitization effect" in note
    assert "not as evidence" in note
    assert "below 1500 nm" in note


def test_artifact_sha256_values_match_repository_files():
    artifact_hashes = _metadata()[
        "artifact_sha256"
    ]

    paths = {
        ALL_PATH.name: ALL_PATH,
        FIT_PATH.name: FIT_PATH,
        VALIDATION_PATH.name: VALIDATION_PATH,
        AUDIT_PATH.name: AUDIT_PATH,
        OVERLAY_PATH.name: OVERLAY_PATH,
    }

    assert set(
        artifact_hashes
    ) == set(paths)

    for name, path in paths.items():
        assert (
            _sha256(path)
            == artifact_hashes[name]
        )


def test_fit_and_validation_dataset_hashes_are_distinct():
    fit_dataset = _load_dataset(
        FIT_PATH,
        dataset_id=(
            "tran2016-sampleA-fig6a-fit"
        ),
        notes="F4f0 fit subset.",
    )
    validation_dataset = _load_dataset(
        VALIDATION_PATH,
        dataset_id=(
            "tran2016-sampleA-fig6a-validation"
        ),
        notes="F4f0 validation holdout.",
    )

    assert (
        fit_dataset.dataset_hash()
        != validation_dataset.dataset_hash()
    )


def test_readme_states_core_scientific_qualification():
    text = README_PATH.read_text(
        encoding="utf-8"
    ).lower()

    normalized_text = " ".join(
        text.split()
    )

    assert (
        "model-derived experimental optical data"
        in normalized_text
    )
    assert (
        "not raw ellipsometry observables"
        in normalized_text
    )
    assert (
        "holdout from the same published curve"
        in normalized_text
    )
    assert (
        "not an independent experiment"
        in normalized_text
    )
