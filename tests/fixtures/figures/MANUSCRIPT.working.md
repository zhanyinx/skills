<!-- R1 — abstract: establishes that the pipeline registers cyclic panels accurately -->
<!-- slot: abstract -->

We register cyclic imaging panels across rounds and report the accuracy of that registration.

<!-- slot: introduction -->

Cyclic imaging acquires one panel per round, and nothing in the existing tooling holds those
panels in a common frame; per-arm agreement is the measurement that settles it
(@fig:dice-by-arm).

<!-- slot: methods -->

The pipeline runs as five stages, each reproducible from the committed configuration
(@fig:stage-graph).

<!-- slot: methods-imaging -->

Panels were acquired on a spinning-disk confocal, one round per marker pair, against the marker
schedule (@fig:antibody-panel).

<!-- slot: methods-registration -->

Registration proceeds pairwise against the DAPI channel, which every round shares
(@fig:dapi-overlay).

<!-- slot: results -->

Accuracy is sufficient for per-arm comparison, which is what the drift left open
(@fig:registration-accuracy), and the arms carry the power the comparison needs
(@fig:power-analysis).
