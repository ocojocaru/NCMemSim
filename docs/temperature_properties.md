# Temperature-dependent material properties — Phase M

## M0 status and baseline

M0 is complete: code-temperature audit, selected property families, ownership,
scientific limits and staged acceptance contracts are frozen here. M4-M7 are
planned. M1 adds property contracts; M2 adds isolated thermal resolution and an
explicit simulator route. M0 itself
introduced no material law or runtime API.
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

M1-M3 are implemented on `dev/v1.4-temperature-properties`. Proceed to M4:
add bulk-Ge Gamma/L optical and electro-optical references, separating gap and
phonon controls and checking wavelength/photon accounting. The package keeps its
v1.3.0 release identity until a dedicated development/release identity change.


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
provide authenticity or prove experimental validity. M6 will add report-level
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
contracts; stored I/K/L workflow/report readers are unchanged. The Tran 300 K
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
acceptance rather than exporting a partial successful subset. M6 will cover
report-level restoration, export contracts and scientific evidence boundaries.
