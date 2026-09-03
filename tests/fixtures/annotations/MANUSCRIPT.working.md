<!-- R1 — abstract: establishes that the pipeline registers cyclic panels accurately -->
<!-- slot: abstract -->

We register cyclic imaging panels across rounds and report the accuracy of that registration.

<!-- slot: introduction -->

Cyclic imaging acquires one panel per round, and nothing in the existing tooling holds those
panels in a common frame.

<!-- @author waiting on the IRB number before submission -->
<!-- obj: the framing overstates how novel the drift problem is -->
<!-- DRAFT NOTES -->
<!-- -->
<!-- RESOLVED the earlier framing of this paragraph is superseded -->

<!-- slot: methods -->

The pipeline runs as five stages, each reproducible from the committed configuration.

<!-- slot: methods-imaging -->

Panels were acquired on a spinning-disk confocal, one round per marker pair.

<!-- slot: methods-registration -->

Registration proceeds pairwise against the DAPI channel, which every round shares, generated
with {{! the production registration arm }}.
<!-- {{ !  the   production  registration arm }}: VALIS accuracy preset plus micro-registration
     state, used for the accuracy figure. The pipeline ships medium-preset and micro-off,
     overridable per run. Reconcile before filling this in. -->
<!-- !@lab-imaging unverified: the six paired fractions are not in any committed table -->

<!-- slot: results -->

Registration raised Dice to {{! best-arm Dice }} from {{ rigid-only Dice }}, which is what the
drift left open.

Accuracy over the paired fractions is reported as {{ @lab-imaging
   the mean and standard deviation of
   the per-round Dice coefficient
   across every marker pair in
   the paired-fraction subset,
   pooled over both arms }} for completeness.

The per-arm comparison rests on {{ a noun phrase that runs a long way past the eighty-character advisory limit on the label naming one missing value }}.

<!-- slot: back-matter -->

{{ SLOT: @author data availability statement }}

{{ SLOT: ethics approval number }}

{{ the funder acknowledgement }}
