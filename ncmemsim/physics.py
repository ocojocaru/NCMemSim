from __future__ import annotations
from dataclasses import dataclass
from .electrostatics import ElectrostaticsEngine
from .tunneling import TunnelingEngine
from .kinetics import OccupancyEngine
from .transport import TransportEngine

@dataclass
class PhysicsModel:
    electrostatics: ElectrostaticsEngine
    tunneling: TunnelingEngine
    occupancy: OccupancyEngine
    transport: TransportEngine

    @classmethod
    def default(cls):
        tunneling=TunnelingEngine()
        return cls(ElectrostaticsEngine(), tunneling, OccupancyEngine(tunneling), TransportEngine(tunneling))
