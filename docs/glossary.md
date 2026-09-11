# Glossary and notation

This page defines the principal terms, symbols, abbreviations, and conventions
used in the NCMemSim v0.10.0 documentation.

## General terms

### NCMemSim

Nanocrystal Memory Simulator.

A compact scientific simulation framework for nanocrystal floating-gate
nonvolatile memories, including electrical, retention, optical, and
electro-optical modelling.

### NVM

Nonvolatile memory.

A memory technology in which stored information can persist without continuous
electrical power.

### FG

Floating gate.

A charge-storage region electrically isolated by surrounding dielectric
material.

### NC

Nanocrystal.

In NCMemSim, nanocrystals form the discrete charge-storage population inside a
floating-gate layer.

### GeSn

Germanium-tin alloy, written compositionally as

\[
\mathrm{Ge}_{1-x}\mathrm{Sn}_x,
\]

where \(x\) is the Sn atomic fraction used by the compact composition model.

### DTCO

Design-technology co-optimization.

Systematic exploration of device geometry, materials, physical parameters, and
operating conditions to identify useful design trade-offs.

### SWIR

Short-wave infrared.

In NCMemSim v0.10.0, SWIR wavelengths are used to study the wavelength-dependent
optical response and photo-assisted programming of Ge/GeSn nanocrystal memory
structures.

## Device and geometry notation

### \(z\)

One-dimensional spatial coordinate normal to the device stack.

Internal physical calculations use SI units, so \(z\) is represented in metres
after conversion from user-facing geometry values where applicable.

### \(t_i\)

Thickness of layer \(i\).

### \(t_{\mathrm{FG}}\)

Physical thickness of a floating-gate layer.

### \(d_{\mathrm{NC}}\)

Nanocrystal diameter.

### \(R_{\mathrm{NC}}\)

Nanocrystal radius,

\[
R_{\mathrm{NC}}
=
\frac{d_{\mathrm{NC}}}{2}.
\]

### \(f_{\mathrm{NC}}\)

Nanocrystal volume fraction inside a floating-gate layer.

In the v0.10.0 optical model, this quantity scales the nanocrystal absorption
coefficient to obtain the effective floating-gate absorption coefficient.

It is distinct from the electrically active fraction used by the charge model.

### Electrically active fraction

Fraction of the nanocrystal population assumed to participate in electrical
charge storage.

This parameter belongs to the charge-state model and must not be silently
substituted for the nanocrystal volume fraction used by the optical absorption
model.

## Charge-state notation

### \(P_0\)

Probability that a nanocrystal is empty.

### \(P_1\)

Probability that a nanocrystal contains one stored electron.

### \(P_2\)

Probability that a nanocrystal contains two stored electrons.

The charge-state probabilities satisfy

\[
P_0 + P_1 + P_2 = 1.
\]

### \(\langle n \rangle\)

Mean number of stored electrons per nanocrystal,

\[
\langle n \rangle
=
P_1 + 2P_2.
\]

### \(Q_{\mathrm{FG},i}\)

Sheet charge associated with floating gate \(i\).

### \(Q_{\mathrm{FG}}\)

Total floating-gate charge,

\[
Q_{\mathrm{FG}}
=
\sum_i Q_{\mathrm{FG},i}.
\]

## Electrostatic notation

### \(V_g\)

Applied gate voltage.

### \(V(z)\)

One-dimensional electrostatic potential through the device stack.

### \(E(z)\)

Electric field,

\[
E(z)
=
-\frac{\mathrm{d}V}{\mathrm{d}z}.
\]

### \(\varepsilon_0\)

Vacuum permittivity.

### \(\varepsilon_r\)

Relative dielectric permittivity.

### \(C_{\mathrm{eq}}\)

Equivalent capacitance of the compact dielectric stack.

For a series stack,

\[
\left(
\frac{C_{\mathrm{eq}}}{A}
\right)^{-1}
=
\sum_i
\frac{t_i}{\varepsilon_0\varepsilon_{r,i}}.
\]

### \(\Delta V_{\mathrm{FB}}\)

Floating-gate-charge-induced flat-band voltage shift.

For multiple floating gates, NCMemSim retains individual FG contributions
before evaluating the total compact shift.

### MW

Memory window.

A voltage-domain measure of hysteresis or state separation used in memory
characterization.

Its precise extraction depends on the selected simulation or experimental
definition and should therefore be reported together with the extraction
method.

## Nanocrystal charging notation

### \(C_{\mathrm{NC}}\)

Compact nanocrystal self-capacitance.

A common approximation used by NCMemSim is

\[
C_{\mathrm{NC}}
\approx
4\pi
\varepsilon_0
\varepsilon_{\mathrm{cap}}
R_{\mathrm{NC}}.
\]

### \(E_c\)

Nanocrystal charging energy,

\[
E_c
=
\frac{q^2}{2C_{\mathrm{NC}}}.
\]

### \(q\)

Magnitude of the elementary charge.

The electron itself carries charge \(-q\).

## Electrical transport notation

### WKB

Wentzel-Kramers-Brillouin approximation.

NCMemSim uses a compact semiclassical WKB-type model to estimate tunnelling
through effective barriers.

### \(T\)

Tunnelling transmission probability.

Conceptually,

\[
T
\sim
\exp
\left[
-2
\int
\frac{\sqrt{2m^*[U(z)-E]}}{\hbar}
\,\mathrm{d}z
\right].
\]

### \(m^*\)

Effective carrier mass used by the compact tunnelling model.

### \(U(z)\)

Effective tunnelling barrier profile.

### \(r_{01}\)

Transition rate from the empty state to the singly occupied state.

### \(r_{12}\)

Transition rate from the singly occupied state to the doubly occupied state.

### \(r_{21}\)

Transition rate from the doubly occupied state to the singly occupied state.

### \(r_{10}\)

Transition rate from the singly occupied state to the empty state.

Electrical and optical contributions may be distinguished using superscripts,
for example

\[
r_{01}^{\mathrm{elec}}
\]

and

\[
r_{01}^{\mathrm{photo}}.
\]

## Compact electrical diagnostics

### \(m\)

Normalized nanocrystal occupation,

\[
m
=
\frac{P_1 + 2P_2}{2}.
\]

With the three-state model used in v0.10.0,

\[
0 \le m \le 1.
\]

This normalized quantity is distinct from the mean electron occupation
\(\langle n \rangle = P_1 + 2P_2\).

### \(V_{\mathrm{FB}}\)

Flat-band voltage used by the compact electrostatic and C-V representation.

### \(V_{\mathrm{eff}}\)

Effective electrostatic voltage used internally by the compact electrical
model.

Its precise construction depends on the electrostatic state and should be
interpreted according to the corresponding simulator diagnostic rather than as
an independently applied terminal voltage.

### `tprog`

Compact programming transmission/rate diagnostic produced by the electrical
tunnelling model.

Its numerical meaning is model dependent and should not automatically be
interpreted as a directly measured programming time.

### `terase`

Compact erase transmission/rate diagnostic produced by the electrical
tunnelling model.

Its numerical meaning is model dependent and should not automatically be
interpreted as a directly measured erase time.

## Optical-source notation

### `LightSource`

NCMemSim object describing an optical excitation source.

The verified v0.10.0 Phase E workflow focuses on monochromatic excitation.

### \(\lambda\)

Optical wavelength.

User-facing optical wavelengths are commonly specified in nanometres.

### \(h\)

Planck constant.

### \(c\)

Speed of light in vacuum.

### \(E_\gamma\)

Photon energy,

\[
E_\gamma
=
\frac{hc}{\lambda}.
\]

Photon energy may be represented in joules or electronvolts depending on the
API quantity.

### \(P_{\mathrm{opt}}\)

Incident optical power density, in

\[
\mathrm{W\,m^{-2}}.
\]

### \(\Phi_\gamma\)

Incident photon flux,

\[
\Phi_\gamma
=
\frac{P_{\mathrm{opt}}}{E_\gamma}.
\]

Its SI unit is

\[
\mathrm{m^{-2}\,s^{-1}}.
\]

### Disabled optical source

A source configuration that retains wavelength-dependent material information
but supplies zero incident optical power.

For such a source:

- incident photon flux is zero;
- absorbed photon flux is zero;
- photo-transition rates are zero;
- wavelength-dependent absorption coefficients may remain defined.

### Dark simulation

A simulation performed without an active optical excitation.

Photo-assisted transition rates are zero in the dark path.

## Ge/GeSn optical notation

### \(E_{g,\Gamma}\)

Direct optical band gap at the Gamma valley.

The v0.10.0 compact model evaluates this quantity as a function of GeSn
composition.

### \(E_{g,L}\)

Indirect optical band gap associated with the L valley.

This quantity is represented separately from the direct-Gamma gap.

### Direct-Gamma transition

Direct optical transition represented by the direct component of the compact
Ge/GeSn absorption model.

### Indirect-L transition

Indirect optical transition involving the L-valley gap and phonon-assisted
absorption.

### Phonon occupation

Temperature-dependent occupation factor used by the compact indirect
absorption contribution.

### Urbach tail

Sub-band-edge absorption contribution used to represent the exponential
absorption tail near the optical edge.

### \(E_U\)

Urbach energy controlling the characteristic energy scale of the Urbach-tail
contribution.

## Optical absorption notation

### \(\alpha_{\Gamma}\)

Direct-Gamma contribution to the nanocrystal absorption coefficient.

### \(\alpha_L\)

Indirect phonon-assisted contribution to the nanocrystal absorption
coefficient.

### \(\alpha_U\)

Urbach-tail contribution to the nanocrystal absorption coefficient.

### \(\alpha_{\mathrm{NC}}\)

Total nanocrystal absorption coefficient,

\[
\alpha_{\mathrm{NC}}
=
\alpha_{\Gamma}
+
\alpha_L
+
\alpha_U.
\]

Its SI unit is

\[
\mathrm{m^{-1}}.
\]

### \(\alpha_{\mathrm{eff}}\)

Effective absorption coefficient of the floating-gate composite layer.

In v0.10.0,

\[
\alpha_{\mathrm{eff}}
=
f_{\mathrm{NC}}
\alpha_{\mathrm{NC}}.
\]

The current model treats the HfO2 matrix as optically transparent.

### Optical depth

Dimensionless Beer-Lambert quantity

\[
\tau_{\mathrm{opt}}
=
\alpha_{\mathrm{eff}}t_{\mathrm{FG}}.
\]

### \(A_{\mathrm{abs}}\)

Absorbed optical fraction,

\[
A_{\mathrm{abs}}
=
1-
\exp
\left(
-\alpha_{\mathrm{eff}}t_{\mathrm{FG}}
\right).
\]

This symbol denotes optical absorption fraction here and should not be confused
with device area \(A\) when both quantities occur in the same derivation.

### \(\Phi_{\mathrm{abs}}\)

Absorbed photon flux,

\[
\Phi_{\mathrm{abs}}
=
A_{\mathrm{abs}}\Phi_\gamma.
\]

### \(\Phi_{\mathrm{trans}}\)

Transmitted photon flux after the compact floating-gate absorption step.

For a single Beer-Lambert layer,

\[
\Phi_{\mathrm{trans}}
=
\Phi_\gamma
-
\Phi_{\mathrm{abs}}.
\]

### \(G_{\mathrm{avg}}\)

Average volumetric optical generation rate inside the floating-gate layer.

Its SI unit is

\[
\mathrm{m^{-3}\,s^{-1}}.
\]

## Photo-assisted kinetics

### Absorbed photon rate per nanocrystal

Number of absorbed photons associated with one nanocrystal per unit time under
the compact ensemble model.

It provides the physical input from which the photo-assisted transition rate
is constructed.

### \(\eta_{\mathrm{photo}}\)

Photo-capture efficiency.

A compact phenomenological coupling parameter converting absorbed photon rate
per nanocrystal into photo-assisted charge-state transition rates.

In v0.10.0, this parameter is not experimentally calibrated by default.

It should not be interpreted automatically as an independently measured
external or internal quantum efficiency.

### `PhotoTransitionConfig`

Configuration object controlling photo-assisted transition-rate generation,
including photo-capture efficiency.

### `PhotoTransitionWeights`

Configuration describing the relative weighting of photo-assisted transitions.

The default v0.10.0 model enables photo-assisted loading through

\[
0\rightarrow1
\]

and

\[
1\rightarrow2,
\]

while photo-assisted detrapping is disabled by default.

### `PhotoTransitionRates`

Container for photo-assisted transition-rate arrays.

### Photo-transition rate

Transition-rate contribution generated from absorbed optical excitation.

It is distinguished from the electrical tunnelling contribution.

## Coupled electro-optical notation

### Electrical-only programming

Programming in which the charge-state kinetics are driven by electrical
transition rates without an active optical contribution.

Conceptually,

\[
r_{ij}
=
r_{ij}^{\mathrm{elec}}.
\]

### Optical-assisted programming

Programming in which optical excitation contributes to charge-state loading.

This may include the zero-gate-bias case used in Phase E validation.

### Electro-optical programming

Programming with simultaneous electrical and optical contributions.

The total compact transition rate is

\[
r_{ij}
=
r_{ij}^{\mathrm{elec}}
+
r_{ij}^{\mathrm{photo}}.
\]

### \(\Delta V\)

Programming-voltage reduction used in the Phase E6 benchmark.

For a common target occupation,

\[
\Delta V
=
V_{\mathrm{dark}}
-
V_{\mathrm{light}}.
\]

A positive value therefore means that illumination reduces the gate voltage
required to reach the selected occupation target.

## Retention terminology

### Retention

Evolution of a previously programmed charge state with time under a specified
external bias, normally zero gate bias.

### Retention fraction

Fraction of the selected initial stored charge remaining at a later time.

### Charge-loss fraction

Fraction of the selected initial charge that has been lost at a later time.

### Quasi-equilibrium

A numerical condition indicating that further evolution has become sufficiently
small according to the selected retention criterion.

It does not imply full thermodynamic equilibrium.

## Numerical terminology

### Dwell time

Physical time for which the simulator evolves a state at a selected voltage.

### Internal timestep

Numerical timestep used to subdivide a dwell interval.

### \(\Delta t_{\mathrm{actual}}\)

Effective integration timestep,

\[
\Delta t_{\mathrm{actual}}
=
\frac{t_{\mathrm{dwell}}}{N_{\mathrm{steps}}}.
\]

This ensures that the total integrated interval equals the requested dwell
time.

### Sweep

Ordered sequence of voltage points evaluated sequentially.

The final state from one voltage point becomes the initial state for the next
point unless a workflow explicitly defines otherwise.

### C-V

Capacitance-voltage.

NCMemSim provides a compact C-V-style workflow built on the simulator's charge
and electrostatic response.

It should not automatically be interpreted as a complete transient
small-signal TCAD calculation.

## Validation terminology

### Verification

Demonstration that the software behaves consistently with the implemented
equations, numerical conventions, physical invariants, and approved regression
baselines.

Examples include:

- probability normalization;
- charge conservation;
- deterministic regression;
- non-negative optical rates;
- dark-source behaviour;
- spectral consistency.

### Validation

Comparison of model behaviour with an appropriate external physical reference,
particularly experimental measurements.

Software verification and experimental validation are therefore distinct.

### Regression test

Test designed to detect an unintended change in established numerical
behaviour.

### Golden case

Deterministic reference result retained for comparison with future software
versions.

A golden case protects numerical behaviour but does not by itself establish
experimental correctness.

### Benchmark

Controlled calculation used to compare behaviour, performance, or model trends
under specified conditions.

A benchmark result is not automatically an experimentally calibrated
prediction.

### Provenance

Information describing the origin and status of a model or parameter.

NCMemSim distinguishes among:

- literature-supported;
- provisional;
- fitted;
- experimentally calibrated.

### Literature-supported

A parameter value or model structure with an identified basis in published
scientific literature.

Literature support does not necessarily imply direct calibration to the device
being simulated.

### Provisional

A compact-model parameter selected for model construction, testing, or
benchmarking but not yet established by device-specific calibration.

### Fitted

A parameter estimated by comparison with selected reference data.

The fitting method, dataset, objective function, and uncertainty should be
reported.

### Experimentally calibrated

A model parameter constrained against suitable experimental measurements for
the intended device or material system.

### Extrapolation

Use of a parameterization outside the composition, wavelength, temperature, or
other domain directly supported by its underlying reference data.

Extrapolated results should be identified explicitly.

## Reproducibility terminology

### Reproducibility manifest

Machine-readable record of the principal software, device, material, and
simulation inputs associated with a run.

### Canonical device hash

Hash generated from a canonical serialization of the device definition.

It identifies a particular serialized configuration but does not establish its
physical correctness.

### Simulation hash

Hash associated with the serialized simulation configuration.

### Release baseline

A versioned software state whose tests, documentation, and release artifacts
have been verified.

The official `v0.10.0` release is the current NCMemSim release baseline.

## Common units

NCMemSim uses SI units internally unless a public API explicitly documents a
different input convention.

Common quantities include:

| Quantity | Symbol | Typical unit |
|---|---|---|
| length | \(z,t,d\) | m |
| wavelength | \(\lambda\) | nm at user-facing interfaces; converted as required |
| voltage | \(V\) | V |
| electric field | \(E\) | V m\(^{-1}\) |
| energy | \(E\) | J or eV as documented |
| time | \(t\) | s |
| transition rate | \(r\) | s\(^{-1}\) |
| sheet charge | \(Q_{\mathrm{FG}}\) | C m\(^{-2}\) |
| absorption coefficient | \(\alpha\) | m\(^{-1}\) |
| optical power density | \(P_{\mathrm{opt}}\) | W m\(^{-2}\) |
| photon flux | \(\Phi\) | m\(^{-2}\) s\(^{-1}\) |
| volumetric generation rate | \(G\) | m\(^{-3}\) s\(^{-1}\) |

## Symbol reuse

Some symbols have conventional meanings in more than one physical context.

In particular:

- \(E\) may denote electric field or energy depending on context;
- \(A\) may denote physical area, while \(A_{\mathrm{abs}}\) denotes optical
  absorption fraction;
- \(T\) may denote tunnelling transmission, while temperature should be written
  explicitly as \(T_{\mathrm{K}}\) or identified clearly by context;
- \(t\) may denote time or layer thickness, with subscripts used where needed.

Documentation and scientific output should prefer explicit subscripts whenever
ambiguity is possible.

## v0.10.0 interpretation rule

Quantities produced by NCMemSim should be interpreted according to the
provenance and calibration status of the parameters that generated them.

The v0.10.0 electrical and optical implementations are software-verified
against their current regression and consistency baselines.

The optical absorption amplitudes and photo-capture coupling are not yet
device-specifically calibrated by default.

Consequently, the Phase E SWIR results establish model behaviour and spectral
consistency, not automatic quantitative agreement with a fabricated device.
