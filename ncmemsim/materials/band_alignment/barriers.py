from __future__ import annotations
from dataclasses import dataclass
from ..base import Material, NanocrystalMaterial

@dataclass(frozen=True)
class BandAlignmentResult:
    conduction_barrier_eV: float
    valence_barrier_eV: float | None
    model: str

class BarrierModel:
    """Electron-affinity-rule estimate or explicit calibrated barrier."""
    @staticmethod
    def affinity_rule(nc: NanocrystalMaterial, oxide: Material) -> BandAlignmentResult:
        if nc.electron_affinity_eV is None or oxide.electron_affinity_eV is None:
            raise ValueError("Electron affinities are required for affinity-rule alignment.")
        dc=max(nc.electron_affinity_eV-oxide.electron_affinity_eV,0.0)
        dv=None
        if nc.bandgap_eV is not None and oxide.bandgap_eV is not None:
            dv=max(oxide.bandgap_eV-nc.bandgap_eV-dc,0.0)
        return BandAlignmentResult(dc,dv,"electron-affinity-rule")

    @staticmethod
    def calibrated(conduction_barrier_eV: float, valence_barrier_eV: float|None=None) -> BandAlignmentResult:
        if conduction_barrier_eV <= 0: raise ValueError("Calibrated barrier must be positive.")
        return BandAlignmentResult(conduction_barrier_eV,valence_barrier_eV,"calibrated")
