from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from ncmemsim.dtco import SweepPoint
from ncmemsim.ensemble.dtco import (
    EnsembleDTCOStudy,
    evaluate_ensemble_eligibility,
)
from ncmemsim.ensemble.reporting import EnsembleReportStudy


def _load_k4c_helpers():
    path = (
        Path(__file__).resolve().parent
        / "test_phase_k4_feasibility_contracts.py"
    )
    spec = importlib.util.spec_from_file_location(
        "phase_k4_feasibility_contract_helpers",
        path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Phase K4c test helpers")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_K4C = _load_k4c_helpers()


def report_study(
    *,
    values=(1.0, 2.0, 3.0),
    point_index=0,
    point_value=1.0,
) -> EnsembleReportStudy:
    population = _K4C.population_statistics(values=values)
    feasibility = _K4C.valid_result(population)
    metric_analysis = population.source
    execution = metric_analysis.source

    design_point = SweepPoint(
        "a" * 64,
        point_index,
        (("x", point_value),),
    )
    study = EnsembleDTCOStudy(
        design_point=design_point,
        source=feasibility,
    )
    eligibility = evaluate_ensemble_eligibility(
        study,
        (),
    )

    return EnsembleReportStudy(
        execution=execution,
        metric_analysis=metric_analysis,
        population_statistics=population,
        feasibility=feasibility,
        study=study,
        eligibility=eligibility,
    )


def test_report_study_accepts_real_k3_through_k5b_chain():
    result = report_study()

    assert result.metric_analysis.source is result.execution
    assert result.population_statistics.source is result.metric_analysis
    assert result.feasibility.source is result.population_statistics
    assert result.study.source is result.feasibility
    assert result.eligibility.study is result.study
    assert result.eligibility.status == "eligible"

    payload = result.to_dict()
    assert payload["schema_version"] == "ensemble-report-study-v1"
    assert (
        payload["execution"]["result_hash"]
        == result.execution.result_hash
    )
    assert (
        payload["metric_analysis"]["result_hash"]
        == result.metric_analysis.result_hash
    )
    assert (
        payload["population_statistics"]["result_hash"]
        == result.population_statistics.result_hash
    )
    assert (
        payload["feasibility"]["result_hash"]
        == result.feasibility.result_hash
    )
    assert payload["study"]["study_hash"] == result.study.study_hash
    assert (
        payload["eligibility"]["result_hash"]
        == result.eligibility.result_hash
    )


def test_report_study_hash_is_deterministic_and_source_sensitive():
    first = report_study()
    same = report_study()
    changed_population = report_study(values=(1.0, 2.0, 4.0))
    changed_design = report_study(point_index=1)

    assert first.result_hash == same.result_hash
    assert first.result_hash != changed_population.result_hash
    assert first.result_hash != changed_design.result_hash


@pytest.mark.parametrize(
    "field",
    (
        "execution",
        "metric_analysis",
        "population_statistics",
        "feasibility",
        "study",
        "eligibility",
    ),
)
def test_report_study_rejects_wrong_component_type(field):
    source = report_study()
    kwargs = {
        "execution": source.execution,
        "metric_analysis": source.metric_analysis,
        "population_statistics": source.population_statistics,
        "feasibility": source.feasibility,
        "study": source.study,
        "eligibility": source.eligibility,
    }
    kwargs[field] = object()

    with pytest.raises(TypeError, match=field):
        EnsembleReportStudy(**kwargs)


def test_report_study_rejects_k4a_source_mismatch():
    source = report_study()
    other = report_study(values=(1.0, 2.0, 4.0))

    with pytest.raises(
        ValueError,
        match="K4a source differs",
    ):
        EnsembleReportStudy(
            execution=source.execution,
            metric_analysis=other.metric_analysis,
            population_statistics=other.population_statistics,
            feasibility=other.feasibility,
            study=other.study,
            eligibility=other.eligibility,
        )


def test_report_study_rejects_k4b_source_mismatch():
    source = report_study()
    other = report_study(values=(1.0, 2.0, 4.0))

    with pytest.raises(
        ValueError,
        match="K4b source differs",
    ):
        EnsembleReportStudy(
            execution=source.execution,
            metric_analysis=source.metric_analysis,
            population_statistics=other.population_statistics,
            feasibility=other.feasibility,
            study=other.study,
            eligibility=other.eligibility,
        )


def test_report_study_rejects_k4c_source_mismatch():
    source = report_study()
    other = report_study(values=(1.0, 2.0, 4.0))

    with pytest.raises(
        ValueError,
        match="K4c source differs",
    ):
        EnsembleReportStudy(
            execution=source.execution,
            metric_analysis=source.metric_analysis,
            population_statistics=source.population_statistics,
            feasibility=other.feasibility,
            study=other.study,
            eligibility=other.eligibility,
        )


def test_report_study_rejects_k5_source_mismatch():
    source = report_study()
    other = report_study(values=(1.0, 2.0, 4.0))

    mismatched_study = EnsembleDTCOStudy(
        design_point=source.study.design_point,
        source=other.feasibility,
    )
    mismatched_eligibility = evaluate_ensemble_eligibility(
        mismatched_study,
        (),
    )

    with pytest.raises(
        ValueError,
        match="K5 study source differs",
    ):
        EnsembleReportStudy(
            execution=source.execution,
            metric_analysis=source.metric_analysis,
            population_statistics=source.population_statistics,
            feasibility=source.feasibility,
            study=mismatched_study,
            eligibility=mismatched_eligibility,
        )


def test_report_study_rejects_k5b_study_mismatch():
    source = report_study()
    other = report_study(point_index=1)

    with pytest.raises(
        ValueError,
        match="K5b source study differs",
    ):
        EnsembleReportStudy(
            execution=source.execution,
            metric_analysis=source.metric_analysis,
            population_statistics=source.population_statistics,
            feasibility=source.feasibility,
            study=source.study,
            eligibility=other.eligibility,
        )
