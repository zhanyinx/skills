---
generated-by: render-paper
do-not-edit: this file is output; edit the source it was rendered from
---

# Registration accuracy in cyclic imaging

## Abstract

We register cyclic imaging panels across rounds and report the accuracy of that registration.

## Introduction

Cyclic imaging acquires one panel per round, and nothing in the existing tooling holds those
panels in a common frame; per-arm agreement is the measurement that settles it
(fig. 1 (b)).

## Methods

The pipeline runs as five stages, each reproducible from the committed configuration
(fig. 2 (a)).

### Imaging

Panels were acquired on a spinning-disk confocal, one round per marker pair, against the marker
schedule (tbl. 1).

### Registration

Registration proceeds pairwise against the DAPI channel, which every round shares
(fig. 1 (a)).

## Results and discussion

Accuracy is sufficient for per-arm comparison, which is what the drift left open
(fig. 1), and the arms carry the power the comparison needs
(suppl. 1).
