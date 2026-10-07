# Strain and nanocrystal confinement planning

## O0 status and baseline

O0 is complete: source audit, separated mechanism scope, ownership and O1-O7
acceptance gates are defined here. O1 contracts and parameter-review boundaries are implemented; O2-O7 are planned.
Target release: v1.6.0. Current package/citation remain published v1.5.0, with
version DOI `10.5281/zenodo.23189313`. No version/citation/runtime change is made
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
| O2 | Hydrostatic optical-gap evaluation plus independent strain reference | Zero/positive/negative strain, slope/sign checks, domain failures, no shear/splitting or barrier mutation |
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
Commit/push O1 and verify exact-commit CI. Next: O2 independent hydrostatic
evaluation and reference; O3 confinement evaluation remains a separate stage.
Package and citation remain published v1.5.0; no physical parameter preset is shipped.


## O1 contracts and reviewed parameter boundary

The additive `ncmemsim.materials.structural` module exports `StructuralEvidence`,
`HydrostaticStrainDomain`, `ConfinementDomain`, `HydrostaticGapProfile` and
`SphericalConfinementProfile`. They are frozen contracts with canonical JSON,
versioned schemas and SHA-256 content identities. Unknown fields, wrong units,
duplicate JSON keys, nonfinite values, booleans as numbers and relabelled physics
are rejected. No profile evaluates a gap yet; O2/O3 add those independent laws.

Initial domains accept Ge only. Temperature bounds are positive finite values;
hydrostatic trace bounds are signed and contain zero, while radius bounds are
positive metres. `validate_point` checks declared bounds without extrapolation.
Domain evidence is mandatory and does not establish experimental qualification.
Gamma/L optical transition targets reuse the existing GapKind enum; substrate
gaps, string-valued targets and unreviewed GeSn applicability fail explicitly.

Hydrostatic coefficients are signed, finite eV per unit trace, with their own
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
from ncmemsim.materials.structural import StructuralEvidence, HydrostaticStrainDomain, HydrostaticGapProfile
from ncmemsim.materials.provenance import ParameterStatus
from ncmemsim.materials.temperature import GapKind

evidence = StructuralEvidence("synthetic unit fixture", "documentation example",
    ParameterStatus.ASSUMED, "arbitrary diagnostic slope/domain; not material qualified")
domain = HydrostaticStrainDomain("Ge", 300.0, 300.0, -.01, .01, evidence)
profile = HydrostaticGapProfile("explicit Gamma fixture", "FG1", GapKind.GAMMA,
    domain, -1.0, evidence)
domain.validate_point(temperature_K=300.0, trace_strain=0.0)
assert HydrostaticGapProfile.from_json(profile.to_json()) == profile
```

Contracts store targets/assumptions without importing an optical evaluator,
changing material presets or running workflows/RNG. Composition with resolved
thermal/spectral contexts remains O4; initial law references must remain separate.
