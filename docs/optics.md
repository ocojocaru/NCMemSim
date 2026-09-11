# Optical Programming

NCMemSim v0.10.0 introduces compact wavelength-dependent optical modelling and photo-assisted programming for Ge/GeSn nanocrystal nonvolatile-memory structures.

## Scope

The optical model provides:

- monochromatic LED and laser sources;
- photon energy and photon flux;
- wavelength-dependent Ge/GeSn absorption;
- direct-Gamma absorption;
- indirect phonon-assisted absorption;
- Urbach-tail absorption;
- Beer-Lambert absorption through the floating-gate layer;
- absorbed photon flux;
- absorbed photon rate per nanocrystal;
- photo-assisted charge-state transition rates;
- combined electrical and optical programming.

The optical model is designed as a compact physical model rather than an experimentally calibrated optical device simulator.

## Optical sources

A monochromatic source is represented by `LightSource`.

For a wavelength `lambda`, the photon energy is

$$
E_\gamma = \frac{hc}{\lambda}.
$$

For incident optical power density `P`, the incident photon flux is

$$
\Phi_\gamma = \frac{P}{E_\gamma}.
$$

Example:

```python
from ncmemsim.optics import LightSource

source = LightSource.laser(
    wavelength_nm=1550.0,
    power_density_W_m2=1000.0,
)
```

## Ge/GeSn optical response

The compact GeSn optical material model separates the absorption coefficient into three contributions:

$$
\alpha(E) = \alpha_\Gamma(E) + \alpha_L(E) + \alpha_U(E).
$$

where:

- `alpha_Gamma` is the direct-Gamma contribution;
- `alpha_L` is the indirect phonon-assisted contribution;
- `alpha_U` is the Urbach-tail contribution.

The direct and indirect band gaps are treated independently.

For GeSn, the direct-gap composition dependence uses literature-based parameters. The indirect-gap model is also literature-informed, while the absolute absorption amplitudes remain compact-model parameters.

The current model supports temperature-dependent phonon occupation for the indirect absorption contribution.

## Floating-gate absorption

The nanocrystal absorption coefficient is converted to an effective floating-gate absorption coefficient using the nanocrystal volume fraction:

$$
\alpha_{\mathrm{eff}} = f_{\mathrm{NC}}\alpha_{\mathrm{NC}}.
$$

The current implementation assumes that the HfO2 matrix is transparent in the modelled spectral range.

Beer-Lambert absorption through a floating-gate layer of thickness `d` is

$$
A = 1 - \exp(-\alpha_{\mathrm{eff}}d).
$$

The absorbed photon flux is

$$
\Phi_{\mathrm{abs}} = A\Phi_\gamma.
$$

## Photo-assisted programming

The absorbed photon flux is converted into an absorbed photon rate per nanocrystal.

A configurable photo-capture efficiency converts this rate into a photo-assisted transition rate.

The default compact transition model supports photo-assisted loading:

- 0 -> 1
- 1 -> 2

while photo-assisted detrapping is disabled by default.

Electrical and optical transition rates are combined additively in the occupancy engine.

Example:

```python
from ncmemsim.optics import LightSource
from ncmemsim.photo import PhotoTransitionConfig

source = LightSource.laser(
    wavelength_nm=1550.0,
    power_density_W_m2=1000.0,
)

photo = PhotoTransitionConfig(
    photo_capture_efficiency=1.0e-7,
)

result = simulator.relax_voltage(
    state,
    gate_voltage_V=2.0,
    light_source=source,
    photo_config=photo,
)
```

## Optical diagnostics

`Simulator.relax_voltage()` exposes optical diagnostics including:

- `optical_absorption_fraction`
- `absorbed_photon_flux_m2_s`
- `photo_transition_rate_s`
- per-floating-gate absorbed photon flux
- per-floating-gate photo-transition rate
- nanocrystal absorption coefficient
- effective floating-gate absorption coefficient

Voltage sweeps and C-V simulations support the same optical source and photo-transition configuration.

## SWIR validation

The Phase E6 validation covers wavelengths in the SWIR range and includes:

- wavelength-dependent absorption;
- Ge versus GeSn spectral response;
- electrical versus illuminated programming;
- electro-optical programming;
- probability conservation;
- photo-rate spectral ordering;
- programming-voltage reduction.

A quantitative benchmark was performed for:

- GeSn composition: 8% Sn;
- nanocrystal diameter: 5 nm;
- floating-gate thickness: 15 nm;
- incident optical power density: 1000 W/m^2;
- programming interval: 1 ms;
- benchmark photo-capture efficiency: 1e-10.

For a common target occupation:

| Wavelength | Vdark | Vlight | Delta V |
|---:|---:|---:|---:|
| 1300 nm | 3.9124 V | 3.8343 V | 0.078071 V |
| 1550 nm | 3.9124 V | 3.8238 V | 0.088539 V |
| 1700 nm | 3.9124 V | 3.8193 V | 0.093025 V |

The spectral ordering is:

```text
1700 nm > 1550 nm > 1300 nm
```

for both photo-transition rate and voltage reduction in this benchmark.

The value `photo_capture_efficiency = 1e-10` used in the voltage-reduction benchmark is a comparison parameter selected to place dark and illuminated programming curves in a common occupation range. It is not experimentally calibrated.

Therefore the reported voltage reductions demonstrate model behaviour and internal consistency rather than absolute experimental prediction.

## Current limitations

The v0.10.0 optical model does not yet include:

- Franz-Keldysh absorption;
- Stark shifts;
- voltage-dependent optical absorption;
- state filling;
- explicit strain-dependent absorption;
- nanocrystal quantum-confinement corrections;
- sequential optical attenuation through multiple floating gates;
- experimentally calibrated photo-capture efficiencies.

These effects can be added in later model revisions without changing the high-level optical programming API.
