<!--
The calibration corpus's own distribution, reproduced at its measured shape.

Outside comments the corpus held 70 bracket spans: 40 citations and 30
author-facing annotations, and zero other legitimate uses — no markdown link,
no reference link, no footnote, no task box in 74 KB of biomedical prose. This
source carries the same 70: 40 citation spans over 17 distinct keys, and the 30
annotations migrated into the annotation channel where they belong. Three more
bracket spans sit inside comments, where the corpus also had three, and are
exempt by construction.

The mention sequence is the corpus's own, and it is the load-bearing evidence:
its first citation was numbered 24 and its second 25, appended last because
renumbering by hand would have shifted every other number. Under keys the
render assigns 1 and 2, and nobody has to decide anything.
-->
<!-- R1 — abstract: establishes that the pipeline registers cyclic panels accurately -->
<!-- slot: abstract -->

Deconvolution signatures disagree with imaging on the same cohort [@foy2022; @sturm2019], and we
show that cross-panel registration [@valis2023] is accurate enough to compare the two per arm.

<!-- slot: introduction -->

Multiplexed imaging resolves protein composition cell by cell [@hickey2022], and the spatial
profiling literature has converged on the tumour microenvironment as its proving ground
[@elhanani2023]. Whole-slide alignment across stains is a solved problem in principle
[@gatenbee2023], and cyclic rounds have been registered pairwise before [@muhlberg2020].

What is not solved is what the alignment costs downstream. Segmentation pipelines assume a common
frame [@bankhead2017], as do the multiplexed analysis toolchains built on top of them
[@schapiro2017], and a whole-slide alignment error propagates into every per-cell measurement they
produce {{ the propagation figure, once the sweep finishes }}. Pixel classifiers inherit the same
assumption [@berg2019].

Classical feature matching [@lowe2004] with a robust fit [@fischler1981] remains the baseline that
the newer whole-slide methods [@valis2023] are measured against, and the deep segmentation models
[@greenwald2022] that replaced hand-tuned pipelines [@bankhead2017] did not change what registration
owes them [@berg2019].

<!-- an ordinary note: the tool list wants a check against the review -->
<!-- [author to supply: whether the 2019 benchmark belongs in this paragraph] -->

<!-- slot: methods -->

The pipeline runs as five stages, each reproducible from the committed configuration. Deformable
registration [@klein2010] and diffeomorphic registration [@avants2008] were both evaluated as arms
{{ the arm count, pending the final sweep }}, against the classical baseline [@lowe2004]
{{ whether the baseline arm is reported at all }}.

<!-- slot: methods-imaging -->

Panels were acquired on a spinning-disk confocal, one round per marker pair, at
{{ the objective magnification }}. Keypoints were detected per round [@lowe2004] before any
whole-slide step [@valis2023], and nuclei were segmented with the published defaults
[@bankhead2017] {{ the segmentation parameter set }}. Marker panels follow the published ordering
[@schapiro2017] {{ whether round 4 and round 5 were swapped }}.

The cohort description is a venue field: {{ SLOT: cohort size and accrual window }}. So is the
deposition statement: {{ SLOT: the accession or controlled-access wording }}.

<!-- slot: methods-registration -->

Registration proceeds pairwise against the DAPI channel, which every round shares
{{ the DAPI binarisation rule }}. The spatial profiling literature treats registration as
preprocessing [@elhanani2023], which is why its error budget is rarely reported
{{ a source for the rarely-reported claim }}. Deconvolution was run with the published signature
[@finotello2019] {{ the deconvolution version }}, and cellpose was used for the comparison
segmentation [@stringer2021] {{ the cellpose model weights }}. The classifier baseline
[@berg2019] was kept unchanged {{ whether the classifier was retrained }}.

<!--
An earlier plan gave this unit a Limitations child; the ladder deleted the rung those words served,
so the child went with it. [author to confirm: whether the deleted rung is recorded in the map]
-->

<!-- slot: results -->

Accuracy is sufficient for per-arm comparison, which is what the drift left open. The imaging and
deconvolution estimates disagree on the same cohort [@elhanani2023], and the disagreement survives
the best registration arm [@valis2023] {{ the best-arm Dice }}. Neither the segmentation model
[@greenwald2022] nor the published pipeline [@bankhead2017] closes it {{ the per-arm Dice values }},
and the pixel classifier [@berg2019] behaves the same way {{ the classifier's per-arm numbers }}.

Per-arm agreement was computed against the published pipeline [@bankhead2017] using the panel
ordering above [@schapiro2017] {{ the agreement metric definition }}. The deconvolution estimates
[@finotello2019] and the comparison segmentation [@stringer2021] were held fixed across arms
{{ whether the fixed-arm assumption holds for round 6 }}, so the residual disagreement is not an
artefact of either {{ the residual figure }}.

The remaining gap sits with the imaging side. The published pipeline [@bankhead2017] and the panel
ordering [@schapiro2017] account for most of it {{ the fraction attributable to ordering }}, the
deconvolution signature [@finotello2019] for a further part {{ the signature's contribution }}, and
the comparison segmentation [@stringer2021] for the remainder {{ the segmentation residual }}. The
whole-slide method [@valis2023] leaves the rest {{ the unexplained fraction }}.

Three questions are still open on the imaging side {{ the hot-group CD45 fraction }}, on the
deconvolution side {{ the six paired fractions }}, and on the registration side
{{ the no-registration Dice }}. The venue's own back matter is unwritten:
{{ SLOT: ethics and consent reference }}, {{ SLOT: competing interests }},
{{ SLOT: funding sources and grant numbers }}, and {{ SLOT: per-author contribution statement }}.

<!-- [FIGURE-PRODUCTION: the scale bar length, once the panel is exported] -->
