# Result contracts reviewed from v0.14.0

These are observed contracts of the v0.14.0 implementation, checked during
[compatibility preparation](api_compatibility.md). They do not establish
experimental calibration or freeze every candidate API for v1.0.
The [source inventory](api_inventory.md) covers declarations and signatures
throughout the package; semantic review below covers the core simulation results.
Fitting/qualification and G/H/I results retain their existing dedicated manuals;
complete per-result semantic approval and historical archive fixtures remain gates.

## Dimensions, ordering and units

Let N be the number of requested sweep points, F the number of floating gates,
G_i the grid-point count of FG i, L the number of all transport links, and I the
number of inter-FG links. FG order follows the device layers from gate towards
substrate. Link IDs follow the transport result's link tuple; inter-FG histories
filter that tuple by kind and need not have the same column count as all links.

| Quantity | Unit |
| --- | --- |
| voltage, flat-band shift, potential | V |
| sheet charge | C/m^2 |
| volumetric charge density | C/m^3 |
| capacitance per area | F/m^2 |
| electric field | V/m |
| optical power density | W/m^2 |
| photon/electron flux per area | 1/(m^2 s) |
| transition or absorbed-photon rate per NC | 1/s |
| absorption coefficient | 1/m |
| probability, normalized occupation, transmission, sensitivity | 1 |
| coupling coefficient | m^2/F |

`tprog`, `terase`, their means and histories are **dimensionless WKB transmission
factors**, despite their names; they are not programming/erase durations in s.
The `r01`, `r12`, `r21`, `r10` rate arrays have units 1/s.

## State and ownership

`DeviceState.floating_gates[i]` owns one `FloatingGateState` with `P0`, `P1`,
`P2` shaped `(G_i,)`. They are writable arrays; valid values are finite,
non-negative and sum to one per grid cell. Normalized occupation is
`0.5 * (P1 + 2 * P2)`, dimensionless. `time_s` is physical elapsed time.
Different FGs may have different G_i; never stack probabilities assuming equal grids.

`copy()` creates independent probability arrays and new top-level metadata dicts.
Nested metadata objects remain shared: it is not a deep metadata copy.
`relax_voltage`, `run_sweep` and retention copy the supplied state before evolving
probabilities. They return mutable states; callers must not infer independence
of nested metadata from probability-array independence.

## Simulator.relax_voltage

The method returns a dictionary. `state` is the updated copy; the supplied state's
probabilities and time remain unchanged. A zero dwell computes diagnostics without
advancing physical time. Two profile keys, `field_profile` and `potential_profile`,
reference the **same FieldProfile object**, not different profile types.

| Keys | Type / shape |
| --- | --- |
| `qfg_C_m2`, `vfb_V`, `veff_V`, `capacitance_F_m2`, `delta_vfb_V` | scalar |
| `mean_occupation`, `field_mean_V_m`, `tprog_mean`, `terase_mean` | scalar; arithmetic mean of FG means |
| `qfg_by_fg_C_m2`, `mean_occupation_by_fg`, `field_mean_by_fg_V_m`, `tprog_mean_by_fg`, `terase_mean_by_fg`, `delta_vfb_by_fg_V` | `(F,)` |
| `coupling_sensitivity_factors`, `coupling_coefficients_m2_F`, `electrostatic_local_field_by_fg_V_m`, `electrostatic_local_potential_by_fg_V`, `transport_net_flux_by_fg_m2_s` | `(F,)` |
| `coupling_matrix_m2_F` | `(F,F)` |
| `rho_by_fg_C_m3` | list of F arrays shaped `(G_i,)` |
| `rho_C_m3` | one array when F=1; list of arrays when F>1 (legacy polymorphism) |
| `transport_link_results`, `transport_link_ids` | tuples for all L links |
| `transport_transmission_by_link` | `(L,)` |
| `inter_fg_flux_by_link_m2_s` | `(I,)`; empty when there are no inter-FG links |
| `transport_network` | TunnelNetwork |
| optical keys ending `_by_fg` or `_by_fg_s`, `_by_fg_m2_s`, `_by_fg_m_inv` | `(F,)`; exact field names are in the simulator inventory |
| `optical_absorption_fraction`, `absorbed_photon_flux_m2_s`, `photo_transition_rate_s` | scalar |

Dark calls retain optical keys. Absorption fractions and NC/effective absorption
coefficients are NaN (unavailable); absorbed flux, per-NC absorbed-photon rate and
photo-transition rate are zero. With light, aggregate absorbed flux is the sum
of FG fluxes; absorption fraction is the available-FG mean and photo rate is the
arithmetic FG mean. These aggregations do not introduce sequential stack optics.
None, NaN and zero have distinct meanings; do not normalize all three to zero.

## SweepResult and CVResult

For nonempty one-dimensional voltage input, scalar histories have shape `(N,)`,
per-FG histories `(N,F)`, inter-FG flux histories `(N,I)` and all-link transmission
histories `(N,L)`. Coupling sensitivity and coefficients are `(F,)`, not histories.
`transport_link_ids` labels all-link transmission columns, not directly the
inter-FG-only columns. `final_state` is the state after the last requested voltage.
Sweeps preserve requested voltage order; they do not sort the input.

Dataclass optional fields default to None for manual/legacy construction. Current
`run_sweep` populates its computed arrays, including dark optical arrays, but
`field_profiles` stays None: profile histories are not currently recorded there.
The dataclass itself is mutable, and result arrays are writable.

`voltages_V` uses `np.asarray(..., dtype=float)` and may share memory with a
supplied compatible NumPy array. Do not promise that every input is defensively
copied. Empty sweeps currently produce rank-one empty history arrays `(0,)`,
`transport_link_ids=None` and a copied initial state; `(0,F)` normalization is not
implemented. Whether to normalize/reject empty input before v1.0 remains a review
item; this preparation preserves current behavior.

`CVResult.forward` and `backward` are SweepResults. Forward goes vmin to vmax;
backward goes vmax to vmin starting from the forward final state. `memory_window_V`
is `vmid_backward_V - vmid_forward_V` at the branch capacitance reference used by
`simulate_cv`; missing crossings can produce NaN. This is a dynamic C-V hysteresis
window, not the separate pulse-defined program/erase memory-window observable.

## RetentionResult

Let T be the actual returned output count, which may be smaller than requested
due to unique time samples or enabled quasi-equilibrium stopping. Scalar histories
are `(T,)`, per-FG histories `(T,F)`, inter-FG histories `(T,I)` and transmission
histories `(T,L)`. `transport_link_ids` covers all links. `time_s` begins at zero
and reports elapsed retention duration; final state's absolute time also includes
the supplied state's initial time. Zero total duration returns one initial sample.
`charge_rate_C_m2_s` is a sheet-charge rate diagnostic.

`quasi_equilibrium_time_s` is None when no quasi-equilibrium event is detected;
`quasi_equilibrium_reached` then is False. These are not manufacturing or material
qualification claims. If the initial total sheet charge is effectively zero
(at or below the float tiny threshold), `total_charge_retention_fraction` returns
ones and `charge_loss_fraction` zeros as a numerical convention; it is not evidence
of retained programmed charge. Otherwise the fraction is q(t)/q(0).

## Other core result containers

| Container | Observed shape / ownership |
| --- | --- |
| `CouplingResult` | FG vectors `(F,)`, matrix `(F,F)`, scalar total shift; frozen container, writable array payloads |
| `ElectrostaticsResult` | scalar electrostatics and optional coupling/FG/profile fields; frozen container, no universal deep-immutability guarantee |
| `FieldProfile` | boundary z/potential arrays `(B,)`, electric field and layer names `(B-1,)`, FG vectors `(F,)`; frozen container with writable arrays; z starts at gate side in nm |
| `RateArrays` | each array `(G_i,)` for one FG; transition rates 1/s, transmissions 1, field V/m |
| `TransportStepResult` | ordered link tuple and net FG flux `(F,)`; `inter_fg_fluxes_m2_s` derives only inter-FG links |
| `LinkTransportResult` | scalar link diagnostics, rates Hz, flux 1/(m^2 s), optional endpoint FG indices |
| `FloatingGateOpticalResult` | scalar optical diagnostics and optional component coefficients/gaps/provenance; scalar units follow explicit names |
| `PhotoTransitionEvaluation` / `PhotoTransitionRates` | scalar efficiency/rate diagnostics and four per-grid rate arrays `(G_i,)`; frozen containers, rate arrays remain writable |

A frozen dataclass prevents field rebinding; it does not freeze NumPy arrays or
nested mappings. G/H/I archive wrappers instead retain canonical payload strings
and supply reconstructed dictionaries; their archive integrity, failure denominators
and runtime limits are described in the linked dedicated manuals, not inferred
from the core dataclass ownership rules.

## Remaining decisions before approval

- Approve supported import paths; source-visible helpers are not automatically public.
- Decide empty-sweep behavior and document input/output aliasing guarantees.
- Review every fitting, qualification and G/H/I result's semantic fields against
  the complete source inventory, not just its generated constructor declarations.
- Retain historical read-only archive fixtures and define supported schemas/migrations.
- Review numerical defaults separately; no physics or defaults change in this patch.
