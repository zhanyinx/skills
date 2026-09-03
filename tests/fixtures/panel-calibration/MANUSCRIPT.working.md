<!--
The calibration corpus's own distribution, reproduced at its measured shape.

Of the parenthesised-letter occurrences in reader-facing prose, 21 of 21 were
panel references or declaration markers, and zero were enumerators. All 21 are
carried here in the form the design gives them — a panel name — and each one
marks a place where a literal panel letter stood.

The 37 legitimate letter-enumerator uses all sat inside comments, and they sit
inside comments here too. The refusal exempts them by construction rather than
by a marker string, because a comment never reaches a reader.
-->
<!-- R1 — abstract: establishes that the pipeline registers cyclic panels accurately -->
<!-- slot: abstract -->

Registration holds every round of a cyclic acquisition in one frame, and the per-arm agreement is
what the accuracy claim rests on (@fig:dice-by-arm).

<!-- slot: introduction -->

Cyclic imaging acquires one panel per round, and nothing in the existing tooling holds those panels
in a common frame (@fig:dapi-overlay). The seam illumination correction leaves is visible before the
correction runs (@fig:seam-crop), and the stage graph shows where in the pipeline it is applied
(@fig:stage-graph). What the existing tooling never measured is whether the alignment is accurate
enough to compare one arm against another (@fig:dice-by-arm).
<!--
   framings considered for this unit, and why the third was taken:
     (a) lead with the tooling gap
     (b) lead with the measurement
     (c) lead with the common frame, then the gap it leaves
     (d) lead with the arms
-->

<!-- slot: methods -->

The pipeline runs as five stages against a common anchor (@fig:stage-graph). Illumination
correction runs before stitching, which is why the seam is a side effect of the correction rather
than of the stitching module (@fig:seam-crop). Registration is the fourth stage, and the overlay is
what it is scored on (@fig:dapi-overlay).
<!--
   stage order, fixed by the config and not by this prose:
     (a) tile acquisition
     (b) illumination correction
     (c) stitching
     (d) registration
     (e) segmentation
-->

<!-- slot: methods-imaging -->

Panels were acquired on a spinning-disk confocal, one round per marker pair, with DAPI in every
round as the common anchor (@fig:dapi-overlay). Tiles overlap by ten per cent, and the overlap is
where the seam appears (@fig:seam-crop). Two arms were acquired at each of two accuracy settings
(@fig:dice-by-arm).
<!--
   acquisition arms, as scheduled:
     (a) high accuracy, micro on
     (b) high accuracy, micro off
     (c) low accuracy, micro on
     (d) low accuracy, micro off
     (e) rigid-only baseline
     (f) no-registration baseline
-->

<!-- slot: methods-registration -->

Registration proceeds pairwise against the DAPI channel, which every round shares
(@fig:dapi-overlay). The stage that performs it is the fourth (@fig:stage-graph), and its score is
the per-arm Dice against the baselines (@fig:dice-by-arm).
<!--
   scoring choices, and why the first was taken:
     (a) Dice on binarised DAPI
     (b) target registration error on landmarks
     (c) mutual information
     (d) normalised cross-correlation
-->

<!-- slot: results -->

Accuracy is sufficient for per-arm comparison, which is what the drift left open
(@fig:dice-by-arm). The overlay before registration shows the drift a reader can see
(@fig:dapi-overlay), and the same field after it shows what the pairwise fit recovers
(@fig:dapi-overlay). The seam survives registration, because it is not a registration defect
(@fig:seam-crop). The production arm is the high-accuracy setting with micro on
(@fig:dice-by-arm), and both baselines sit below it (@fig:dice-by-arm). Where in the pipeline the
recovery happens is fixed by the stage order (@fig:stage-graph).
<!--
   what the discussion owes, in the order the ladder opens it:
     (a) the drift claim
     (b) the accuracy claim
     (c) the per-arm comparison
     (d) the generalisation debt
     (e) the seam, which is not ours
     (f) the baselines
     (g) the production arm
     (h) what the numbers do not license
     (i) the marker-to-round justification, which needs an experimentalist
     (j) the limits of a single cohort
     (k) what a second cohort would settle
     (l) what the frozen arms cannot answer
     (m) the archive
     (n) the release tag
     (o) the frozen configuration
     (p) the reviewer's own cohort
     (q) what the abstract may claim
     (r) what the title may claim
-->
