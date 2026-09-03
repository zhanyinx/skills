---
generated-by: render-paper
do-not-edit: this file is output; edit the source it was rendered from
---

# Registration accuracy in cyclic imaging

## Abstract

We register cyclic imaging panels across rounds and report the accuracy of that registration.

## Introduction

Cyclic imaging acquires one panel per round, and nothing in the existing tooling holds those
panels in a common frame.

## Methods

The pipeline runs as five stages, each reproducible from the committed configuration.

### Imaging

Panels were acquired on a spinning-disk confocal, one round per marker pair.

### Registration

Registration proceeds pairwise against the DAPI channel, which every round shares, generated
with ⟦HOLE: the production registration arm⟧.

## Results and discussion

Registration raised Dice to ⟦HOLE: best-arm Dice⟧ from ⟦HOLE: rigid-only Dice⟧, which is what the
drift left open.

Accuracy over the paired fractions is reported as ⟦HOLE: the mean and standard deviation of the per-round Dice coefficient across every marker pair in the paired-fraction subset, pooled over both arms⟧ for completeness.

The per-arm comparison rests on ⟦HOLE: a noun phrase that runs a long way past the eighty-character advisory limit on the label naming one missing value⟧.

## Data availability

⟦SLOT: data availability statement⟧

⟦SLOT: ethics approval number⟧

⟦HOLE: the funder acknowledgement⟧
