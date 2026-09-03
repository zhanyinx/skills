<!--
The figure split, reproduced as the real event.

A planning roster's Fig 2 covered the pipeline and the accuracy of the
registration stage inside it. During drafting it split in two: pipeline, and
registration accuracy. Under literal numbers the split is a document-wide
renumber, and the frozen draft's `Fig 2c-d` did not dangle — it changed
meaning, which is the one failure a dangling-reference check cannot catch.

Under names the split is a one-line roster edit. This source is what both
states are rendered from, and it is not edited between them.
-->
<!-- R1 — abstract: establishes that the pipeline registers cyclic panels accurately -->
<!-- slot: abstract -->

Two arms of a cyclic acquisition were registered and compared per arm
(@fig:study-design).

<!-- slot: introduction -->

Cyclic imaging acquires one panel per round, and the pipeline that aligns them runs as five stages
against a common anchor (@fig:stage-graph).

<!-- slot: methods -->

Illumination correction runs before stitching, so the seam it leaves is a side effect of the
correction rather than of the stitching module (@fig:seam-crop).

<!-- slot: methods-imaging -->

Panels were acquired on a spinning-disk confocal with DAPI in every round, and the overlay is what
registration is scored on (@fig:dapi-overlay).

<!-- slot: methods-registration -->

Registration proceeds pairwise against the DAPI channel, and its score is the per-arm Dice against
both baselines (@fig:dice-by-arm).

<!-- slot: results -->

Accuracy is sufficient for per-arm comparison, which is what the drift left open
(@fig:outcome-by-arm), and the arms separate on the outcome the cohort was powered for
(@fig:survival).
