from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from .physics import PhysicsModel
from .state import DeviceState
from .optics import (
    LightSource,
    evaluate_floating_gate_optical_absorption,
)
from .photo import (
    PhotoTransitionConfig,
    PhotoTransitionWeights,
    evaluate_photo_transition_rates,
)

@dataclass(frozen=True)
class SimulationConfig:
    dwell_time_s: float = 0.005
    internal_dt_s: float = 1.0e-5
    qfix_C_m2: float = 0.0
    qit_C_m2: float = 0.0


@dataclass
class SweepResult:
    voltages_V: np.ndarray
    capacitance_F_m2: np.ndarray
    qfg_C_m2: np.ndarray
    vfb_V: np.ndarray
    veff_V: np.ndarray
    mean_occupation: np.ndarray
    field_mean_V_m: np.ndarray
    tprog_mean: np.ndarray
    terase_mean: np.ndarray
    final_state: DeviceState
    qfg_by_fg_C_m2: np.ndarray | None = None
    mean_occupation_by_fg: np.ndarray | None = None
    field_mean_by_fg_V_m: np.ndarray | None = None
    tprog_mean_by_fg: np.ndarray | None = None
    terase_mean_by_fg: np.ndarray | None = None
    delta_vfb_V: np.ndarray | None = None
    delta_vfb_by_fg_V: np.ndarray | None = None
    coupling_sensitivity_factors: np.ndarray | None = None
    coupling_coefficients_m2_F: np.ndarray | None = None
    electrostatic_local_field_by_fg_V_m: np.ndarray | None = None
    electrostatic_local_potential_by_fg_V: np.ndarray | None = None
    field_profiles: list | None = None
    inter_fg_flux_by_link_m2_s: np.ndarray | None = None
    transport_transmission_by_link: np.ndarray | None = None
    transport_link_ids: tuple[str, ...] | None = None
    optical_absorption_fraction: np.ndarray | None = None
    absorbed_photon_flux_m2_s: np.ndarray | None = None
    photo_transition_rate_s: np.ndarray | None = None

    optical_absorption_fraction_by_fg: np.ndarray | None = None
    absorbed_photon_flux_by_fg_m2_s: np.ndarray | None = None
    absorbed_photon_rate_per_nc_by_fg_s: np.ndarray | None = None
    photo_transition_rate_by_fg_s: np.ndarray | None = None
    optical_alpha_nc_by_fg_m_inv: np.ndarray | None = None
    optical_alpha_eff_by_fg_m_inv: np.ndarray | None = None


@dataclass
class CVResult:
    forward: SweepResult
    backward: SweepResult
    memory_window_V: float
    vmid_forward_V: float
    vmid_backward_V: float


class Simulator:
    """Transient simulator with compact electrostatic coupling for N FGs.

    Phase D2 keeps the occupations kinetically independent (inter-FG transport
    arrives in D4), but each FG charge now contributes through a centroid-based
    electrostatic sensitivity factor.  For one FG the validated legacy
    ``-QFG/Cox`` relation is preserved exactly.
    """

    def __init__(
        self,
        device,
        physics: PhysicsModel | None = None,
        config: SimulationConfig | None = None,
    ):
        device.validate()
        self.device = device
        self.physics = physics or PhysicsModel.default()
        self.config = config or SimulationConfig()

    def _tunnel_base_distance_m(self, fg_index: int = 0) -> float:
        fg = self.device.floating_gates()[fg_index]
        idx = self.device.layers.index(fg)
        return sum(
            layer.thickness_nm * 1e-9
            for layer in self.device.layers[idx + 1 :]
            if layer.role in {"tunnel_dielectric", "native_oxide", "interlayer_dielectric"}
        )

    def _charge_one(self, state: DeviceState, fg_index: int):
        fg = self.device.floating_gates()[fg_index]
        fg_state = state.floating_gates[fg_index]
        x_m, dx_m = self.physics.occupancy.grid(fg)
        density_m3 = self.physics.occupancy.density_profile(fg, x_m)
        rho_C_m3 = self.physics.occupancy.charge_density_C_m3(fg_state, density_m3)
        qfg_C_m2 = self.physics.occupancy.total_charge_C_m2(rho_C_m3, dx_m)
        return qfg_C_m2, rho_C_m3, x_m, dx_m

    def _charges(self, state: DeviceState):
        per_fg = [self._charge_one(state, i) for i in range(self.device.number_of_fgs())]
        q_by_fg = np.asarray([item[0] for item in per_fg], dtype=float)
        return float(np.sum(q_by_fg)), q_by_fg, per_fg

    # Kept for compatibility with code that used the private Phase-B helper.
    def _charge(self, state: DeviceState):
        if self.device.number_of_fgs() == 1:
            return self._charge_one(state, 0)
        q_total, _, per_fg = self._charges(state)
        return q_total, [item[1] for item in per_fg], [item[2] for item in per_fg], [item[3] for item in per_fg]

    def relax_voltage(
        self,
        state: DeviceState,
        gate_voltage_V: float,
        dwell_time_s: float | None = None,
        internal_dt_s: float | None = None,
        light_source: LightSource | None = None,
        photo_config: PhotoTransitionConfig | None = None,
        photo_weights: PhotoTransitionWeights | None = None,
    ):
        state.validate(self.device)
        dwell = self.config.dwell_time_s if dwell_time_s is None else dwell_time_s
        dt = self.config.internal_dt_s if internal_dt_s is None else internal_dt_s
        if dwell < 0 or dt <= 0:
            raise ValueError("dwell_time_s must be non-negative and internal_dt_s positive")

        current = state.copy()
        fgs = self.device.floating_gates()
        grids = [self.physics.occupancy.grid(fg) for fg in fgs]
        bases = [self._tunnel_base_distance_m(i) for i in range(len(fgs))]
        photo_rates_by_fg = [None] * len(fgs)
        optical_results_by_fg = [None] * len(fgs)
        photo_evaluations_by_fg = [None] * len(fgs)

        if light_source is not None:
            for fg_index, fg in enumerate(fgs):
                optical_result = evaluate_floating_gate_optical_absorption(
                    light_source,
                    fg,
                )
                
                photo_evaluation = evaluate_photo_transition_rates(
                    optical_result,
                    fg,
                    config=photo_config,
                    weights=photo_weights,
                )
                              
                optical_results_by_fg[fg_index] = optical_result
                photo_evaluations_by_fg[fg_index] = photo_evaluation
                photo_rates_by_fg[fg_index] = photo_evaluation.rates
                     
        nsteps = max(1, int(math.ceil(dwell / dt)))
        actual_dt = dwell / nsteps
        rates_by_fg = [None] * len(fgs)
        transport_result = None

        for _ in range(nsteps):
            q_total, q_by_fg, _ = self._charges(current)
            electro_charge = q_total if len(fgs) == 1 else q_by_fg
            electro = self.physics.electrostatics.evaluate(
                self.device,
                gate_voltage_V,
                electro_charge,
                self.config.qfix_C_m2,
                self.config.qit_C_m2,
            )
            next_states = []
            for fg_index, fg in enumerate(fgs):
                x_m, _ = grids[fg_index]
                local_field = None
                if len(fgs) > 1 and electro.local_fields_by_fg_V_m is not None:
                    local_field = electro.local_fields_by_fg_V_m[fg_index]
                
                rates = self.physics.occupancy.rates(
                    fg,
                    x_m,
                    electro.veff_V,
                    bases[fg_index],
                    self.device.temperature_K,
                    field_V_m=local_field,
                )

                photo_rates = photo_rates_by_fg[fg_index]

                if photo_rates is not None:
                    rates = self.physics.occupancy.combine_rates(
                        rates,
                        photo_rates,
                    )

                rates_by_fg[fg_index] = rates
                
                next_states.append(
                    self.physics.occupancy.step(
                        current.floating_gates[fg_index], rates, actual_dt
                    )
                )
            current.floating_gates = next_states
            # D4: conservative nearest-neighbour redistribution between FGs.
            # Substrate injection/emission remains in OccupancyEngine, while the
            # transport network supplies inter-FG exchange and link diagnostics.
            if len(fgs) > 1:
                q_after, q_after_by_fg, _ = self._charges(current)
                electro_after = self.physics.electrostatics.evaluate(
                    self.device,
                    gate_voltage_V,
                    q_after_by_fg,
                    self.config.qfix_C_m2,
                    self.config.qit_C_m2,
                )
                current, transport_result = self.physics.transport.step(
                    self.device,
                    current,
                    electro_after.field_profile,
                    self.physics.occupancy,
                    actual_dt,
                )

        current.time_s = state.time_s + dwell
        q_total, q_by_fg, per_fg = self._charges(current)
        electro_charge = q_total if len(fgs) == 1 else q_by_fg
        electro = self.physics.electrostatics.evaluate(
            self.device,
            gate_voltage_V,
            electro_charge,
            self.config.qfix_C_m2,
            self.config.qit_C_m2,
        )
        for fg_index, fg_state in enumerate(current.floating_gates):
            fg_state.local_field_V_m = float(electro.local_fields_by_fg_V_m[fg_index])
            fg_state.local_potential_V = float(electro.local_potentials_by_fg_V[fg_index])
        occupations = current.mean_normalized_occupations
        field_by_fg = np.asarray(
            [float(np.mean(r.field_V_m)) for r in rates_by_fg], dtype=float
        )
        tprog_by_fg = np.asarray(
            [float(np.mean(r.tprog)) for r in rates_by_fg], dtype=float
        )
        terase_by_fg = np.asarray(
            [float(np.mean(r.terase)) for r in rates_by_fg], dtype=float
        )

        if transport_result is None:
            transport_result = self.physics.transport.evaluate(
                self.device, current, electro.field_profile, self.physics.occupancy
            )
        transport_links = transport_result.links

        # Aggregate means retain the Phase-B scalar API. For one FG they are
        # bit-for-bit equivalent to the former implementation.
        
        if light_source is None:
            optical_absorption_fraction_by_fg = np.full(
                len(fgs),
                np.nan,
                dtype=float,
            )

            absorbed_photon_flux_by_fg_m2_s = np.zeros(
                len(fgs),
                dtype=float,
            )

            absorbed_photon_rate_per_nc_by_fg_s = np.zeros(
                len(fgs),
                dtype=float,
            )

            photo_transition_rate_by_fg_s = np.zeros(
                len(fgs),
                dtype=float,
            )

            optical_alpha_nc_by_fg_m_inv = np.full(
                len(fgs),
                np.nan,
                dtype=float,
            )

            optical_alpha_eff_by_fg_m_inv = np.full(
                len(fgs),
                np.nan,
                dtype=float,
            )

        else:
            optical_absorption_fraction_by_fg = np.asarray(
                [
                    result.absorption_fraction
                    for result in optical_results_by_fg
                ],
                dtype=float,
            )

            absorbed_photon_flux_by_fg_m2_s = np.asarray(
                [
                    result.absorbed_photon_flux_m2_s
                    for result in optical_results_by_fg
                ],
                dtype=float,
            )

            absorbed_photon_rate_per_nc_by_fg_s = np.asarray(
                [
                    result.absorbed_photon_rate_per_nc_s
                    for result in photo_evaluations_by_fg
                ],
                dtype=float,
            )

            photo_transition_rate_by_fg_s = np.asarray(
                [
                    result.base_photo_transition_rate_s
                    for result in photo_evaluations_by_fg
                ],
                dtype=float,
            )

            optical_alpha_nc_by_fg_m_inv = np.asarray(
                [
                    result.nc_absorption_coefficient_m_inv
                    for result in optical_results_by_fg
                ],
                dtype=float,
            )

            optical_alpha_eff_by_fg_m_inv = np.asarray(
                [
                    result.effective_absorption_coefficient_m_inv
                    for result in optical_results_by_fg
                ],
                dtype=float,
            )
        
        return {
            "state": current,
            "rho_C_m3": per_fg[0][1] if len(per_fg) == 1 else [x[1] for x in per_fg],
            "rho_by_fg_C_m3": [x[1] for x in per_fg],
            "qfg_C_m2": q_total,
            "qfg_by_fg_C_m2": q_by_fg,
            "vfb_V": electro.vfb_V,
            "veff_V": electro.veff_V,
            "capacitance_F_m2": electro.capacitance_F_m2,
            "mean_occupation": float(np.mean(occupations)),
            "mean_occupation_by_fg": occupations,
            "field_mean_V_m": float(np.mean(field_by_fg)),
            "field_mean_by_fg_V_m": field_by_fg,
            "tprog_mean": float(np.mean(tprog_by_fg)),
            "tprog_mean_by_fg": tprog_by_fg,
            "terase_mean": float(np.mean(terase_by_fg)),
            "terase_mean_by_fg": terase_by_fg,
            "delta_vfb_V": electro.delta_vfb_V,
            "delta_vfb_by_fg_V": electro.delta_vfb_by_fg_V,
            "coupling_sensitivity_factors": electro.coupling.sensitivity_factors.copy(),
            "coupling_coefficients_m2_F": electro.coupling.coefficients_m2_F.copy(),
            "coupling_matrix_m2_F": electro.coupling.matrix_m2_F.copy(),
            "electrostatic_local_field_by_fg_V_m": electro.local_fields_by_fg_V_m.copy(),
            "electrostatic_local_potential_by_fg_V": electro.local_potentials_by_fg_V.copy(),
            "field_profile": electro.field_profile,
            "potential_profile": electro.field_profile,
            "transport_network": self.physics.transport.build_network(self.device),
            "transport_link_results": transport_links,
            "transport_link_ids": tuple(link.link_id for link in transport_links),
            "inter_fg_flux_by_link_m2_s": transport_result.inter_fg_fluxes_m2_s,
            "transport_transmission_by_link": np.asarray(
                [link.transmission for link in transport_links], dtype=float
            ),
            "transport_net_flux_by_fg_m2_s": transport_result.net_electron_flux_by_fg_m2_s.copy(),
            "optical_absorption_fraction_by_fg":
                optical_absorption_fraction_by_fg,

            "absorbed_photon_flux_by_fg_m2_s":
                absorbed_photon_flux_by_fg_m2_s,

            "absorbed_photon_rate_per_nc_by_fg_s":
                absorbed_photon_rate_per_nc_by_fg_s,

            "photo_transition_rate_by_fg_s":
                photo_transition_rate_by_fg_s,

            "optical_alpha_nc_by_fg_m_inv":
                optical_alpha_nc_by_fg_m_inv,

            "optical_alpha_eff_by_fg_m_inv":
                optical_alpha_eff_by_fg_m_inv,
                
            "optical_absorption_fraction": (
                float(optical_absorption_fraction_by_fg[0])
                if len(fgs) == 1
                else (
                    float(np.nanmean(optical_absorption_fraction_by_fg))
                    if np.any(np.isfinite(optical_absorption_fraction_by_fg))
                    else float("nan")
                )
            ),

            "absorbed_photon_flux_m2_s": float(
                np.sum(absorbed_photon_flux_by_fg_m2_s)
            ),

            "photo_transition_rate_s": (
                float(photo_transition_rate_by_fg_s[0])
                if len(fgs) == 1
                else float(np.mean(photo_transition_rate_by_fg_s))
            ),
        }

    def run_sweep(
        self,
        voltages_V,
        state: DeviceState | None = None,
        light_source: LightSource | None = None,
        photo_config: PhotoTransitionConfig | None = None,
        photo_weights: PhotoTransitionWeights | None = None,
    ):
        current = state.copy() if state else DeviceState.empty_for_device(self.device)
        current.validate(self.device)
        scalar_keys = [
            "capacitance_F_m2",
            "qfg_C_m2",
            "vfb_V",
            "veff_V",
            "mean_occupation",
            "field_mean_V_m",
            "tprog_mean",
            "terase_mean",
            "optical_absorption_fraction",
            "absorbed_photon_flux_m2_s",
            "photo_transition_rate_s",
        ]
        vector_keys = [
            "qfg_by_fg_C_m2",
            "mean_occupation_by_fg",
            "field_mean_by_fg_V_m",
            "tprog_mean_by_fg",
            "terase_mean_by_fg",
            "delta_vfb_by_fg_V",
            "electrostatic_local_field_by_fg_V_m",
            "electrostatic_local_potential_by_fg_V",
            "optical_absorption_fraction_by_fg",
            "absorbed_photon_flux_by_fg_m2_s",
            "absorbed_photon_rate_per_nc_by_fg_s",
            "photo_transition_rate_by_fg_s",
            "optical_alpha_nc_by_fg_m_inv",
            "optical_alpha_eff_by_fg_m_inv",
        ]
        histories = {key: [] for key in scalar_keys + vector_keys}
        transport_flux_history = []
        transport_transmission_history = []
        transport_link_ids = None
        for voltage in voltages_V:
            out = self.relax_voltage(
                current,
                float(voltage),
                light_source=light_source,
                photo_config=photo_config,
                photo_weights=photo_weights,
            )
            current = out["state"]
            for key in histories:
                histories[key].append(out[key])
            transport_flux_history.append(out["inter_fg_flux_by_link_m2_s"])
            transport_transmission_history.append(out["transport_transmission_by_link"])
            transport_link_ids = out["transport_link_ids"]
        return SweepResult(
            voltages_V=np.asarray(voltages_V, dtype=float),
            capacitance_F_m2=np.asarray(histories["capacitance_F_m2"]),
            qfg_C_m2=np.asarray(histories["qfg_C_m2"]),
            vfb_V=np.asarray(histories["vfb_V"]),
            veff_V=np.asarray(histories["veff_V"]),
            mean_occupation=np.asarray(histories["mean_occupation"]),
            field_mean_V_m=np.asarray(histories["field_mean_V_m"]),
            tprog_mean=np.asarray(histories["tprog_mean"]),
            terase_mean=np.asarray(histories["terase_mean"]),
            final_state=current,
            qfg_by_fg_C_m2=np.asarray(histories["qfg_by_fg_C_m2"]),
            mean_occupation_by_fg=np.asarray(histories["mean_occupation_by_fg"]),
            field_mean_by_fg_V_m=np.asarray(histories["field_mean_by_fg_V_m"]),
            tprog_mean_by_fg=np.asarray(histories["tprog_mean_by_fg"]),
            terase_mean_by_fg=np.asarray(histories["terase_mean_by_fg"]),
            delta_vfb_V=np.asarray([v - self.physics.electrostatics.flatband_zero(self.device, self.config.qfix_C_m2, self.config.qit_C_m2) for v in histories["vfb_V"]]),
            delta_vfb_by_fg_V=np.asarray(histories["delta_vfb_by_fg_V"]),
            coupling_sensitivity_factors=self.physics.electrostatics.coupling_model.sensitivity_factors(self.device),
            coupling_coefficients_m2_F=self.physics.electrostatics.coupling_model.sensitivity_factors(self.device) / self.physics.electrostatics.equivalent_capacitance(self.device),
            electrostatic_local_field_by_fg_V_m=np.asarray(histories["electrostatic_local_field_by_fg_V_m"]),
            electrostatic_local_potential_by_fg_V=np.asarray(histories["electrostatic_local_potential_by_fg_V"]),
            inter_fg_flux_by_link_m2_s=np.asarray(transport_flux_history),
            transport_transmission_by_link=np.asarray(transport_transmission_history),
            transport_link_ids=transport_link_ids,
            optical_absorption_fraction=np.asarray(
                histories["optical_absorption_fraction"]
            ),
            absorbed_photon_flux_m2_s=np.asarray(
                histories["absorbed_photon_flux_m2_s"]
            ),
            photo_transition_rate_s=np.asarray(
                histories["photo_transition_rate_s"]
            ),

            optical_absorption_fraction_by_fg=np.asarray(
                histories["optical_absorption_fraction_by_fg"]
            ),
            absorbed_photon_flux_by_fg_m2_s=np.asarray(
                histories["absorbed_photon_flux_by_fg_m2_s"]
            ),
            absorbed_photon_rate_per_nc_by_fg_s=np.asarray(
                histories["absorbed_photon_rate_per_nc_by_fg_s"]
            ),
            photo_transition_rate_by_fg_s=np.asarray(
                histories["photo_transition_rate_by_fg_s"]
            ),
            optical_alpha_nc_by_fg_m_inv=np.asarray(
                histories["optical_alpha_nc_by_fg_m_inv"]
            ),
            optical_alpha_eff_by_fg_m_inv=np.asarray(
                histories["optical_alpha_eff_by_fg_m_inv"]
            ),
        )


    def simulate_retention(self, state: DeviceState | None = None, config=None):
        """Run adaptive charge redistribution and retention at fixed bias."""
        from .retention import RetentionConfig, RetentionSolver

        cfg = config if config is not None else RetentionConfig()
        return RetentionSolver(self, cfg).run(state)

    @staticmethod
    def voltage_at_capacitance(voltage, capacitance, reference):
        v = np.asarray(voltage)
        c = np.asarray(capacitance)
        idx = np.argsort(v)
        vs = v[idx]
        cs = c[idx]
        order = np.argsort(cs)
        cu, ui = np.unique(cs[order], return_index=True)
        vu = vs[order][ui]
        if reference < cu[0] or reference > cu[-1]:
            return float("nan")
        return float(np.interp(reference, cu, vu))

    def simulate_cv(
        self,
        vmin_V=-3.0,
        vmax_V=3.0,
        points=241,
        light_source: LightSource | None = None,
        photo_config: PhotoTransitionConfig | None = None,
        photo_weights: PhotoTransitionWeights | None = None,
    ):
        vf = np.linspace(vmin_V, vmax_V, points)
        vb = np.linspace(vmax_V, vmin_V, points)
        forward = self.run_sweep(
            vf,
            light_source=light_source,
            photo_config=photo_config,
            photo_weights=photo_weights,
        )

        backward = self.run_sweep(
            vb,
            forward.final_state,
            light_source=light_source,
            photo_config=photo_config,
            photo_weights=photo_weights,
        )
        cmax = max(
            np.max(forward.capacitance_F_m2), np.max(backward.capacitance_F_m2)
        )
        cmin = min(
            np.min(forward.capacitance_F_m2), np.min(backward.capacitance_F_m2)
        )
        cmid = 0.5 * (cmax + cmin)
        vmf = self.voltage_at_capacitance(vf, forward.capacitance_F_m2, cmid)
        vmb = self.voltage_at_capacitance(vb, backward.capacitance_F_m2, cmid)
        return CVResult(forward, backward, vmb - vmf, vmf, vmb)
