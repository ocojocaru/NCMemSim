# Temperature-dependent material properties — Phase M

## M0 status and baseline

M0 is complete: code-temperature audit, selected property families, ownership,
scientific limits and staged acceptance contracts are frozen here. M1-M7 are
planned; no new material law or runtime API is implemented by M0.
The provisional release target is v1.4.0. Package/citation identity remains 1.3.0
at this planning checkpoint; v1.3.0 historical release evidence is retained.

Audit baseline: main commit `79c5d579d4a735ccd71f7c8fe5d02b77bb6b2f11`,
after the v1.3.0 release and DOI/test follow-up. The reproducible code audit is
[temperature_properties_audit.json](temperature_properties_audit.json).
Its 250/300/350 K diagnostic grid is ASSUMED and is not a validated material range.

## Existing behavior: audit before extension

| Owner | Existing temperature behavior | M0 conclusion |
|---|---|---|
| `device.py` | Device temperature defaults to 300 K; physical device input | Changing this scalar alone is not a material-property model |
| `electrostatics.py` | Fermi potential uses kT/q; `SemiconductorConfig` holds constant Si gap 1.12 eV and intrinsic density 1e16 m^-3 | Extend gap and intrinsic density together through an explicit opt-in context |
| `kinetics.py` | Charging factor E_charge/(kT) enters exp(-gamma) for r12 | Retain this dependence exactly once; separate it from material-law effects |
| `materials/base.py`, `models/gesn.py`, `database.py` | Electronic gaps, affinities, masses, permittivities and programming/erase barriers are scalar/composition values | Electronic gap changes must not implicitly change independent compact barriers |
| `materials/optics/models.py` | Gamma/L gap interpolation is composition-only; optical parameter temperature is descriptive; absorption temperature enters Bose-Einstein phonon occupation | Introduce explicit gap laws; reuse the existing phonon factor once |
| `materials/optics/near_edge.py` | 300 K is a reference condition; fitted A/Urbach parameters are not multi-temperature fits | Preserve this model/domain; do not claim its amplitude/tail is calibrated at other temperatures |
| `materials/optics/domain.py` | Validation checks composition and wavelength; temperature is a note | New thermal applicability must be checked separately, not inferred from legacy classification |
| `optics.py` | Low-level absorption accepts an optical model; incandescent source temperature describes the emitter; end-to-end evaluation is monochromatic | Emitter temperature is not device temperature; broadband work belongs to N |
| `simulator.py` | Occupancy receives device temperature; optical call constructs the default model unless explicitly integrated through a future path | M2 must introduce an explicit, reproducible optical-context route |
| `retention.py` | Retention runs the existing simulator; no independent thermal material law | Use the same resolved material/physics context for electrical and retention references |
| `dtco/binding.py` | DEVICE temperature binding already exists | Reuse the axis but resolve the full thermal context for each candidate |
| `workflows/application.py` | Existing I contexts store fixed optical configs and reject unsupported nondefault application | Add a separate explicit adapter/context; preserve stored I evidence readers |

The audit executes existing code: temperature metadata alone leaves Ge Gamma/L
gaps unchanged, explicit absorption temperature changes phonon occupation, and
device temperature changes the electrical/charging factors. These observations
are software behavior, not experimental validation of thermal material properties.

## Frozen property selection

| Property | First supported owner | Proposed law | Required qualification |
|---|---|---|---|
| Substrate electronic gap Eg(T), eV | Si `SemiconductorConfig` | Reference-anchored Varshni | Source-specific coefficients, bounds and baseline offset |
| Intrinsic carrier density ni(T), m^-3 | Si substrate | Gap-coupled relative nondegenerate density law | Declared DOS approximation, ionization/doping regime and inherited ni reference |
| Optical direct gap Eg_Gamma(T), eV | Unstrained bulk Ge first | Reference-anchored Varshni with its own Gamma coefficients | Independent source/valley identity; no substitution of the electronic scalar gap |
| Optical indirect gap Eg_L(T), eV | Unstrained bulk Ge first | Reference-anchored Varshni with its own L coefficients | Independent source/valley identity; existing phonon occupation retained |

These are the only new temperature-dependent property families selected for M.
GeSn can enter the same optical contracts only with an explicit composition-
and temperature-qualified profile. Ge coefficients are not automatically copied
to alpha-Sn endpoints or GeSn bowing. The legacy 300 K GeSn composition model
remains available; it does not establish a finite temperature-validation interval.

Permittivity, electron affinity, effective/tunnelling mass, capture efficiency,
phonon energy, absorption prefactors, Urbach width, trap density/cross section,
and programming/erase barriers remain constant unless another reviewed phase
introduces their laws. Strain, confinement, self-heating, thermal gradients,
time-dependent temperature, Arrhenius TAT/emission, freeze-out, degeneracy,
band-gap narrowing and broadband spectra are outside M's first implementation.

## Equations and source discipline

The empirical gap form is Eg(T)=E0-alpha*T^2/(T+beta), from
[Varshni (1967), DOI 10.1016/0031-8914(67)90062-6](https://doi.org/10.1016/0031-8914(67)90062-6).
The [primary paper](https://websrv.physik.uni-halle.de/F-Praktikum/PDF/Varshni_Temperature_dependence_of_the_energy_gap_in_semiconductors_1967.pdf)
also discusses imperfect low-temperature agreement and extrapolation limits.
M uses its reference-anchored equivalent, derived to recover the existing baseline:

\[
E_g(T)=E_{g,ref}-\alpha\left[\frac{T^2}{T+\beta}
-\frac{T_{ref}^2}{T_{ref}+\beta}\right].
\]

T, Tref and beta are in K; alpha is in eV/K; Eg is in eV. Initial Si/Ge
profiles require alpha >= 0 and beta > 0. Distinct Gamma/L coefficient records
are mandatory. Returning the stored value at T=Tref must recover it exactly.
The anchoring offset is DERIVED; the inherited baseline and literature slope
retain their separate provenance. It must not be described as a direct fit of
an entire experimental curve.

For the selected constant-DOS-mass, nondegenerate approximation, the planned
relative intrinsic-density relation is:

\[
\log\frac{n_i(T)}{n_{i,ref}}=\frac32\log\frac{T}{T_{ref}}
-\frac{E_g(T)}{2k_BT}+\frac{E_{g,ref}}{2k_BT_{ref}},
\]

with kB in eV/K. This ratio is a DERIVED compact approximation, not a new
absolute ni measurement. It must recover ni_ref exactly at the reference point.
Density-of-states/statistical assumptions and their limits are documented in
[NIST SP 400-85, EPROP](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication400-85.pdf).
That report includes more detailed statistical models; adopting this simpler
ratio does not inherit those models' accuracy or applicability.
[Thurmond (1975), DOI 10.1149/1.2134410](https://doi.org/10.1149/1.2134410)
is a coefficient/source-review lead for M1; its full parameter tables have not
been adopted by this planning step.

No numerical literature coefficient table or universal temperature interval is
approved in M0. M1 must trace each implemented profile to its equation/table,
material/valley, units and source range before calling it LITERATURE or
LITERATURE_FITTED. Synthetic profiles are explicitly ASSUMED with a declared
numerical domain. No temperature-calibration claim follows from a DOI, an
algebraic limit test or the legacy 300 K baseline.

## Contract and ownership rules

1. Introduce an opt-in module-qualified material-temperature contract, planned
   under `ncmemsim.materials.temperature`; proposed names are not stable API yet.
   It stores model/schema identity, material/valley/property target, law and units,
   coefficients, reference temperature/value, inclusive temperature bounds,
   composition/strain conditions, source/range evidence and parameter status.
2. Material resolution receives one finite positive device temperature for an
   isothermal run. Resolve substrate config and optical gaps/phonon temperature
   consistently; keep source-emitter temperature separate. Different requested
   material/optical temperatures are rejected unless a future reviewed contract
   explicitly supports nonequilibrium conditions.
3. Validate finite coefficients, reference inside bounds, positive evaluated gaps
   and densities, compatible composition and applicability before simulation.
   Reject values outside the declared domain; no hidden clipping or extrapolation.
   Doping/statistical applicability must be explicit for the Si ni adapter.
4. Resolve owned candidate objects/configurations from an immutable nominal
   snapshot. Do not mutate global presets, caller dictionaries, another point's
   material or physics context. Preserve original overrides and record unchanged
   parameters as well as every evaluated value and baseline hash.
5. Disabled mode preserves v1.3.0 behavior for every pre-existing input. Enabled
   mode at Tref recovers the chosen nominal config and optical point. Default
   reference is 300 K; other reference temperatures require explicit profiles.
6. Electronic and optical gaps remain separate targets. Gap evaluation does not
   rewrite affinity, tunnelling barriers, TAT parameters or fitted amplitudes.
   No subtraction/addition of a gap is applied to a compact barrier implicitly.
7. Maintain stored K/L and I workflow schemas/readers. Temperature is an existing
   DEVICE axis, not a new arbitrary MODEL binding. Thermal context IDs belong
   in separately versioned application/report contracts; reject unsupported
   combinations instead of silently treating them as legacy contexts.
8. Report all attempts, invalid-domain failures and denominators. Keep ASSUMED,
   DERIVED, FITTED and CALIBRATED distinctions. Reconstruction validates nested
   sources and recomputes derived projections; it does not rerun physics or fit.

## M1-M7 implementation sequence

| Stage | Deliverable | Acceptance |
|---|---|---|
| M1 | Typed gap/ni profiles, domain/provenance contracts and source-reviewed coefficient records | Finite units/inputs, exact anchors, independent equation/limit tests, negative domain cases; no implicit presets |
| M2 | Isolated temperature resolution and explicit electrical/optical evaluator contexts | Disabled/default identity, reference identity, no mutation, one temperature owner and strict context restoration |
| M3 | Si electrical/programming/retention reference | Compare legacy T-only, gap-only, ni-only and coupled cases; resolve contexts independently, bound timestep/conservation errors |
| M4 | Bulk-Ge Gamma/L optical and electro-optical reference | Separate gap-only and phonon-only controls, near-edge wavelength audit and photon accounting; preserve room-temperature GeSn reference limits |
| M5 | Deterministic/variability-aware DTCO integration on the existing temperature axis | Resolve each candidate, distinguish domain failure/metric failure/infeasibility, preserve scalar/Pareto denominators and K/L contracts |
| M6 | Source-linked reports and reproducibility bundles | Temperature/profiles/values/limits captured; strict nested readers, all-failed cases, deterministic export and tamper rejection |
| M7 | v1.4 compatibility and release gates | Full tests, strict docs, clean wheel/sdist, Python 3.11-3.13 exact-commit CI, final citation/tag/release checks |

M3 retention results represent the selected isothermal compact model, not a
universal lifetime acceleration law. M4 temperature shifts with held-constant
prefactors/tails are conditional model predictions, not independently calibrated
absorption curves. Numerical convergence and physical applicability are reported
separately. Temperature invalidity is retained in attempted-population failure
accounting, not removed to improve feasible fractions.

## Next action

Proceed to M1 on `dev/v1.4-temperature-properties`: define typed contracts and
review the first coefficient/range records. Freeze schemas and baseline recovery
before simulator integration. M0 itself changes documentation and audit evidence
only; release artifacts and v1.3.0 citation remain untouched.
