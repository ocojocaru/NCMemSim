# Broadband spectra and sequential multilayer optics

## N0 status and baseline

N0 is complete: source/code audit, scope, units, integration boundaries and
N1-N7 acceptance sequence are defined here. N1 spectral contracts and N2 single-layer absorption are implemented; N3-N7 are planned.
Target release: v1.5.0. Current published package/citation remain v1.4.0;
the v1.4 DOI and immutable release identities are retained.
Audit baseline: `7bf9096de2148201ab301376ce1baac786a06e08` (M7 DOI follow-up).
The machine-readable audit is [broadband_optics_audit.json](broadband_optics_audit.json).
N0 changed planning only. N1 adds a separate opt-in source contract module;
no existing source, simulator default or archive schema changes.

## Existing behavior and integration boundaries

| Source | Audited behavior | Phase N consequence |
|---|---|---|
| `ncmemsim/optics.py` | LED/laser photon energy and flux; incandescent metadata; end-to-end evaluator rejects non-monochromatic sources | Add explicit spectral contracts; an incandescent constructor is not broadband execution |
| `ncmemsim/optics.py` | Beer-Lambert absorption and first-order volume-fraction alpha, transparent matrix and no scattering | Retain this compact law and identify every layer assumption |
| `ncmemsim/simulator.py` | Each FG is evaluated with the same source; no transmitted-source handoff | Separate new sequential stack mode from legacy independent-FG illumination |
| `ncmemsim/materials/optics/models.py` | Wavelength-dependent optical models and per-point provenance | Resolve a model per layer, retain domains and channel decomposition |
| `ncmemsim/photo.py` | Converts absorbed-photon evidence to NC photo-transition rates | Absorption is not stored charge or unit quantum efficiency; retain capture settings |
| `ncmemsim/temperature_context.py` | Owned, layer-specific thermal optical models; explicit device temperature | Reuse resolved models without replacing M laws or confusing emitter/device temperature |
| `ncmemsim/workflows/application.py` | Existing applied optical protocols require monochromatic sources | Introduce an additive context/protocol; keep historical I/K/L/M readers intact |
| `ncmemsim/device.py` | Device layer sequence and floating-gate selection | Store illumination direction and explicit ordered optical path; FG enumeration alone does not establish incident direction |

## Frozen scope

Deliver tabulated incident spectra, explicit normalization, integrated absorption,
sequential attenuation through an ordered compact stack, opt-in electro-optical
integration and reproducible multispectral references. Support one to three FGs
within the existing device family. Source spectra may be measured inputs, but
input provenance alone does not qualify simulated device response as CALIBRATED.

For v1.5, propagation is normal-incidence, single-pass incoherent Beer-Lambert.
Every traversed layer has a named identity, thickness, model/domain and explicit
absorption treatment. An assumed-transparent dielectric has alpha zero recorded
as ASSUMED; unsupported materials are rejected unless explicitly declared
transparent. Absorption in passive layers is an optical loss, not an NC capture
source. Existing NC volume-fraction scaling remains a compact assumption.

Reflection/Fresnel losses, interference/transfer matrices, scattering,
polarization/oblique incidence, coherent fields, new effective-medium laws,
strain/confinement and nonlinear/state-dependent absorption are outside N.
Do not describe this approximation as complete electromagnetic stack propagation.
Thermal changes reuse M's declared laws; no new GeSn thermal law is implied.
Independent calibration belongs to P and requires qualified data/holdouts.

## Source and units contract for N1

- Canonical coordinate: positive strictly increasing vacuum wavelength in nm.
  Spectral irradiance: finite nonnegative W m^-2 nm^-1. Integrated irradiance:
  W m^-2. Distinguish node densities, integrated bins and discrete line powers.
  A one-line monochromatic source uses integrated power, never a one-node density.
- Absolute measured spectra retain acquisition units, coordinate type, detector
  bandwidth/resolution, source/file digest, transformations, uncertainties when
  supplied and the measured support. Unknown uncertainty is recorded as unknown.
  Relative shapes require an explicit target in-band irradiance; normalization
  cannot silently turn absolute measurements into relative inputs.
- Initial implementation accepts wavelength-density tables and discrete lines.
  Frequency/energy densities require a separately tested Jacobian adapter before
  acceptance; changing the horizontal axis alone is invalid. No implicit adapter.
- Store support, quadrature/interpolation policy and units with source identity.
  Use piecewise-linear node density and trapezoidal wavelength integration as
  the initial declared power-integration policy. N1 computes the photon moment
exactly for that same piecewise-linear density, rather than applying a second
trapezoid approximation to wavelength times density. No extrapolation, silent sorting,
  duplicate coordinates, missing-value repair or hidden clipping.
- Reject invalid dimensions, NaN/Inf, negative values, duplicate/nonordered
  wavelengths and unsupported coordinate units. Explicit dark spectra/disabled
  sources return zeros; normalizing a zero-integral relative shape is an error.
- Incandescent emission may be an explicitly normalized Planck shape with
  emitter temperature and finite wavelength support. In-band irradiance is not
  bolometric irradiance; record captured-support assumptions. This temperature
  is distinct from the device/material temperature.

## Integration and conservation contract for N2-N3

For wavelength density S(lambda) in W m^-2 nm^-1, integrate over d lambda in nm.
Use lambda in metres in photon energy hc/lambda. The spectral photon density is
S(lambda) * lambda_m/(hc), in photons m^-2 s^-1 nm^-1. Integrate this quantity
directly; integrated power divided by a mean photon energy is not the contract.

For each ordered layer i, evaluate alpha_i(lambda) in m^-1 and thickness d_i
in metres. Transmission is exp(-alpha_i*d_i); absorbed fraction uses the stable
`-expm1(-alpha_i*d_i)` expression. Only transmitted spectral irradiance becomes
the next layer's incident spectrum. Store incoming, absorbed and outgoing power
and photon flux per layer, plus model provenance and numerical policy.

Require at every wavelength and after integration:
incident = sum(layer absorption) + final transmission, separately for power and
photons, within declared floating-point tolerances. No reflection term is present
in this scope. No FG receives the original source twice in sequential mode.
Use explicit path ordering/direction, including passive losses. With transparent
layers the result reduces to the shorter path; zero thickness/alpha is identity.
The incident source and nominal material/context objects must remain unchanged.

## Numerical and scientific acceptance

Recover the existing single-FG monochromatic evaluator using discrete lines and
the same model/settings. Recover independent-FG results only in explicit legacy
mode; sequential illumination is an opt-in physical change for multiple FGs.
Test analytical constant-alpha cases, transparent/opaque limits, zero input and
order dependence for unequal layers. Preserve per-channel provenance while
preventing double-counting channel totals and layer-absorbed energy.

Use at least three nested spectral grids on the same support, adding explicit
nodes at known material thresholds. Set observable-specific convergence targets
before running each reference; record grids, residuals and failures. Distinguish
quadrature error from measured sampling resolution, finite spectral support and
material-model uncertainty. Refining interpolated measured data adds no measured
information. Unknown model domains cannot be described as qualified coverage.
Audit pulse timestep convergence, charge/photon bookkeeping, capture constraints
and conservation independently when optical evidence drives electrical dynamics.

## N1-N7 implementation sequence

| Stage | Deliverable | Acceptance gate |
|---|---|---|
| N1 | Immutable tabulated/line spectral sources, units, normalization, provenance and strict readers | Invalid inputs rejected; units and integrals reproducible; absolute/relative/dark cases; no API/default changes |
| N2 | Single-layer spectral absorption and integration | Monochromatic limit, analytical power/photon balance, model domain failures and grid convergence |
| N3 | Ordered single-pass stack propagation | Explicit direction/layer identities/passive losses; per-layer and whole-stack balances; no repeated incident power |
| N4 | Opt-in simulator/thermal/workflow adapter | Legacy results preserved; owned layer models; spectral-to-NC transition mapping and pulse conservation audited |
| N5 | Controlled broadband/electro-optical and multispectral reference | One/two/three-FG controls, fixed-source comparisons, temperature/source separation, spectral and timestep convergence; diagnostic assumptions labelled |
| N6 | Strict source-linked spectral/stack reports and bundles | Complete source/path/settings/observations/failures, deterministic export, tamper rejection and no workflow/RNG replay; prior archives retained |
| N7 | v1.5 API/compatibility/release gates | Full regression, docs, wheel/sdist, Python 3.11-3.13 exact-commit CI, citation/tag/release evidence; actual DOI after deposit |

N5 must include deliberate unsupported-domain and invalid-path cases. If DTCO or
MODEL composition is included, retain attempted-population denominators, typed
failures and paired source/sample identities; do not imply calibration or yield.
Public names/schema identifiers will be reviewed during N1/N6, not promised here.

## Next action

N0 branch CI and Documentation passed on `e0d382d16f3f8bba3c2cfd8bd52509021312a157`.
N1 CI and Documentation passed on `14ae290cb91ce06a5f0556658fccb6804f809cbc`.
Commit/push N2 single-layer absorption on `dev/v1.5-broadband-optics`, verify
exact-commit CI, then implement N3 ordered stack attenuation. Package version and
CITATION.cff remain v1.4.0 through planning; final candidate identity is a N7 task.
The Phase M API review, release validators and historical fixtures remain intact.


## N1 source contracts

The additive `ncmemsim.spectral_sources` module exports `SpectralEvidence`,
`TabulatedSpectrum` and `DiscreteLineSpectrum`. Frozen contracts require immutable
tuples, finite positive ordered wavelengths and nonnegative finite input values.
Evidence records source/locator, original units, transformations, resolution,
uncertainty (including explicit unknown), notes and optional source SHA-256.
ASSUMED, MEASURED, DERIVED and LITERATURE describe input provenance; they do not
qualify an absorption model or device as CALIBRATED.

`TabulatedSpectrum` accepts absolute W m^-2 nm^-1 node densities or a dimensionless
relative shape with explicit target in-band W m^-2. The original values and target
are archived; the normalization factor and resolved densities are derived.
Absolute inputs reject renormalization targets. Zero absolute spectra, zero-target
nonzero shapes and disabled sources return zero power/photons. Zero-integral
relative shapes are rejected, including when disabled.

The power integral is trapezoidal over wavelength in nm. For endpoints a,b and
densities x,y, the exact wavelength-weighted moment of the linear interpolant is
`(b-a) * (a*(x/3+y/6) + b*(x/6+y/3))`. Multiplication by `1e-9/(h*c)` gives photon
flux. This policy is archived as `piecewise-linear-density-exact-moments-v1`.
It integrates the supplied representation, not an unknown measured continuum.

`DiscreteLineSpectrum` stores W m^-2 per ordered unique line; power is summed
and photon flux is summed using each line's own photon energy. One line recovers
the existing laser source's flux. Tables require at least two nodes; line lists
require at least one line. Duplicate lines must be explicitly aggregated upstream
with recorded provenance, never silently merged by the reader.

Both source types provide strict `to_dict`/`from_dict`, canonical JSON and SHA-256
`contract_hash`. Unknown fields, wrong schemas/units/policies, duplicate JSON keys
and nonfinite values are rejected. No solver or random sampling is involved.
Hashes identify content, not authenticity. Readers reconstruct sources only;
spectral absorption is provided by N2 below; simulator integration remains N4 work.

```python
from ncmemsim.spectral_sources import SpectralEvidence, TabulatedSpectrum, DiscreteLineSpectrum

evidence = SpectralEvidence(
    source="synthetic two-node reference", locator="documentation example",
    status="ASSUMED", original_units="dimensionless", transformations=(),
    resolution="two wavelength nodes", uncertainty="unknown", notes="not calibrated",
)
source = TabulatedSpectrum(
    wavelength_nm=(1000.0, 2000.0), values=(1.0, 1.0), evidence=evidence,
    input_kind="relative_shape", target_irradiance_W_m2=1000.0,
)
assert source.in_band_irradiance_W_m2 == 1000.0
assert TabulatedSpectrum.from_json(source.to_json()) == source
line = DiscreteLineSpectrum((1550.0,), (1000.0,), evidence)
assert line.photon_flux_m2_s > 0
```

Frequency/energy-density conversions, bin-integrated measurement import and
sampled Planck-shape generation are deferred; N1 accepts canonical tables and
lines without inventing a spectrum from incandescent metadata. N2 uses the
same stored integration semantics and declares material-domain coverage.


## N2 single-layer spectral absorption

`ncmemsim.spectral_absorption` exports `SpectralAbsorptionProfile`,
`SpectralAbsorptionResult`, `evaluate_spectral_absorption` and
`evaluate_floating_gate_spectrum`. A profile stores finite nonnegative effective
alpha in m^-1 on exactly the source grid, a layer identity, thickness in metres,
explicit wavelength applicability bounds and evidence. Bounds must cover the
entire source support, including dark/disabled sources. Unknown applicability
cannot be inferred from finite outputs; an ASSUMED diagnostic range is recorded
as such, without claiming model qualification.

The FG adapter requires an explicit optical model, identity and applicability
evidence. It uses owned model/layer/material copies, retains the layer/material
snapshot, channel decomposition, gaps and per-point parameter provenance, and
scales NC alpha once by NC volume fraction. It rejects invalid coefficients,
wrong returned wavelengths and inconsistent complete channel sums. The existing
M resolved thermal models can be supplied explicitly; N2 creates no independent
material-temperature owner or new material law.

At each wavelength, absorbed and transmitted samples are `S*(-expm1(-alpha*d))`
and `S*exp(-alpha*d)`. The exp expression preserves small transmitted signals
near the opaque limit. Power and photon moments are integrated separately.
For continuous tables, the resulting absorbed/transmitted **sample densities**
are represented as piecewise-linear functions, using N1's exact moments. This is
a sampled numerical approximation to the generally nonlinear product of source
and transmission, not exact integration of the continuum absorption law.
Grid refinement at fixed support is required; finite measured resolution and
material-model uncertainty remain separate from quadrature error.

The policy is `sampled-beer-lambert-linear-density-exact-moments-v1`. Discrete
lines are integrated independently without a continuum interpolation. Incoming
power equals absorbed plus transmitted power, and likewise photon flux, within
relative floating-point tolerance `1e-12`; dark cases have exact zero budgets.
Zero-alpha/zero-thickness profiles transmit all input. Absorbed photon flux per
thickness is a volumetric generation diagnostic, not capture efficiency or stored
charge. Zero thickness gives zero generation.

Strict result readers reconstruct sources/profiles and recompute every stored
derived projection without evaluating the optical model or running simulation.
Unknown units/fields/schemas and inconsistent projections/node records fail.
The stored alpha samples are authoritative observations: a coherently replaced
profile and recomputed projection describe different evidence, not independent
verification of the model. Content hashes are not authenticity signatures.
N6 will add broader report/bundle contracts; N2 leaves older archives unchanged.

```python
from ncmemsim.spectral_sources import SpectralEvidence, DiscreteLineSpectrum
from ncmemsim.spectral_absorption import SpectralAbsorptionProfile, evaluate_spectral_absorption, SpectralAbsorptionResult

evidence = SpectralEvidence(
    source="constant-alpha diagnostic", locator="N2 documentation example",
    status="ASSUMED", original_units="m^-1", transformations=(),
    resolution="one optical line", uncertainty="unknown", notes="not calibrated",
)
source = DiscreteLineSpectrum((1550.0,), (1000.0,), evidence)
profile = SpectralAbsorptionProfile(
    layer_name="diagnostic layer", wavelength_nm=(1550.0,),
    effective_alpha_m_inv=(1e6,), thickness_m=1e-6,
    wavelength_min_nm=1500.0, wavelength_max_nm=2000.0, evidence=evidence,
)
result = evaluate_spectral_absorption(source, profile)
assert result.summary["absorbed_irradiance_W_m2"] > 0
assert SpectralAbsorptionResult.from_json(result.to_json()) == result
```

N2 analytical acceptance uses three nested grids (33/65/129 nodes) and an
independently integrated exponential-transmission reference: final relative power
and photon errors below `1e-5`, decreasing on refinement. A compact Ge diagnostic
uses 65/129/257 nodes plus explicit Gamma and phonon-assisted threshold nodes;
successive power/photon changes decrease and the last relative change is below
`1e-3`. This is numerical evidence for that diagnostic, not a universal validated
spectral grid or independently calibrated absorption model.

Sequential multi-layer attenuation is N3; full broadband programming/capture
integration remains N4. N2 does not feed each FG with transmitted illumination.
