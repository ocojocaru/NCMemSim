from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TunnelLink:
    """A directed-capable tunnelling path between two transport nodes."""

    link_id: str
    left_node_id: str
    right_node_id: str
    length_m: float
    barrier_eV: float
    effective_mass_m0: float
    dielectric_layers: tuple[str, ...]
    kind: str
    left_fg_index: int | None = None
    right_fg_index: int | None = None

    def validate(self) -> None:
        if self.length_m <= 0.0:
            raise ValueError("Tunnel-link length must be positive")
        if self.barrier_eV <= 0.0:
            raise ValueError("Tunnel-link barrier must be positive")
        if self.effective_mass_m0 <= 0.0:
            raise ValueError("Tunnel-link effective mass must be positive")
