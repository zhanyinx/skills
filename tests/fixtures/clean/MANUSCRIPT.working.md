<!-- R1 — abstract: establishes that the pipeline registers cyclic panels accurately -->
<!-- slot: abstract -->

We register cyclic imaging panels across rounds and report the accuracy of that registration.

<!-- slot: introduction -->

Cyclic imaging acquires one panel per round, and nothing in the existing tooling holds those
panels in a common frame.
<!-- @author confirm the tool list against the review before submission -->
<!--
## superseded outline
   an earlier plan gave the introduction a Limitations child; the ladder deleted the rung
   those words served, so the child went with it
-->

<!-- slot: methods -->

The pipeline runs as five stages, each reproducible from the committed configuration.

<!-- slot: methods-imaging -->

Panels were acquired on a spinning-disk confocal, one round per marker pair.

<!-- slot: methods-registration -->

Registration proceeds pairwise against the DAPI channel, which every round shares.

<!-- slot: results -->

Accuracy is sufficient for per-arm comparison, which is what the drift left open.
