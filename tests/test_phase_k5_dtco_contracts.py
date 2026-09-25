from unittest.mock import Mock

import pytest

from ncmemsim.dtco import SweepPoint
from ncmemsim.ensemble.dtco import (
    EnsembleDTCOStudy,
    EnsembleScalarDefinition,
    EnsembleScalarKind,
)
from ncmemsim.ensemble.feasibility import (
    EnsembleFeasibilitySummary,
)


@pytest.fixture(scope="module")
def source():
    result = Mock(spec=EnsembleFeasibilitySummary)
    result.result_hash = "b" * 64
    return result


def point(
    index=0,
    value=1.0,
    experiment_hash="a" * 64,
):
    return SweepPoint(
        experiment_hash,
        index,
        (("x", value),),
    )


def test_study_links_existing_dtco_point_and_k4_result(source):
    design_point = point()
    study = EnsembleDTCOStudy(
        design_point,
        source,
    )

    assert study.design_point is design_point
    assert study.source is source
    assert study.experiment_hash == design_point.experiment_hash
    assert study.point_hash == design_point.point_hash
    assert study.index == design_point.index
    assert study.assignments == {"x": 1.0}
    assert study.source_result_hash == source.result_hash

    payload = study.to_dict()
    assert payload["schema_version"] == "ensemble-dtco-study-v1"
    assert payload["design_point"] == design_point.to_dict()
    assert payload["point_hash"] == design_point.point_hash
    assert payload["source_result_hash"] == source.result_hash


def test_study_assignments_are_not_an_authoritative_duplicate(source):
    study = EnsembleDTCOStudy(
        point(),
        source,
    )

    assignments = study.assignments
    assignments["x"] = 99.0

    assert study.assignments == {"x": 1.0}
    assert study.design_point.assignments == {"x": 1.0}


@pytest.mark.parametrize(
    "design_point",
    [
        None,
        object(),
        "point",
    ],
)
def test_study_rejects_invalid_design_point(
    source,
    design_point,
):
    with pytest.raises(TypeError, match="SweepPoint"):
        EnsembleDTCOStudy(
            design_point,
            source,
        )


@pytest.mark.parametrize(
    "bad_source",
    [
        None,
        object(),
        {},
    ],
)
def test_study_rejects_invalid_source(
    bad_source,
):
    with pytest.raises(
        TypeError,
        match="EnsembleFeasibilitySummary",
    ):
        EnsembleDTCOStudy(
            point(),
            bad_source,
        )


def test_study_hash_is_deterministic_and_sensitive(
    source,
):
    baseline = EnsembleDTCOStudy(
        point(),
        source,
    )
    same = EnsembleDTCOStudy(
        point(),
        source,
    )
    changed_point = EnsembleDTCOStudy(
        point(index=1),
        source,
    )
    alternate_source = Mock(
        spec=EnsembleFeasibilitySummary,
    )
    alternate_source.result_hash = "c" * 64
    changed_source = EnsembleDTCOStudy(
        point(),
        alternate_source,
    )

    assert baseline.study_hash == same.study_hash
    assert baseline.study_hash != changed_point.study_hash
    assert baseline.study_hash != changed_source.study_hash


def test_scalar_kind_contract_is_explicit_and_excludes_variance():
    assert tuple(
        kind.value
        for kind in EnsembleScalarKind
    ) == (
        "mean",
        "standard_deviation",
        "minimum",
        "maximum",
        "median",
        "quantile",
        "coverage_fraction",
        "simulated_pass_fraction",
        "ensemble_feasibility_fraction",
        "failure_fraction",
    )
    assert not hasattr(
        EnsembleScalarKind,
        "VARIANCE",
    )


@pytest.mark.parametrize(
    "kind",
    [
        EnsembleScalarKind.MEAN,
        EnsembleScalarKind.STANDARD_DEVIATION,
        EnsembleScalarKind.MINIMUM,
        EnsembleScalarKind.MAXIMUM,
        EnsembleScalarKind.MEDIAN,
    ],
)
def test_metric_scalar_definition_accepts_declared_unit(
    kind,
):
    definition = EnsembleScalarDefinition(
        name=f"response_{kind.value}",
        kind=kind,
        unit="V",
        metric_name="response",
    )

    assert definition.metric_name == "response"
    assert definition.unit == "V"
    assert definition.quantile is None


def test_quantile_scalar_normalizes_probability():
    definition = EnsembleScalarDefinition(
        name="response_p05",
        kind=EnsembleScalarKind.QUANTILE,
        unit="V",
        metric_name="response",
        quantile=0.05,
    )

    assert definition.quantile == 0.05
    assert type(definition.quantile) is float


@pytest.mark.parametrize(
    "quantile",
    [
        None,
        True,
        "0.5",
        -0.01,
        1.01,
        float("nan"),
        float("inf"),
    ],
)
def test_quantile_scalar_rejects_invalid_probability(
    quantile,
):
    with pytest.raises(
        ValueError,
        match="finite probability",
    ):
        EnsembleScalarDefinition(
            name="response_quantile",
            kind=EnsembleScalarKind.QUANTILE,
            unit="V",
            metric_name="response",
            quantile=quantile,
        )


def test_nonquantile_metric_rejects_quantile_probability():
    with pytest.raises(
        ValueError,
        match="only valid for QUANTILE",
    ):
        EnsembleScalarDefinition(
            name="response_mean",
            kind=EnsembleScalarKind.MEAN,
            unit="V",
            metric_name="response",
            quantile=0.5,
        )


@pytest.mark.parametrize(
    "kind",
    [
        EnsembleScalarKind.MEAN,
        EnsembleScalarKind.QUANTILE,
    ],
)
def test_metric_scalar_requires_metric_name(
    kind,
):
    kwargs = (
        {"quantile": 0.5}
        if kind is EnsembleScalarKind.QUANTILE
        else {}
    )

    with pytest.raises(
        ValueError,
        match="requires metric_name",
    ):
        EnsembleScalarDefinition(
            name="metric_scalar",
            kind=kind,
            unit="V",
            **kwargs,
        )


@pytest.mark.parametrize(
    "kind",
    [
        EnsembleScalarKind.COVERAGE_FRACTION,
        EnsembleScalarKind.SIMULATED_PASS_FRACTION,
        EnsembleScalarKind.ENSEMBLE_FEASIBILITY_FRACTION,
        EnsembleScalarKind.FAILURE_FRACTION,
    ],
)
def test_fraction_scalar_is_explicitly_dimensionless(
    kind,
):
    definition = EnsembleScalarDefinition(
        name=kind.value,
        kind=kind,
        unit="1",
    )

    assert definition.metric_name is None
    assert definition.quantile is None
    assert definition.unit == "1"


@pytest.mark.parametrize(
    "kwargs,match",
    [
        (
            {"metric_name": "response"},
            "cannot declare metric_name",
        ),
        (
            {"quantile": 0.5},
            "cannot declare quantile",
        ),
        (
            {"unit": "V"},
            "requires unit '1'",
        ),
    ],
)
def test_fraction_scalar_rejects_metric_quantile_or_unit(
    kwargs,
    match,
):
    values = {
        "name": "failure_fraction",
        "kind": EnsembleScalarKind.FAILURE_FRACTION,
        "unit": "1",
    }
    values.update(kwargs)

    with pytest.raises(
        ValueError,
        match=match,
    ):
        EnsembleScalarDefinition(**values)


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "name": "",
            "kind": EnsembleScalarKind.MEAN,
            "unit": "V",
            "metric_name": "response",
        },
        {
            "name": " mean",
            "kind": EnsembleScalarKind.MEAN,
            "unit": "V",
            "metric_name": "response",
        },
        {
            "name": "mean",
            "kind": EnsembleScalarKind.MEAN,
            "unit": "",
            "metric_name": "response",
        },
        {
            "name": "mean",
            "kind": EnsembleScalarKind.MEAN,
            "unit": "V",
            "metric_name": " response",
        },
    ],
)
def test_scalar_definition_rejects_invalid_labels(
    kwargs,
):
    with pytest.raises(ValueError):
        EnsembleScalarDefinition(**kwargs)


def test_scalar_definition_requires_typed_kind():
    with pytest.raises(
        TypeError,
        match="EnsembleScalarKind",
    ):
        EnsembleScalarDefinition(
            name="response_mean",
            kind="mean",
            unit="V",
            metric_name="response",
        )


def test_scalar_definition_serialization_and_hash_are_deterministic():
    first = EnsembleScalarDefinition(
        name="response_p95",
        kind=EnsembleScalarKind.QUANTILE,
        unit="V",
        metric_name="response",
        quantile=0.95,
    )
    same = EnsembleScalarDefinition(
        name="response_p95",
        kind=EnsembleScalarKind.QUANTILE,
        unit="V",
        metric_name="response",
        quantile=0.95,
    )
    changed = EnsembleScalarDefinition(
        name="response_p50",
        kind=EnsembleScalarKind.QUANTILE,
        unit="V",
        metric_name="response",
        quantile=0.5,
    )

    assert first.to_dict() == {
        "schema_version": "ensemble-scalar-definition-v1",
        "name": "response_p95",
        "kind": "quantile",
        "metric_name": "response",
        "unit": "V",
        "quantile": 0.95,
    }
    assert first.definition_hash == same.definition_hash
    assert first.definition_hash != changed.definition_hash
