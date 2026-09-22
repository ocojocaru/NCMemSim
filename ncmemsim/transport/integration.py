"""Explicit Phase J4 attachment of opt-in mechanisms to transport links.

The stable :class:`TransportEngine` remains the direct-tunnelling baseline.
This module provides an additive wrapper: only link identifiers named in an
``AdvancedTransportSpec`` receive a trap-assisted contribution.  Per-link
failures are recorded and contribute zero flux, so a failed optional mechanism
cannot erase the direct result or corrupt a neighbouring link.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Any

import numpy as np

from ..hashing import canonical_hash
from .barrier_corrections import (
    CorrectedTATRateEvaluation,
    ImageForceBarrierSpec,
    evaluate_trap_assisted_transport_with_barrier_correction,
)
from .engine import TransportEngine
from .rates import LinkTransportResult, TransportStepResult
from .traps import TrapAssistedTransportSpec


class TransportMechanism(str, Enum):
    """Mechanisms reported by the J4 composite result."""

    DIRECT_TUNNELLING = "direct_tunnelling"
    TRAP_ASSISTED = "trap_assisted"


class MechanismEvaluationStatus(str, Enum):
    """Outcome of one mechanism on one explicit network link."""

    EVALUATED = "evaluated"
    NOT_ATTACHED = "not_attached"
    DISABLED = "disabled"
    DIAGNOSTIC_ONLY = "diagnostic_only"
    FAILED = "failed"


@dataclass(frozen=True)
class MechanismFailure:
    """Sanitized failure information retained without raising across links."""

    exception_type: str
    message: str

    def __post_init__(self) -> None:
        if type(self.exception_type) is not str or not self.exception_type:
            raise ValueError("exception_type must be nonempty text")
        if type(self.message) is not str or not self.message:
            raise ValueError("message must be nonempty text")

    def to_dict(self) -> dict[str, str]:
        return {"exception_type": self.exception_type, "message": self.message}


@dataclass(frozen=True)
class TATLinkAttachment:
    """Attach one immutable TAT configuration to one exact link identifier."""

    link_id: str
    specification: TrapAssistedTransportSpec
    barrier_correction: ImageForceBarrierSpec = ImageForceBarrierSpec()

    def __post_init__(self) -> None:
        if type(self.link_id) is not str or not self.link_id or self.link_id != self.link_id.strip():
            raise ValueError("link_id must be nonempty text without outer whitespace")
        if not isinstance(self.specification, TrapAssistedTransportSpec):
            raise TypeError("specification must be TrapAssistedTransportSpec")
        if not isinstance(self.barrier_correction, ImageForceBarrierSpec):
            raise TypeError("barrier_correction must be ImageForceBarrierSpec")

    def to_dict(self) -> dict[str, Any]:
        return {
            "link_id": self.link_id,
            "specification": self.specification.to_dict(),
            "barrier_correction": self.barrier_correction.to_dict(),
        }


@dataclass(frozen=True)
class AdvancedTransportSpec:
    """Complete explicit link-attachment map for one composite evaluation."""

    attachments: tuple[TATLinkAttachment, ...] = ()

    def __post_init__(self) -> None:
        if type(self.attachments) is not tuple or any(
            not isinstance(item, TATLinkAttachment) for item in self.attachments
        ):
            raise TypeError("attachments must be a tuple of TATLinkAttachment")
        ids = [item.link_id for item in self.attachments]
        if len(ids) != len(set(ids)):
            raise ValueError("each transport link may have at most one TAT attachment")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "attachments": [item.to_dict() for item in self.attachments],
        }

    @property
    def configuration_hash(self) -> str:
        return canonical_hash(self.to_dict())


@dataclass(frozen=True)
class MechanismContribution:
    """Rates and signed electron flux from one mechanism on one link."""

    mechanism: TransportMechanism
    status: MechanismEvaluationStatus
    forward_rate_Hz: float
    backward_rate_Hz: float
    net_electron_flux_m2_s: float
    evaluation: CorrectedTATRateEvaluation | None = None
    failure: MechanismFailure | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.mechanism, TransportMechanism):
            raise TypeError("mechanism must be TransportMechanism")
        if not isinstance(self.status, MechanismEvaluationStatus):
            raise TypeError("status must be MechanismEvaluationStatus")
        for name in ("forward_rate_Hz", "backward_rate_Hz"):
            value = float(getattr(self, name))
            if not math.isfinite(value) or value < 0.0:
                raise ValueError(f"{name} must be finite and nonnegative")
            object.__setattr__(self, name, value)
        flux = float(self.net_electron_flux_m2_s)
        if not math.isfinite(flux):
            raise ValueError("net_electron_flux_m2_s must be finite")
        object.__setattr__(self, "net_electron_flux_m2_s", flux)
        if self.status is MechanismEvaluationStatus.FAILED:
            if self.failure is None:
                raise ValueError("failed contributions require failure details")
        elif self.failure is not None:
            raise ValueError("only failed contributions may contain failure details")

    def to_dict(self) -> dict[str, Any]:
        return {
            "mechanism": self.mechanism.value,
            "status": self.status.value,
            "forward_rate_Hz": self.forward_rate_Hz,
            "backward_rate_Hz": self.backward_rate_Hz,
            "net_electron_flux_m2_s": self.net_electron_flux_m2_s,
            "evaluation": None if self.evaluation is None else self.evaluation.to_dict(),
            "failure": None if self.failure is None else self.failure.to_dict(),
        }


@dataclass(frozen=True)
class IntegratedLinkTransportResult:
    """Legacy direct result plus complete mechanism-resolved accounting."""

    baseline: LinkTransportResult
    contributions: tuple[MechanismContribution, ...]
    total_forward_rate_Hz: float
    total_backward_rate_Hz: float
    total_net_electron_flux_m2_s: float

    @property
    def link_id(self) -> str:
        return self.baseline.link_id

    @property
    def kind(self) -> str:
        return self.baseline.kind

    @property
    def field_V_m(self) -> float:
        return self.baseline.field_V_m

    @property
    def potential_difference_V(self) -> float:
        return self.baseline.potential_difference_V

    @property
    def transmission(self) -> float:
        return self.baseline.transmission

    @property
    def forward_rate_Hz(self) -> float:
        return self.total_forward_rate_Hz

    @property
    def backward_rate_Hz(self) -> float:
        return self.total_backward_rate_Hz

    @property
    def net_electron_flux_m2_s(self) -> float:
        return self.total_net_electron_flux_m2_s

    @property
    def left_fg_index(self) -> int | None:
        return self.baseline.left_fg_index

    @property
    def right_fg_index(self) -> int | None:
        return self.baseline.right_fg_index

    def contribution(self, mechanism: TransportMechanism) -> MechanismContribution:
        if not isinstance(mechanism, TransportMechanism):
            raise TypeError("mechanism must be TransportMechanism")
        return next(item for item in self.contributions if item.mechanism is mechanism)


@dataclass(frozen=True)
class IntegratedTransportStepResult:
    """Composite result with the untouched direct baseline retained."""

    baseline: TransportStepResult
    links: tuple[IntegratedLinkTransportResult, ...]
    net_electron_flux_by_fg_m2_s: np.ndarray

    def __post_init__(self) -> None:
        values = np.asarray(self.net_electron_flux_by_fg_m2_s, dtype=float).copy()
        if values.ndim != 1 or not np.all(np.isfinite(values)):
            raise ValueError("net_electron_flux_by_fg_m2_s must be a finite vector")
        values.setflags(write=False)
        object.__setattr__(self, "net_electron_flux_by_fg_m2_s", values)

    @property
    def inter_fg_fluxes_m2_s(self) -> np.ndarray:
        return np.asarray(
            [item.total_net_electron_flux_m2_s for item in self.links if item.kind == "inter_fg"],
            dtype=float,
        )


class AdvancedTransportEngine:
    """Compose explicit optional mechanisms with a stable direct engine."""

    def __init__(
        self,
        baseline: TransportEngine,
        specification: AdvancedTransportSpec | None = None,
    ):
        if not isinstance(baseline, TransportEngine):
            raise TypeError("baseline must be TransportEngine")
        if specification is not None and not isinstance(specification, AdvancedTransportSpec):
            raise TypeError("specification must be AdvancedTransportSpec")
        self.baseline = baseline
        self.specification = specification or AdvancedTransportSpec()

    @property
    def tunneling(self):
        return self.baseline.tunneling

    @property
    def config(self):
        return self.baseline.config

    def build_network(self, device):
        return self.baseline.build_network(device)

    @staticmethod
    def _direct(item: LinkTransportResult) -> MechanismContribution:
        return MechanismContribution(
            TransportMechanism.DIRECT_TUNNELLING,
            MechanismEvaluationStatus.DIAGNOSTIC_ONLY
            if item.kind == "substrate" else MechanismEvaluationStatus.EVALUATED,
            item.forward_rate_Hz,
            item.backward_rate_Hz,
            item.net_electron_flux_m2_s,
        )

    @staticmethod
    def _inactive(status: MechanismEvaluationStatus) -> MechanismContribution:
        return MechanismContribution(
            TransportMechanism.TRAP_ASSISTED, status, 0.0, 0.0, 0.0
        )

    def evaluate(self, device, state, field_profile, occupancy_engine) -> IntegratedTransportStepResult:
        direct = self.baseline.evaluate(device, state, field_profile, occupancy_engine)
        network = self.build_network(device)
        links_by_id = {item.link_id: item for item in network.links}
        attachments = {item.link_id: item for item in self.specification.attachments}
        unknown = sorted(set(attachments) - set(links_by_id))
        if unknown:
            raise ValueError("advanced transport attachment references unknown links: " + ", ".join(unknown))

        fgs = device.floating_gates()
        sheet_sites = np.asarray(
            [self.baseline._sheet_site_density(occupancy_engine, fg) for fg in fgs],
            dtype=float,
        )
        electron_sheet = 2.0 * state.mean_normalized_occupations * sheet_sites
        capacity_sheet = 2.0 * sheet_sites
        net = np.asarray(direct.net_electron_flux_by_fg_m2_s, dtype=float).copy()
        integrated: list[IntegratedLinkTransportResult] = []

        for base in direct.links:
            contributions = [self._direct(base)]
            attachment = attachments.get(base.link_id)
            if attachment is None:
                tat = self._inactive(MechanismEvaluationStatus.NOT_ATTACHED)
            elif not attachment.specification.enabled:
                tat = self._inactive(MechanismEvaluationStatus.DISABLED)
            else:
                link = links_by_id[base.link_id]
                try:
                    evaluation = evaluate_trap_assisted_transport_with_barrier_correction(
                        attachment.specification,
                        attachment.barrier_correction,
                        link_length_m=link.length_m,
                        electric_field_V_m=base.field_V_m,
                        effective_mass_m0=link.effective_mass_m0,
                    )
                    forward_bias = 1.0 / (
                        1.0 + math.exp(-self.config.direction_beta_V_inv * base.potential_difference_V)
                    )
                    kf = evaluation.total_rate_Hz * forward_bias
                    kb = evaluation.total_rate_Hz * (1.0 - forward_bias)
                    if not math.isfinite(kf) or not math.isfinite(kb):
                        raise ArithmeticError(
                            "non-finite optional mechanism directional rate"
                        )
                    if base.kind == "inter_fg":
                        li, ri = base.left_fg_index, base.right_fg_index
                        available_left = float(electron_sheet[li])
                        empty_right = float(capacity_sheet[ri] - electron_sheet[ri])
                        available_right = float(electron_sheet[ri])
                        empty_left = float(capacity_sheet[li] - electron_sheet[li])
                        forward_flux = kf * min(available_left, empty_right)
                        backward_flux = kb * min(available_right, empty_left)
                        flux = forward_flux - backward_flux
                        if not all(
                            math.isfinite(value)
                            for value in (forward_flux, backward_flux, flux)
                        ):
                            raise ArithmeticError(
                                "non-finite optional mechanism flux"
                            )
                        next_left = float(net[li]) - flux
                        next_right = float(net[ri]) + flux
                        if not math.isfinite(next_left) or not math.isfinite(next_right):
                            raise ArithmeticError(
                                "non-finite optional mechanism net flux"
                            )
                        # Mutate only after the optional contribution is finite.
                        net[li] = next_left
                        net[ri] = next_right
                        status = MechanismEvaluationStatus.EVALUATED
                    else:
                        flux = 0.0
                        status = MechanismEvaluationStatus.DIAGNOSTIC_ONLY
                    tat = MechanismContribution(
                        TransportMechanism.TRAP_ASSISTED,
                        status,
                        kf,
                        kb,
                        flux,
                        evaluation=evaluation,
                    )
                except Exception as exc:
                    message = str(exc).strip() or "optional mechanism evaluation failed"
                    tat = MechanismContribution(
                        TransportMechanism.TRAP_ASSISTED,
                        MechanismEvaluationStatus.FAILED,
                        0.0,
                        0.0,
                        0.0,
                        failure=MechanismFailure(type(exc).__name__, message),
                    )
            contributions.append(tat)
            integrated.append(
                IntegratedLinkTransportResult(
                    base,
                    tuple(contributions),
                    math.fsum(item.forward_rate_Hz for item in contributions),
                    math.fsum(item.backward_rate_Hz for item in contributions),
                    math.fsum(item.net_electron_flux_m2_s for item in contributions),
                )
            )
        return IntegratedTransportStepResult(direct, tuple(integrated), net)

    def step(self, device, state, field_profile, occupancy_engine, dt_s: float):
        result = self.evaluate(device, state, field_profile, occupancy_engine)
        if not self.config.enabled or device.number_of_fgs() < 2 or dt_s <= 0.0:
            return state.copy(), result

        fgs = device.floating_gates()
        sheet_sites = np.asarray(
            [self.baseline._sheet_site_density(occupancy_engine, fg) for fg in fgs], dtype=float
        )
        current_e = 2.0 * state.mean_normalized_occupations * sheet_sites
        delta_e = result.net_electron_flux_by_fg_m2_s * dt_s
        max_delta = self.config.max_transfer_fraction_per_step * 2.0 * sheet_sites
        delta_e = np.clip(delta_e, -max_delta, max_delta)
        positive = float(np.sum(delta_e[delta_e > 0.0]))
        negative = float(-np.sum(delta_e[delta_e < 0.0]))
        transferable = min(positive, negative)
        if positive > 0.0:
            delta_e[delta_e > 0.0] *= transferable / positive
        if negative > 0.0:
            delta_e[delta_e < 0.0] *= transferable / negative
        lower = -current_e
        upper = 2.0 * sheet_sites - current_e
        delta_e = np.minimum(np.maximum(delta_e, lower), upper)
        imbalance = float(np.sum(delta_e))
        if imbalance > 0.0:
            candidates = delta_e > lower
            room = delta_e[candidates] - lower[candidates]
            if room.size and float(np.sum(room)) > 0.0:
                delta_e[candidates] -= imbalance * room / float(np.sum(room))
        elif imbalance < 0.0:
            candidates = delta_e < upper
            room = upper[candidates] - delta_e[candidates]
            if room.size and float(np.sum(room)) > 0.0:
                delta_e[candidates] += (-imbalance) * room / float(np.sum(room))
        target_e = np.clip(current_e + delta_e, 0.0, 2.0 * sheet_sites)
        out = state.copy()
        out.floating_gates = [
            self.baseline._set_mean_occupation(
                fg_state, target_e[index] / (2.0 * sheet_sites[index])
            )
            for index, fg_state in enumerate(state.floating_gates)
        ]
        return out, result


__all__ = [
    "TransportMechanism",
    "MechanismEvaluationStatus",
    "MechanismFailure",
    "TATLinkAttachment",
    "AdvancedTransportSpec",
    "MechanismContribution",
    "IntegratedLinkTransportResult",
    "IntegratedTransportStepResult",
    "AdvancedTransportEngine",
]
