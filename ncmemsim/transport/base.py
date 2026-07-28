from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class NodeKind(str, Enum):
    SUBSTRATE = "substrate"
    FLOATING_GATE = "floating_gate"
    GATE = "gate"


@dataclass(frozen=True)
class TransportNode:
    node_id: str
    kind: NodeKind
    z_nm: float
    fg_index: int | None = None
