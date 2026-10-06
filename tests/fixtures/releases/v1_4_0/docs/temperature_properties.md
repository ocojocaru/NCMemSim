# Temperature-dependent material properties — Phase M

## M0 status and baseline

M0 is complete: code-temperature audit, selected property families, ownership,
scientific limits and staged acceptance contracts are frozen here. M1-M6 are
implemented. M7 is complete; v1.4.0 is published.
M0 itself introduced no material law or runtime API.
Published identity: `1.4.0`, citation date `2026-10-02`, DOI [10.5281/zenodo.23102549](https://doi.org/10.5281/zenodo.23102549). Historical evidence is retained.

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

M0-M7 are complete in published v1.4.0. Next: plan Phase N / v1.5 broadband spectra
and multilayer propagation against the roadmap; no Phase N runtime change is included here.


## M1 contracts and coefficient review

The additive API lives in `ncmemsim.materials.temperature`; existing material
presets and public aliases retain their behavior. M1 evaluates property contracts
only. It does not install profiles in `Device`, `Simulator` or optical models.

`AnchoredVarshniProfile` owns one material, gap target, Sn composition and reference
anchor. `IntrinsicDensityProfile` couples a Si substrate gap to its inherited ni
anchor. Both preserve the reference value exactly and reject out-of-domain inputs,
nonpositive gaps, nonfinite values and density underflow/overflow. A caller must
supply doping for each ni evaluation. The carrier contract records an explicit
nondegenerate, fully ionized, constant-DOS-mass approximation, doping bounds and a
minimum doping/ni ratio greater than one; these are declared assumptions, not an
automatic assessment of degeneracy or freeze-out. Construction checks the complete
temperature/doping rectangle at its limiting endpoints.

The reviewed rows below come from [Varshni (1967), Table I, p. 152](https://websrv.physik.uni-halle.de/F-Praktikum/PDF/Varshni_Temperature_dependence_of_the_energy_gap_in_semiconductors_1967.pdf),
[DOI 10.1016/0031-8914(67)90062-6](https://doi.org/10.1016/0031-8914(67)90062-6).

| Record | Table-I E0 (eV) | alpha (eV/K) | beta (K) |
|---|---:|---:|---:|
| Si substrate | 1.1557 | 7.021e-4 | 1108 |
| Ge optical Gamma (direct) | 0.8893 | 6.042e-4 | 398 |
| Ge optical L (indirect) | 0.7412 | 4.561e-4 | 210 |

The Si row uses an exciton-subtracted gap convention. E0 is recorded for source
traceability; the factory uses alpha/beta with the caller's explicit reference
gap, rather than replacing that reference with Table-I E0. These coefficients
are LITERATURE_FITTED; an anchored evaluation is DERIVED, and its inherited
reference may remain ASSUMED. This is an offset model, not a refit or calibration.

`profile_from_reviewed_record` accepts only these reviewed records and requires an
ASSUMED operating domain. The proposed 250-350 K diagnostic window is not a
certified range from Table I. GeSn requires a separately supplied composition-
qualified profile and evidence; no reviewed GeSn coefficient record is supplied.
A profile cannot be reused at a different Sn composition, even if both compositions
lie inside its declared domain. Strained profiles are rejected.

A complete source transcription and qualifications are stored in
[temperature_coefficients_review.json](temperature_coefficients_review.json).
The M0 audit remains historical evidence rather than being rewritten after M1.

```python
from ncmemsim.materials.provenance import ParameterStatus
from ncmemsim.materials.temperature import (
    ThermalEvidence, ThermalMaterial, TemperatureDomain,
    reviewed_varshni_coefficients, profile_from_reviewed_record,
)

assumption = ThermalEvidence(
    source="Inherited compact-model baseline",
    locator="Explicit user-selected numerical domain and 300 K anchor",
    status=ParameterStatus.ASSUMED,
    notes="Conditional diagnostic profile; no independent thermal calibration",
)
si_gap = profile_from_reviewed_record(
    reviewed_varshni_coefficients()[0], name="si-gap-diagnostic",
    domain=TemperatureDomain(ThermalMaterial.SILICON, 250, 350, 0, 0, assumption),
    reference_temperature_K=300, reference_gap_eV=1.12,
    reference_evidence=assumption,
)
assert si_gap.evaluate(300) == 1.12
assert si_gap.evaluate(350) < 1.12
assert type(si_gap).from_json(si_gap.to_json()).contract_hash == si_gap.contract_hash
```

Profile archives use `anchored-varshni-v1` and `relative-intrinsic-density-v1`.
Their units, schemas, nested applicability and evidence are validated on restore;
unknown/missing fields, duplicate JSON keys, nonfinite numbers and unsupported
calibration claims are rejected. Fresh dictionary projections do not share state
with the frozen profile. `contract_hash` hashes canonical JSON, including all
coefficients, anchors and evidence; it identifies a declared contract and does not
provide authenticity or prove experimental validity. M6 adds report-level
reconstruction and derived-value verification.


## M2 owned application contexts

The additive API is module-qualified under `ncmemsim.temperature_context`.
`ThermalContext.from_nominal` stores canonical JSON snapshots of the complete
nominal device, material/layer metadata, core physics and simulation defaults.
Optical attachments record parameter overrides and their reference conditions;
when omitted, the factory records explicit legacy default attachments for all
FGs. Supplying attachments requires exactly one per FG, including explicit legacy
controls. Sources and profiles retain separate M1 evidence.

The context is immutable. `resolve(temperature_K=...)` receives the single device
and material evaluation temperature and returns a `ResolvedThermalContext`.
It applies no profile when `enabled=False`; device temperature still enters
existing electrical/charging expressions. With enabled laws, each profile checks
its declared range, composition and statistics domain. Different component
reference temperatures and mismatched nominal anchors are rejected. The resolver
does not create a new MODEL axis or change existing DEVICE temperature bindings.

Each device/physics property access returns an independent owned object. Physics
reconstruction preserves the shared tunneling engine within that candidate,
without sharing it across candidates. Only the selected Si bandgap/intrinsic
density change; affinity, permittivity, masses, independent barriers, charge terms
and other core configurations retain their nominal overrides. No material
preset or caller dictionary is modified.

| Control | Updated values | Held reference/legacy values |
|---|---|---|
| Semiconductor LEGACY | Existing device kT factors | Gap and ni |
| GAP_ONLY | Si gap | ni |
| DENSITY_ONLY | ni evaluated from its gap-coupled law | Semiconductor gap |
| COUPLED | Si gap and coupled ni | Other semiconductor parameters |
| Optical LEGACY | None | Existing composition gaps and phonon temperature |
| GAPS_ONLY | Gamma/L gaps at device temperature | Phonon temperature |
| PHONONS_ONLY | Phonon occupation at device temperature | Gamma/L gaps |
| Optical COUPLED | Gamma/L gaps and phonon occupation | Prefactors, phonon energy, tail width/amplitude |

Gaps-only, density-only and phonons-only are declared diagnostic controls; held
values do not introduce an independently requested material temperature. Every
active optical control requires both valley profiles and checks their domain,
even when the profiles supply only the applicability limit for a phonons-only
control. GeSn needs independently supplied composition-qualified profiles.
Active optical attachments accept declared `GeModel`/`GeSnModel` materials;
arbitrary chemical material identities cannot inherit Ge thermal laws.

`resolution.create_simulator()` builds an owned `ThermalSimulator`. The original
`Simulator` constructor and public methods retain their signatures. Its new
private optical hook delegates to the same legacy function by default; the
thermal adapter supplies each FG's explicit resolved model. Existing optical
absorption components are reused, including one Bose-Einstein factor. At the
reference point the complete optical point and transient numerical result recover
the nominal model. Source-emitter temperature stays separate from device
temperature. `resolution.optical_model("FG1")` exposes the same owned evaluator
for low-level optical audits.

The thermal simulator checks device, physics and simulation defaults before each
relaxation; changing temperature, doping, composition, metadata or other inputs
requires a new resolution. It can be passed directly to existing electrical,
electro-optical and retention solvers. Operating arguments such as pulses,
wavelengths, photo configurations and dwell-time overrides remain explicit run
inputs; the M2 context archive does not by itself archive an operating protocol,
photo configuration, fitted workflow, output history or scientific validation.

M2 supports the exact core physics configurations already represented by the
existing typed snapshot/reconstruction helpers. Runtime subclasses/callbacks,
advanced transport engines and near-edge optical runtime models are rejected,
rather than partially serialized. Their future combinations need explicit
contracts; M5 now provides a separate explicit thermal/MODEL composition below.
Stored I/K/L workflow/report readers are unchanged. The Tran 300 K
near-edge fit is not relabeled as a thermal fit.

```python
from ncmemsim import DeviceBuilder, DeviceState
from ncmemsim.temperature_context import ThermalContext, SemiconductorThermalMode

# si_gap is the explicitly qualified M1 profile constructed above.
nominal = DeviceBuilder.v2(1)
thermal = ThermalContext.from_nominal(
    nominal, enabled=True,
    semiconductor_mode=SemiconductorThermalMode.GAP_ONLY,
    substrate_gap=si_gap,
)
resolved = thermal.resolve(temperature_K=350)
simulator = resolved.create_simulator()
state = DeviceState.empty_for_device(simulator.device)
result = simulator.relax_voltage(state, 2.0, dwell_time_s=1e-6, internal_dt_s=1e-6)
assert nominal.temperature_K == 300
assert simulator.device.temperature_K == 350
assert type(resolved).from_json(resolved.to_json()).context_hash == resolved.context_hash
```

`thermal-context-v1` records the nominal definitions and selected laws.
`resolved-thermal-context-v1` additionally records nominal/source hashes and every
resolved device, physics and optical projection. Readers validate nested source
contracts and reconstruct the projection; tampered evaluated values, unchanged
parameters, unknown/missing fields, duplicate JSON keys, nonfinite values and
hash mismatches are rejected. A coherent new source is a new declared context;
a content hash does not establish experimental validity or authenticity.


## M3 controlled Si program/read and zero-bias retention

The standalone reference `examples/phase_m3_si_temperature_reference.py` runs
12 independently resolved cases: 250/300/350 K times LEGACY, GAP_ONLY,
DENSITY_ONLY and COUPLED semiconductor modes. The device has a Si substrate and
one Ge nanocrystal FG; the Ge material itself receives no thermal gap change in
M3, and no optical source is used. The 250-350 K diagnostic domain and compact
carrier assumptions remain ASSUMED. The Si coefficients retain their M1 source
status and their exact inherited 300 K gap/ni anchors.

The deliberately synthetic nominal device uses 3 nm tunnel SiO2, a 6 nm FG,
7 spatial cells, 0.2 NC volume fraction, 0.1 active fraction and equal 0.65 eV
program/erase barriers. Kinetic attempt frequencies are 1e7/5e7/3e7 Hz for
nu0/nu1/nu2. These choices provide a measurable numerical response; they are not
experimental device/process inputs. Every source context includes the complete
nominal materials, physics configurations and unchanged parameters. Default WKB
quadrature remains 160 points; spatial/quadrature convergence is not claimed by
the timestep audit.

Program/read uses a 3 V pulse lasting 5e-7 s followed by a zero-dwell 0 V read.
The zero-dwell read preserves probabilities within floating-point roundoff.
Retention uses the same owned thermal context and the programmed state, with
0 V external gate bias for 1e-3 s, backward Euler and quasi-equilibrium stopping
disabled. Zero external voltage does not eliminate built-in or charge-dependent
fields. Both injection and emission remain active in the compact model. These
results are conditional short-time model behavior, not a universal retention
lifetime or an Arrhenius acceleration law.

The exported `reference.json` records all 12 source/resolved contexts, protocols,
thermal values, Fermi/flatband quantities, states and charge/occupation histories.
Three disabled-profile controls and three original-Simulator controls provide an
independent legacy comparison. At 300 K all four enabled modes recover the same
observations. Content hashes are reproducible in the recorded Python/NumPy
runtime; bitwise portability across arbitrary runtimes is not asserted.

Numerical acceptance is checked separately from applicability:

- Program and retention endpoint probabilities are compared for 64/128/256
  steps. The finest pair must differ by at most 2e-3 per probability component.
  Retention output grids depend on the first timestep, so this compares common
  final endpoints rather than falsely aligning intermediate arrays.
- Each thermal program shift is also compared against its same-temperature
  legacy control at matching step counts. The finest-pair contrast variation
  must be below 1e-5 V; this separates small thermal contrasts from common
  discretization error.
- Probability mass error is bounded by 1e-12. An independent per-step reservoir
  budget integrates program pre-step Euler flux and retention post-step implicit
  flux with frozen pre-step rates. Its relative charge residual is bounded by
  1e-10. Uniform-step retention is independently compared with the existing
  output-aligned RetentionSolver endpoint.

The existing charge convention is explicitly preserved:
`QFG = q * sum(n_eff * dx * 0.5 * (P1 + 2*P2))`.
The budget uses the same half factor; it audits the stored compact-model charge
rather than silently changing the meaning of microscopic electron counts.
Charge in an open FG is not required to be constant. The audit also records the
unclipped explicit-Euler trial probabilities: a deliberately unsafe step can
produce normalized output while violating the reservoir budget, and is rejected.

Run from the repository with the package available in the environment:

```bash
python examples/phase_m3_si_temperature_reference.py --output results/m3-si
```

The JSON is standalone numerical evidence with a content hash, not a new strict
report reader or M6 reproducibility bundle. Validation aborts on failed numerical
acceptance rather than exporting a partial successful subset. M6 covers
report-level restoration, export contracts and scientific evidence boundaries.


## M4 controlled bulk-Ge optical and electro-optical reference

`examples/phase_m4_ge_temperature_reference.py` applies the reviewed M1 bulk-Ge
Gamma/L gap coefficients to the inherited 300 K anchors (0.7985/0.664 eV).
The 250/300/350 K window is an explicit numerical assumption. The material is
unstrained bulk Ge used in a compact NC layer; confinement and strain are absent.
The Si substrate stays in legacy mode, with its existing device-temperature kT.

Four independently resolved controls hold gaps and phonon populations at the
reference temperature, change gaps only, change phonons only, or change both.
Direct/indirect amplitudes, Urbach energy/amplitude, phonon energy, geometry,
barriers and capture efficiency remain constant. Thus the thermal absorption
curves are conditional derived predictions, not experimentally calibrated spectra.
The existing indirect absorption law includes the Bose population once.

The monochromatic wavelength audit uses 1450, 1500, 1550, 1600, 1700, 1800,
1850, 1900, 2000 and 2200 nm, covering both moving band edges. Each wavelength
is evaluated independently; this is neither a spectrum integral nor sequential
multilayer propagation. The effective absorption is volume fraction times NC
absorption and the Beer-Lambert photon budget is incident = absorbed + transmitted.
No reflection or scattering is introduced.

Illuminated programming uses 1550 and 1850 nm, a 3 V pulse for 1 microsecond,
1e6 W/m2 monochromatic power, an assumed capture efficiency of 0.1 and default
loading weights. These are synthetic diagnostic conditions. The 0 V read is dark
and has zero dwell. Each illuminated result is paired with a dark run at the same
T and timestep; disabled thermal contexts and the original Simulator recover
legacy results. Zero capture efficiency recovers the dark charge shift.

The 32/64/128-step refinement bounds the finest endpoint probability difference
by 2e-3 and the change in light-minus-dark flatband contrast by 1e-5 V. Probability
mass and read changes are bounded by 1e-12; photon-budget relative error by 1e-12.
Absorbed photon generation is converted to rate per physical NC and multiplied
once by capture efficiency. Absorbed photons are not equated with stored charge:
state-dependent transition weights, active fraction and the existing normalized
charge convention remain distinct.

A separate `GeSnNearEdgeReferenceModel` audit records its existing 300 K
composition/wavelength classifications, including out-of-domain probes. It is
not the thermal optical evaluator; bulk-Ge coefficients are not copied to GeSn
and its room-temperature fit does not qualify any multi-temperature curve.

```bash
python examples/phase_m4_ge_temperature_reference.py --output results/m4-ge
```

The output records complete contexts, resolutions, protocols, assumptions,
all twelve cases and numerical controls with a content hash. Numerical acceptance
must pass before export. This is standalone evidence; strict report restoration
and reproducibility bundles are provided by the separate M6 contracts below.


## M5 thermal DTCO and MODEL integration

The additive module `ncmemsim.thermal_dtco` resolves existing DEVICE candidates
through `resolve_thermal_candidate(template, candidate_device, model_context=...)`.
It rebuilds a nominal context using the candidate device and the template's
reference physics, simulation defaults and fixed profiles, then evaluates the
single candidate device temperature. Geometry and doping changes are retained;
profile composition/domain incompatibility fails rather than being repaired.
No MODEL temperature axis or independent material temperature is introduced.

`ThermalCandidateResolution` is an immutable, separately versioned
`thermal-dtco-candidate-v1` envelope containing the complete M2 thermal resolution
and optional L transport context with both identities. Its strict reader restores
and validates source/derived content; it neither converts nor changes older M2,
K or L schemas. Operating protocols and full report restoration use the M6 contracts below.
`create_simulator()` returns the existing thermal simulator when MODEL is absent,
or an owned `ThermalModelSimulator` when the explicit transport context is given.

The MODEL path restores the declared TAT/image-force attachments, requires known
inter-FG link targets and reconstructs the advanced engine over the exact owned
core baseline. Core settings and shared tunneling identity remain validated.
Each relaxation checks device, physics, defaults and attachment configuration
for drift. Runtime engine callbacks/subclasses are not accepted as archived
implementations. A failed optional mechanism raises an execution error; zeroing
a failed contribution is never reported as a successful thermal MODEL run.
This explicit fail-fast policy is limited to the new M5 composition.

`ThermalCandidateError` denotes incompatible candidate/context/model inputs;
`ThermalDomainError` denotes failure to evaluate the declared thermal domain.
Existing sweep and MODEL executors retain ordinary execution failures and their
error types. Metric extraction failures stay in the existing analysis category,
and valid numerical samples that violate constraints remain infeasible. None
are discarded or relabeled as calibrated evidence. Coverage/pass fractions keep
attempted denominators; feasibility fractions and statistics keep assessed
complete-case denominators, including undefined results for empty populations.

`examples/phase_m5_thermal_dtco_reference.py` uses the existing DEVICE binding
`("temperature_K",)` with 250/300/350/400 K. The last point deliberately falls
outside the declared 250-350 K profile window. The deterministic path uses the
nominal TAT density; the MODEL path stores eight paired, seeded lognormal draws
per temperature. All densities and image-force assumptions remain those of the
synthetic L3 reference. Their parameters have no added temperature law: the
resolved Si properties affect the initial electrostatic field, while the optical
Gamma/L/phonon controls determine the independent FG1 1550 nm absorption metric.

The transport diagnostic is closed inter-FG redistribution for 4e-14 s with a
fixed initial field at 4 V and zero sheet charge. It is not a self-consistent
retention or illuminated programming experiment. Nominal/minimum/maximum density
runs at each successful temperature audit 16 versus 32 steps, occupation error
below 1e-3, charge conservation below 1e-12 and absence of transfer clamping.
The illustrative absorption constraint is alpha >= 1e5 m^-1. Deterministic
objectives maximize absorption and minimize nominal TAT rate; population
objectives maximize mean absorption and minimize TAT-rate standard deviation.
Only candidates with complete coverage and every sample passing are ranked.
These objectives are diagnostic choices, not a calibrated technology optimum;
eight draws do not demonstrate tail or sampling convergence or process yield.

```bash
python examples/phase_m5_thermal_dtco_reference.py --output results/m5-thermal-dtco
```

The evidence records the template, resolved candidates, explicit model inputs,
stored draws, source-linked deterministic/population analyses, exact Pareto
projection and numerical audits. A content hash identifies the standalone JSON;
strict source-linked restoration and bundles are provided by M6 below.

## M6 thermal reports and reproducibility bundles

The additive module `ncmemsim.thermal_reporting` exports `ThermalRunEvidence`,
`build_thermal_run_evidence`, `ThermalReportStudy`, `ThermalReport`,
`build_thermal_report`, `write_thermal_report` and `load_thermal_report_bundle`.
The new `thermal-run-evidence-v1`, `thermal-report-study-v1`, `thermal-report-v1`
and `thermal-report-bundle-v1` contracts leave earlier I/K/L/M2 archives intact.

A run source records the complete nominal template, candidate device, optional
transport context, initial `DeviceState` (including all occupation arrays),
explicit protocol/settings, runtime, resolved thermal candidate and stored
observations or typed failure. Omitting the initial state explicitly archives
an empty state; it does not infer an earlier state from results. Workflow kinds
are `program_pulse_read`, `electro_optical_program_pulse_read`, `retention` and
`fixed_field_redistribution`. Electrical/optical protocols and photo-capture
configuration are restored through their existing contracts. Retention settings
and initial probability mass are checked. The builder records evidence; it does
not execute a workflow. Observations must be finite JSON objects.

`ThermalReportStudy` supports `run`, `deterministic_dtco` and `model_dtco` sources.
The DTCO adapter is restricted to the existing DEVICE design axes and requires
explicit thermal template/model settings and candidate-linked outputs. Readers
restore each stored MODEL realization from its stored sample values, compare
candidate/model identities, reevaluate thermal inputs and rebuild metrics,
constraints, population statistics and Pareto projections from stored outputs.
They do not execute transport, program/read or retention, and do not draw new
random samples. Each attempted candidate remains represented, including domain
and extraction failures, infeasible results and entirely failed populations.
Attempted/assessed denominators retain the K/L distinction; empty statistics
and conditional fractions remain undefined rather than being assigned zero.

A report requires explicit scientific limitations and always declares
`conditional-unqualified-simulation`. Its JSON retains authoritative nested
sources, temperatures, full profiles with provenance/domains, resolved values,
protocols, runtime and failures. Markdown and CSV are derived projections.
The bundle contains exactly `report.json`, `report.md`, `attempts.csv`,
`statistics.csv`, `designs.csv` and `bundle.json`. The manifest hashes all five
payload files. Loading checks complete membership, regular files, strict JSON,
nested identities and rebuilt projections; coherently rehashing a changed CSV
or Markdown file does not make it acceptable. Repeated exports are byte-identical
for the same source. Writing requires a new destination and rolls back files
created by an interrupted export.

```bash
python examples/phase_m6_thermal_report.py --input results/m5-thermal-dtco/reference.json --output results/m6-thermal-report
```

This example converts the stored M5 reference into deterministic and paired
MODEL studies, retaining all four deterministic attempts and all 32 population
attempts. The paired draws and timestep audits are retained as declared evidence;
restoration does not independently reproduce the numerical refinement experiment.
M3/M4-style program/read and retention runs can be recorded through the explicit
run-source API; their earlier standalone reference JSON formats are not silently
upgraded into this new source contract.

Content hashes detect inconsistent edits, not authorship or authenticity.
Stored observations are authoritative inputs to analysis, not independently
verified solver trajectories or measurements. A consistently replaced source
with its rebuilt analyses represents different evidence. Nothing in this report
qualifies temperature coefficients, process yield or experimental calibration.
The M7 package and citation describe published 1.4.0, dated 2026-10-02.
Publication evidence is recorded in the release checklist; the DOI is [10.5281/zenodo.23102549](https://doi.org/10.5281/zenodo.23102549).

## M7 candidate review and release gates

The reviewed additive surface is `v1_4_api_review.json`, checked by
`python scripts/validate_v1_4_api_review.py`. It records four thermal modules,
the retained Simulator contract, stable paths/ensemble exports, coefficient and
scope evidence, historical v1.3 identity snapshots and a frozen thermal report.
Existing MODEL contracts and earlier historical JSON evidence remain pinned.
The source API inventory and reviewed contracts must agree before CI proceeds.

The distribution gate restores the frozen report with all-failed deterministic
and MODEL populations, checks 300 K anchors and rejected out-of-domain requests,
and re-exports byte-identical bundles from independently installed wheel/sdist.
Its probe forbids solver execution and new RNG draws during restoration. Local
Windows checks do not substitute for the remote Python 3.11-3.13 matrix.

See [v1.4 release checklist](v1_4_release_checklist.md) for verified
exact-commit PR/main/tag checks, release publication and the author-confirmed DOI.

Final identity is checked by `python scripts/validate_v1_4_release_identity.py`.
Preparation CI passed on `dc79dd625ead691c9c3c3512ed8eebbb4a641b53`; this evidence
belongs to the development preparation and does not approve the later final candidate.
