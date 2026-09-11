# NCMemSim v6.0 — Software Design Specification

> **Historical design document:** This Revision 1 specification records the
> original Phase A / alpha design of NCMemSim and is retained for project
> provenance. It does not describe the current software architecture or
> implementation status. For the current v0.10.0 model, see `index.md`,
> `architecture.md`, `physics.md`, `optics.md`, and `roadmap.md`.

**Expanded name:** Unified Nanocrystal Memory Simulation Platform  
**Version:** 6.0 Revision 1  
**Implementation status:** Phase A / alpha

## 1. Scope

NCMemSim v6.0 is a modular platform for simulating nanocrystal non-volatile memories with electrical, optical, and combined electro-optical charging. It supports Ge and GeSn nanocrystals, two device architectures, one to three independently configurable floating gates, independent thickness for every layer, experimental fitting, and automated comparison.

## 2. Device architectures

### V1

Gate / HfO2 / SiO2 / [FG containing Ge or GeSn NCs / SiO2 / HfO2]n / tunnel HfO2 / tunnel or native SiO2 / Si, with n = 1–3.

### V2

Gate / SiO2 / [FG containing Ge or GeSn NCs / tunnel SiO2]n / Si, with n = 1–3.

The ordered layer list, not the architecture label, is the source of truth. Every layer thickness is independently configurable.

## 3. Core data model

- `Material`: bulk dielectric or semiconductor properties.
- `NanocrystalMaterial`: Ge or GeSn composition, effective mass, dielectric constant, and effective barriers.
- `Layer`: conventional layer with material, role, and thickness.
- `FloatingGateLayer`: NC-containing layer with independent thickness, NC composition, diameter, volume fraction, active fraction, spatial profile, and grid.
- `Device`: ordered stack, geometry validation, positions, total thickness, equivalent dielectric capacitance, and serialization.
- `DeviceBuilder`: reproducible V1/V2 constructors with user-overridable thicknesses.
- `LightSource`: incandescent, LED, laser, or custom illumination.
- `FloatingGateState`: distributed P0/P1/P2 state for later physics migration.

Each floating gate may use a different composition and geometry, including graded devices such as Ge / GeSn 2% / GeSn 10%.

## 4. GeSn composition model

Composition-dependent properties are generated with configurable interpolation:

P(x) = (1-x)P_Ge + xP_Sn - b_P x(1-x).

Dedicated functions will generate dielectric constant, band gap, effective mass, and effective program/erase barriers. Initial values are explicitly provisional and must later be validated or fitted.

## 5. Electrostatics

For a series stack:

1/(Ceq/A) = sum_i[t_i/(epsilon0 epsilon_r,i)].

The multi-FG phase will add gate-to-FG, FG-to-substrate, and FG-to-FG coupling, preferably through a capacitance matrix Q = C V.

Nanocrystal self-capacitance remains:

C_NC ≈ 4 pi epsilon0 epsilon_cap R_NC,

with charging energy E_c = q^2/(2 C_NC). The capacitance permittivity must be explicitly distinguished from bulk NC and matrix permittivities.

## 6. Electrical and optical charging

The simulator will support:

- electrical: Vg != 0, Popt = 0;
- optical: Vg = 0, Popt > 0;
- electro-optical: Vg != 0, Popt > 0.

Rates are decomposed as:

r_ij = r_ij^elec + r_ij^photo.

Photo-assisted trapping and detrapping use independent coefficients.

### Incandescent lamp

Two levels are planned:

1. Compact mode: r_ij^photo = k_ij^photo Popt.
2. Spectral mode: blackbody-like spectral irradiance integrated with wavelength-dependent absorption and photon energy.

The light-source object stores lamp temperature, incident power density, and wavelength limits. A default incandescent temperature of 2800 K is provided but remains configurable.

## 7. Physics migration

Phase B will migrate the validated v5.3 mechanisms:

- trapezoidal WKB tunneling;
- Coulomb blockade;
- P0/P1/P2 kinetics;
- distributed charge;
- dynamic flat-band voltage;
- C–V hysteresis;
- retention;
- program/erase pulse response.

The one-FG reference case must reproduce v5.3 before new multi-FG physics is accepted.

## 8. Experimental fitting

Phase F will fit forward/backward C–V and retention C–t data using bounded least squares, optionally preceded by global search. Candidate fit parameters include active fraction, NC diameter, program/erase barriers, attempt frequencies, field factors, effective capacitance permittivity, and photo-trapping/photo-detrapping coefficients.

Outputs will include best-fit values, RMSE, normalized RMSE, R2, reduced chi-square when uncertainties exist, residuals, confidence estimates, parameter-correlation warnings, and full metadata.

## 9. Benchmark matrix

Default comparison:

- V1 and V2;
- 1, 2, and 3 FGs;
- Ge, GeSn 2%, and GeSn 10%.

This gives 18 standard device cases. Optical comparisons will additionally include dark, optical-only, electrical-only, and electro-optical operation.

## 10. Project structure

```text
NCMemSim_v6/
├── README.md
├── CHANGELOG.md
├── pyproject.toml
├── requirements.txt
├── configs/
├── docs/
├── examples/
├── experimental/
├── results/
├── tests/
└── ncmemsim/
    ├── constants.py
    ├── composition.py
    ├── materials.py
    ├── layers.py
    ├── device.py
    ├── builder.py
    ├── state.py
    ├── optics.py
    ├── electrostatics.py
    ├── tunneling.py
    ├── kinetics.py
    ├── simulator.py
    ├── fitting.py
    ├── benchmark.py
    ├── plotting.py
    └── io.py
```

## 11. Development phases

- Phase A: structure, data classes, builders, optics source definitions, examples, tests.
- Phase B: v5.3 physics migration and regression.
- Phase C: validated GeSn composition support.
- Phase D: multiple floating gates and capacitance coupling.
- Phase E: V1/V2 benchmark.
- Phase F: experimental fitting.
- Phase G: optical and electro-optical programming.

## 12. Phase A acceptance criteria

Phase A is complete when:

1. the package imports;
2. Ge, GeSn 2%, and GeSn 10% objects can be created;
3. V1 and V2 can be built with 1–3 FGs;
4. every layer thickness is independently editable;
5. each FG may have independent material and geometry;
6. layer positions, total thickness, and equivalent dielectric capacitance are computed;
7. incandescent, LED, and laser sources are represented;
8. device and source objects serialize to dictionaries;
9. tests pass.
