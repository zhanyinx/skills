<!-- slot: abstract -->

We register cyclic imaging panels across rounds and report the accuracy of that registration.

<!-- slot: introduction -->

Cyclic imaging acquires one panel per round, and the pipeline is compatible with XXX inputs.

<!-- slot: methods -->

The pipeline runs as five stages, each reproducible from the committed configuration.
<!-- @author TODO chase the archive DOI before submission -->

<!-- slot: methods-imaging -->

Panels were acquired on a spinning-disk confocal, one round per marker pair.

```text
# FIXME: pin the exact resampling order before the release
```

<!-- slot: methods-registration -->

Registration proceeds pairwise against the DAPI channel, which every round shares, and reports
{{ @lab-imaging TBD residual distance }} for each pair.

<!-- slot: results -->

The residual distance is of order of XX, which is acceptable for the intensity analysis.
Archiving the panel stacks is a submission-readiness item. We should confirm that the container
mirror is published before the paper goes out.
