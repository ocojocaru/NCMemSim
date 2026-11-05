# Scientific scope and assumptions

> **Release context:** Included in published NCMemSim v1.10.0. See [current platform status](platform_status.md) for implemented extensions and limits. Earlier phase/version statements identify their original checkpoint or retained default path.

## Purpose

NCMemSim is a compact scientific simulator for nanocrystal floating-gate
nonvolatile-memory structures.

Version 0.10.0 supports electrical, retention, optical, and electro-optical
studies of devices containing one or more nanocrystal floating gates embedded
in dielectric multilayer stacks.

The simulator is designed primarily for:

- mechanism studies;
- controlled comparison of device configurations;
- electrical programming and erase studies;
- charge-retention studies;
- Ge/GeSn composition studies;
- wavelength-dependent optical-response studies;
- photo-assisted programming;
- combined electro-optical programming;
- parameter sweeps;
- reproducible design-space exploration;
- deterministic design-technology co-optimization (DTCO).

NCMemSim is intentionally a compact-model framework. It is not intended to
replace a full multidimensional TCAD, atomistic, quantum-transport, or
electromagnetic solver.

## Current verified model scope

The v0.10.0 verified model covers Phases A through E6.

The electrical framework includes:

- ordered one-dimensional multilayer device geometry;
- one, two, or three floating-gate structures;
- independent floating-gate state representations;
- three-state nanocrystal occupation;
- compact electrostatic coupling;
- local one-dimensional potential and electric-field reconstruction;
- WKB-type tunnelling;
- electrical charge-state kinetics;
- explicit inter-floating-gate transport;
- conservative internal charge redistribution;
- voltage relaxation;
- voltage sweeps;
- compact C-V simulation;
- retention simulation.

The optical framework includes:

- monochromatic optical sources;
- photon-energy calculations;
- incident photon-flux calculations;
- wavelength-dependent Ge/GeSn optical response;
- separate direct-Gamma, indirect phonon-assisted, and Urbach-tail absorption
  contributions;
- Beer-Lambert floating-gate absorption;
- nanocrystal-volume-fraction effective absorption;
- absorbed photon flux;
- average volumetric optical generation;
- absorbed photon rate per nanocrystal;
- photo-assisted charge-state transitions;
- electrical-only, optical-assisted, and electro-optical programming;
- optical diagnostics in simulator workflows;
- SWIR wavelength-sweep validation;
- SWIR programming and voltage-reduction benchmarks.

The complete v0.10.0 validation suite contains 194 tests.

## Device representation

A device is represented as an ordered one-dimensional stack of dielectric,
floating-gate, and substrate regions.

Each floating-gate layer may specify quantities including:

- nanocrystal material;
- nanocrystal diameter;
- nanocrystal volume fraction;
- electrically active fraction;
- physical thickness;
- state discretization.

The one-dimensional coordinate is normal to the device stack.

The current compact model does not explicitly resolve random lateral
nanocrystal positions, lateral field variations, individual nanocrystal
contacts, or three-dimensional electrostatic field enhancement.

## Charge-state approximation

Each nanocrystal population is represented using three occupation states:

\[
P_0,\qquad P_1,\qquad P_2,
\]

with

\[
P_0 + P_1 + P_2 = 1.
\]

These states represent empty, singly occupied, and doubly occupied
nanocrystals.

This is a deliberately reduced state space. Higher charge states, detailed
many-body spectra, and explicit microscopic trap populations are outside the
current model.

## Electrical-model scope

Electrical programming and retention are represented using compact
electrostatics, local electric fields, WKB-type tunnelling, and charge-state
kinetics.

The electrical model is intended to capture physically meaningful trends and
coupling between geometry, barriers, fields, charge occupation, and retention.

It does not constitute a complete microscopic transport solution.

In particular, the current release does not explicitly include:

- full Poisson-Schrodinger self-consistency;
- multidimensional electrostatics;
- coherent quantum transport;
- a universal microscopic defect-transport or spatial image-potential solver;
- non-parabolic-band transport;
- detailed interface-state distributions;
- mobile ionic charge;
- full semiconductor carrier-statistics coupling.

Opt-in compact TAT/image-force corrections are implemented; see
[advanced transport](advanced_transport.md). Explicit barrier profiles and direct
inter-FG replacements are available through [Phase S](barrier_transport.md). These
are separate reviewed approximations, not the microscopic solvers excluded above.

Some omitted effects may be represented indirectly through effective fitted
parameters, but such use must be documented as an effective-model
approximation.

## Multi-floating-gate transport

Multi-FG devices are represented through explicit transport nodes and tunnel
links.

Internal floating-gate redistribution is availability limited and designed to
preserve charge conservation within numerical tolerance.

This allows NCMemSim to study charge redistribution between floating gates
without treating each FG as a completely isolated subsystem.

The transport network remains a compact representation and does not resolve
the microscopic path of individual carriers.

## Retention scope

Retention simulations evolve an initially programmed state at fixed external
bias, normally zero gate bias.

The retention model can update:

- electrostatics;
- local electric fields;
- tunnelling rates;
- charge-state occupation;
- inter-floating-gate redistribution.

The solver supports increasing timesteps for efficient simulation over broad
time ranges.

Long-time retention predictions remain sensitive to barrier heights, effective
masses, attempt frequencies, transport assumptions, and other compact-model
parameters.

Agreement over short simulated times does not by itself establish the accuracy
of a multi-year extrapolation.

## Optical-model scope

Version 0.10.0 introduces the first verified optical-programming framework in
NCMemSim.

The current optical implementation focuses on monochromatic excitation.

For a specified wavelength and incident optical power density, the model
evaluates:

- photon energy;
- incident photon flux;
- nanocrystal absorption coefficient;
- effective floating-gate absorption coefficient;
- absorbed photon fraction;
- absorbed and transmitted photon flux;
- average volumetric generation rate;
- absorbed photon rate per nanocrystal.

The optical response is coupled to the occupancy model through configurable
photo-assisted transition rates.

## Ge/GeSn optical model

The v0.10.0 optical material model distinguishes the optical direct-Gamma and
indirect-L gaps from the compact electronic band-gap information used by the
electrical model.

The absorption coefficient contains:

\[
\alpha
=
\alpha_{\Gamma}
+
\alpha_L
+
\alpha_U,
\]

representing:

- direct-Gamma absorption;
- indirect phonon-assisted absorption;
- Urbach-tail absorption.

The direct-gap composition dependence is literature based.

The indirect-gap model is literature informed and should be treated as a
versioned compact parameterization rather than a universal material law.

Absolute optical absorption amplitudes remain provisional unless independently
calibrated.

## Optical effective-medium assumption

For optical absorption, the current floating-gate model uses

\[
\alpha_{\mathrm{eff}}
=
f_{\mathrm{NC}}\alpha_{\mathrm{NC}},
\]

where \(f_{\mathrm{NC}}\) is the nanocrystal volume fraction.

The HfO2 matrix is treated as optically transparent in the current Phase E
model.

The implementation does not yet include:

- detailed effective-medium electrodynamics;
- an automatically inferred matrix optical-response law;
- multiple optical scattering;
- interference in the multilayer stack;
- complete wavelength-dependent refractive-index propagation.

The nanocrystal volume fraction used for optical absorption is distinct from
the electrically active fraction used by the charge-state model.

## Photo-assisted programming

Absorbed photons contribute additional transition rates to the nanocrystal
charge-state kinetics.

The default compact photo-loading model enables:

\[
0 \rightarrow 1
\]

and

\[
1 \rightarrow 2.
\]

Photo-assisted detrapping is disabled by default.

Electrical and optical rates combine additively, allowing simulation of:

- electrical-only programming;
- optical-assisted programming at zero gate bias;
- electro-optical programming.

The photo-capture efficiency is phenomenological in v0.10.0 and is not
experimentally calibrated by default.

## Voltage dependence of optical response

For a fixed optical source and material, the v0.10.0 absorption model is
voltage independent.

The current model therefore does not explicitly include:

- Franz-Keldysh absorption;
- Stark shifts;
- field-dependent band-edge shifts;
- state filling.

These effects require explicit future model extensions rather than silent
reinterpretation of the existing optical parameters.

## Multi-FG optical propagation

The retained default monochromatic `LightSource` path evaluates each FG with the
same incident source independently. That default is preserved for compatibility.
Published v1.5 adds explicit spectral sources and ordered single-pass propagation:

```text
spectral source -> passive/FG layers in declared order -> transmitted output
```

Use the [broadband/spectral context](broadband_optics.md) for sequential attenuation,
per-layer active/passive absorption and photon/energy accounting. It is an opt-in
route, not an implicit change to the default optical model. Coherent interference,
multiple scattering and a full-wave/effective-medium solver remain outside scope.

## Strain and quantum confinement

The current optical model does not explicitly calculate strain-dependent band
structure for a particular fabricated GeSn layer or nanocrystal ensemble.

The retained default does not apply structural corrections automatically.
Opt-in [structural profiles](strain_confinement.md) implement hydrostatic
strain-induced transition shifts and spherical kinetic confinement of optical
gaps. These are not a general strain band-structure or interacting finite-barrier model.

These effects can become important depending on:

- Sn composition;
- nanocrystal diameter;
- strain state;
- surrounding matrix;
- fabrication history.

Results should therefore not be presented as quantitatively predictive of a
specific nanostructure unless these effects are shown to be negligible or are
included through a validated future model.

## Spectral applicability

The optical parameterizations are based on literature data and compact
interpolation models with finite composition and wavelength ranges.

Use outside the underlying experimental range constitutes extrapolation.

In particular, the v0.10.0 SWIR validation includes a 12% Sn case that extends
beyond the principal 0-10% Sn experimental composition range used for guidance.

Such cases are useful for testing model behaviour and trends but should be
identified explicitly as extrapolative.

## Parameter provenance

NCMemSim distinguishes among:

1. literature-supported physical parameters or model structures;
2. provisional compact-model parameters;
3. fitted effective parameters;
4. experimentally calibrated device-specific parameters.

These categories must not be treated as equivalent.

A parameter included in the default configuration is not automatically an
experimentally established material constant.

Scientific use should report, where relevant:

- parameter value;
- unit;
- source;
- model version;
- composition range;
- wavelength range;
- temperature;
- strain assumption;
- calibration status;
- extrapolation status.

## Verification versus experimental validation

NCMemSim uses the term **verification** for tests that establish that the
software behaves consistently with the implemented equations, numerical
conventions, regression baselines, and physical invariants.

Examples include:

- probability normalization;
- charge conservation;
- regression against retained reference calculations;
- non-negative absorption coefficients;
- non-negative photon rates;
- dark-source behaviour;
- spectral ordering;
- deterministic golden cases.

This is different from **experimental validation**.

Experimental validation requires comparison with appropriate measurements from
real devices or materials.

The v0.10.0 optical model has been verified as a software implementation but
has not yet been fully calibrated and validated against a specific fabricated
Ge/GeSn nanocrystal memory.

## SWIR benchmark interpretation

The Phase E6 SWIR benchmarks demonstrate that the implemented model produces
spectrally consistent photo-assisted programming.

For the GeSn 8% voltage-reduction benchmark, a deliberately weak coupling

```text
photo_capture_efficiency = 1e-10
```

is used so that the dark and illuminated occupation curves share a common
comparison range.

The resulting voltage reductions are approximately:

| Wavelength | Delta V |
|---:|---:|
| 1300 nm | 0.0781 V |
| 1550 nm | 0.0885 V |
| 1700 nm | 0.0930 V |

These values demonstrate the behaviour of the compact model under the selected
benchmark conditions.

They are **not experimentally calibrated predictions** of the programming
voltage reduction of a fabricated device.

## Appropriate scientific use

Version 0.12.0 is appropriate for studies such as:

- comparison of one-, two-, and three-FG architectures;
- sensitivity to dielectric thickness;
- sensitivity to nanocrystal diameter;
- sensitivity to nanocrystal volume fraction;
- sensitivity to electrically active fraction;
- Ge versus GeSn comparison;
- Sn-composition trends;
- programming and erase trends;
- charge redistribution;
- retention trends;
- wavelength-dependent optical-response trends;
- electrical versus electro-optical programming;
- relative SWIR programming efficiency;
- controlled voltage-reduction studies;
- reproducible parameter sweeps;
- deterministic DTCO sweeps, feasibility and Pareto trade-offs;
- adjacent-grid sensitivity with explicit coverage and units.

## Uses requiring additional validation

Additional physical modelling or experimental calibration is required before
using NCMemSim v0.12.0 for claims such as:

- absolute prediction of programming voltage for a fabricated device;
- absolute prediction of optical quantum efficiency;
- quantitative prediction of measured absorption without calibration;
- quantitative prediction of multi-year retention without validated transport
  parameters;
- microscopic interpretation of individual defects;
- three-dimensional field-enhancement prediction;
- strain-resolved GeSn band-structure prediction;
- quantum-confinement-resolved optical spectra;
- full multilayer optical propagation;
- endurance or breakdown prediction.

## Current validation baseline

Version v1.0.0 preserves the electrical/optical and fitting/calibration
baselines, nominal/Robust DTCO and linked scientific workflow evidence.

The historical v1.0 preparation validation record contains:

```text
more than 2200 tests
```

and covers retained Phases A–F, 717 Phase G/H and 192 Phase I cases.

Those are historical preparation counts, not the v1.10 suite size. Current
release and metadata closure passed supported-runtime CI; see
[current status](platform_status.md). Every new commit still requires its own CI.

Phase I final preparation verifies clean installed wheel/source workflows and
strict documentation locally; remote gates and publication follow the prepared commit.
This is software verification,
not independent physical validation of every material or device.

Future changes to physical assumptions or numerical behaviour should preserve
this baseline through explicit regression testing or document intentionally
reviewed changes.

## Future scientific scope

The next development stages are expected to focus on:

- calibrated optical absorption;
- calibrated photo-capture parameters;
- broader strain-dependent optical models beyond implemented hydrostatic shifts;
- confinement beyond the implemented spherical kinetic approximation;
- field-dependent optical response;
- coherent/full-wave propagation beyond implemented sequential single-pass optics;
- correlated and experimentally qualified uncertainty models beyond the
  implemented independent bounded DTCO marginals;
- adaptive optimization beyond deterministic Cartesian grids.

These remaining research directions are distinct from the shipped opt-in
extensions. See the delivered/research split in the [roadmap](roadmap.md).
