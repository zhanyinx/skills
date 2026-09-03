<!-- R1 — abstract: establishes that the pipeline registers cyclic panels accurately -->
<!-- slot: abstract -->

We register cyclic imaging panels across rounds and report the accuracy of that registration.

<!-- slot: introduction -->

Cyclic imaging acquires one panel per round, and nothing in the existing tooling holds those
panels in a common frame.

<!-- slot: methods -->

The pipeline runs as five stages, each reproducible from the committed configuration
(@fig:pipeline). Every stage writes its intermediate to a versioned store, so a rerun of one
stage reproduces the same output from the same input, and the stage graph is what a reader
follows through the procedure (@fig:stage-graph). Marker panels were chosen against the schedule
the earlier mapping work published @hickey2022, and the acquisition order follows that schedule
round by round [@gatenbee2023].

Registration ran against the {{! the registration preset }} arm, and the accuracy figure was
produced from that arm rather than from the shipped default.

<!-- slot: methods-imaging -->

Panels were acquired on a spinning-disk confocal, one round per marker pair, and every round
carries its own illumination reference (@fig:seam-crop).

<!-- slot: methods-registration -->

Registration proceeds pairwise against the DAPI channel, which every round shares
(@fig:dapi-overlay).

<!-- slot: results -->

Accuracy is sufficient for per-arm comparison, which is what the drift left open
(@fig:registration-accuracy), and the per-arm agreement holds in both arms (@fig:dice-by-arm)
[@gatenbee2023].
