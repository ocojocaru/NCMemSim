from __future__ import annotations

from dataclasses import dataclass

from .base import NodeKind, TransportNode
from .link import TunnelLink


@dataclass(frozen=True)
class TunnelNetwork:
    nodes: tuple[TransportNode, ...]
    links: tuple[TunnelLink, ...]

    def validate(self) -> None:
        ids = {node.node_id for node in self.nodes}
        if len(ids) != len(self.nodes):
            raise ValueError("Transport-node identifiers must be unique")
        for link in self.links:
            link.validate()
            if link.left_node_id not in ids or link.right_node_id not in ids:
                raise ValueError("Tunnel link references an unknown node")

    @classmethod
    def from_device(
        cls,
        device,
        *,
        barrier_eV: float = 1.78,
        effective_mass_m0: float = 0.15,
        include_substrate_link: bool = True,
    ) -> "TunnelNetwork":
        positions = device.layer_positions_nm()
        fgs = device.floating_gates()
        nodes = [
            TransportNode("gate", NodeKind.GATE, 0.0),
            *[
                TransportNode(
                    f"fg:{fg.name}",
                    NodeKind.FLOATING_GATE,
                    0.5 * sum(positions[fg.name]),
                    fg_index=i,
                )
                for i, fg in enumerate(fgs)
            ],
            TransportNode("substrate", NodeKind.SUBSTRATE, device.total_thickness_nm()),
        ]

        links: list[TunnelLink] = []
        # Adjacent FG links follow physical stack order (gate -> substrate).
        for i in range(len(fgs) - 1):
            left, right = fgs[i], fgs[i + 1]
            left_idx = device.layers.index(left)
            right_idx = device.layers.index(right)
            between = device.layers[left_idx + 1 : right_idx]
            length_m = sum(layer.thickness_nm for layer in between) * 1e-9
            names = tuple(layer.name for layer in between)
            links.append(
                TunnelLink(
                    link_id=f"{left.name}<->{right.name}",
                    left_node_id=f"fg:{left.name}",
                    right_node_id=f"fg:{right.name}",
                    length_m=length_m,
                    barrier_eV=barrier_eV,
                    effective_mass_m0=effective_mass_m0,
                    dielectric_layers=names,
                    kind="inter_fg",
                    left_fg_index=i,
                    right_fg_index=i + 1,
                )
            )

        if include_substrate_link:
            nearest = fgs[-1]
            idx = device.layers.index(nearest)
            between = device.layers[idx + 1 :]
            length_m = sum(layer.thickness_nm for layer in between) * 1e-9
            if length_m > 0.0:
                links.append(
                    TunnelLink(
                        link_id=f"{nearest.name}<->substrate",
                        left_node_id=f"fg:{nearest.name}",
                        right_node_id="substrate",
                        length_m=length_m,
                        barrier_eV=barrier_eV,
                        effective_mass_m0=effective_mass_m0,
                        dielectric_layers=tuple(layer.name for layer in between),
                        kind="substrate",
                        left_fg_index=len(fgs) - 1,
                        right_fg_index=None,
                    )
                )

        network = cls(tuple(nodes), tuple(links))
        network.validate()
        return network
