# Advanced transport physics

## Status and purpose

This page defines the Phase J development contract for NCMemSim v1.1.0.
The current `1.1.0.dev0` bootstrap is **J0 only**: it introduces scope,
interfaces, invariants, validation requirements, and a delivery sequence. It
does not yet add trap-assisted transport, defect-mediated currents,
image-force barrier lowering, or new calibrated material parameters.

The published v1.0.0 direct-tunnelling and retention behavior remains the
reference baseline. All future Phase J mechanisms must be opt-in and must
reproduce that baseline exactly when disabled.

## Scientific objective

Phase J will extend the compact transport layer so that a study can represent
well-defined additional conduction mechanisms without hiding their origin in
an effective tunnelling prefactor. The first target is trap-assisted transport
through dielectric links. Image-force barrier lowering may be added after its
electrostatic and sign conventions are independently fixed and tested.

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

J0 does not select the final trap-assisted equation. J1 must record the exact
equation, literature provenance, validity range, and limiting behavior before
J2 implements it.

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

### J3 - image-force and barrier corrections

- define explicit opt-in barrier-lowering contracts;
- preserve unmodified barrier diagnostics;
- verify sign symmetry, limits, and applicability.

This stage may be deferred if its scientific contract is not sufficiently
supported. Deferral does not block a narrower, accurately described v1.1.0.

### J4 - transport-network integration

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
