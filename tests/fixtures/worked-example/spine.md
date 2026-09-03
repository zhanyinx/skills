# Spine — cross-panel registration and single-cell quantification

## Central claim

The pipeline is a reproducible end-to-end cyclic-imaging analysis, and the clinical figure is a
proof of concept rather than a claim about clinical performance.

## Rungs

### R1 — abstract

- establishes: the pipeline registers separately acquired panels accurately enough to quantify
- restates: R5

### R2 — background

- establishes: the unaddressed gap is cross-panel, and not the whole-slide scale the field reports
- opens: D1 (closed by R5) — whether registration across separately acquired panels is accurate

### R3 — experimental-protocol

- establishes: one physical section carries every panel, acquired one round at a time

### R4 — implementation

- establishes: the pipeline is reproducible from the committed configuration
- opens: D2 (closed by R5) — whether reproducibility says anything about correctness
- actual: drafted, hedged; the continuous-integration gate is a stub and the weights are unarchived

### R5 — results-discussion

- establishes: alignment accuracy is credible on a metric the engine does not control, and the imaging immune quantification recovers an orthogonal molecular contrast
- closes: D1
- closes: D2
- opens: D3 (closed by R6) — whether the concordance holds beyond six contrast-enriched cases
- actual: drafted, with six values still owed by the author

### R6 — limitations

- establishes: the design bounds what the proof of concept supports, and names the cohort that would lift those bounds
- closes: D3
