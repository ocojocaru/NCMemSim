"""Phase K6c multi-parameter ensemble DTCO reference study.

This module first freezes the deterministic DTCO design space used by the
K6c variability-aware reference. Ensemble construction and K3-K6 execution
are added incrementally after this design-space contract is validated.
"""

from __future__ import annotations

from ncmemsim import DeviceBuilder
from ncmemsim.dtco import (
    BindingScope,
    DesignVariable,
    DesignVariableRole,
    ExperimentSpec,
    ParameterBinding,
    SweepPoint,
    iter_cartesian_points,
)
from ncmemsim.program_protocol import ProgramPulseReadProtocol


TUNNEL_THICKNESS_VALUES_NM = (6.0, 8.0, 10.0)
PROGRAM_VOLTAGE_VALUES_V = (4.0, 5.0, 6.0)

NOMINAL_TUNNEL_THICKNESS_NM = 8.0
NOMINAL_PROGRAM_VOLTAGE_V = 5.0
PROGRAMMING_TIME_S = 1.0e-6

REFERENCE_EXPERIMENT_NAME = "phase-k6c-ensemble-dtco-reference"


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


def main() -> None:
    """Print the frozen deterministic K6c design space."""

    _, _, experiment, points = build_reference_design_space()

    print("experiment_hash:", experiment.experiment_hash)
    print("design_point_count:", experiment.design_point_count)
    for point in points:
        print(point.index, point.assignments)


if __name__ == "__main__":
    main()
