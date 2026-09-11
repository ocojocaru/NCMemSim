# Materials and parameter provenance

## Material objects

NCMemSim distinguishes bulk/dielectric `Material` objects from
`NanocrystalMaterial` objects.

Built-in public constructors and presets include:

- `SILICON`
- `SIO2`
- `HFO2`
- `make_ge()`
- `make_gesn(sn_fraction)`

The material framework separates electronic material parameters, optical
material parameters, composition models, band-alignment models, and parameter
provenance.

## GeSn composition

`make_gesn(x)` uses a Sn atomic fraction `x`.

For example:

```python
from ncmemsim import make_gesn

gesn_2pct = make_gesn(0.02)
gesn_10pct = make_gesn(0.10)
```

Composition-dependent quantities are model outputs rather than universal
constants. Their interpretation depends on the selected interpolation law,
temperature, strain state, composition range, and underlying literature or
fitted parameter set.

Scientific results should therefore report the material-model version and
parameter provenance together with the GeSn composition.

## Electronic material parameters

Electronic `NanocrystalMaterial` properties include quantities used by the
electrostatic and tunnelling models, such as:

- dielectric constant;
- effective mass;
- compact band-gap information;
- effective programming barrier;
- effective erase barrier.

These quantities belong to the electrical model.

The electronic `bandgap_eV` field should not be interpreted as a substitute
for the optical direct-Gamma or indirect-L gaps used by the optical model.

## Parameter provenance

The material framework supports provenance metadata so that a parameter can be
traced to its physical or modelling origin.

A reproducible parameter should ideally record:

- value and unit;
- source or citation;
- model or interpolation rule;
- composition range;
- temperature range;
- strain assumptions when applicable;
- whether the value is measured, fitted, assumed, or inherited;
- uncertainty when available;
- extrapolation status when used outside the source range.

NCMemSim distinguishes literature-supported values from provisional compact
model parameters. A parameter being present in the software does not imply that
it has been experimentally calibrated for a particular fabricated device.

The reproducibility manifest includes material-model information and hashes the
device definition. Scientific workflows should preserve that manifest together
with numerical results.

## Band alignment

Compact barrier heights can be generated using band-alignment helpers such as
an electron-affinity rule.

Example:

```python
from ncmemsim import make_gesn
from ncmemsim.materials import BarrierModel, HFO2

alignment = BarrierModel.affinity_rule(
    make_gesn(0.10),
    HFO2,
)
```

These values are model choices and should not automatically be interpreted as
experimentally measured interface offsets for every GeSn/dielectric structure.

Barrier values used for tunnelling are especially sensitive parameters and
should be reported explicitly in reproducible simulation studies.

## Optical material models

NCMemSim v0.10.0 includes a dedicated optical material layer under:

```text
ncmemsim.materials.optics
```

The optical model is intentionally separated from the electronic
`NanocrystalMaterial` representation.

Principal public optical objects include:

- `OpticalPoint`
- `GeSnOpticalParameterSet`
- `GeSnAbsorptionParameterSet`
- `CompactOpticalMaterialModel`
- `CompositeGeSnAbsorptionModel`

Supporting functions include:

- `photon_energy_eV`
- `direct_gap_gesn_eV`
- `indirect_gap_gesn_eV`
- `phonon_occupation`

## Direct optical gap

The compact GeSn direct-Gamma gap model uses a composition-dependent bowing
relation.

At 300 K, the current parameter set uses:

- Ge direct-Gamma gap: `0.7985 eV`;
- alpha-Sn direct-Gamma gap: `-0.413 eV`;
- direct-gap bowing parameter: `2.89 eV`.

The direct-gap composition dependence is literature-based.

The current implementation follows the parameterization used in the
literature source identified in the optical-model provenance metadata.

The optical direct gap is distinct from the electronic compact `bandgap_eV`
field used elsewhere in the simulator.

## Indirect optical gap

The compact indirect-L model uses separate parameters:

- Ge indirect gap: `0.664 eV`;
- alpha-Sn indirect gap: `0.092 eV`;
- indirect-gap bowing parameter: `0.89 eV`.

These values are literature-informed compact-model parameters.

The indirect bowing parameter is not universal. Reported values depend on
temperature, strain state, measurement technique, and model definition.

For this reason, the indirect-gap parameter set should be treated as a
versioned modelling choice rather than a composition-independent physical
constant.

## Optical absorption model

The v0.10.0 Ge/GeSn absorption model separates three contributions:

\[
\alpha(E)
=
\alpha_{\Gamma}(E)
+
\alpha_{L}(E)
+
\alpha_{U}(E),
\]

where:

- \(\alpha_{\Gamma}\) is the direct-Gamma contribution;
- \(\alpha_L\) is the indirect phonon-assisted contribution;
- \(\alpha_U\) is the Urbach-tail contribution.

The indirect contribution includes temperature-dependent phonon occupation.

The composite formulation is based on published Ge/GeSn absorption modelling,
while the current numerical amplitudes are compact-model parameters rather than
a complete experimentally calibrated optical-constant database.

## Current absorption parameters

The default compact absorption parameter set includes quantities such as:

```text
direct_prefactor_A
indirect_prefactor_A
phonon_energy_eV
urbach_energy_eV
urbach_edge_alpha_m_inv
temperature_K
```

The current default amplitudes are provisional.

They are suitable for:

- implementation verification;
- controlled parameter studies;
- spectral trend analysis;
- relative Ge versus GeSn comparisons;
- electro-optical mechanism studies.

They should not be treated as absolute experimentally validated absorption
coefficients without independent calibration.

## Nanocrystal volume fraction

Optical absorption in a floating-gate layer uses the nanocrystal volume
fraction:

\[
\alpha_{\mathrm{eff}}
=
f_{\mathrm{NC}}\alpha_{\mathrm{NC}}.
\]

Here:

- \(\alpha_{\mathrm{NC}}\) is the optical absorption coefficient assigned to
  the nanocrystal material;
- \(f_{\mathrm{NC}}\) is the nanocrystal volume fraction.

This optical weighting is distinct from the electrically active fraction used
by the charge-state population model.

A nanocrystal can contribute to optical absorption even when only part of the
ensemble is treated as electrically active by the compact occupancy model.

## Optical matrix assumption

For the current Phase E model, the HfO2 matrix is treated as optically
transparent over the modelled wavelength range.

The implementation therefore neglects:

- matrix absorption;
- detailed effective-medium electrodynamics;
- multiple scattering;
- interference within the multilayer stack;
- wavelength-dependent refractive-index propagation;
- sequential attenuation through multiple floating gates.

These effects may be introduced in later optical-model revisions.

## Spectral validity and extrapolation

The optical model should be interpreted with its source ranges in mind.

The GeSn absorption literature used for the compact formulation includes
measurements over limited composition and wavelength ranges. Simulations
outside those ranges may therefore constitute extrapolation.

For example, a material composition or wavelength outside the experimental
range of the source data should be reported explicitly as an extrapolated
compact-model result.

Spectral smoothness or physically plausible trends do not by themselves
constitute experimental validation.

## Calibration status

NCMemSim distinguishes three different concepts:

1. **literature-supported model structure or parameter values**;
2. **provisional compact-model parameters**;
3. **device-specific experimentally calibrated parameters**.

The v0.10.0 optical model contains the first two categories.

Device-specific calibration is planned for the experimental-fitting stage and
is not implied by the current defaults.

In particular:

- absolute absorption amplitudes remain provisional;
- photo-capture efficiency is not a material constant established by the
  current implementation;
- SWIR programming-voltage-reduction benchmarks demonstrate internal model
  behaviour rather than absolute predictive accuracy.

## Adding a material

A new material model should provide:

1. an unambiguous identifier;
2. parameters with explicit units;
3. provenance metadata;
4. composition and temperature validity ranges;
5. strain assumptions where relevant;
6. tests at endpoints and representative intermediate values;
7. documentation of extrapolation behaviour;
8. explicit calibration status;
9. a registry entry only after the model is stable enough for public use.

For an optical material model, also document:

- direct and indirect transition definitions;
- absorption-model assumptions;
- spectral range;
- experimental or literature basis;
- any phenomenological amplitudes;
- whether quantum confinement, strain, field effects, or state filling are
  included.
