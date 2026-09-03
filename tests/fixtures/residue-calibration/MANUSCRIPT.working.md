<!--
The calibration record for the bare-hole token list.

`G3` measured the list at zero hits across all thirteen section drafts and the mechanical
baseline — zero false positives in 74 KB of biomedical prose. That measurement is the warrant
for refusing rather than warning, so it is carried here as prose rather than as a comment in a
spec: every shape in this file is one the list comes close to and must not fire on.

Nothing here is corpus text. The shapes are what matters, not the sentences.
-->

<!-- slot: abstract -->

Cyclic imaging of fixed tissue resolves marker pairs one round at a time, and we report the
registration accuracy that supports per-arm comparison across n = 24 donors.

<!-- slot: introduction -->

Cyclic acquisition leaves each round in its own frame, and nothing in the existing tooling holds
those frames together. Panels stained for FOXP3, TBX21 and NKX2-1 must be compared in a single
coordinate system before any per-marker claim can be made, and the same holds for the MAX and
HOXA9 panels acquired alongside them. Donors were karyotypically normal at 46,XY, and grade II
and stage III cases were represented in similar proportion. Is one common frame enough to carry
a per-arm comparison?

<!-- slot: methods -->

The pipeline runs as five stages, each reproducible from the committed configuration.

<!-- slot: methods-imaging -->

Cells were fixed in 4% paraformaldehyde, washed three times in TBS, and blocked in TBST for
thirty minutes before the first round. Fixation was held constant across rounds so that the
registration error could not absorb a fixation artefact. Cohorts on TKI therapy were imaged on
the same instrument as the untreated cohorts, and the two TKIs in use were recorded per donor.
Cranial nerve XII was outside the imaged field in every case.

<!-- slot: methods-registration -->

Registration proceeds pairwise against the DAPI channel, which every round shares, at 10×
magnification. The residual distance between paired centroids is reported per pair, and the
paired difference across arms was significant at p < 0.001.

<!-- slot: results -->

Registration accuracy is sufficient for per-arm comparison, which is what the cross-round drift
left open. The residual distance is below one pixel in every pair, so the intensity analysis
rests on a measured value rather than on an absent one. Screening for latent TB was negative in
all donors, and no MTB culture was positive.
