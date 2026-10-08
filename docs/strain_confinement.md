# Strain and nanocrystal confinement planning

## O0 status and baseline

O0 is complete: source audit, separated mechanism scope, ownership and O1-O7
acceptance gates are defined here. O1 contracts, O2 hydrostatic strain-induced shifts and O3 kinetic spherical confinement are implemented; O4 owned optical/spectral composition is implemented; O5 controlled references are implemented; O6 strict reports are implemented; O7 preparation is implemented; release approval remains pending.
Target release: v1.6.0. Final candidate identity: `1.6.0`, citation date `2026-10-08`; publication and version-specific DOI pending.
Published v1.5.0 remains separately citable with DOI `10.5281/zenodo.23189313`. No version/citation/runtime change is made
by O0. O1 adds only separate opt-in contracts; no law evaluation or simulator integration.

Baseline: `46965a3d7ed86fd64223b587db71500f4a7e7e44`, the N7 DOI closure.
[strain_confinement_audit.json](strain_confinement_audit.json) records source
inspection and canonical LF/UTF-8 digests; it is not a numerical model audit.

## Existing code and integration boundaries

| Source | Current behavior | O boundary |
|---|---|---|
| materials/base.py | NC composition, one effective mass, barriers, optional electronic gap and provenance | Do not silently treat the tunnelling mass as an optical electron/hole confinement mass |
| layers.py | NC diameter, volume/active fractions and independent FG thickness | Diameter is not radius or FG thickness; choose the actual named FG |
| kinetics.py | Diameter affects NC density, capacitance and electrostatic charging energy | Keep charging separate from optical confinement and electron-hole attraction |
| tunneling.py | Existing effective mass and programming/erase barriers | An optical gap correction alone does not determine a band offset or barrier correction |
| materials/optics/models.py | Bulk-like Gamma/L composition laws, compact absorption channels and provisional amplitudes | Add explicit valley/transition targets, retain channel provenance and nominal presets |
| materials/optics/near_edge.py | Separate bulk-like unstrained reference with its own applicability classification | No silent replacement or claim that its bulk validation covers strained/confined NCs |
| temperature_context.py | Owned reference-anchored thermal property resolution and layer-specific models | One temperature owner, explicit baseline identity and named gap targets |
| spectral_absorption.py / spectral_context.py | Explicit model sampling, domain evidence and source-bound pulse contexts | Rebuild optical evidence after changing a structural profile or diameter; no stale alpha reuse |
| spectral_reporting.py | Complete states/inputs and strict source-linked projections | New O sources/readers must preserve existing archives and no-replay semantics |

## Initial v1.6 scope

Start with opt-in optical transition-gap corrections for bulk-Ge Gamma and L
targets, evaluated independently before composition. Profile contracts may name
other materials/compositions but must reject unreviewed applicability; O0 supplies
no GeSn interpolation law or universal coefficient table. Substrate gap/ni,
affinity, electron/hole band offsets, tunnelling masses/barriers, NC density and
capture efficiency are not implicitly derived from an optical shift.

The first strain model is **hydrostatic linear response only**. Define the input
as dimensionless `trace(epsilon)` with positive tensile dilation; three equal
diagonal strains have trace three times each diagonal component. A gap deformation
coefficient for each named optical transition is in eV per unit trace. The proposed
evaluation contract is `delta_Eg = gap_coefficient_eV * trace_strain`. This coefficient
is a transition-gap derivative, not an absolute conduction-band deformation
potential. No coefficient magnitude/sign or qualified strain range is supplied
by O0. Percent strain requires an explicit conversion, not silent reinterpretation.

The first confinement model is a **spherical infinite-barrier effective-mass
kinetic diagnostic**. Radius is in metres, with explicit positive electron and
hole confinement masses normalized to the free electron mass. Its proposed term
is `delta_Eg = pi^2*hbar^2/(2*R^2) * (1/me + 1/mh)`, converted from joules to eV.
Masses in this expression are in kg after conversion. Electron masses are valley
specific; the hole branch/equivalent scalar mass must be declared. Treating an
anisotropic valley by a scalar confinement mass is an explicit model assumption,
not an inferred physical equivalence. A small NC diameter alone does not establish
effective-mass applicability or bulk-like optical selection rules.

Electron-hole attraction, dielectric polarization/image effects, finite barriers,
atomistic/tight-binding/k.p confinement, interface chemistry and shape anisotropy
require separately reviewed models. The kinetic-only term is not the complete
Brus optical excitation model. No Coulomb term is automatically added to existing
electrostatic charging energies. NC radius/diameter uncertainty remains input
evidence, not an inferred measured size distribution.

Shear/biaxial/uniaxial splitting, strain tensors/orientations and elasticity or
lattice-mismatch-to-strain conversion are outside the first hydrostatic contract.
Franz-Keldysh, Stark shifts, state filling and altered oscillator strengths/capture
remain separate candidates, as required by the roadmap.

## Evidence and coefficient review for O1

Each law/profile needs equation identity, units, sign/coordinate convention,
valley and hole/transition target, material/composition/temperature/radius or
strain domain, parameter source/locator and status. Preserve ASSUMED, DERIVED,
LITERATURE, FITTED and CALIBRATED distinctions. A literature framework does not
provide qualified coefficients for embedded nanocrystals or calibrate a device.

Reference framework for strain: [Van de Walle, Phys. Rev. B 39, 1871 (1989)](https://journals.aps.org/prb/abstract/10.1103/PhysRevB.39.1871)
discusses band lineups and deformation potentials. Material/valley-specific
parameter values and the convention mapping require a separate primary-source
review before any default is accepted.

Reference framework for confinement: [Brus, J. Chem. Phys. 80, 4403 (1984)](https://doi.org/10.1063/1.447218)
considers effective-mass kinetic energy and interactions in small crystallites;
the planning review used the [author's paper available through an academic repository](https://www.fkit.unizg.hr/_download/repository/Brus_LE_1984.pdf).
The publisher endpoint was unavailable in this session. This establishes a
framework reference, not validated Ge/GeSn NC masses or a selected radius range.

O1 must explicitly review those coefficient/domain choices. Until then numerical
examples use labelled synthetic assumptions and make no material qualification
claim. No coefficient is silently borrowed from an unrelated valley, bulk transport
mass or fitted optical amplitude.

## Ownership and composition acceptance

Validate finite values, positive sizes/masses, consistent material/valley targets
and declared domains before evaluation. No clipping, silent extrapolation,
automatic percent/radius conversion or inference from missing coefficients.
Archive the nominal context, profiles, geometry and every applied shift with
source identities. Inputs and presets must remain unchanged across runs/layers.

O2 and O3 must pass their independent analytical references before O4 coupling.
Zero hydrostatic strain recovers the nominal transition gap. Confinement must
show the analytic inverse-square-radius dependence: doubling radius quarters the
kinetic shift. The formal large-radius limit approaches zero; this must not be
used to evaluate outside a declared material domain. A diameter/radius conversion
mistake produces a factor-four error and gets an explicit regression check.

O4 resolves M's thermal baseline once, then records separate strain and confinement
contributions for each Gamma/L target. Additive shifts are an explicitly assumed
composition policy; they do not imply an independently validated coupled law.
Disable-all mode must preserve v1.5 behavior without imposing new model domains on
legacy inputs. Reject profiles attached to the wrong layer/material, baseline
temperature or geometry. Reject nonphysical/nonrepresentable resulting gaps;
do not repair them with hidden floors.

Size sweeps also change density/charging in the existing device model. Separate
optical-gap-only controls at fixed device geometry from genuine diameter changes,
or report all those changes explicitly; do not attribute the full response to
confinement. Inspect valley/threshold movement before applying spectral integration;
N's old alpha samples are not transferable to a new structural context.

## O1-O7 implementation sequence

| Stage | Deliverable | Acceptance |
|---|---|---|
| O1 | Separate strain/confinement evidence, domains and immutable contracts; coefficient review | Explicit units/sign/valley/radius/mass identities, strict readers, no hidden defaults or calibration claim |
| O2 | Optical gap shifts induced by hydrostatic strain plus independent reference | Zero/positive/negative strain, slope/sign checks, domain failures, no shear/splitting or barrier mutation |
| O3 | Kinetic spherical confinement plus independent size reference | Radius/diameter and J/eV checks, inverse-square scaling, mass sensitivity and declared applicability; charging left distinct |
| O4 | Owned opt-in optical context composed with M/N | Separate shifts and baseline identities, disabled recovery, no mutation, correct layer/geometry/temperature, rebuild alpha |
| O5 | Controlled optical/broadband and electro-optical reference | Baseline/strain-only/confinement-only/composed controls, threshold-grid/time convergence, budgets and retained negative outcomes |
| O6 | Strict structural reports and deterministic bundles | Complete profiles/inputs/states/failures, rebuilt projections, all-failed/undefined cases, no solver/RNG replay and previous archives retained |
| O7 | v1.6 API/compatibility and release gates | Full tests/docs, wheel/sdist, supported-Python exact-commit CI, citation/tag/publication checks and actual DOI after deposit |

The first applied material is Ge. Extension to GeSn, anisotropic strain, finite
barriers or interacting excitons depends on independently reviewed evidence and
may become a later scope; it is not promised by an empty contract. P remains the
independent experimental-calibration milestone. Public names/schema identifiers
will be reviewed in O1/O6, not frozen prematurely here.

## Next action

O0 exact-commit CI and Documentation passed on `90d0f7146afb048b9a6d8d0a6df0285245a93356`.
O1 terminology-corrected CI passed on `625d5d1ef4f50076dc1283ca1fd7d255dfad1427`.
O2 exact-commit CI/Documentation passed on `eb88e2ef5a76381669141158c96d76ab03606da4`.
O3 exact-commit CI/Documentation passed on `8fd49f86e923429f7ab81f36456f49b9a4e6ddc6`.
O4 and O5 exact-commit CI/Documentation passed; O5 is `9e82212f75c4d7370865c43aa1a5f1f4383260ed`.
O6 exact-commit CI/Documentation passed on `13b05572567d5124079372f295b39dc6547595e8`.
O7 preparation is implemented; release approval remains pending. See [v1.6 checklist](v1_6_release_checklist.md).
Package and citation are the final 1.6.0 candidate; no physical parameter preset is shipped.


## O1 contracts and reviewed parameter boundary

The additive `ncmemsim.materials.structural` module exports `StructuralEvidence`,
`HydrostaticStrainDomain`, `ConfinementDomain`, `HydrostaticStrainGapShiftProfile` and
`SphericalConfinementProfile`. They are frozen contracts with canonical JSON,
versioned schemas and SHA-256 content identities. Unknown fields, wrong units,
duplicate JSON keys, nonfinite values, booleans as numbers and relabelled physics
are rejected. Profiles remain data contracts. O2 adds a separate strain-induced
gap-shift evaluator below; O3 adds separate kinetic confinement evaluation.

Initial domains accept Ge only. Temperature bounds are positive finite values;
hydrostatic trace bounds are signed and contain zero, while radius bounds are
positive metres. `validate_point` checks declared bounds without extrapolation.
Domain evidence is mandatory and does not establish experimental qualification.
Gamma/L optical transition targets reuse the existing GapKind enum; substrate
gaps, string-valued targets and unreviewed GeSn applicability fail explicitly.

Gap deformation potentials for hydrostatic strain are signed, finite eV per unit trace, with their own
evidence and optical-gap-derivative semantics. Confinement requires positive
electron and hole masses in m0, an explicit hole branch, separate mass evidence
and explicit approximation evidence. Archives name the spherical infinite-barrier,
isotropic-equivalent, kinetic-only model. No tunnelling mass, diameter, dielectric
constant or Coulomb term is inferred. Optional uncertainties require paired units;
coefficient uncertainty uses eV_per_unit_trace and mass uncertainty uses m0.

Evidence retains source, locator, notes, typed provenance status and optional DOI.
ASSUMED/DERIVED/ESTIMATED/LITERATURE/FITTED/LITERATURE_FITTED remain distinct.
CALIBRATED is rejected by this stage: device qualification needs a separately
reviewed evidence contract; a label or framework citation does not establish it.

[structural_parameters_review.json](structural_parameters_review.json), checked
by `python scripts/validate_structural_parameters.py`, records the review outcome:
**zero qualified physical presets**. Four synthetic Gamma/L diagnostic profiles
use arbitrary slopes (-1/-0.5 eV per trace), electron masses (.2/.3 m0), hole mass
(.4 m0), 300 K, trace [-.01,.01] and radius [2,10] nm, all marked ASSUMED. These
values test contracts and future analytical limits; they are not Ge parameter
recommendations or a literature-derived valid window. They are documentation/test
fixtures, never automatically loaded as package defaults. Physical coefficient,
mass and domain selection remains pending explicit material-specific review.

```python
from ncmemsim.materials.structural import StructuralEvidence, HydrostaticStrainDomain, HydrostaticStrainGapShiftProfile
from ncmemsim.materials.provenance import ParameterStatus
from ncmemsim.materials.temperature import GapKind

evidence = StructuralEvidence("synthetic unit fixture", "documentation example",
    ParameterStatus.ASSUMED, "arbitrary diagnostic slope/domain; not material qualified")
domain = HydrostaticStrainDomain("Ge", 300.0, 300.0, -.01, .01, evidence)
profile = HydrostaticStrainGapShiftProfile("explicit Gamma fixture", "FG1", GapKind.GAMMA,
    domain, -1.0, evidence)
domain.validate_point(temperature_K=300.0, trace_strain=0.0)
assert HydrostaticStrainGapShiftProfile.from_json(profile.to_json()) == profile
```

Contracts store targets/assumptions without importing an optical evaluator,
changing material presets or running workflows/RNG. Composition with resolved
thermal/spectral contexts remains O4; initial law references must remain separate.


## O2 optical gap shifts induced by hydrostatic strain

The additive `ncmemsim.materials.structural_strain` module exports
`HydrostaticStrainGapShiftResult` and `evaluate_hydrostatic_strain_gap_shift`.
The input is a typed O1 profile, the explicit **unstrained optical transition
gap at temperature_K**, its provenance, and dimensionless trace_strain.
The evaluator computes `gap_shift_eV = gap_deformation_potential_eV_per_trace * trace_strain`
and `shifted_gap_eV = unstrained_gap_eV + gap_shift_eV`. Hydrostatic describes the
strain component; the gap target is still the Gamma/L optical transition.

Temperature validates the declared profile domain. O2 does not calculate thermal
gap dependence, select a material gap, infer pressure/strain from lattice mismatch,
or bind the named FG to an actual device. O4 owns that composition/binding below.
Both baseline gap and coefficient remain explicit caller inputs with provenance;
the result is conditional on those inputs and makes no parameter qualification claim.

For zero strain or zero coefficient, the exact supplied gap is retained. Signed
compression/tension and signed coefficients are supported; the sign of the shift
comes from their product. Percent strain and individual diagonal tensor entries
are not silently converted: for equal diagonal entries the trace is three times
one entry. No shear, valley splitting, conduction/valence band-offset assignment,
barrier correction or optical-amplitude change is performed.

Domain failures, nonfinite/boolean inputs, nonpositive shifted gaps, overflow and
underflow of a nonzero shift are rejected. There is no hidden floor or clipping.
A representable tiny shift can round away in the final gap addition; the signed
shift and baseline remain recorded separately. This is floating-point precision,
not a material-domain extension or physical regularization.

The result archive stores the complete profile and identity, unstrained-gap
evidence, temperature/trace convention and separate signed/final energies. Strict
readers reconstruct the profile, recheck domains and recompute the linear law;
unknown units/coordinates/schemas and inconsistent derived projections fail.
No optical evaluator, solver or RNG is involved; existing material presets and
profiles are unchanged.

```python
from ncmemsim.materials.structural import StructuralEvidence, HydrostaticStrainDomain, HydrostaticStrainGapShiftProfile
from ncmemsim.materials.structural_strain import evaluate_hydrostatic_strain_gap_shift, HydrostaticStrainGapShiftResult
from ncmemsim.materials.provenance import ParameterStatus
from ncmemsim.materials.temperature import GapKind

evidence = StructuralEvidence("synthetic O2 diagnostic", "documentation", ParameterStatus.ASSUMED,
    "arbitrary coefficient/domain and explicit baseline; not qualified Ge strain data")
profile = HydrostaticStrainGapShiftProfile("Gamma diagnostic", "FG1", GapKind.GAMMA,
    HydrostaticStrainDomain("Ge", 300.0, 300.0, -.01, .01, evidence), -1.0, evidence)
result = evaluate_hydrostatic_strain_gap_shift(profile, unstrained_gap_eV=.7985,
    unstrained_gap_evidence=evidence, temperature_K=300.0, trace_strain=.01)
assert result.gap_shift_eV == -.01
assert HydrostaticStrainGapShiftResult.from_json(result.to_json()) == result
```

The standalone `examples/phase_o2_hydrostatic_strain_reference.py` audits Gamma/L
at trace [-.01,0,.01] and 300 K using O1's synthetic slopes (-1/-0.5 eV per trace)
with retained nominal Ge baseline gaps .7985/.664 eV. Independent Decimal
multiplication/addition checks the numerical law, not empirical Ge strain response.
Nine attempts include six completed cases and three retained failures: strain
outside the domain, temperature outside the domain and a nonpositive final gap.
Requests, provenance, independent values and failure messages are retained with
a content hash. Failed attempts are not removed from the population.

```bash
python examples/phase_o2_hydrostatic_strain_reference.py --output results/o2-hydrostatic-strain-reference.json
```

The reference does not select literature-qualified deformation potentials or
validate embedded-NC response. Those choices remain explicit parameter review.
Confinement evaluation is provided separately in O3 below; no combined O4 model is inferred.


## O3 kinetic contribution of spherical confinement

`ncmemsim.materials.structural_confinement` exports
`SphericalKineticConfinementGapShiftResult` and
`evaluate_spherical_kinetic_confinement_gap_shift`. The model remains the
spherical, infinite-barrier, isotropic-equivalent effective-mass **kinetic-only**
diagnostic declared in O1. It is not a complete excitonic transition model.

For each carrier, `E = pi^2*hbar^2/(2*m*R^2) = h^2/(8*m*R^2)`. The evaluator
uses the latter equivalent form with existing `PLANCK_J_S`, `ELECTRON_MASS_KG`
and `ELEMENTARY_CHARGE_C`. Input masses are multiples of m0; output energies
are eV. Explicit exponent scaling avoids avoidable intermediate R^2 underflow
or overflow; nonrepresentable **individual** energies, their sum or final gap
are rejected. No zero-energy floor or clipping is applied.

The result records electron and hole confinement energies, their summed kinetic
gap shift and the shifted gap separately, with complete profile, unconfined-gap
evidence, radius/temperature and numerical constants. The supplied unconfined
transition gap is at temperature_K; O3 does not determine a thermal baseline,
infer strain dependence, select a valley mass or bind a device geometry.
Tiny representable contributions may round away when added to the baseline,
but are retained explicitly. The formal large-radius limit is analytical; it
does not authorize evaluation outside an evidence-backed applicability domain.

Radius is accepted in metres only. A caller with NC diameter must explicitly use
R = diameter/2. Using diameter as radius lowers the kinetic contribution by four;
the regression test makes this distinction explicit. FG layer thickness is an
independent geometry and is never interpreted as NC size. Scalar confinement
masses are not taken from the legacy tunnelling mass or substrate hole mass.

Electron-hole attraction, polarization/image terms, finite barriers, strain,
selection-rule/amplitude changes and transport barrier/charging corrections are
not included. Existing density/capacitance/charging laws are unchanged; adding
their charging energy to this optical shift is not part of O3. GeSn and other
unreviewed applicability remain rejected by the O1 domain contract.

Strict readers reconstruct inputs, validate domains and recompute both carrier
energies and their sum. Altered constants, units, coordinates, masses, projections
or unknown interaction terms fail. No optical evaluator, solver or RNG is used.
Profiles and material presets remain unchanged.

```python
from ncmemsim.materials.structural import StructuralEvidence, ConfinementDomain, SphericalConfinementProfile
from ncmemsim.materials.structural_confinement import evaluate_spherical_kinetic_confinement_gap_shift, SphericalKineticConfinementGapShiftResult
from ncmemsim.materials.provenance import ParameterStatus
from ncmemsim.materials.temperature import GapKind

evidence = StructuralEvidence("synthetic O3 masses", "documentation", ParameterStatus.ASSUMED,
    "arbitrary scalar masses/domain; not qualified embedded-Ge NC data")
profile = SphericalConfinementProfile("Gamma kinetic diagnostic", "FG1", GapKind.GAMMA,
    "effective_scalar", ConfinementDomain("Ge", 300.0, 300.0, 2e-9, 1e-8, evidence),
    .2, .4, evidence, evidence, evidence)
result = evaluate_spherical_kinetic_confinement_gap_shift(profile, unconfined_gap_eV=.7985,
    unconfined_gap_evidence=evidence, temperature_K=300.0, radius_m=4e-9)
assert result.kinetic_gap_shift_eV > 0
assert SphericalKineticConfinementGapShiftResult.from_json(result.to_json()) == result
```

The standalone `examples/phase_o3_kinetic_confinement_reference.py` uses Gamma/L
diagnostics at radii 2/4/8 nm and 300 K with O1's ASSUMED electron masses .2/.3 m0
and hole mass .4 m0, retaining nominal .7985/.664 eV gaps. Decimal arithmetic
at 60-digit precision independently checks each kinetic energy and J/eV conversion.
Doubling radius quarters the shift; changing one carrier mass affects only its
own term. Eight attempts include six completed cases and two retained domain
failures (radius and temperature), with requests, source records and a content hash.

```bash
python examples/phase_o3_kinetic_confinement_reference.py --output results/o3-kinetic-confinement-reference.json
```

This is numerical validation of an explicit diagnostic law, not selection of
qualified Ge/GeSn NC masses or domains. Independent O2/O3 mechanisms remain
separate; their owned composition with thermal/spectral models is provided by O4 below.


## O4 owned structural optical composition with M/N

`ncmemsim.structural_optical_context` exports `StructuralOpticalBinding`,
`StructuralOpticalContext`, `StructuralSpectralContext`,
`StructuralSpectralSimulator`, `build_structural_spectral_context` and
`run_structural_spectral_program_pulse_read`. Profiles are grouped by the actual
named FG and mechanism; duplicate targets within a mechanism, mismatched profile
layer names and unknown FG attachments fail. Enabled attachments require the
declared Ge material model with zero Sn fraction. No GeSn law is inferred.

The thermal resolution is the sole device-temperature owner and must explicitly
cover every FG optically as required by M; partial coverage is rejected by M. Each Gamma/L target
stores that already-resolved baseline, an independent O2 strain result and an
independent O3 confinement result when requested. NC radius is taken explicitly
as half the associated device NC diameter, not FG thickness. Domain failures for
temperature/trace/radius stop composition; O2 rejects a nonphysical strain-only
gap even if a positive confinement shift would otherwise mask it.

The composition policy is `thermal-baseline-plus-independent-structural-shifts-assumed-v1`.
Both shifts are evaluated on the same thermal baseline, then their separately
stored contributions are added with that baseline exactly once. Additive optical
gap composition is an ASSUMED policy, not a qualified interacting/coupled NC law.
The baseline optical amplitudes and resolved phonon temperature remain unchanged.
No substrate gap/ni, density, effective mass, barrier, charging or capture parameter
is modified. Geometry remains the supplied M device geometry.

An empty binding tuple or disabled attachment delegates to M's existing optical
model. Disabled attachments retain profiles as evidence without imposing their
new applicability domains on legacy inputs. Enabled zero strain without confinement
recovers the original optical numbers and retains structural provenance. The
associated material is checked against its owned snapshot; caller mutations or
supplying a different material cannot silently change that evaluator.

With shifted gaps, the owned optical evaluator recomputes direct, indirect and
Urbach absorption from the resolved Gamma/L gaps and M's absorption parameters.
It does not reuse an alpha sampled before the structural change. Provenance stores
the structural composition identity and per-FG baseline/contribution evidence.
Gap-only changes do not qualify oscillator strength or capture efficiency, and
may move thresholds requiring an independently refined spectral grid in O5.

The spectral builder requires the complete set of explicit passive-layer profiles
and samples each FG from the structural optical owner. The wrapper retains both
the full structural owner and unchanged N spectral context. Context identity and
sampled gap targets are checked on restoration; old samples from a changed trace,
profile or device radius are rejected. Alpha observations remain stored evidence:
readers rebuild structural contributions and nested N projections, not optical
trajectories or fresh alpha samples. Coherently replaced observations describe
different evidence, not independent physical verification.

The simulator uses N4's photo/occupancy/transport stepping on the new stored
optical evidence, checks drift of its M device/physics/configuration, and exposes
structural context identity. The pulse wrapper retains the complete structural
owner around N4's illuminated pulse and zero-dwell dark read. Existing N/M schemas
and readers are not converted or changed. O6 defines separate structural report
contracts for those stored runs.

```python
from ncmemsim import DeviceBuilder, PhysicsModel, SimulationConfig
from ncmemsim.materials import make_ge
from ncmemsim.materials.temperature import GapKind
from ncmemsim.materials.provenance import ParameterStatus
from ncmemsim.materials.structural import StructuralEvidence, HydrostaticStrainDomain, ConfinementDomain, HydrostaticStrainGapShiftProfile, SphericalConfinementProfile
from ncmemsim.temperature_context import ThermalContext
from ncmemsim.structural_optical_context import StructuralOpticalBinding, StructuralOpticalContext

device = DeviceBuilder.v2(1, nc_material=make_ge(), nc_diameter_nm=8.0)
resolution = ThermalContext.from_nominal(device, PhysicsModel.default(), SimulationConfig()).resolve(temperature_K=300.0)
evidence = StructuralEvidence("synthetic O4", "documentation", ParameterStatus.ASSUMED,
    "arbitrary masses/slope/domains and additive policy, not material qualified")
strain = HydrostaticStrainGapShiftProfile("Gamma strain diagnostic", "FG1", GapKind.GAMMA,
    HydrostaticStrainDomain("Ge", 300.0, 300.0, -.01, .01, evidence), -1.0, evidence)
confinement = SphericalConfinementProfile("Gamma kinetic diagnostic", "FG1", GapKind.GAMMA,
    "effective_scalar", ConfinementDomain("Ge", 300.0, 300.0, 2e-9, 1e-8, evidence),
    .2, .4, evidence, evidence, evidence)
context = StructuralOpticalContext(resolution,
    (StructuralOpticalBinding("FG1", (strain,), (confinement,), .001),))
assert StructuralOpticalContext.from_json(context.to_json()) == context
```

Tests cover baseline/strain-only/confinement-only/composed modes, independent
absorption equations, derived device radius, thermal baseline applied once,
one/two/three-FG spectral coupling, stale sampling rejection and no optical
resampling during restoration. Disabled optical/pulse values recover N4, and
caller/device/material ownership and structural source identity are retained.
O5 supplies the broader spectral/time convergence and negative-outcome references.


## O5 controlled structural optical reference

`examples/phase_o5_structural_reference.py` compares thermal baseline, strain only,
kinetic confinement only and their assumed additive composition with identical
8 nm NC diameter, source, temperature and transport inputs. The parameters remain
explicit synthetic ASSUMED diagnostics; this reference does not qualify a Ge
nanocrystal material model or a capture efficiency.

A flat relative spectrum is explicitly normalized to 1e6 W/m2 over 1000-2200 nm.
Each refinement grid contains the union of shifted Gamma and L phonon thresholds
for the four mechanism modes at 300 and 350 K. Power and photon accounting use
ordered single-pass propagation with explicitly transparent passive layers.
Spectral refinement requires successive absorbed-power/photon changes below
0.2%; temporal refinement requires probability changes below 0.002 and changes
of illuminated-minus-dark read contrast below 1e-5 V. These are numerical
acceptance criteria for this diagnostic, not uncertainty estimates for a device.

The pulse uses 2 V for 1e-7 s, backward Euler, capture efficiency 0.1 and a
zero-dwell dark read. Negative probabilities, probability-mass errors above
1e-12 and read-state changes above 1e-12 are rejected. Zero capture recovers the
matched dark trajectory. Separate controls cover two/three FGs, 300/350 K and
4/8 nm diameters. Diameter controls retain the corresponding changes to physical
NC density and charging energy; their electrical response is not attributed
solely to optical confinement.

The main population retains four completed mechanism cases and three explicit
failures for strain, radius and temperature outside their declared domains.
Refinements and auxiliary controls are recorded separately from that population.
The JSON diagnostic retains source, structural inputs, layer budgets, pulse
observations and its canonical identity. It is not the O6 structural report
contract and is not a manufacturing-yield study.

```bash
python examples/phase_o5_structural_reference.py --output structural-reference.json
```

O6 adds strict structural reports and reproducibility bundles; O7
performs the v1.6 API review and release gates.


## O6 strict structural reports and reproducibility bundles

`ncmemsim.structural_reporting` provides immutable `StructuralRunEvidence`,
`StructuralReportStudy` and `StructuralReport` contracts. Optical studies retain
an entire structural/spectral context. Pulse studies retain that owner alongside
unchanged N run evidence: explicit initial/programmed/read states, protocol,
capture efficiency, runtime, charge, read shift and photon flux/rate/fluence.
Readers match the nested spectral owner to the structural context, reconstruct
the O2/O3 contributions and N projections, and verify state-derived charge/read
observables without replaying a simulator, optical evaluation or random generator.
Stored alpha samples and trajectories remain authoritative observations;
coherently changed observations represent different evidence, not independent
physical validation or authenticity.

Failure studies retain a JSON request, stage, error type and message. Invalid
requests are preserved as attempts rather than coerced into successful contexts.
Each optical/pulse/failure study counts as one attempt. Pulse statistics use only
completed pulse studies and disclose that denominator; an all-failed report has
zero estimates and a null mean. Broadband scalar alpha remains null, and a
disabled source retains zero optical budgets without inventing illumination.
Duplicate names/JSON keys, nonfinite values, unknown fields, stale structural
inputs, altered projections and inconsistent observations are rejected.

`build_structural_run_evidence` freezes O4 workflow output;
`build_structural_report` collects studies with mandatory scientific limitations.
`write_structural_report` writes a new directory containing `report.json`,
`report.md`, `attempts.csv`, `layers.csv`, `structural.csv`, `sources.csv` and
`bundle.json`. The structural CSV separates the thermal baseline, signed
hydrostatic strain-induced shift, kinetic confinement shift and resolved optical
transition gap by named FG/target, with radius in metres and gaps in eV.
JSON/source CSV retain complete evidence. The manifest records content hashes;
`load_structural_report_bundle` checks exact ordinary-file membership and rebuilds
all CSV/Markdown bytes, rejecting modified exports even if their hashes were
updated. Existing directories are never overwritten. Old M/N archives continue
to use their existing readers and schemas.

```python
from ncmemsim.structural_reporting import (
    StructuralRunEvidence, build_structural_run_evidence, StructuralReportStudy,
    StructuralReport, build_structural_report, write_structural_report,
    load_structural_report_bundle,
)
```

```bash
python examples/phase_o6_structural_report.py --output structural-bundle
python examples/phase_o6_structural_report.py --input structural-bundle/report.json --output restored-bundle
```

The example makes two completed studies and retains two out-of-domain failures.
Its five spectral nodes/eight time steps demonstrate reporting, not convergence;
O5 supplies refined numerical reference evidence. Report status remains conditional
and unqualified, with synthetic ASSUMED parameters, kinetic-only confinement and
no experimental material, capture or device calibration.

O7 preparation CI/Documentation passed on `dcee61c47f62659f95e5c6c6bb54d4d14ee3f5c0`. Final candidate identity: `1.6.0`; publication and version-specific DOI pending.
