# Advanced transport physics

## Status and purpose

This page defines the Phase J development contract for NCMemSim v1.1.0.
The current `1.1.0.dev0` work has completed **J4**. J0 introduced scope,
interfaces, invariants, validation requirements, and a delivery sequence. J1
added inert trap/TAT specifications and selected the first compact equation.
J2 evaluates that conditional compact path with explicit diagnostics, but does
not attach it to the transport engine or evaluate a device current. J3 adds a
separate, explicitly enabled compact image-force correction while retaining
the complete unmodified barrier profile. J4 adds explicit link attachment,
mechanism-resolved rates/fluxes, conservative copied-state evolution and
link-local failure results. It does not introduce calibrated material
parameters.

The published v1.0.0 direct-tunnelling and retention behavior remains the
reference baseline. All future Phase J mechanisms must be opt-in and must
reproduce that baseline exactly when disabled.

## Scientific objective

Phase J will extend the compact transport layer so that a study can represent
well-defined additional conduction mechanisms without hiding their origin in
an effective tunnelling prefactor. The first target is trap-assisted transport
through dielectric links. J3 uses the classical Schottky peak-lowering
expression after fixing its energy units, field symmetry,
effective-permittivity provenance and compact two-interface applicability.

The implementation is intended for controlled compact-model studies. It will
not, by itself, establish defect populations for a fabricated stack or turn a
simulated leakage current into an experimentally calibrated prediction.

## Frozen v1 compatibility boundary

Phase J must preserve the approved v1 public API and archive readers.

- Existing imports, parameter defaults, result fields, and positional calls
  remain supported according to the v1 compatibility contract.
- Existing WKB paths retain their current equations and numerical results.
- New mechanisms are disabled by default.
- A configuration with every new mechanism disabled must reproduce v1.0.0
  reference results within the existing exact or declared numerical tolerance.
- Published v0.14.0 archive fixtures remain readable.
- Existing manifests keep their meaning; a new schema field may be optional,
  but an old field must not be silently reinterpreted.
- No synthetic example may be described as experimental calibration.

Additive APIs may be introduced during J1-J6 only after their units,
ownership, serialization, and compatibility behavior are tested. Removal or
renaming of an approved v1 path is outside the v1.1.0 scope.

## Mechanism boundary

The transport engine currently represents direct WKB transfer across explicit
links. Phase J will retain that contribution and, where configured, evaluate
additional mechanism contributions separately before forming a total rate.

The required decomposition is conceptually:

\[
\Gamma_{\mathrm{total}} =
\Gamma_{\mathrm{direct}} +
\Gamma_{\mathrm{TAT}} +
\Gamma_{\mathrm{other,enabled}}.
\]

Each contribution must remain observable in diagnostics. Implementations must
not overwrite the direct contribution or expose only a total from which the
selected mechanisms cannot be reconstructed.

J1 selected the first trap-assisted equation below. J2 now implements it as
an isolated conditional-rate kernel after fixing its barrier profile, numerical
behavior and limiting cases. J4 performs the first explicit network integration through an additive wrapper.

## Quantities and canonical units

Future contracts must use explicit SI units at their public boundary.

| Quantity | Canonical unit | J0 rule |
|---|---:|---|
| trap energy | J | Energy reference and sign must be explicit |
| trap density | m^-3 or m^-2 | Dimensionality must be part of the model |
| capture cross section | m^2 | Carrier species and provenance required |
| attempt frequency | s^-1 | Must not be inferred from an unrelated default |
| dielectric thickness | m | Reuse the explicit transport-link geometry |
| electric field | V m^-1 | Reuse the existing signed link convention |
| temperature | K | Must be positive and recorded in evidence |
| transition rate | s^-1 | Individual and total contributions reported |
| barrier energy | J | Reference level and lowering convention required |

Convenience input units may be added only through named conversion helpers.
There will be no implicit eV/J, cm^-3/m^-3, or nm/m conversion in a low-level
transport contract.

## Trap and defect provenance

Every enabled trap population must carry enough evidence to distinguish a
literature assumption, a fitted effective parameter, and an independently
calibrated parameter set. At minimum, later phases must define:

- material and region applicability;
- carrier species;
- energy reference;
- spatial dimensionality and density unit;
- source or dataset identifier;
- parameter status such as assumed, literature, fitted, or calibrated;
- applicability ranges for field, temperature, and geometry;
- a stable configuration or evidence hash.

A fitted leakage curve does not uniquely identify a microscopic trap species.
Phase J documentation and reports must retain that identifiability limitation.

## Numerical and failure contracts

New rate models must reject invalid states explicitly rather than returning a
plausible number from an undefined expression. Later phases must cover:

- non-finite inputs;
- non-positive temperature;
- negative densities or cross sections;
- energy references outside the selected model definition;
- exponential overflow and underflow;
- zero-thickness links;
- incompatible carrier or barrier definitions;
- solver failure and incomplete propagation.

Zero contribution from a disabled mechanism is distinct from a failed enabled
mechanism. Diagnostics, sweeps, and Robust DTCO failure counts must preserve
that distinction.

## J1 contract state

J1 adds `TrapSpecies` and `TrapAssistedTransportSpec` as immutable,
serializable contracts. It does not execute a rate and it does not attach a
mechanism to `TransportEngine`. The default specification is disabled and
empty. Enabling a specification requires at least one species with positive
volume density.

The initial scope is deliberately narrow:

- electron traps only;
- homogeneous volume density `density_m3` in m^-3;
- a single representative trap position `position_fraction` in `(0, 1)`,
  measured from the source end of a directed link;
- `energy_depth_J = E_C - E_trap > 0`, so a positive value is a level below
  the local conduction-band edge;
- capture cross section in m^2 and attempt frequency in s^-1;
- explicit assumed, literature, fitted, or calibrated parameter status;
- no implicit eV, cm^-3, nm, or percentage conversion.

Every species records a source and applicability statement. A deterministic
SHA-256 hash covers the complete canonical dictionary. The enclosing
configuration has an exact, strict-JSON round trip with its own integrity
hash; duplicate keys, non-finite constants, unknown fields and schema drift
are rejected.

### Selected compact equation for J2

The first kernel is a **sequential two-step WKB** compact model. For one
species on a link of length `L`, let `x = position_fraction * L`. J2 evaluates
two dimensionless WKB leg transmissions, `T_in` from source to the
representative trap and `T_out` from the trap to the destination. Positive
field points from source to destination and lowers electron potential energy
by `q F s`. Relative to the representative trap energy, the raw linear leg
barriers are

\[
U_{\mathrm{in}}(0)=E_d+qFx,\quad U_{\mathrm{in}}(x)=E_d,
\]

\[
U_{\mathrm{out}}(x)=E_d,\quad
U_{\mathrm{out}}(L)=E_d-qF(L-x),
\]

where `E_d = energy_depth_J`. Each WKB action integrates
`sqrt(max(U(s), 0))`; a segment at or below the tunnelling energy contributes
zero action. This clipping is reported by the raw endpoint diagnostics and is
not image-force barrier lowering. With attempt frequency `nu`,

\[
k_{\mathrm{in}}=\nu T_{\mathrm{in}},\qquad
k_{\mathrm{out}}=\nu T_{\mathrm{out}}.
\]

The compact probability that the path encounters an active trap is

\[
p_{\mathrm{active}}=1-\exp(-N_t\sigma L),
\]

where `N_t` is `density_m3` and `sigma` is
`capture_cross_section_m2`. The steady two-state sequential rate selected for
J2 is

\[
\Gamma_{\mathrm{TAT}} = p_{\mathrm{active}}
\frac{k_{\mathrm{in}}k_{\mathrm{out}}}
     {k_{\mathrm{in}}+k_{\mathrm{out}}}.
\]

The denominator-zero case has rate zero. The disabled and zero-density limits
are exactly zero; a slow leg limits the rate; increasing the other leg without
bound approaches the slow-leg rate. J2 exposes both WKB exponents and
transmissions, both leg rates, `p_active`, every species contribution, the
aggregate rate, raw barrier endpoints, deterministic result hashes and an
explicit status. Exponential underflow is an exact zero with status
`transmission_underflow`; invalid geometry, mass or non-finite inputs raise
rather than create a plausible result.

This equation is an NCMemSim compact engineering contract inferred from a
steady two-state sequence. It is **not the full multiphonon** or stochastic
percolation formulation. Primary oxide/Flash literature supports the physical
relevance of inelastic/multiphonon trap-assisted paths and the importance of
trap energy and population: Kang et al., IEEE TED 48 (2001),
[doi:10.1109/16.954471](https://doi.org/10.1109/16.954471), and Ielmini et al.,
IEEE TED 50 (2003),
[doi:10.1109/TED.2003.813236](https://doi.org/10.1109/TED.2003.813236).
The Hurkx junction-recombination model
([doi:10.1109/16.121690](https://doi.org/10.1109/16.121690)) is useful
background but is not claimed as the implemented dielectric-link equation.
Multiphonon coupling, random spatial percolation, trap occupancy interactions,
and device-specific defect calibration remain outside this first kernel.

## J2 isolated kernel state

`evaluate_tat_species` evaluates one trap population.
`evaluate_trap_assisted_transport` preserves ordered per-species diagnostics
and sums contributions with `math.fsum`. The disabled specification returns an
exact zero and no evaluated components. `evaluate_trap_assisted_transport_array`
broadcasts link length, signed field and effective mass, then applies the same
scalar reference kernel at every point; `total_rates_Hz` returns an independent
NumPy array.

The WKB action for a linear leg is integrated analytically and checked against
independent numerical quadrature. Active probability uses `-expm1(-N_t sigma L)`
to retain small-probability accuracy. The harmonic sequential rate is evaluated
through the slow leg to avoid overflow and must not exceed that leg.
Field reversal combined with `position_fraction -> 1-position_fraction` swaps
the two actions and preserves the combined rate.

These rates are conditional pathway frequencies in s^-1. They do not contain
reservoir occupations, Fermi factors, trap-state dynamics, thermal multiphonon
capture, link area, carrier supply or a conversion to A m^-2. J2 therefore does
not claim a device leakage current. `TransportEngine` is untouched, and the
new mechanism cannot alter simulation state until a later integration phase.

```python
from ncmemsim.transport import (
    TrapAssistedTransportSpec,
    TrapParameterStatus,
    TrapSpecies,
    evaluate_trap_assisted_transport,
)

trap = TrapSpecies(
    name="synthetic-electron-trap",
    energy_depth_J=1.602176634e-19,
    position_fraction=0.4,
    density_m3=1.0e23,
    capture_cross_section_m2=1.0e-19,
    attempt_frequency_Hz=1.0e13,
    parameter_status=TrapParameterStatus.ASSUMED,
    source="synthetic J2 documentation example",
    applicability="conditional homogeneous dielectric-link rate only",
)
result = evaluate_trap_assisted_transport(
    TrapAssistedTransportSpec(enabled=True, species=(trap,)),
    link_length_m=8.0e-9,
    electric_field_V_m=2.0e8,
    effective_mass_m0=0.2,
)
assert result.total_rate_Hz >= 0.0
assert result.total_rate_Hz <= min(
    result.components[0].entry_rate_Hz,
    result.components[0].exit_rate_Hz,
)
```

## J3 image-force correction state

J3 adds an independent compact correction contract. For signed link field
`F` and effective image-force relative permittivity `epsilon_r`, the classical
Schottky peak lowering in energy units is

\[
\Delta E_{\mathrm{IF}} =
\sqrt{\frac{q^3 |F|}{4\pi\epsilon_0\epsilon_r}}.
\]

The absolute field makes the magnitude even under field reversal. The
effective image-force permittivity is an explicit input with provenance and
applicability; it is not silently copied from a static material property.
The physical basis and the importance of dielectric response for thin-film
tunnelling are discussed by Simmons, *Journal of Applied Physics* 34 (1963),
[doi:10.1063/1.1702682](https://doi.org/10.1063/1.1702682). Experimental
metal/dielectric barrier measurements also distinguish the square-root
Schottky term and field penetration: Mead, Snow and Deal, *Applied Physics
Letters* 9 (1966), [CaltechAUTHORS record](https://authors.library.caltech.edu/records/ft7c5-rnk11).

`ImageForceBarrierSpec` is disabled by default. When enabled, J3 subtracts the
same compact peak-lowering energy from the source and destination interface
heights of the J2 trap-referenced profile. The trap height itself is unchanged.
This is a symmetric two-interface engineering approximation, not the full
spatial image potential, a self-consistent electrostatic solution, or a
one-sided Schottky-junction current law. Every result retains:

- the complete unmodified J2 barrier profile;
- source and destination lowering energies;
- signed corrected interface heights before WKB clipping;
- explicit `disabled`, `zero_field`, `applied`, or `barrier_suppressed` status;
- the correction configuration hash and both TAT/correction hashes on the
  aggregate result.

A corrected interface height at or below the tunnelling reference is retained
as a signed diagnostic. The existing J2 WKB rule then integrates
`sqrt(max(U, 0))`; J3 does not hide this condition by silently replacing the
diagnostic with zero. A disabled correction and an enabled correction at zero
field are exact no-ops. Field reversal combined with mirroring the trap
position swaps the two actions and preserves the combined conditional rate.

```python
from ncmemsim.transport import (
    ImageForceBarrierSpec,
    TrapAssistedTransportSpec,
    TrapParameterStatus,
    TrapSpecies,
    evaluate_trap_assisted_transport_with_barrier_correction,
)

trap = TrapSpecies(
    name="synthetic-j3-trap",
    energy_depth_J=1.602176634e-19,
    position_fraction=0.4,
    density_m3=1.0e23,
    capture_cross_section_m2=1.0e-19,
    attempt_frequency_Hz=1.0e13,
    parameter_status=TrapParameterStatus.ASSUMED,
    source="synthetic J3 documentation example",
    applicability="conditional homogeneous dielectric-link rate only",
)
correction = ImageForceBarrierSpec(
    enabled=True,
    relative_permittivity=3.9,
    parameter_status=TrapParameterStatus.LITERATURE,
    source="study-selected effective image-force permittivity",
    applicability="symmetric two-interface compact correction",
)
result = evaluate_trap_assisted_transport_with_barrier_correction(
    TrapAssistedTransportSpec(enabled=True, species=(trap,)),
    correction,
    link_length_m=8.0e-9,
    electric_field_V_m=2.0e8,
    effective_mass_m0=0.2,
)
assert result.total_rate_Hz >= 0.0
assert result.components[0].barrier_diagnostics.unmodified_profile.trap_barrier_J == trap.energy_depth_J
```

The J3 output remains a conditional pathway frequency. It is not a current
density, a calibrated oxide-defect model or evidence that image-force lowering
is required for a particular device. `TransportEngine` remains untouched;
explicit link attachment and state isolation begin in J4.

## Validation ladder

Phase J uses a staged validation ladder.

1. **Dimensional and sign checks** verify canonical units and field direction.
2. **Analytic limiting cases** verify disabled, zero-density, low-field, and
   high-barrier limits.
3. **Independent kernel references** compare the selected equations against
   directly evaluated reference expressions.
4. **Transport integration tests** verify contribution accounting and state
   isolation on explicit links.
5. **Retention/programming regressions** verify the unchanged v1 baseline when
   the mechanisms are disabled and controlled changes when enabled.
6. **DTCO and Robust DTCO integration** verifies provenance, failures,
   serialization, and reproducibility.
7. **Clean distributions and supported-runtime CI** verify installed behavior
   before the final v1.1.0 tag.

Synthetic examples demonstrate deterministic implementation behavior only.
Experimental qualification requires independent measurements and predeclared
criteria.


## J4 explicit transport-network integration

J4 leaves `TransportEngine` as the stable direct-tunnelling implementation and
adds `AdvancedTransportEngine` as an explicit wrapper. A study supplies an
`AdvancedTransportSpec` containing exact `TATLinkAttachment.link_id` values.
Unknown and duplicate identifiers are configuration errors; unlisted links are
reported as `not_attached` and never receive an inferred mechanism.

```python
from ncmemsim.transport import (
    AdvancedTransportEngine,
    AdvancedTransportSpec,
    ImageForceBarrierSpec,
    MechanismEvaluationStatus,
    TATLinkAttachment,
    TransportEngine,
    TransportMechanism,
    TrapAssistedTransportSpec,
)

direct = TransportEngine(tunneling_engine)
attachment = TATLinkAttachment(
    link_id="FG1<->FG2",
    specification=TrapAssistedTransportSpec(enabled=True, species=trap_species),
    barrier_correction=ImageForceBarrierSpec(),
)
transport = AdvancedTransportEngine(
    direct,
    AdvancedTransportSpec((attachment,)),
)
```

The J2/J3 aggregate conditional frequency is split with the existing signed
potential-difference convention. For an inter-FG link, the two directed rates
are multiplied by the same available-electron and empty-destination sheet
densities used by the direct engine. The resulting signed TAT flux is added to
the retained direct flux. Substrate links are diagnostic only because
`OccupancyEngine` already owns substrate injection and emission.

Every `IntegratedLinkTransportResult` retains the complete legacy
`LinkTransportResult`, two explicit `MechanismContribution` records and the
reconstructible totals. The composite step uses the summed inter-FG flux on a
copy of the candidate state, applies the existing transfer-fraction and
occupation bounds, and rebalances the update to conserve electron sheet
density.

Optional-mechanism exceptions are caught per link and represented by
`MechanismEvaluationStatus.FAILED` plus `MechanismFailure`. The failed TAT
contribution is exactly zero; the direct contribution and later links are not
discarded. Structural errors such as an attachment to a nonexistent link fail
before optional evaluation because they invalidate the study configuration.

J4 does not claim that the synthetic trap parameters establish dielectric
defect density, leakage current or retention accuracy for a fabricated device.
Those questions remain part of J5 validation, sensitivity and identifiability.

## Delivery sequence

### J0 - scope and architecture freeze

- start `1.1.0.dev0` from the published v1.0.0 tag;
- preserve v1 API, result, archive, and scientific contracts;
- define mechanism boundaries, units, provenance, failures, and validation;
- keep CI and Documentation automatic pushes limited to `main` until final
  version preparation; both remain manually runnable.

### J1 - trap and defect contracts

- define immutable trap/defect specifications;
- select and document the first TAT equation;
- fix energy, field, carrier, and dimensional conventions;
- add serialization and provenance hashes without executing new physics.

### J2 - trap-assisted transport kernel

- implement the selected scalar/vectorized rate contribution;
- expose component diagnostics;
- test analytic limits, numerical range, invalid inputs, and reproducibility.

### J3 - image-force and barrier corrections (complete)

- define the explicit opt-in Schottky peak-lowering contract with provenance;
- preserve unmodified and signed corrected barrier diagnostics;
- verify exact disabled/zero-field limits, sign symmetry, barrier suppression,
  deterministic hashing and unchanged J2 behavior when disabled.

### J4 - transport-network integration (complete)

- attach enabled mechanisms to explicit links;
- keep candidate state isolated;
- preserve per-link and per-mechanism accounting;
- propagate failures without corrupting neighboring candidates.

### J5 - scientific validation and sensitivity

- add controlled electrical/retention references;
- record parameter sensitivity and identifiability limits;
- verify DTCO and Robust DTCO integration without yield claims.

### J6 - reproducible examples and reports

- provide normal and deliberate-failure references;
- export mechanism-resolved results and provenance;
- document interpretation and limitations.

### J7 - final release gates

- audit version, citation, API additions, docs, and archives;
- run the full regression and strict documentation locally;
- validate clean wheel and source-distribution installations;
- require green Python 3.11-3.13 CI and Documentation on the exact final
  candidate commit before tagging v1.1.0.

## Explicitly outside J0

J0 does not introduce or approve:

- numerical trap-assisted rates;
- a universal trap distribution for Ge/GeSn memory stacks;
- experimental leakage or retention calibration;
- self-consistent Poisson-carrier iteration;
- multi-phonon, non-radiative multiphonon, or atomistic defect calculations;
- quantum confinement or a higher-fidelity TCAD replacement;
- breaking changes to the stable v1 API.

These items require separate equations, provenance, tests, and review.

## J0 acceptance state

J0 is complete when the development version and documentation consistently
identify `1.1.0.dev0`, the latest stable citation remains `1.0.0`, the new page
is present in navigation and source-distribution inventory, the workflow policy
does not run expensive Actions for ordinary development pushes, and focused
checks confirm that no simulator physics or stable API path was changed.
