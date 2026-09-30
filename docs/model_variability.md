# Model and trap-assisted transport variability

## L0 status and baseline

Planning baseline: published v1.2.0, commit b9d2ff77136217af5b3b5a4b5a4780af5d75d6d5.
Target release: v1.3.0. This document establishes the L0 planning contract;
L1 contracts are implemented; L2-L7 are pending. No MODEL binding or new runtime API is implemented by L0.
The package remains 1.2.0 until a separate development-cycle bootstrap.

## Scientific objective and first executable scope

Extend Phase K realization to explicitly selected MODEL inputs owned by the
existing advanced transport configuration. The first supported quantity will
be TrapSpecies.density_m3, in m^-3, finite and non-negative, addressed through
an explicit transport-link and trap-species identity. L1 freezes the binding path as
`advanced_transport / attachments / <link_id> / species / <species_name> / density_m3`
with `BindingScope.MODEL`. Exact names, rather than positional indices, identify targets.
Duplicate or ambiguous identities, conflicting assignments and unsupported
model paths must fail explicitly. Arbitrary attribute mutation is excluded.

Trap energy, capture cross section, barrier parameters and attempt frequency
remain later candidates, not promised L1 capabilities. Synthetic density
distributions are assumptions, not experimentally established defect populations.
No new transport equation, atomistic defects, kinetic Monte Carlo, spatial
percolation, fabrication-yield prediction or automatic distribution fitting is
included. Hierarchical uncertainty is a separate future contract.

## Compatibility and ownership

- Preserve the stable v1.2 imports, deterministic behavior, defaults, archive
  readers, DTCO, Robust DTCO and calibration semantics.
- Stochastic model application is explicit and opt-in. Existing MODEL rejection
  stays intact until the reviewed additive implementation is available.
- Reconstruct and validate immutable model configuration for each realization;
  never mutate the nominal device, transport configuration or other samples.
- Preserve direct/TAT mechanism decomposition and existing failure semantics.
- Reuse Phase K distributions, RNG and correlation rules. Do not introduce a
  second sampler or silently resample, clip or discard invalid realizations.
- Constant nominal assignments must recover the nominal workflow within its
  existing exact or declared numerical tolerance. Disabled TAT must preserve
  the existing direct baseline. Zero-density cases follow the existing TAT
  validation rules; they must not be forced through an invalid enabled spec.

## Identity, archives and accounting

Record the nominal and realized transport-configuration identities, ordered
bindings, sample identity, distribution and dependence provenance, model
version and enabled mechanisms. L1 introduces separate versioned definition contracts; L2 must review its
execution/result schema independently. Existing Phase K payloads and
hashes retain their meaning; old archives must not acquire inferred MODEL data.
Round-trip readers must reject unknown fields and unsupported versions under
the existing archival policy.

Configuration failures remain distinct from numerical execution failures,
metric extraction failures and physical infeasibility. Reuse existing failure
stages where their meaning applies; review any additional stage explicitly.
Every attempted realization remains in population counts and report evidence.
Keep simulated_pass_fraction, ensemble_feasibility_fraction and their current
denominators. No manufacturing yield or experimental calibration is claimed.

## Delivery sequence and acceptance

| Step | Deliverable | Acceptance |
|---|---|---|
| L0 | Scope, invariants, ownership and delivery plan | Documented v1.2 baseline; no runtime change |
| L1 | Density binding, typed ownership and identity contracts | Unambiguous link/species addressing; units/domains; round trips; compatibility decision |
| L2 | Isolated model realization and execution integration | Nominal and sibling inputs unchanged; invalid configurations isolated; model hashes retained |
| L3 | Controlled density-variability transport reference | Real solver; nominal/constant/disabled-mechanism limits; direct/TAT diagnostics |
| L4 | Phase K statistics and failure integration | Exact counts/denominators; all-failed and mixed-result cases; no silent exclusions |
| L5 | Variability-aware DTCO reference | Explicit design linkage; eligibility and transparent Pareto objectives |
| L6 | Integrity-checked reports and reproducibility | Nested identities checked; complete attempted population; deterministic rebuilds; no overwrite |
| L7 | Compatibility review and release | Regression, strict docs, clean wheel/sdist, Python 3.11-3.13 CI, exact-commit docs/tag/release checks |

The first density reference must declare its distribution, seed, sample count,
nominal TAT configuration, protocol, observable, units and numerical tolerances.
Select numerical values from the existing validated J references during L3;
do not invent a process distribution. Audit timestep sensitivity and sample-size
limitations before interpreting tails. Density and capture cross section can
be structurally confounded; a density-only study fixes cross section explicitly
and cannot establish independent experimental identifiability of both.

## Immediate L1 preparation

1. Audit ensemble/realization.py, ensemble execution/specification, transport/
   integration.py, transport/traps.py and DTCO binding contracts.
2. Freeze the smallest density-only binding and model-context serialization.
3. Define focused checks for ambiguous targets, domain and enabled-spec
   validation, input isolation, zero variation, old archives and failure counts.
4. Implement contracts before model execution; keep L2-L6 incremental.

Historical v1.0/v1.1/v1.2 evidence remains historical. Candidate checks must be
rerun on the final v1.3 identity; L0 does not approve a release.

## L1 implemented contracts

The provisional module `ncmemsim.ensemble.model_contracts` provides
`trap_density_binding`, `TrapDensityVariable`, `TransportModelContext` and
`ModelVariabilitySpec`. These module-qualified paths are development contracts;
they are not added to the 59 frozen v1.2 package exports or declared stable by L1.

The new schemas are `trap-density-variable-v1`, `transport-model-context-v1`
and `model-variability-spec-v1`. Strict dictionary readers reconstruct nested
TAT species, specifications and image-force corrections, reject unknown fields
and unsupported versions, and recompute canonical identities from actual data.
Hash properties are derived identities; `from_dict` does not authenticate an
archive or validate an external claimed digest. Transport declaration order is
identity-significant, matching the existing AdvancedTransportSpec contract.

TransportModelContext owns the complete AdvancedTransportSpec attachment map,
including mechanism enablement, equation family, species and barrier-correction
provenance. It is not a complete PhysicsModel or engine configuration. L2 must
link the remaining workflow physics/engine inputs explicitly before execution.
ModelVariabilitySpec binds this context to a complete device-definition hash,
an optional supported operating-protocol identity and an ordered variable list.
It accepts density variables together with existing DEVICE/OPERATING variables,
requires at least one density variable, and rejects unknown targets, duplicate
names/bindings, nominal/context mismatches and invalid physical domains.

Phase K StochasticVariable, EnsembleSpec, samplers and executors remain unchanged
and do not accept the new MODEL definitions. L1 neither draws samples nor applies
densities to a model. No zero-variation solver equivalence is claimed until L2/L3.

```python
from ncmemsim.ensemble.model_contracts import trap_density_binding

binding = trap_density_binding("declared-link-id", "declared-trap-species")
assert binding.path[-1] == "density_m3"
```

L1 tests cover strict nested round trips, physical units/domains, target
resolution, identity sensitivity, immutable source ownership, disabled/zero-density
rules and preserved Phase K rejection/archival boundaries. The current source API
inventory is regenerated for the additive module; historical stable proposals,
release reviews, release evidence and package version remain unchanged.
