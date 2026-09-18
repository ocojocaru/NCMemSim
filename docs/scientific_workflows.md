# Scientific workflow integration — Phase I / v0.14.0 development

## Status and baseline

I0 starts `0.14.0.dev0` from published v0.13.0 commit
`c3b1c10824c8296e7900e0b9bd8cbb19d6d75f8f` on
`dev/v0.14.0-scientific-workflows`. Citation metadata remains on v0.13.0.
Existing fitting/calibration, nominal DTCO and Robust DTCO APIs remain available.
I0 supplies scope/contracts and development setup; the integration APIs and
references below are planned, not implemented.

## Delivery sequence

| Phase | Deliverable | Status |
|---|---|---|
| I0 | Bootstrap, scope and acceptance contracts | Implemented |
| I1 | Immutable workflow evidence and identity contracts | Next |
| I2 | Explicit fitted-parameter application and evaluator context adapter | Planned |
| I3 | Electrical fitting/qualification → nominal/Robust DTCO reference | Planned |
| I4 | Electro-optical fitting/qualification → nominal/Robust DTCO reference | Planned |
| I5 | End-to-end provenance, failure and compatibility verification | Planned |
| I6 | Linked workflow evidence report and reproducible exports | Planned |
| I7 | Final version/documentation audit, full CI and clean distributions | Planned |

## Scope

Connect existing Phase F fitting/qualification results to Phase G/H studies
without changing simulator physics, unit contracts, observation semantics or
existing qualification rules. Initial references use small explicitly synthetic
training/held-out datasets so development does not depend on unavailable measured
data. They verify software execution and identity links; experimental validation
requires independently sourced measurements and an applicable model.

The integration layer will preserve dataset/protocol/specification identities,
fitted values, fitting diagnostics, qualification criteria and results, applied
parameter contexts, nominal evaluations, exact sample manifests, sample failures,
response statistics, constraints, robust objectives and full source links. Runtime
provenance is recorded; cross-runtime bitwise reproducibility is not promised.

## Frozen contracts

1. **Evidence and scientific claims.** Keep data origin (synthetic/measured),
   source, applicability and qualification status separately explicit. Optimizer
   convergence, passing synthetic validation criteria or producing a Pareto front
   does not establish experimental device calibration or manufacturing yield.
   Preserve any existing qualification result as evidence without silently
   changing its status; never reinterpret synthetic evidence as measurements.
2. **Application.** Apply supported fitted parameters using existing validated
   application APIs, canonical units and fresh isolated contexts. Record full
   resulting device/material definitions, physics/photo settings, simulation
   configuration and operating protocol. A parameter-application hash alone is
   not a complete simulator identity. Unsupported applications fail explicitly;
   no alias, guessed mapping or implicit conversion is introduced.
3. **Nominal/sample consistency.** Nominal and sampled evaluation use the same
   declared response model, fitted context, configuration and protocol family.
   Each evaluation gets fresh mutable state. Identity mismatches and missing
   evidence fail before execution where possible; staged sample failures remain
   visible and are not relabelled as physical infeasibility.
4. **Uncertainty.** Users supply bounded independent Phase H variation definitions
   with explicit origin/provenance. Fit standard errors or covariance are not
   automatically transformed into probability laws or fabrication variation.
   Parameter-estimation and fabrication assumptions remain distinct. Correlations,
   hierarchical laws and general MODEL-scope sweeps are outside this cycle.
5. **Model-side fitted parameters.** For photo-capture or other supported fitting
   targets applied to model/configuration, snapshot that evaluator context
   explicitly. This does not add MODEL-scope design variables or distributions.
   DEVICE/OPERATING sampling remains within existing Phase H contracts.
6. **Reports.** Link complete source snapshots and identities rather than combine
   unrelated hashes or pass-status labels. Retain all failures, denominators and
   undefined statistics; integrity hashes establish consistency, not signatures
   or physical validation. Report serialization does not reevaluate physics.

## Acceptance by phase

I1 must reject malformed/missing evidence and preserve immutable snapshots,
source identity, data origin and qualification semantics. Public object names
and schema versions are introduced with the implementation review, not assumed
by this planning document.

I2 must demonstrate exact parameter application, isolation of baseline/context,
canonical units and complete evaluator provenance, including model-side settings.
Tests must distinguish full context identity from the narrower application hash.

I3/I4 must execute real existing simulator/protocol calls, with declared synthetic
training/held-out data and retained fit/qualification evidence. Fitted parameters
must actually drive predictions. Nominal/sample contexts must be demonstrably
consistent; deliberate failures are separated from physical responses. Any
chosen success/error thresholds require explicit units and applicability.

I5 must check source/context tampering or mismatches, complete-case/failure
accounting, preserved Phase F/G/H contracts and end-to-end electrical/optical
execution. It adds meaningful integration verification, not a second fitting
algorithm or altered scientific defaults.

I6 must restore/export linked evidence without rerunning fits or physics, reject
broken source links, preserve JSON/CSV/Markdown scientific labels and denominators,
and use explicit non-overwrite behavior.

I7 audits all current status/version claims, examples, imports, rendered links and
anchors before the release tag. It runs full pytest, supported-Python CI and
clean wheel/sdist installations with both new references and retained G/H probes.
Built and published source archives must contain the actual audited documentation.

## Development and final-release gates

Update docs and CHANGELOG and run focused local tests at each step. Intermediate
I0–I6 branch pushes/PRs do not launch CI or Documentation. Local checks validate
snippet syntax/public imports and current executable examples without MkDocs.
Package builds, full regression and strict rendered-documentation auditing belong
to final-version preparation. At I7, enable automatic CI and Documentation for
this exact dev branch, including final corrections. No separate release branch
is required. Tags continue to launch CI/Release; Pages deploys only from main.

## Outside this scope

No new quantum, strain, broadband or sequential multilayer optics; no automatic
experimental qualification, calibrated yield prediction, correlated uncertainty,
adaptive optimizer, numerical backend acceleration or physics-default changes.
DOI/archive and stable-API review remain separate v1.0 readiness requirements;
completing this integration cycle alone does not declare v1.0 stability.
