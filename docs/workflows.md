# Scientific workflows

NCMemSim v0.10.0 supports reproducible electrical, optical, electro-optical,
retention, sweep, C-V, validation, and provenance workflows.

This page focuses on how the principal components fit together during a
scientific study.

For a shorter executable introduction, see
[Quick start](quickstart.md).

For model equations and assumptions, see
[Physics model](physics.md) and
[Optical programming](optics.md).

## 1. General workflow

A typical NCMemSim study follows the sequence

```text
define device
    |
    v
define material parameters
    |
    v
initialize DeviceState
    |
    v
configure Simulator
    |
    +---------------------------+
    |                           |
    v                           v
electrical excitation      optical excitation
    |                           |
    +-------------+-------------+
                  |
                  v
         charge-state kinetics
                  |
                  v
          updated DeviceState
                  |
        +---------+---------+
        |         |         |
        v         v         v
      sweep      C-V    retention
        |         |         |
        +---------+---------+
                  |
                  v
             validation
                  |
                  v
          reproducibility
                  |
                  v
       exported scientific data
```

The device and its physical parameters should be defined before selecting a
workflow.

Do not treat a plotting script or a numerical sweep as the definition of the
physical model.

## 2. Build and validate a device

The documented builder API can be used for reproducible standard stacks.

```python
from ncmemsim import DeviceBuilder, make_ge, make_gesn

device = DeviceBuilder.v1(
    n_fgs=3,
    nc_material=[
        make_ge(),
        make_gesn(0.02),
        make_gesn(0.10),
    ],
    fg_thickness_nm=[12.0, 15.0, 18.0],
    nc_diameter_nm=[3.0, 5.0, 7.0],
    active_fraction=[0.22, 0.18, 0.12],
)

device.validate()
```

`DeviceBuilder.v1` and `DeviceBuilder.v2` support the documented device
families.

For non-standard research structures, an ordered layer stack may be constructed
explicitly instead.

A custom device should always be validated before simulation.

## 3. Distinguish electrical and optical fractions

For optical studies, two different concepts must remain distinct.

The electrically active fraction controls the fraction of nanocrystals that
participate in the electrical charge-state model.

The nanocrystal volume fraction controls the effective optical absorption of
the floating-gate composite.

These quantities should not be substituted for one another unless a specific
physical model justifies that identification.

## 4. Initialize a traceable state

Create a state directly from the device:

```python
from ncmemsim import DeviceState

state = DeviceState.empty_for_device(device)
state.validate(device)
```

Each physical floating gate owns its own `FloatingGateState`.

The distributed probabilities are

```text
P0
P1
P2
```

corresponding to the three compact charge states.

The state also carries identifying information that connects it to the
corresponding floating-gate layer.

## 5. Configure the simulator

Create a simulator with explicit numerical settings:

```python
from ncmemsim import SimulationConfig, Simulator

simulator = Simulator(
    device,
    config=SimulationConfig(
        dwell_time_s=2e-5,
        internal_dt_s=1e-5,
    ),
)
```

The default dwell time controls the physical duration represented by one
relaxation operation.

The internal timestep controls numerical subdivision of that interval.

The simulator uses an effective timestep that spans the requested dwell
interval exactly.

## 6. Electrical programming workflow

Electrical-only programming requires no optical source.

```python
electrical = simulator.relax_voltage(
    state,
    gate_voltage_V=2.0,
)
```

Principal electrical outputs include:

```python
print(electrical["qfg_C_m2"])
print(electrical["qfg_by_fg_C_m2"])
print(electrical["delta_vfb_V"])
print(electrical["mean_occupation_by_fg"])
```

The updated state is:

```python
electrical_state = electrical["state"]
```

A subsequent simulation should continue from this returned state rather than
manually modifying internal probability arrays unless that modification is
deliberate and validated.

## 7. Inspect electrostatic diagnostics

The relaxation result provides the reconstructed one-dimensional field profile:

```python
profile = electrical["field_profile"]

print(profile.z_nm)
print(profile.potential_V)
print(profile.electric_field_V_m)
print(profile.local_potentials_by_fg_V)
print(profile.local_fields_by_fg_V_m)
```

These quantities connect the applied terminal voltage to the local electrical
conditions experienced by each floating gate.

For multi-FG structures, per-floating-gate diagnostics should normally be used
instead of relying only on scalar averages.

## 8. Define a monochromatic optical source

Optical excitation is configured separately from the electrical model.

```python
from ncmemsim.optics import LightSource

light = LightSource.laser(
    wavelength_nm=1550.0,
    power_density_W_m2=1000.0,
)
```

The source provides derived quantities including:

- photon energy;
- optical power density;
- incident photon flux.

The optical material model then determines how strongly the nanocrystal system
absorbs those photons.

## 9. Optical material workflow

The public optical-material API is exposed through:

```python
ncmemsim.materials.optics
```

For example:

```python
from ncmemsim.materials.optics import CompositeGeSnAbsorptionModel

optical_model = CompositeGeSnAbsorptionModel()
```

The v0.10.0 Ge/GeSn optical response contains separate compact contributions
from:

- direct-Gamma absorption;
- indirect-L phonon-assisted absorption;
- Urbach-tail absorption.

Optical material quantities must not be inferred from the electronic
`NanocrystalMaterial.bandgap_eV` value.

The electronic and optical gaps have distinct roles.

## 10. Electro-optical programming workflow

Pass the optical source into the same voltage-relaxation workflow:

```python
electro_optical = simulator.relax_voltage(
    state,
    gate_voltage_V=2.0,
    light_source=light,
)
```

The simulator evaluates both:

```text
electrical transition rates
+
photo-assisted transition rates
```

before updating the charge-state probabilities.

This enables direct comparison between electrical-only and illuminated
programming under otherwise identical conditions.

## 11. Optical-assisted zero-bias workflow

Optical assistance can also be studied without an externally applied gate
voltage:

```python
optical_assisted = simulator.relax_voltage(
    state,
    gate_voltage_V=0.0,
    light_source=light,
)
```

This workflow is useful for separating the contribution of optical loading from
field-assisted electrical injection.

A non-zero photo-assisted response at zero gate voltage should not
automatically be interpreted as a calibrated experimental prediction.

Its magnitude depends on the optical absorption model and photo-transition
coupling.

## 12. Configure photo-assisted coupling

The photo-assisted transition model can be configured explicitly.

```python
from ncmemsim.photo import (
    PhotoTransitionConfig,
    PhotoTransitionWeights,
)

photo_config = PhotoTransitionConfig(
    photo_capture_efficiency=1e-7,
)

photo_weights = PhotoTransitionWeights(
    r01=1.0,
    r12=1.0,
    r10=0.0,
    r21=0.0,
)
```

Use these settings during simulation:

```python
configured_optical = simulator.relax_voltage(
    state,
    gate_voltage_V=2.0,
    light_source=light,
    photo_config=photo_config,
    photo_weights=photo_weights,
)
```

The default compact optical-loading pathway is

```text
0 -> 1
1 -> 2
```

with photo-assisted detrapping disabled by default.

`photo_capture_efficiency` is a phenomenological compact-model coupling
parameter.

Unless explicitly fitted to appropriate data, it should be described as
provisional rather than experimentally calibrated.

## 13. Inspect optical diagnostics

Illuminated simulator results expose optical quantities such as:

```python
print(
    configured_optical[
        "optical_absorption_fraction_by_fg"
    ]
)

print(
    configured_optical[
        "absorbed_photon_flux_by_fg_m2_s"
    ]
)

print(
    configured_optical[
        "absorbed_photon_rate_per_nc_by_fg_s"
    ]
)

print(
    configured_optical[
        "photo_transition_rate_by_fg_s"
    ]
)

print(
    configured_optical[
        "optical_alpha_nc_by_fg_m_inv"
    ]
)

print(
    configured_optical[
        "optical_alpha_eff_by_fg_m_inv"
    ]
)
```

Per-FG arrays are the primary representation for multi-floating-gate devices.

Scalar convenience diagnostics are also available for workflows where a single
aggregate value is useful.

## 14. Interpret dark and disabled-source cases correctly

For a dark simulation with no optical source:

```text
absorbed photon flux = 0
photo-transition rate = 0
```

For an explicitly disabled optical source:

```text
incident photon flux = 0
photo-transition rate = 0
```

while wavelength-dependent material properties may still be evaluated.

Therefore a non-zero absorption coefficient does not imply that photons are
actually incident on the device.

## 15. Wavelength-sweep workflow

A spectral study should hold the non-spectral parameters fixed while varying
wavelength.

Conceptually:

```python
wavelengths_nm = [
    1300.0,
    1550.0,
    1700.0,
    2000.0,
]
```

For every wavelength:

1. construct or update the light source;
2. evaluate optical absorption;
3. record incident photon flux;
4. record absorbed photon flux;
5. record absorbed photon rate per NC;
6. record photo-transition rate;
7. optionally run a programming transient;
8. retain material composition and power density in the output dataset.

The executable reference implementation is:

```text
examples/e6a_swir_wavelength_sweep.py
```

This workflow is intended for spectral comparison.

It should not impose a global assumption that absorption or photo-transition
rate must be monotonic with wavelength.

At fixed optical power density, the incident photon flux itself changes with
photon energy.

## 16. Composition-sweep workflow

For GeSn studies, composition and wavelength may both affect the optical
response.

A defensible composition sweep should record:

- Sn fraction;
- wavelength;
- direct-Gamma gap;
- indirect-L gap;
- direct absorption;
- indirect absorption;
- Urbach contribution;
- total nanocrystal absorption;
- effective floating-gate absorption;
- absorbed photon flux;
- photo-transition rate.

Results outside the literature-supported composition or wavelength range should
be identified as extrapolations.

In particular, smooth numerical behaviour does not establish experimental
validity outside the reference-data range.

## 17. Voltage-sweep workflow

NCMemSim supports state-evolving voltage sweeps.

For a dark sweep:

```python
import numpy as np

voltages_V = np.linspace(
    0.0,
    4.0,
    17,
)

dark_sweep = simulator.run_sweep(
    voltages_V,
    state,
)
```

For an illuminated sweep:

```python
light_sweep = simulator.run_sweep(
    voltages_V,
    state,
    light_source=light,
    photo_config=photo_config,
    photo_weights=photo_weights,
)
```

A voltage sweep is stateful.

The occupation produced at one voltage point becomes the starting state for the
next point.

Therefore changing voltage order can change the result.

## 18. Comparing dark and illuminated voltage sweeps

For optical voltage-reduction studies, compare dark and illuminated curves
using the same:

- device;
- initial state;
- voltage grid;
- dwell time;
- internal timestep;
- material model;
- target metric.

A voltage reduction should be defined through an explicit comparison target.

For example, one may determine the voltage required to reach a common
occupation value on both dark and illuminated curves.

The target must lie in the overlap range of all curves being compared.

Do not compare values obtained from different target occupations and describe
the difference as a programming-voltage reduction.

## 19. SWIR voltage-reduction benchmark

The reference v0.10.0 benchmark is implemented in:

```text
examples/e6d_swir_voltage_reduction.py
```

It uses:

```text
GeSn composition       = 8% Sn
NC diameter            = 5 nm
FG thickness           = 15 nm
optical power density  = 1000 W/m^2
programming time       = 1 ms
voltage range          = 0 to 4 V
voltage spacing        = 0.25 V
photo capture eta      = 1e-10
```

The benchmark compares:

```text
dark
1300 nm
1550 nm
1700 nm
```

using one common target occupation.

The verified benchmark gives approximately:

| Wavelength | Photo rate (s^-1) | V_dark (V) | V_light (V) | Delta V (V) |
|---:|---:|---:|---:|---:|
| 1300 nm | 3.092040e-07 | 3.9124 | 3.8343 | 0.0781 |
| 1550 nm | 3.506618e-07 | 3.9124 | 3.8238 | 0.0885 |
| 1700 nm | 3.684289e-07 | 3.9124 | 3.8193 | 0.0930 |

A positive `Delta V` means that illumination reduces the gate voltage required
to reach the selected common occupation.

The benchmark value

```text
photo_capture_efficiency = 1e-10
```

is deliberately benchmark-specific.

It is not the global model default and is not experimentally calibrated.

The numerical voltage reductions therefore demonstrate internal compact-model
behaviour rather than absolute device prediction.

## 20. C-V workflow

The simulator supports forward and backward compact C-V sweeps.

A dark C-V workflow can be run through:

```python
cv_dark = simulator.simulate_cv(
    vmin_V=-3.0,
    vmax_V=3.0,
    points=241,
)
```

The result contains the forward and backward sweep objects and the extracted
memory window.

Optical configuration can also be propagated through the C-V workflow:

```python
cv_light = simulator.simulate_cv(
    vmin_V=-3.0,
    vmax_V=3.0,
    points=241,
    light_source=light,
    photo_config=photo_config,
    photo_weights=photo_weights,
)
```

This enables controlled comparison between dark and illuminated compact C-V
behaviour.

The current optical absorption model is not voltage dependent.

Therefore illumination modifies the charge-state kinetics, while the optical
absorption coefficients themselves remain fixed for a fixed material and
source.

## 21. Retention workflow

Retention normally begins from a previously programmed state.

For example:

```python
from ncmemsim import RetentionConfig

retention = simulator.simulate_retention(
    electrical["state"],
    RetentionConfig(
        total_time_s=1e4,
        initial_dt_s=1e-6,
        maximum_dt_s=100.0,
        output_points=61,
    ),
)
```

Inspect both the total and per-FG response:

```python
print(retention.time_s)
print(retention.qfg_C_m2)
print(retention.mean_occupation_by_fg)
print(retention.total_charge_retention_fraction)
```

For multi-FG devices, total stored charge and charge redistribution are
different observables.

A nearly constant total charge can coexist with substantial movement of charge
between floating gates.

## 22. Programming followed by retention

A common study is:

```text
initial empty state
    |
    v
programming pulse
    |
    v
programmed DeviceState
    |
    v
zero-bias retention
    |
    v
charge-loss trajectory
```

The programmed state must be passed directly into retention.

Do not reconstruct the retention initial condition from only a scalar total
charge if the spatial or per-FG occupation information is scientifically
relevant.

## 23. Multi-FG optical workflow

In v0.10.0, every floating gate evaluates its optical response using the same
incident source.

The current implementation does not propagate transmitted optical flux
sequentially from one FG to the next.

Therefore the present model behaves conceptually as:

```text
source -> FG0
source -> FG1
source -> FG2
```

rather than:

```text
source -> FG0 -> attenuated source -> FG1 -> attenuated source -> FG2
```

Sequential optical attenuation through multi-FG stacks is a future model
extension.

This limitation should be stated when interpreting multi-FG optical
simulations.

## 24. Validate a simulation

NCMemSim provides structured validation utilities.

```python
from ncmemsim import validate_simulation

report = validate_simulation(
    device,
    electrical["state"],
    electrical,
)

report.raise_for_errors()
```

Validation checks model and numerical invariants such as:

- probability normalization;
- device consistency;
- field consistency;
- internal charge conservation;
- expected result structure.

Passing validation means that the simulation satisfies the implemented
consistency checks.

It does not mean that the result has been experimentally validated.

## 25. Validation inside parameter sweeps

Parameter sweeps should validate individual cases rather than only inspecting
the final averaged dataset.

A useful workflow is:

```text
parameter set
    |
    v
build device
    |
    v
simulate
    |
    v
validate
    |
    +------ error ------> reject / flag case
    |
    v
store result
```

This prevents physically invalid or numerically inconsistent cases from being
silently incorporated into aggregate trends.

## 26. Record reproducibility metadata

Use the reproducibility manifest for traceable simulations.

```python
from ncmemsim import build_reproducibility_manifest

manifest = build_reproducibility_manifest(
    device,
    simulation_config={
        "gate_voltage_V": 2.0,
    },
)
```

The manifest can contain information such as:

- NCMemSim version;
- runtime environment;
- device definition;
- material models;
- simulation configuration;
- canonical hashes.

Save the manifest beside the numerical data that it describes.

## 27. Optical reproducibility

For an optical study, the scientific dataset should additionally preserve the
optical configuration, including where relevant:

```text
source type
wavelength
power density
material composition
optical parameter set
photo-capture efficiency
photo-transition weights
temperature
FG geometry
nanocrystal volume fraction
```

The current reproducibility hash identifies serialized model inputs.

A matching hash proves identity of recorded inputs, not physical correctness or
experimental calibration.

## 28. Export raw data before plotting

For publication-oriented work, numerical results should be exported before
plotting.

Prefer a workflow of the form:

```text
simulation
    |
    v
validation
    |
    v
raw numerical export
    |
    v
plot / figure
```

rather than allowing the plotting script to become the only persistent record
of the simulation result.

For a spectral study, useful raw columns may include:

```text
wavelength_nm
photon_energy_eV
incident_photon_flux_m2_s
alpha_direct_m_inv
alpha_indirect_m_inv
alpha_urbach_m_inv
alpha_nc_m_inv
alpha_eff_m_inv
absorption_fraction
absorbed_photon_flux_m2_s
photo_transition_rate_s
mean_occupation
```

## 29. Suggested publication workflow

For a figure or table intended for publication:

1. record the NCMemSim version;
2. keep the input configuration under version control;
3. record material parameter provenance;
4. identify provisional, fitted, and calibrated parameters separately;
5. record extrapolated wavelength or composition regions;
6. run the appropriate validation checks;
7. export raw numerical data;
8. create the reproducibility manifest;
9. record the script and Git commit used to generate the result;
10. generate the figure from the stored numerical data;
11. avoid modifying golden references during routine figure production.

For optical results, also report enough information to reconstruct the incident
photon flux and photo-assisted coupling.

## 30. Verification versus experimental validation

NCMemSim distinguishes several evidence levels.

### Software verification

Examples include:

- unit tests;
- normalization tests;
- limiting cases;
- conservation checks;
- regression tests;
- deterministic golden cases.

### Physical consistency

Examples include:

- correct spectral ordering;
- physically meaningful limiting behaviour;
- sensible composition trends;
- consistent rate coupling.

### Experimental validation

Experimental validation requires comparison with measured data from an
appropriately characterized material or device.

The first two categories do not replace the third.

## 31. Current optical calibration status

The v0.10.0 optical model combines literature-supported structure with
provisional compact parameters.

In particular:

- the direct and indirect optical-gap framework has a literature basis;
- the absorption decomposition has a literature basis;
- absolute compact absorption amplitudes remain provisional;
- the default photo-capture efficiency is provisional;
- device-specific electro-optical calibration has not yet been completed.

Results intended for direct comparison with fabricated devices should therefore
document any fitting or calibration performed in addition to the default
software model.

## 32. Spectral extrapolation

The principal room-temperature GeSn absorption dataset used to guide the
compact model covers only a finite composition and wavelength range.

Therefore simulations outside those regions should be labelled as
extrapolations.

Examples include:

- Sn compositions beyond the supporting experimental composition range;
- wavelengths outside the supporting measured spectral interval.

An extrapolated result may still be useful for mechanism exploration, but its
status must be reported explicitly.

## 33. Current workflow limitations

The v0.10.0 optical workflows do not yet model:

- voltage-dependent absorption;
- Franz-Keldysh effects;
- Stark shifts;
- state filling;
- explicit strain-dependent absorption;
- nanocrystal quantum-confinement corrections;
- sequential attenuation through multiple floating gates;
- experimentally calibrated absolute absorption amplitudes;
- experimentally calibrated photo-capture efficiency.

These are model-scope limitations, not execution errors.

## 34. Useful executable examples

The most relevant v0.10.0 optical examples are:

```text
examples/e6a_swir_wavelength_sweep.py
examples/e6d_swir_voltage_reduction.py
```

Earlier examples remain useful for electrical and multi-FG workflows:

```text
examples/build_devices.py
examples/phase_b_regression.py
examples/phase_c_material_framework.py
examples/phase_d1_multistate.py
examples/phase_d2_electrostatic_coupling.py
examples/phase_d3_local_field_profile.py
examples/phase_d4_inter_fg_transport.py
examples/phase_d5_retention.py
examples/phase_d6_validation.py
```

Executable examples should be treated as reproducibility aids, not substitutes
for the model documentation.

## 35. Recommended study structure

A complete scientific study should preserve enough information to reconstruct:

```text
device
+
materials
+
initial state
+
electrical conditions
+
optical conditions
+
simulation settings
+
physical-model assumptions
+
parameter provenance
+
calibration status
+
validation results
+
raw numerical outputs
+
software version
```

This is the preferred NCMemSim workflow for keeping scientific conclusions
traceable to both the physical model and the software configuration.

## Where to go next

For further details, see:

- [Quick start](quickstart.md) for concise executable usage;
- [Scientific scope and assumptions](scientific_scope.md) for model boundaries;
- [Physics model](physics.md) for the integrated physical framework;
- [Electrostatics and fields](electrostatics.md) for the electrical field model;
- [Transport and retention](transport_retention.md) for charge redistribution;
- [Materials and provenance](materials.md) for parameter status;
- [Optical programming](optics.md) for the Phase E optical model;
- [Validation](validation.md) for verification methodology;
- [Reproducibility](reproducibility.md) for manifests and traceability;
- [API reference](api.md) for documented programming interfaces;
- [Developer guide](developer.md) for extension rules.
