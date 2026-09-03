<!--
The negative fixture for the workflow-phrase lint: legitimate reader-facing prose it currently
flags, and should not.

`pending` and `we should` are ordinary academic English — a pending trial is a fact about the
literature, and "we should expect" is a hedge, not a note to the author. The lint is short and
dumb by design, so it fires on both. This is the accepted cost, recorded so that sharpening the
lint is a deliberate, visible change rather than a quietly loosened pattern.

The cost is bounded differently from the bare-hole list: this lint only **warns** under
`--circulate`, so the everyday path is undisturbed and the refusal lands only at submission.
-->

<!-- slot: abstract -->

We register cyclic imaging panels across rounds and report the accuracy of that registration.

<!-- slot: introduction -->

Cyclic imaging acquires one panel per round, and nothing in the existing tooling holds those
panels in a common frame. One pending multi-centre trial will test the same panels prospectively,
and its design assumes a common frame.

<!-- slot: methods -->

The pipeline runs as five stages, each reproducible from the committed configuration.

<!-- slot: methods-imaging -->

Panels were acquired on a spinning-disk confocal, one round per marker pair.

<!-- slot: methods-registration -->

Registration proceeds pairwise against the DAPI channel, which every round shares.

<!-- slot: results -->

Registration accuracy is sufficient for per-arm comparison. Because the error accumulates
pairwise, we should expect the residual distance to scale with the number of rounds, and it does.
