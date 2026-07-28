"""Public package interface for NCMemSim."""

from ._version import __version__
from .benchmark import (
    BenchmarkRecord,
    benchmark_case,
    run_benchmark_suite,
    write_benchmark_report,
)
from .builder import DeviceBuilder
from .coupling import CompactCouplingModel, CouplingModel, CouplingResult
from .device import Device
from .electrostatics import (
    ElectrostaticsEngine,
    ElectrostaticsResult,
    SemiconductorConfig,
)
from .fieldsolver import FieldProfile, FieldSolver1D
from .golden import build_golden_suite, compare_golden, write_golden_suite
from .kinetics import KineticsConfig, OccupancyEngine, RateArrays
from .layers import FloatingGateLayer, Layer
from .materials import HFO2, SILICON, SIO2, Material, NanocrystalMaterial, make_ge, make_gesn
from .optics import LightSource
from .physics import PhysicsModel
from .reference import make_v53_reference_device
from .reproducibility import build_reproducibility_manifest
from .retention import RetentionConfig, RetentionResult, RetentionSolver
from .simulator import CVResult, SimulationConfig, Simulator, SweepResult
from .state import DeviceState, FloatingGateState
from .transport import (
    LinkTransportResult,
    NodeKind,
    TransportConfig,
    TransportEngine,
    TransportNode,
    TransportStepResult,
    TunnelLink,
    TunnelNetwork,
)
from .tunneling import TunnelingConfig, TunnelingEngine
from .validation import (
    ValidationIssue,
    ValidationReport,
    validate_device_physics,
    validate_field_profile,
    validate_internal_charge_conservation,
    validate_probabilities,
    validate_simulation,
)

__all__ = [
    "__version__",
    "BenchmarkRecord",
    "CVResult",
    "CompactCouplingModel",
    "CouplingModel",
    "CouplingResult",
    "Device",
    "DeviceBuilder",
    "DeviceState",
    "ElectrostaticsEngine",
    "ElectrostaticsResult",
    "FieldProfile",
    "FieldSolver1D",
    "FloatingGateLayer",
    "FloatingGateState",
    "HFO2",
    "KineticsConfig",
    "Layer",
    "LightSource",
    "LinkTransportResult",
    "Material",
    "NanocrystalMaterial",
    "NodeKind",
    "OccupancyEngine",
    "PhysicsModel",
    "RateArrays",
    "RetentionConfig",
    "RetentionResult",
    "RetentionSolver",
    "SILICON",
    "SIO2",
    "SemiconductorConfig",
    "SimulationConfig",
    "Simulator",
    "SweepResult",
    "TransportConfig",
    "TransportEngine",
    "TransportNode",
    "TransportStepResult",
    "TunnelLink",
    "TunnelNetwork",
    "TunnelingConfig",
    "TunnelingEngine",
    "ValidationIssue",
    "ValidationReport",
    "benchmark_case",
    "build_golden_suite",
    "build_reproducibility_manifest",
    "compare_golden",
    "make_ge",
    "make_gesn",
    "make_v53_reference_device",
    "run_benchmark_suite",
    "validate_device_physics",
    "validate_field_profile",
    "validate_internal_charge_conservation",
    "validate_probabilities",
    "validate_simulation",
    "write_benchmark_report",
    "write_golden_suite",
]
