# Broadband spectra and sequential multilayer optics

## N0 status and baseline

N0 is complete: source/code audit, scope, units, integration boundaries and
N1-N7 acceptance sequence are defined here. N1-N6 source, absorption, propagation, opt-in integration, controlled references and strict reports are implemented; N7 preparation is implemented; release approval remains pending.
Target release: v1.5.0. Final candidate identity: `1.5.0`, citation date 2026-10-06; publication remains pending;
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
N2 CI and Documentation passed on `5c2fd6a756b349d7554b910c129fcf25cddcf956`.
N3 CI and Documentation passed on `d9c7796b0fbd3e38a38c2c3e09fe5f17879589c8`.
N4 CI and Documentation passed on `80c8327d9e6d8bf748c883b744b64fe682b5c7e8`.
N5 CI and Documentation passed on `f7673c597e799e093daea09c3d14d8c35ba2c723`.
N6 CI and Documentation passed on `23cf78cd8088658c9eb95a56f46fa30d04c83b14`.
N7 preparation is implemented; release approval remains pending. Commit/push preparation
and verify exact-commit CI before preparing final v1.5.0 identity and publication.
CITATION.cff describes final candidate 1.5.0; v1.4.0 remains the latest published
release. Next: verify final candidate CI, review PR/main, then tag/publication.
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
spectral absorption is provided by N2 below; simulator integration is provided by N4 below.

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
N6 adds broader report/bundle contracts below; N2 leaves older archives unchanged.

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

N3 provides sequential multi-layer attenuation and N4 explicit broadband
programming integration below. N2 itself is a single-layer evaluator.


## N3 ordered single-pass optical paths

The additive `ncmemsim.spectral_stack` module exports `SpectralStackLayer`,
`SpectralStackPath`, `SpectralStackResult`, `bind_spectral_stack_path` and
`evaluate_spectral_stack`. A layer wraps an N2 profile with explicit
`floating_gate` or `passive` role and `absorbing` or `assumed_transparent`
treatment. Assumed-transparent treatment requires a passive layer, zero alpha
and ASSUMED evidence. An absorbing passive profile requires explicit coefficients
and applicability evidence; no material is automatically declared transparent.

Layers are stored in physical substrate-to-gate order. Direction is explicitly
`substrate_to_gate` or `gate_to_substrate`; the latter reverses traversal without
changing the stored physical order. Layer identities must be unique and every
profile must use the same spectral grid. Up to three FGs are supported; paths with
only passive layers are allowed for diagnostics. Unsupported directions and
implicit interpolation fail before any propagation.

A standalone path describes exactly its listed layers, not a complete device.
`bind_spectral_stack_path` takes owned device evidence and requires all device
layers in their stored order, with matching roles and thicknesses. FG sampling
records, when present, must match that device layer. Omitted/extra/relabelled
layers or changed thicknesses fail. This does not qualify optical constants or
infer missing material models.

For each traversed layer, N2 evaluates the current incoming spectrum. Only its
transmitted samples become the next layer's absolute density/line-power source.
Relative input normalization occurs once at the incident boundary; no downstream
renormalization is performed. The original source and path remain immutable.
Per-layer evidence retains its actual source, absorption/transmission samples,
power/photon integrals and provenance. Both integrated and nodewise whole-path
balances are checked to relative tolerance `1e-12`; dark budgets are exactly zero.

The stack projection reports total absorption, final transmission and separate
FG/passive absorbed power and photon flux. Passive loss has no NC absorbed-photon
capture source (`nc_absorbed_photon_flux_m2_s` is None); FG photon absorption is
not automatically stored charge or unit-efficiency capture. N2 volumetric
absorption diagnostics remain optical bookkeeping, not carrier qualification.

Unequal layers change their allocated absorption when illumination direction is
reversed. For this linear single-pass model, total transmission is the product of
the same layer transmissions and is order-independent. Reflection/interference,
scattering and nonlinear/state-dependent optics are outside this contract.

Strict result archives restore source/path evidence and recompute the entire
sequential projection without invoking optical models, simulator or RNG. They
reject changed handoffs, node/integrated budgets, roles, directions and unknown
schemas/fields. Coherently replaced sources/profiles describe different evidence;
hashes prove internal content identity, not authenticity. N1/N2 schemas and older
archives are unchanged. Continuous spectra inherit N2's sampled linear-density
approximation and require grid convergence.

```python
from ncmemsim.spectral_sources import SpectralEvidence, DiscreteLineSpectrum
from ncmemsim.spectral_absorption import SpectralAbsorptionProfile
from ncmemsim.spectral_stack import SpectralStackLayer, SpectralStackPath, evaluate_spectral_stack, SpectralStackResult

evidence = SpectralEvidence(
    "N3 constant-alpha example", "documentation", "ASSUMED", "m^-1", (),
    "one line", "unknown", "single-pass diagnostic, not calibrated",
)
source = DiscreteLineSpectrum((1550.0,), (1000.0,), evidence)
def layer(name, alpha, role):
    profile = SpectralAbsorptionProfile(name, (1550.0,), (alpha,), 1e-6,
                                        1500.0, 2000.0, evidence)
    return SpectralStackLayer(profile, role)
path = SpectralStackPath(
    (layer("passive filter", 1e6, "passive"), layer("FG1", 2e5, "floating_gate")),
    "substrate_to_gate", evidence,
)
result = evaluate_spectral_stack(source, path)
assert result.projection["summary"]["passive_absorbed_irradiance_W_m2"] > 0
assert SpectralStackResult.from_json(result.to_json()) == result
```

N3 validates one/two/three-FG analytical transmission, relative-source handoff,
transparent/zero-thickness/opaque/dark limits and direction-dependent per-layer
absorption. A passive-plus-FG exponential-attenuation continuum reference uses
33/65/129 nested grids: power/photon errors decrease and final relative errors
are below `1e-5`. This is numerical evidence for the declared diagnostic only.
The original Simulator retains its legacy optical path. N4 adds a separate
opt-in adapter that maps these optical inputs into photo-transition rates.


## N4 explicit spectral simulation context

`ncmemsim.spectral_context` exports `SpectralSimulationContext`,
`SpectralSimulator`, `build_spectral_simulation_context`, `SpectralPulseProtocol`
and `run_spectral_program_pulse_read`. The context pairs an owned M resolved
isothermal device/physics/configuration with an N3 optical result whose bound
device snapshot must match exactly. Changing temperature, geometry or another
device/configuration input requires a new resolution and optical context.

The factory samples each resolution-owned FG model using N2 and then propagates
the complete path using N3. Every passive optical layer must be supplied explicitly
with its profile/treatment. Device temperature is owned by M; source evidence is
separate. Applicability bounds/evidence are explicit diagnostic declarations,
not inferred model qualification. The direct context constructor also supports
explicit stored profile observations; it does not automatically reevaluate alpha.
Only the factory establishes that FG samples came from the resolution's models.

`SpectralSimulator` subclasses the owned thermal adapter without changing the
original Simulator or ThermalSimulator. Illumination accepts only the source
bound to the context; None means dark. Each FG's absorbed photon flux **after**
sequential attenuation is divided by physical NC density and thickness, then
mapped through the existing layer-average photo-transition law. Passive losses
never become NC capture inputs. This is a constant capture-efficiency/weight model
across the supplied spectrum; wavelength-dependent capture is outside N4.

Illuminated calls require explicit PhotoTransitionConfig and PhotoTransitionWeights.
Values must be finite, nonnegative and physically bounded. N4 additionally limits
capture efficiency times the maximum outgoing photo weight (r01, r12+r10, r21)
to one, so the compact mapping does not allocate more than one photo event per
absorbed photon per active NC. This restriction applies to the new adapter only.
It does not impose a bound on electrical injection or claim quantum-efficiency
calibration. Active fractions and occupancy/transport stepping retain their
existing definitions. Spatial photo generation remains layer-averaged.

Inherited diagnostics report per-FG photo rates and absorbed photon flux. The
absorption fraction is photon-weighted relative to that FG's incoming spectrum.
For broadband/multiple lines, scalar alpha diagnostic arrays are NaN (undefined),
while all actual alpha samples remain in the source-linked `spectral_stack`
evidence. A single discrete line retains its scalar alpha interpretation. No
average photon energy or averaged material coefficient substitutes for integration.
The output also includes the spectral context hash; dark outputs have no applied
spectral_stack evidence. Raw simulator dictionaries are not strict JSON reports.

The new pulse protocol reuses ProgramPulseReadProtocol for electrical timing,
stores photo weights and the occupancy integrator, and requires a dark zero-dwell
read. The workflow owns/copies the initial state, executes the illuminated pulse,
then evaluates the programmed state electrostatically without further evolution.
Its delta_vfb observable is relative to the initial dark read, not a memory window.
Returned run evidence contains raw program/read outputs, context/protocol identity,
capture efficiency and per-FG absorbed photon fluence. N6 provides strict
report/bundle serialization below, including undefined diagnostic handling.

Context/protocol readers restore contracts and optical projections without solver,
optical-model or RNG replay; M resolution inputs are reconstructed using M's
existing deterministic property evaluation. Previously published I/K/L/M schemas
and protocols remain unchanged.

```python
from ncmemsim import DeviceBuilder, PhysicsModel, SimulationConfig
from ncmemsim.materials import make_ge
from ncmemsim.temperature_context import ThermalContext
from ncmemsim.spectral_sources import SpectralEvidence, DiscreteLineSpectrum
from ncmemsim.spectral_absorption import SpectralAbsorptionProfile
from ncmemsim.spectral_stack import SpectralStackLayer
from ncmemsim.spectral_context import build_spectral_simulation_context, SpectralPulseProtocol, run_spectral_program_pulse_read
from ncmemsim.program_protocol import ProgramPulseReadProtocol
from ncmemsim.photo import PhotoTransitionConfig, PhotoTransitionWeights

device = DeviceBuilder.v2(1, nc_material=make_ge())
device.floating_gates()[0].grid_points = 3
resolution = ThermalContext.from_nominal(device, PhysicsModel.default(), SimulationConfig()).resolve(temperature_K=300)
evidence = SpectralEvidence("N4 diagnostic", "documentation", "ASSUMED", "canonical inputs", (),
                            "one line", "unknown", "transparent matrix/passive layers, not calibrated")
source = DiscreteLineSpectrum((1550.0,), (1000.0,), evidence)
passive = tuple(
    SpectralStackLayer(SpectralAbsorptionProfile(layer.name, source.wavelength_nm, (0.0,),
        layer.thickness_nm*1e-9, 1500.0, 2000.0, evidence), "passive", "assumed_transparent")
    for layer in resolution.device.layers if layer.role != "floating_gate"
)
context = build_spectral_simulation_context(resolution, source, direction="gate_to_substrate",
    passive_layers=passive, wavelength_min_nm=1500.0, wavelength_max_nm=2000.0, evidence=evidence)
protocol = SpectralPulseProtocol(ProgramPulseReadProtocol(0.0, 1e-8, 0.0, 1e-9), PhotoTransitionWeights())
run = run_spectral_program_pulse_read(context, protocol, photo_config=PhotoTransitionConfig(0.1))
assert run["read"]["spectral_stack"] is None
```

N4 tests dark identity on one/two/three-FG devices, one-line legacy pulse/state
equivalence, broadband sequential rates and passive losses, source/device drift,
thermal model composition and strict context/protocol restoration. An isolated
photo-only pulse (electrical rates explicitly set to zero in the test) converges
on 32/64/128 time steps against analytical loading probabilities; final absolute
error is below `2e-3`, probabilities remain normalized/nonnegative and stored
electrons do not exceed captured photon fluence. This isolates mapping/numerics;
it does not validate combined transport, device calibration or a universal step.
N5 supplies the broader controlled broadband/electro-optical references below.


## N5 controlled broadband and multispectral reference

The standalone `examples/phase_n5_broadband_reference.py` runs a synthetic
one/two/three-FG matrix with three equal-power incident sources:

- one 1550 nm line;
- two lines at 1550 and 1850 nm, with equal line powers;
- a flat relative wavelength-density shape on 1500-2000 nm, explicitly normalized.

Every source has in-band irradiance `1e6 W m^-2`. This is an equal-power comparison,
not equal photon flux. All source/capture/passive-optics assumptions are labelled
ASSUMED. No measured spectrum or experimental device qualification is claimed.
Bulk-Ge compact amplitudes, NC volume fraction .2, active fraction .1, FG thickness
6 nm, three spatial cells and capture efficiency .1 are synthetic choices. The
baseline device temperature is 300 K. Passive layers are declared transparent in
the main matrix; the NC matrix remains transparent under the inherited compact law.

Broadband optical audits use 65/129/257 base nodes plus explicit nominal Gamma
and phonon-assisted threshold wavelengths. The final successive relative changes
in FG-absorbed power and photon flux must be below `1e-3`. Models are sampled on
the stored grids and integrated with N1-N3 numerical policies. Refinement is not
new measured information or a universal spectral-grid guarantee.

Each main case programs at 2 V for `1e-7 s`, using backward Euler on 16/32/64
internal steps, then performs the zero-dwell dark read. A matching dark pulse is
run on each temporal grid. Photo contrast is illuminated minus dark read Vfb;
it is not a memory window. Final successive probability change must be below
`2e-3` and photo-contrast change below `1e-5 V`. Probability normalization,
nonnegativity and unchanged read probabilities are audited independently.
Combined electrical/optical charge is not attributed solely to photons; the
isolated charge/photon mapping audit remains in N4.

Auxiliary controls for each FG count compare dark, zero capture and disabled
sources, and explicitly absorbing passive layers (alpha `1e6 m^-1`) against the
transparent path. A separate one-FG thermal control uses the reviewed M coupled
Ge model at 300/350 K with the **identical stored source**. It distinguishes device
property changes from illumination changes; the nominal source grid is retained
for this diagnostic and does not claim a thermally qualified wavelength grid.

The attempted main population is 11: nine completed source/device cases and two
deliberate ValueError failures (1499 nm outside the declared domain and an omitted
passive layer). Auxiliary convergence/compatibility/thermal controls are audits,
not additional members of that population. Failed attempts are not discarded.

The JSON reference stores complete final contexts, source/model/layer provenance,
coarse-grid optical summaries, pulse probabilities, photo rates, read/charge
observables, controls and failure messages, plus a content hash. Its standalone
validator checks finite JSON, population/refinement completeness, source-linked
context restoration, probability/read limits and compatibility controls. It
does not replay trajectories to certify observations; N6 provides report
contracts and deterministic multi-file bundles below. Hashes do not establish authenticity.

```bash
python examples/phase_n5_broadband_reference.py --output results/n5-broadband-reference.json
```

This reference does not qualify absorption amplitudes, capture efficiency,
temperature laws, manufacturing yield or transfer-matrix propagation. Strain,
confinement, scattering, reflection/interference, measured-spectrum import and
wavelength-dependent capture remain outside this reference.


## N6 strict reports and deterministic bundles

`ncmemsim.spectral_reporting` exports `SpectralRunEvidence`,
`build_spectral_run_evidence`, `SpectralReportStudy`, `SpectralReport`,
`build_spectral_report`, `write_spectral_report` and `load_spectral_report_bundle`.
Study kinds are `stack`, `pulse` and `failure`; each study counts as one report
attempt. These counts describe the selected report population, not manufacturing
yield or the separate eleven-attempt N5 reference population.

Stack studies retain complete N3 sources/paths/projections. Pulse studies retain
the complete N4 context/protocol/capture settings, explicit initial state, stored
programmed/read states, per-FG optical and charge observables and runtime versions.
The builder takes a completed N4 workflow result; it neither runs that workflow nor
infers its initial state. All occupation arrays and structural/state metadata are
preserved. Failed-request studies retain finite JSON request evidence, stage,
exception type and message without inventing a valid resolution or observations.
Intentionally invalid requests remain authoritative failure descriptions; their
validity is not asserted by the reader.

Strict readers restore nested inputs, check state normalization/timing and
unchanged dark-read probabilities, rebuild static charge/read observables and
derive expected photo rates/fluence from stored optical evidence. They do not
reevaluate the optical model, integrate a pulse, run transport or draw RNG samples.
M's existing deterministic parameter resolution and static electrostatics are
used for consistency checks, not independent trajectory validation. Stored states
and alpha observations remain authoritative; a coherently replaced source and its
rebuilt projection represent different evidence. Hashes are not authenticity or
experimental qualification signatures.

The report retains attempted/completed/failed denominators. Delta-Vfb statistics
refer only to completed pulse studies; stack/failure studies have no such metric.
An all-failed report has estimated_count zero and mean None, serialized as null.
Broadband scalar alpha is also null in derived reporting; actual spectral alpha
samples remain in nested optical sources. No NaN/Inf is allowed in report JSON.

The bundle contains exactly six files: `report.json`, `report.md`, `attempts.csv`,
`layers.csv`, `sources.csv` and `bundle.json`. CSV and Markdown are deterministic
derived views; JSON retains full source/state evidence. The manifest stores member
SHA-256 digests and report identity. Loading checks membership, ordinary files,
all nested sources/projections and rebuilt member bytes, so rehashing inconsistent
CSV/Markdown or nested report summaries does not make them acceptable. Existing
destination directories are never overwritten.

Use the standalone example to create a new controlled one-FG optical/pulse
execution plus retained unsupported-domain and incomplete-path failures:

```bash
python examples/phase_n6_spectral_report.py --output results/n6-spectral-bundle
```

This is a new four-study N6 report: two completed studies (stack/pulse) and two
failed requests, not a reconstruction of missing full states from the N5 JSON.
To restore/export stored report evidence without execution, supply `--input`:

```bash
python examples/phase_n6_spectral_report.py --input results/n6-spectral-bundle/report.json --output results/n6-restored-bundle
```

Tests forbid optical-model, solver and RNG replay during restoration, verify
byte-identical exports, preserve all-failed/null statistics and reject altered
observations, states, protocols, nested projections and coherently rehashed
bundle views. Older I/K/L/M and N1-N4 contracts remain unchanged. N7 will review
the additive surface, historical compatibility and installed distributions before
any final v1.5 citation/tag/release change.
