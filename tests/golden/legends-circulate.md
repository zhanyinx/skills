---
generated-by: render-paper
do-not-edit: this file is output; edit the source it was rendered from
---

# Registration accuracy in cyclic imaging

## Abstract

We register cyclic imaging panels across rounds [1] and report the accuracy of that
registration.

## Introduction

Cyclic imaging acquires one panel per round [2], and nothing in the existing tooling holds
those panels in a common frame; per-arm agreement is the measurement that settles it
(fig. 1 (b)).

## Methods

The pipeline runs as five stages, each reproducible from the committed configuration
(fig. 2 (a)).

### Imaging

Panels were acquired on a spinning-disk confocal, one round per marker pair, against the marker
schedule (tbl. 1) and with the reagents listed in ext. tbl. 1.

### Registration

Registration proceeds pairwise against the DAPI channel, which every round shares
(fig. 1 (a)).

## Results and discussion

Accuracy is sufficient for per-arm comparison, which is what the drift left open
(fig. 1), the drift stays flat across rounds (ext. fig. 1), and the arms
carry the power the comparison needs (suppl. 1).

## References

1. Gatenbee, Chandler D.; Baker, Ann-Marie. Virtual alignment of pathology image series. Nature Communications (2023).
2. Hickey, John W.; Neumann, Elizabeth K. Spatial mapping of protein composition in tissue. Nature Methods 19:284–295 (2022). doi:10.1038/s41592-021-01316-y.
3. Muhlberg, Alexander. Registration of cyclic immunofluorescence rounds. MICCAI (2020).
4. Elhanani, Ofer; Ben-Uri, Reut. Spatial profiling technologies illuminate the tumour microenvironment. Cancer Cell (2023).

## Legends

### Tbl. 1

Marker pairs by round, with the clone and the dilution for each, after Muhlberg [3].

### Fig. 1

**Registration holds every round in one frame.**

a shows the DAPI overlay before and after registration, on the stages of
fig. 2 (a). b shows per-arm Dice [4,2].

### Fig. 2

Five stages, each reproducible from the committed configuration. a shows the stage
graph and b a tile-boundary crop [2].

### Ext. fig. 1

Residual drift per round after registration, against fig. 1.

### Ext. tbl. 1

Every reagent, with its supplier and lot.

### Suppl. 1

Power for each per-arm comparison at the planned sample size.
