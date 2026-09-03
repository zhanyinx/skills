<!-- R1 — abstract: establishes that the pipeline registers cyclic panels accurately -->
<!-- slot: abstract -->

We register cyclic imaging panels across rounds [@gatenbee2023] and report the accuracy of that
registration.

<!-- slot: introduction -->

Cyclic imaging acquires one panel per round [@hickey2022; @elhanani2023], and nothing in the
existing tooling holds those panels in a common frame.

<!-- slot: methods -->

The pipeline runs as five stages, each reproducible from the committed configuration.

<!-- slot: methods-imaging -->

Panels were acquired on a spinning-disk confocal, one round per marker pair.

<!-- slot: methods-registration -->

Registration proceeds pairwise against the DAPI channel, as Muhlberg and colleagues @muhlberg2020
describe, and every round shares it [@gatenbee2023].

<!-- slot: results -->

Accuracy is sufficient for per-arm comparison, which is what the drift left open [@hickey2022].
