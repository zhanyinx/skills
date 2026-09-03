<!--
The worked example, before.

The same two units as `MANUSCRIPT.working.md`, drafted the way the old design drafted them: the
section mints its own headings, references figures and panels by literal number, carries its
author-facing gaps in improvised bracket spans, and ends with a block of drafting notes that sits
in the stream a reader reads.

This file is a source the current renderer cannot parse, and that is the measurement. The five
counts pinned against it live in `tests/test_worked_example.py`.

Nothing here is corpus text. The shapes are what matters, not the sentences.
-->

# Results and Discussion

Reproducibility by construction says nothing about whether the alignment a pipeline performs is
correct — correctness is what the two evaluations below test. They are reported together, each
result beside its interpretation, because separating them would make the reader hold one without
the other. The first quantifies alignment of separately acquired panels (Fig 2). The second asks
whether the single-cell immune quantification built on top of it is trustworthy (Fig 3).

## Registration accuracy

Alignment is the pipeline's load-bearing capability — we therefore quantified it directly. A
two-colour anchor overlay of two separately acquired panels shows the cross-panel drift between
acquisitions, and shows that drift resolved once the panels are aligned (Fig 2c). To put a number
on the alignment we compared a matrix of configurations on the same data — two engine accuracy
presets crossed with micro-registration on and off — against two baselines, a rigid-only alignment
and no alignment at all (Fig 2d). Additional files carry the full per-arm table.

Two metrics were used — no single one answers both questions honestly. The engine-internal target
registration error is the residual distance between matched keypoints after alignment. It ranks
the arms cleanly, which is what makes it the method-selection metric, but it is computed on the
same correspondences the engine optimised against, and only where matching succeeded. It is an
optimistic, self-reported quantity.

The second metric closes that gap. We binarised the anchor channel of each aligned panel — the
binarisation rule is a fixed intensity percentile followed by a morphological opening — and
measured the Dice overlap of the resulting nuclear masks across panels. Because the anchor channel
is present in every panel and is not the object the engine optimises against, Dice either
corroborates the ranking or exposes it as circular (Fig 2c–d).

The two metrics agree. Alignment substantially improved cross-panel anchor overlap over both
baselines — the no-alignment and rigid-only arms left the nuclear masks visibly misaligned, while
full rigid-plus-non-rigid alignment raised Dice to [author to supply: best-arm Dice value] from
[author to supply: rigid-only Dice value] and [author to supply: no-registration Dice value]
respectively. The best-performing arm was [author to supply: the winning arm]. Because an
independent metric moves in step with the internal one, the ranking is not an artefact of the
engine scoring its own work.

Alignment is driven by an automated, open-source whole-slide method reported to reach
state-of-the-art accuracy on a public benchmark [citation needed: the benchmark the engine reports
on]. That standing justifies the choice of tool — it does not transfer to this pipeline's own
accuracy, which is what Dice is for. The comparison reported here is internal, not a benchmark
against competing pipelines, so no relative-performance claim follows from it (Figure 2).

## Proof of concept

Alignment being accurate does not make what is measured on top of it meaningful — so we asked
whether the single-cell immune quantification is trustworthy, using two orthogonal molecular
readouts as checks.

The pipeline and the downstream gating were applied together to six cases — the three highest and
three lowest on a transcriptomic immune score, drawn from a larger profiled cohort. Imaging
populations were called by strict sequential hierarchical gating on the exported per-cell feature
table (Fig 1), with a pan-immune gate on one marker; T and natural-killer lineages resolve at
single-cell level, while myeloid and B compartments are recovered only in aggregate. Neither
anchor is a ground truth — this is concordance among proxies, not validation against a ground
truth.

The imaging pan-immune fraction separates the three hot cases from the three cold ones, with the
six individual case values overlaid on the boxplots (Fig 3a). The imaging immune fraction was
consistently higher in the hot group — [author to supply: hot and cold group imaging fractions] —
so an imaging quantity recovers an ordering fixed before any imaging by orthogonal
transcriptomics. The groups are separated on the score axis by construction — the score is the
selection variable — and the contrast-enriched design inflates the apparent gap (Fig 3a). No
p-value is reported: three against three is too small to support an inferential test.

Whether the imaging immune fraction tracks an orthogonal molecular estimate case by case is the
load-bearing question (Fig 3b). For each of the six cases the deconvolution immune fraction is
plotted against the imaging fraction — the quanTIseq run used here is the one described in Methods
— at the total-immune tier. Cases scored immune-high by imaging were immune-high by deconvolution
[author to supply: the six paired fractions], so the two estimates place the six cases in a
concordant order (Fig 3b).

The two axes use different denominators — imaging counts a fraction of segmented cells while
deconvolution estimates a fraction of a bulk expression mixture — so the points are not expected
to fall on the identity line. No correlation coefficient, p-value or confidence interval is
reported: at six cases any such statistic would overstate the precision of a six-point visual. The
lower-tier scatters appear in Additional files (Fig 4a, Fig 4b) and are directionally consistent
with the total-immune tier (Fig 4c).

## Limitations and future work

Autofluorescence is the first limitation. The acquisition protocol did not capture a pre-stain
blank image, so local background subtraction was applied instead. Panel coverage is the second: the
antibody panel carries a pan-immune gate on one marker and no myeloid or B-cell markers, so those
compartments resolve only in aggregate (Fig 3b). Third, the segmentation model's generalisation to
this tissue and scanner is assumed rather than benchmarked here.

With six cases and a contrast-enriched selection the design inflates both the group separation and
the co-variation, and precludes any inferential statistic — the findings are descriptive and
hypothesis-generating. A larger, unselected cohort would move the analysis toward quantitative
agreement, and a broader antibody panel would resolve the missing compartments at single-cell
level.

DRAFT NOTES

Layout A was used here: two result blocks plus a shared tail, 800 words for registration, 1,200
for concordance, 500 for the tail. Check the figure ordering once the pipeline figure is
split. Author must confirm each committed DIRECTION holds once the run values are filled in
[check with the imaging lab whether this arm produced the Fig 3 data]. The tier-to-lineage mapping
was cut from this section and has not landed anywhere else yet.
