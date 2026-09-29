"""Phase K6c multi-parameter ensemble DTCO reference study.

This reference combines a deterministic tunnel-thickness/program-voltage
design space with paired stochastic nanocrystal-diameter and
electrically-active-fraction realizations.

The stochastic distributions are controlled assumptions inherited from the
K6b references. They are not measured process distributions and simulated
pass fractions are not manufacturing-yield estimates.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

from ncmemsim import DeviceBuilder
from ncmemsim.dtco import (
    AppliedExperimentPoint,
    BindingScope,
    DesignVariable,
    DesignVariableRole,
    ExperimentSpec,
    ParameterBinding,
    SweepPoint,
    apply_experiment_point,
    iter_cartesian_points,
)
from ncmemsim.ensemble import (
    EnsembleSpec,
    NormalDistribution,
    PhysicalDomain,
    RNGSpec,
    SampleManifest,
    SamplingSpec,
    StochasticVariable,
    generate_sample_manifest,
)
from ncmemsim.materials.provenance import (
    ParameterProvenance,
    ParameterStatus,
)
from ncmemsim.program_protocol import ProgramPulseReadProtocol


TUNNEL_THICKNESS_VALUES_NM = (6.0, 8.0, 10.0)
PROGRAM_VOLTAGE_VALUES_V = (4.0, 5.0, 6.0)

NOMINAL_TUNNEL_THICKNESS_NM = 8.0
NOMINAL_PROGRAM_VOLTAGE_V = 5.0
PROGRAMMING_TIME_S = 1.0e-6

NOMINAL_DIAMETER_NM = 5.0
DIAMETER_STANDARD_DEVIATION_NM = 0.35
NOMINAL_ACTIVE_FRACTION = 0.22
ACTIVE_FRACTION_STANDARD_DEVIATION = 0.03

REFERENCE_SEED = 2028
REFERENCE_SAMPLE_COUNT = 6

REFERENCE_EXPERIMENT_NAME = "phase-k6c-ensemble-dtco-reference"
REFERENCE_ENSEMBLE_NAME = "phase-k6c-paired-variability"


@dataclass(frozen=True)
class ReferenceEnsembleCase:
    """One DTCO point with its applied baseline and paired sample manifest."""

    point: SweepPoint
    applied: AppliedExperimentPoint
    manifest: SampleManifest


def _diameter_provenance() -> ParameterProvenance:
    return ParameterProvenance(
        source=(
            "Phase K6c controlled reference assumption inherited from K6b; "
            "not an experimentally measured diameter distribution"
        ),
        status=ParameterStatus.ASSUMED,
    )


def _active_fraction_provenance() -> ParameterProvenance:
    return ParameterProvenance(
        source=(
            "Phase K6c controlled reference assumption inherited from K6b; "
            "not an experimentally measured active-fraction distribution"
        ),
        status=ParameterStatus.ASSUMED,
    )


def _stochastic_variables() -> tuple[StochasticVariable, StochasticVariable]:
    """Return the frozen ordered K6c stochastic-variable definitions."""

    return (
        StochasticVariable(
            name="nc_diameter",
            binding=ParameterBinding(
                BindingScope.DEVICE,
                (
                    "layers",
                    "FG1",
                    "nc_diameter_nm",
                ),
            ),
            distribution=NormalDistribution(
                mean=NOMINAL_DIAMETER_NM,
                standard_deviation=DIAMETER_STANDARD_DEVIATION_NM,
            ),
            unit="nm",
            physical_domain=PhysicalDomain(
                lower=0.0,
                lower_inclusive=False,
            ),
            provenance=_diameter_provenance(),
            applicability=(
                "Controlled paired variability reference for one-FG "
                "electrical program/read DTCO"
            ),
            nominal_value=NOMINAL_DIAMETER_NM,
        ),
        StochasticVariable(
            name="active_fraction",
            binding=ParameterBinding(
                BindingScope.DEVICE,
                (
                    "layers",
                    "FG1",
                    "electrically_active_fraction",
                ),
            ),
            distribution=NormalDistribution(
                mean=NOMINAL_ACTIVE_FRACTION,
                standard_deviation=ACTIVE_FRACTION_STANDARD_DEVIATION,
            ),
            unit="1",
            physical_domain=PhysicalDomain(
                lower=0.0,
                upper=1.0,
                lower_inclusive=True,
                upper_inclusive=True,
            ),
            provenance=_active_fraction_provenance(),
            applicability=(
                "Controlled paired electrically-active-fraction disorder "
                "reference; not TAT trap-density variation"
            ),
            nominal_value=NOMINAL_ACTIVE_FRACTION,
        ),
    )


def build_reference_experiment():
    """Return the K6c base device, operating protocol and DTCO experiment."""

    device = DeviceBuilder.v2(
        n_fgs=1,
        name="k6c-ensemble-dtco-reference",
    )
    protocol = ProgramPulseReadProtocol(
        NOMINAL_PROGRAM_VOLTAGE_V,
        PROGRAMMING_TIME_S,
    )

    variables = (
        DesignVariable(
            name="tunnel_thickness_nm",
            binding=ParameterBinding(
                BindingScope.DEVICE,
                (
                    "layers",
                    "tunnel_sio2",
                    "thickness_nm",
                ),
            ),
            values=TUNNEL_THICKNESS_VALUES_NM,
            role=DesignVariableRole.GEOMETRY,
            unit="nm",
        ),
        DesignVariable(
            name="program_voltage_V",
            binding=ParameterBinding(
                BindingScope.OPERATING,
                (
                    "program",
                    "voltage_V",
                ),
            ),
            values=PROGRAM_VOLTAGE_VALUES_V,
            role=DesignVariableRole.ELECTRICAL,
            unit="V",
        ),
    )

    experiment = ExperimentSpec.from_device(
        name=REFERENCE_EXPERIMENT_NAME,
        device=device,
        variables=variables,
        description=(
            "Phase K6c controlled variability-aware DTCO reference: "
            "tunnel thickness versus program voltage."
        ),
        operating_protocol=protocol,
    )

    return device, protocol, experiment


def build_reference_design_points(
    experiment: ExperimentSpec,
) -> tuple[SweepPoint, ...]:
    """Return all nine canonical DTCO points in declared Cartesian order."""

    if not isinstance(experiment, ExperimentSpec):
        raise TypeError("experiment must be an ExperimentSpec")

    return tuple(iter_cartesian_points(experiment))


def build_reference_design_space():
    """Return base device, protocol, experiment and its ordered design points."""

    device, protocol, experiment = build_reference_experiment()
    points = build_reference_design_points(experiment)
    return device, protocol, experiment, points


def build_reference_ensemble_cases(
    *,
    sample_count: int = REFERENCE_SAMPLE_COUNT,
    seed: int = REFERENCE_SEED,
) -> tuple[ReferenceEnsembleCase, ...]:
    """Build distinct per-design manifests with deterministic paired draws."""

    if type(sample_count) is not int or sample_count <= 0:
        raise ValueError("sample_count must be a positive integer")
    if type(seed) is not int or seed < 0:
        raise ValueError("seed must be a nonnegative integer")

    device, protocol, experiment, points = build_reference_design_space()
    stochastic_variables = _stochastic_variables()

    cases: list[ReferenceEnsembleCase] = []

    for point in points:
        applied = apply_experiment_point(
            experiment,
            device,
            protocol,
            point.assignments,
        )

        ensemble = EnsembleSpec.from_device(
            name=REFERENCE_ENSEMBLE_NAME,
            device=applied.device,
            variables=stochastic_variables,
            description=(
                "Phase K6c paired NC-diameter and electrically-active-fraction "
                "variability at one DTCO design point."
            ),
            operating_protocol=applied.operating_protocol,
        )

        sampling_spec = SamplingSpec(
            ensemble_spec=ensemble,
            rng=RNGSpec(seed=seed),
            sample_count=sample_count,
        )
        manifest = generate_sample_manifest(sampling_spec)

        cases.append(
            ReferenceEnsembleCase(
                point=point,
                applied=applied,
                manifest=manifest,
            )
        )

    return tuple(cases)


def main() -> None:
    """Print the frozen K6c design space and paired manifest identities."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sample-count",
        type=int,
        default=REFERENCE_SAMPLE_COUNT,
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=REFERENCE_SEED,
    )
    args = parser.parse_args()

    _, _, experiment, points = build_reference_design_space()
    cases = build_reference_ensemble_cases(
        sample_count=args.sample_count,
        seed=args.seed,
    )

    print("experiment_hash:", experiment.experiment_hash)
    print("design_point_count:", experiment.design_point_count)
    print("sample_count:", args.sample_count)
    print("seed:", args.seed)

    for point, case in zip(points, cases):
        print(
            point.index,
            point.assignments,
            "manifest_hash=",
            case.manifest.manifest_hash,
        )


if __name__ == "__main__":
    main()
