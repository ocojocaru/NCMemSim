# Vendor-neutral simulated-data exchange - Phase R4

R4 provides a versioned JSON interchange contract and explicit conversion API.
It does not parse a proprietary TCAD export, establish external agreement, or
qualify experimental data. No external TCAD file was available. R5 [controlled comparison references](interoperability_comparison.md) preserve
positive, negative and unavailable outcomes; real comparisons require admitted exports and
review of their observable definitions and conditions.

## Owned source, data and mapping

`ncmemsim.interoperability` exports `InteroperabilitySource`,
`InteroperabilityDataset`, `ObservableMapping` and
`convert_interoperability_data`. All three contracts provide `to_dict()`,
`to_json()`, `from_dict()`, `from_json()` and `contract_hash`. JSON imports reject
unknown fields, duplicate keys, incompatible schema versions and nonfinite data.
Dictionaries returned by contracts are independent copies. The schema identifier
is `ncmemsim-interoperability-v1`. This is additive; package identity remains 1.8.0.

The source declares upstream file SHA-256, source identifier, simulator/version,
model declarations and citation. Its evidence kind is always `simulated`.
Synthetic generators must identify themselves and must not impersonate TCAD
measurements. The digest refers to the original upstream file, not the normalized
JSON contract. The API checks digest syntax; the importing adapter/reviewer must
verify it against upstream bytes. Hashes establish consistency, not authenticity.
Model declarations are finite nonempty JSON objects; completeness is reviewed,
not certified automatically.

Datasets own ordered named columns (`name`, `quantity`, `unit`, `values`). Every
column has the same positive number of finite numeric samples. Duplicate names,
booleans and nonfinite/overflowing numeric values are rejected. Original ordering,
original values, source and conditions remain in every conversion result.
Exclusions contain zero-based row indices and a nonempty reason, apply to the
whole row, and never remove values from the original dataset. Duplicate/out-of-range
exclusions fail. Excluding every row yields an unavailable result.

## Explicit conditions

All metadata keys below must be present. An unknown condition is JSON `null`,
which is retained. A known declaration is an object with exactly the listed keys;
each value is nonempty trimmed descriptive text. Include numeric units in that
text. These are reviewable declarations, not a geometry/PDE simulator schema.
Use an explicit justified description for a condition that is not applicable;
do not invent a numeric value for it.

| Metadata | Fields / domain |
|---|---|
| `geometry_materials` | `layers`, `contacts` |
| `contacts_bias` | `contact_voltages` |
| `temperature_K` | Positive finite temperature or null |
| `history` | `sweep_direction`, `prior_operations` |
| `initial_state` | `description` |
| `time_conditions` | `description` |
| `frequency_conditions` | `description` |
| `area_m2` | Positive finite area in square metres or null |
| `coordinates` | `origin`, `axis_direction`, `layer_order` |
| `potential_reference`, `energy_reference` | `description` |
| `electron_charge_sign` | `negative` or null |
| `applicability` | `scope`, `limitations` |
| `optical_conditions` | `sample_plane_spectrum`, `normalization`, `reflection`, `generation_assumptions`, `contributing_regions` |

Every conversion requires geometry/materials, contacts/bias, temperature, history,
initial state, time conditions, coordinates, electron sign and applicability.
Capacitance additionally requires frequency conditions; voltage observables require
a potential reference; optical transition/tunnelling barrier energies require an
energy reference. Optical transition energies also require optical conditions.
Area is required for an explicit total/per-area conversion. Missing applicable
conditions produce `status="unavailable"`, `values=null` and named
`missing_conditions`; they never become a passing comparison. A converted result
only means the declared transformation was computable, not physically applicable
or scientifically equivalent to another dataset.

## Dimensional and semantic conversion

A mapping binds the complete original dataset hash and a source column. It names
the target quantity/unit, integer sign (+1 or -1), offset in target units, area
operation and rationale. Every choice is explicit, including identity conversion.
Supported units are `1`, `m`, `nm`, `um`, `s`, `ms`, `us`, `V`, `mV`, `C`,
`C/m^2`, `F`, `F/m^2`, `A`, `A/m^2`, `eV` and `J`.
The joule/electronvolt relation uses the exact SI elementary charge
1.602176634e-19 C. No unit is inferred from magnitude or column labels.

Quantities distinguish position, time, gate voltage, potential, signed flat-band
shift, absolute threshold voltage, total charge, charge per area, small-signal
capacitance (total/per-area), compact capacitance readout, current (total/per-area),
optical transition energy, tunnelling barrier energy and occupation fraction.
A dimension match alone does not authorize semantic substitution. In particular,
signed flat-band shift cannot become absolute threshold voltage, small-signal
capacitance cannot become a compact readout, and optical transition energy cannot
become a tunnelling barrier.

`area_operation` is `none`, `divide_by_area` (total to density), or
`multiply_by_area` (density to total), only for charge, small-signal capacitance or
current. Offset is permitted only for position, time, potential or gate voltage.
No interpolation, sorting, smoothing, fitting, absolute value or implicit reference
shift occurs. Sign and offset change values without reordering samples; the
rationale must explain the target reference/convention. The explicit formula is:

`target = sign * original * source_unit_factor / target_unit_factor * area_factor + offset`

Finite checks reject overflow. Included indices preserve acquisition order.
The result contains original data, full mapping, both hashes, exclusions and
missing-condition accounting, with `experimental_qualification=false` and
`external_agreement=false`. These flags do not turn true through conversion.
The projection is a fresh JSON-compatible dictionary; strict R6 report/bundle
restoration is a separate milestone. Unknown external formats and unsupported
units need a reviewed adapter/contract extension rather than guessed mappings.

## CI and retained R3 experiment

CI and Documentation passed for R3 commit
`8c63a0a07a4eebd6273df75cc81da2711c87b765`. Its paired comparison job now checks
that immutable accepted commit against R2, retaining the original one-file-delta
guard. Adding R4 modules would otherwise invalidate that isolated experiment.
The job is explicitly historical: its result is not evidence about current-package
performance. Current tests, installed distributions and the R2 workload matrix
continue to check the current checkout. Historical R0/R2/R3 measurement audits and
published archives remain unchanged.
