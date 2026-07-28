from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np


@dataclass(frozen=True)
class LinkTransportResult:
    link_id: str
    kind: str
    field_V_m: float
    potential_difference_V: float
    transmission: float
    forward_rate_Hz: float
    backward_rate_Hz: float
    net_electron_flux_m2_s: float
    left_fg_index: int | None
    right_fg_index: int | None


@dataclass(frozen=True)
class TransportStepResult:
    links: tuple[LinkTransportResult, ...]
    net_electron_flux_by_fg_m2_s: np.ndarray

    @property
    def inter_fg_fluxes_m2_s(self) -> np.ndarray:
        return np.asarray(
            [link.net_electron_flux_m2_s for link in self.links if link.kind == "inter_fg"],
            dtype=float,
        )
