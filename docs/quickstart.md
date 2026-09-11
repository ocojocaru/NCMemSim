# Quick start

This guide introduces the main NCMemSim v0.10.0 workflows:

1. build a nanocrystal-memory device;
2. create its initial charge state;
3. run electrical programming;
4. inspect electrostatic diagnostics;
5. run optical or electro-optical programming;
6. inspect optical diagnostics;
7. run retention;
8. validate the result and record provenance.

The examples below use the documented public API wherever possible.

## 1. Import NCMemSim

```python
import ncmemsim

print(ncmemsim.__version__)
```

For the official release, the expected version is:

```text
0.10.0
```

## 2. Build a device

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
```

`DeviceBuilder.v1` and `DeviceBuilder.v2` accept scalar values or per-FG
sequences for supported floating-gate parameters.

The example above creates three floating gates with different nanocrystal
materials, thicknesses, diameters, and electrically active fractions.

For optical studies, remember that the electrically active fraction is
distinct from the nanocrystal volume fraction used by the optical absorption
model.

## 3. Create an empty state

```python
from ncmemsim import DeviceState

state = DeviceState.empty_for_device(device)
```

Each `FloatingGateState` contains the distributed charge-state probabilities

```text
P0
P1
P2
```

for its corresponding physical floating gate.

The state also records identifying and geometric information linking it to the
device.

## 4. Create the simulator

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

The simulation configuration controls the default physical dwell interval and
internal integration timestep.

## 5. Run electrical programming

Relax the initially empty state at a positive gate voltage:

```python
electrical = simulator.relax_voltage(
    state,
    gate_voltage_V=2.0,
)
```

Inspect the principal electrical outputs:

```python
print(electrical["qfg_C_m2"])
print(electrical["qfg_by_fg_C_m2"])
print(electrical["delta_vfb_V"])
print(electrical["mean_occupation_by_fg"])
```

The output dictionary also contains the updated device state and additional
electrical diagnostics.

The updated state is available as:

```python
electrical_state = electrical["state"]
```

## 6. Inspect the electric-field profile

```python
profile = electrical["field_profile"]

print(profile.z_nm)
print(profile.potential_V)
print(profile.electric_field_V_m)
print(profile.local_potentials_by_fg_V)
print(profile.local_fields_by_fg_V_m)
```

`FieldSolver1D` reconstructs a compact one-dimensional potential and electric
field through the ordered device stack.

These quantities provide local electrical inputs to the tunnelling and
charge-state models.

## 7. Define a monochromatic optical source

NCMemSim v0.10.0 supports optical programming through `LightSource`.

For example, define a SWIR source at 1550 nm:

```python
from ncmemsim.optics import LightSource

light = LightSource.laser(
    wavelength_nm=1550.0,
    power_density_W_m2=1000.0,
)
```

The source provides quantities such as photon energy and incident photon flux.

For a monochromatic source,

\[
E_\gamma
=
\frac{hc}{\lambda},
\]

and

\[
\Phi_\gamma
=
\frac{P_{\mathrm{opt}}}{E_\gamma}.
\]

You can inspect the source directly:

```python
print(light.photon_energy_eV)
print(light.photon_flux_m2_s)
```

## 8. Run electro-optical programming

The same simulator can include the optical source during voltage relaxation:

```python
electro_optical = simulator.relax_voltage(
    state,
    gate_voltage_V=2.0,
    light_source=light,
)
```

The electrical and photo-assisted transition rates are combined internally
before the occupancy state is advanced.

Conceptually,

\[
r_{ij}
=
r_{ij}^{\mathrm{elec}}
+
r_{ij}^{\mathrm{photo}}.
\]

This means the electrical-only and electro-optical workflows use the same
device-state representation and occupancy engine.

Compare the resulting occupations:

```python
print("Electrical:")
print(electrical["mean_occupation_by_fg"])

print("Electro-optical:")
print(electro_optical["mean_occupation_by_fg"])
```

The magnitude of the difference depends strongly on the optical material
parameters and photo-capture configuration.

Default optical coupling parameters in v0.10.0 are not device-specifically
calibrated.

## 9. Run optical-assisted programming at zero gate bias

Optical excitation can also be evaluated without an applied programming
voltage:

```python
optical_only = simulator.relax_voltage(
    state,
    gate_voltage_V=0.0,
    light_source=light,
)
```

This workflow is useful for separating the photo-assisted contribution from
the positive-bias electrical programming contribution.

It should not be interpreted as a claim that a specific fabricated device will
program efficiently at zero bias without experimental calibration.

## 10. Inspect optical diagnostics

When an optical source is supplied, the simulator exposes optical diagnostics.

For example:

```python
print(
    electro_optical[
        "optical_absorption_fraction_by_fg"
    ]
)

print(
    electro_optical[
        "absorbed_photon_flux_by_fg_m2_s"
    ]
)

print(
    electro_optical[
        "absorbed_photon_rate_per_nc_by_fg_s"
    ]
)

print(
    electro_optical[
        "photo_transition_rate_by_fg_s"
    ]
)
```

Additional per-FG diagnostics include:

```python
print(
    electro_optical[
        "optical_alpha_nc_by_fg_m_inv"
    ]
)

print(
    electro_optical[
        "optical_alpha_eff_by_fg_m_inv"
    ]
)
```

Scalar convenience diagnostics are also available:

```python
print(
    electro_optical[
        "optical_absorption_fraction"
    ]
)

print(
    electro_optical[
        "absorbed_photon_flux_m2_s"
    ]
)

print(
    electro_optical[
        "photo_transition_rate_s"
    ]
)
```

For multi-FG devices, the per-floating-gate arrays are the primary diagnostic
representation.

## 11. Understand the optical absorption path

For a nanocrystal floating gate, NCMemSim evaluates the nanocrystal absorption
coefficient

\[
\alpha_{\mathrm{NC}}
=
\alpha_{\Gamma}
+
\alpha_L
+
\alpha_U,
\]

where the terms represent direct-Gamma, indirect phonon-assisted, and
Urbach-tail absorption.

The effective floating-gate absorption coefficient is

\[
\alpha_{\mathrm{eff}}
=
f_{\mathrm{NC}}
\alpha_{\mathrm{NC}}.
\]

The absorbed fraction follows Beer-Lambert attenuation:

\[
A_{\mathrm{abs}}
=
1-
\exp
\left(
-\alpha_{\mathrm{eff}}t_{\mathrm{FG}}
\right).
\]

The absorbed photon flux then supplies the input to the photo-assisted
charge-state model.

See [Optical programming](optics.md) for the complete model description.

## 12. Configure photo-assisted coupling

For controlled studies, the photo-assisted transition model can be configured
explicitly.

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

Pass these configurations into the simulator:

```python
configured_optical = simulator.relax_voltage(
    state,
    gate_voltage_V=2.0,
    light_source=light,
    photo_config=photo_config,
    photo_weights=photo_weights,
)
```

The default v0.10.0 photo-assisted model represents optical loading through

\[
0\rightarrow1
\]

and

\[
1\rightarrow2.
\]

Photo-assisted detrapping is disabled by default.

`photo_capture_efficiency` is a phenomenological compact-model parameter. A
value used in an example or benchmark must not automatically be interpreted as
an experimentally measured quantum efficiency.

## 13. Run retention

Retention can be started from a previously programmed state.

For example, continue from the electrical programming result:

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

Inspect the retention trajectory:

```python
print(retention.time_s)
print(retention.qfg_C_m2)
print(retention.mean_occupation_by_fg)
print(retention.total_charge_retention_fraction)
```

Retention evolves the physical state rather than applying a fixed analytical
decay factor.

Long-time retention remains sensitive to the physical transport parameters and
their calibration.

## 14. Validate the simulation state

NCMemSim provides validation utilities for scientific and numerical
consistency.

```python
from ncmemsim import validate_simulation

report = validate_simulation(
    device,
    electrical["state"],
    electrical,
)

report.raise_for_errors()
```

Validation checks software and model invariants.

Passing validation does not by itself establish agreement with a fabricated
device.

## 15. Record reproducibility information

Create a reproducibility manifest:

```python
from ncmemsim import build_reproducibility_manifest

manifest = build_reproducibility_manifest(
    device,
    simulation_config={
        "gate_voltage_V": 2.0,
    },
)

print(manifest["device_hash"])
print(manifest["simulation_hash"])
```

The manifest records enough simulation context to help identify and reproduce
a numerical calculation.

Hashes establish identity of serialized inputs; they do not establish physical
correctness.

## 16. Run the SWIR wavelength-sweep example

Version 0.10.0 includes an executable Phase E6 wavelength-sweep example:

```bash
python examples/e6a_swir_wavelength_sweep.py
```

The example compares wavelength-dependent optical behaviour for Ge and GeSn
nanocrystals.

It reports quantities including:

- photon energy;
- direct and indirect optical gaps;
- direct, indirect, and total absorption;
- effective floating-gate absorption;
- absorbed photon flux;
- volumetric generation;
- absorbed photon rate per nanocrystal;
- photo-assisted transition rate.

The example is intended to demonstrate spectral consistency of the compact
model.

## 17. Run the SWIR voltage-reduction example

The quantitative Phase E6 voltage-reduction benchmark can be reproduced with:

```bash
python examples/e6d_swir_voltage_reduction.py
```

The benchmark uses:

```text
GeSn composition       : 8% Sn
NC diameter            : 5 nm
FG thickness           : 15 nm
Optical power density  : 1000 W/m^2
Photo capture eta      : 1e-10
Programming time       : 1 ms
Voltage range          : 0 to 4 V
Voltage step           : 0.25 V
```

Representative v0.10.0 results are:

| Wavelength | Photo rate (s^-1) | Vdark (V) | Vlight (V) | Delta V (V) |
|---:|---:|---:|---:|---:|
| 1300 nm | 3.092040e-07 | 3.9124 | 3.8343 | 0.0781 |
| 1550 nm | 3.506618e-07 | 3.9124 | 3.8238 | 0.0885 |
| 1700 nm | 3.684289e-07 | 3.9124 | 3.8193 | 0.0930 |

Positive `Delta V` means that illumination reduces the gate voltage required
to reach the selected common occupation target.

The benchmark value

```text
photo_capture_efficiency = 1e-10
```

is deliberately selected for the benchmark comparison and is **not
experimentally calibrated**.

Therefore these voltage reductions demonstrate the behaviour of the v0.10.0
compact model rather than an absolute prediction for a fabricated device.

## 18. Other executable examples

The `examples/` directory contains phase-oriented scripts covering the
electrical, retention, transport, and optical development path.

The most useful starting points for the current release are:

```text
examples/e6a_swir_wavelength_sweep.py
examples/e6d_swir_voltage_reduction.py
```

Earlier phase examples remain useful for reproducing the development and
validation history of the electrical framework.

## 19. Run the test suite

From the repository root:

```bash
python -m pytest -q
```

The official v0.10.0 validation baseline contains:

```text
194 passed
```

Continuous integration verifies the supported Python 3.11, 3.12, and 3.13
matrix.

## 20. Build the documentation

Install the development dependencies if required, then run:

```bash
python -m mkdocs build --strict
```

A successful strict build confirms that MkDocs can resolve the documentation
structure and links.

## Where to go next

After completing this quick start:

- read [Scientific scope and assumptions](scientific_scope.md) to understand
  what the current model can and cannot claim;
- read [Physics model](physics.md) for the coupled physical framework;
- read [Materials and provenance](materials.md) for electronic and optical
  parameter status;
- read [Optical programming](optics.md) for the complete Phase E model;
- read [Validation](validation.md) for the verification strategy;
- read [API reference](api.md) for the public programming interface;
- read [Roadmap](roadmap.md) for planned calibration and DTCO development.

## Scientific interpretation

NCMemSim v0.10.0 is a software-verified compact physical simulator.

The electrical and optical workflows can be used for controlled mechanism
studies, parameter sweeps, spectral comparisons, retention studies, and
electro-optical design exploration.

However, literature-supported model structure, provisional compact parameters,
and experimentally calibrated device parameters are not equivalent.

In particular, the current absolute optical absorption amplitudes and
photo-capture coupling are not device-specifically calibrated by default.

Results intended for quantitative comparison with fabricated devices should
therefore document the parameter provenance, fitting procedure, calibration
status, and applicable experimental range.
