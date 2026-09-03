<!--
The worked example, after.

`before/results-discussion.md` is the same two units as they were drafted under the old design.
This is what they become under the new one, and the two files are the fixed points the
before/after deltas are measured between.

The first four slots are not part of the redraft. They exist so that the roster resolves against a
whole document rather than a section: the five roster names are first mentioned in roster order, so
`registration-accuracy` numbers fourth and `proof-of-concept` fifth, which is the numbering the
figure split reached by hand. A section-scoped render cannot see that, which is why the regression
renders the document as well as the unit.

Nothing here is corpus text. The shapes are what matters, not the sentences.
-->

<!-- slot: abstract -->

We align separately acquired panels of one physical section into a common frame and quantify
single-cell immune content on the aligned result. Alignment accuracy is measured against a metric
the alignment engine does not optimise against, and the immune fractions that follow are checked
against two orthogonal molecular readouts of the same tissue.

<!-- slot: background -->

Cyclic acquisition leaves each round in its own frame, and the tooling that exists holds rounds
together within one acquisition rather than across separate ones. The gap the field reports is one
of scale. The gap that blocks this analysis is the cross-panel one: two panels of the same section,
acquired on different days, share no coordinate system until something puts them in one. Whether an
alignment computed across separate acquisitions is accurate enough to quantify on is the question
the rest of this paper answers.

<!-- slot: experimental-protocol -->

Every panel was acquired from one physical section, one round per marker pair, with the anchor
channel repeated in every round (@fig:protocol-schematic). Rounds were separated by a stripping
step, and the section was re-mounted between acquisitions, so the frames the rounds arrive in are
related by an unknown transform rather than by a stage offset.

<!-- slot: implementation -->

The pipeline runs as five stages against the anchor channel, each reading a declared input and
writing a declared artefact, so a run is reproducible from the committed configuration
(@fig:pipeline). Segmentation and per-cell feature extraction close the run, and the feature table
it exports is what the gating operates on (@fig:phenotyping).

<!-- slot: results-discussion -->

<!-- RUNG R5 of 6.
     establishes: alignment accuracy is credible on a metric the engine does not control
                  (@fig:registration-accuracy); imaging immune quantification recovers an
                  orthogonal transcriptomic contrast and co-varies with an orthogonal molecular
                  estimate of the same immune content (@fig:proof-of-concept)
     closes:      D1, the cross-panel accuracy debt; D2, the correctness debt
     opens:       D3, generalisation beyond six contrast-enriched cases -->

Reproducibility by construction says nothing about whether the alignment a pipeline performs is
correct, and correctness is what the two evaluations below test. They are reported together so that
each result sits beside its interpretation. The first quantifies how well the pipeline brings
separately acquired panels of one section into register, and whether the configuration used here is
justified among the alternatives (@fig:registration-accuracy). The second asks whether the
single-cell immune quantification built on top of that alignment is trustworthy enough to interpret
(@fig:proof-of-concept). The implementation unit specifies the procedures that produced every
number reported below.

Alignment is the pipeline's load-bearing capability, so we quantified it directly rather than
inferring it from downstream results. A two-colour anchor-channel overlay of two separately
acquired panels shows the cross-panel drift between acquisitions, and shows that drift resolved
once the panels are aligned into a common coordinate space (@fig:anchor-overlay). To put a number
on the alignment we compared a matrix of configurations on the same data: two engine accuracy
presets, which differ in the image resolution at which features are matched rather than in the
underlying matcher, crossed with micro-registration on and off, and set against two baselines, a
rigid-only alignment and no alignment at all. Additional files carry the full per-arm results; the
summary and what it supports are given here (@fig:dice-by-arm).

Two metrics were used, because no single one answers both of the questions honestly. The
engine-internal target registration error is the residual distance between the keypoints the engine
matched across panels after alignment. It ranks the arms cleanly, which is what makes it the
method-selection metric. It is computed on the same correspondences the engine optimised against,
and only where matching succeeded, so it excludes exactly the hard regions in which alignment is
most likely to fail. It is therefore an optimistic, self-reported quantity, and it cannot stand
alone as a claim about absolute accuracy.

The second metric closes that gap. We binarised the anchor channel of each aligned panel and
measured the Dice overlap of the resulting nuclear masks across panels, a quantity computed
independently of the engine's matcher, on the raw aligned images, and uniformly across every arm
including the baselines. Because the anchor channel is present in every panel and is not the object
the engine optimises against, Dice either corroborates the ranking or exposes it as circular. The
implementation unit states the rule used to binarise the anchor channel before Dice is computed.

The two metrics agree, which is the finding. Alignment substantially improved cross-panel anchor
overlap over both baselines: the no-alignment and rigid-only arms left the nuclear masks visibly
and quantifiably misaligned, whereas full rigid-plus-non-rigid alignment raised Dice to
{{! best-arm Dice }} from {{! rigid-only Dice }} and {{! no-alignment Dice }} respectively, with a
corresponding fall in the residual error. The best-performing arm was
{{! winning alignment arm }}. Because an independent metric moves in step with the internal one,
the ranking is not an artefact of the engine scoring its own work, and the absolute-accuracy
statement rests on the engine-agnostic Dice.

<!-- {{ ! winning alignment arm }}: accuracy preset plus micro-registration state, from the
     benchmark. The pipeline ships the medium preset with micro off, overridable per run, and the
     invocation behind the proof-of-concept data is not committed. If the shipped default was the
     production setting it falls outside the benchmarked arms, so reconcile before filling it in. -->

<!-- !@author unverified: that the arm named above is the arm that produced the
     @fig:proof-of-concept data. Not provable from the repository. -->

Two bounds hold on what this benchmark claims. The engine choice is the first. Alignment is driven
by an automated, open-source whole-slide method [@gatenbee2023] reported to reach state-of-the-art
accuracy on a public histological-image-registration benchmark [@borovec2020]. That external
standing justifies the choice of tool, although it does not transfer to this pipeline's own
accuracy, which is what Dice is for: the public benchmark scored transforms against hidden
landmarks on a different modality and scale, and the setting here is same-section and iterative.
The scope is the second. This is an internal cross-arm comparison rather than a head-to-head
against other pipelines, and no relative-performance claim against them follows from it. The
capability difference is what positions this work: it generalises the established nuclear-anchor
alignment idea, used within a single run [@muhlich2022], to automated cross-panel,
cross-acquisition alignment.

<!-- obj: reader asks why an externally benchmarked engine does not settle this pipeline's own
     accuracy -->

Alignment being accurate does not make what is measured on top of it meaningful. So we asked
whether the single-cell immune quantification is trustworthy, using two orthogonal molecular
readouts of the same tissue as checks.

The pipeline and the downstream gating were applied together to six cases, drawn from a larger
profiled cohort as the three highest and three lowest on a transcriptomic immune score. The
selection is contrast-enriched rather than unselected, and what that costs is set out below. Both
anchors compared against, the immune score and the deconvolution fractions, derive from the same
adjacent-section bulk expression data, so they share one source. Imaging populations were called by
strict sequential hierarchical gating on the per-cell feature table the pipeline exports, with a
pan-immune gate on one marker; the T and natural-killer lineages resolve at single-cell level,
whereas the myeloid and B compartments are recovered only in aggregate. Neither anchor is a ground
truth. Both are orthogonal molecular proxies for immune content, so what is tested is concordance
among proxies.

The imaging pan-immune fraction separates the three transcriptomically hot cases from the three
cold ones, with the six individual case values overlaid on the boxplots so that the actual data is
visible rather than a summary of it (@fig:group-contrast). The imaging immune fraction was
consistently higher in the hot group, {{! hot- and cold-group imaging immune fractions }}, so an
independently measured imaging quantity recovers an ordering that was fixed, before any imaging, by
orthogonal transcriptomics.

Two things bound that result. The groups are separated on the score axis by construction: the score
is the selection variable, taken from an immunologically active gene-expression signature
[@foy2022], with the highest-scoring cases labelled hot and the lowest cold and no independent
threshold applied. It is therefore the axis along which the cases were chosen, and the
contrast-enriched design inflates the apparent gap. No p-value is reported: three against three is
too small to support an inferential test, and one would lend the appearance of inference to a
separation the selection built in. The raw points are the evidence.

<!-- obj: reader asks why no significance test is reported for a three-against-three comparison -->

Whether the imaging immune fraction tracks an orthogonal molecular estimate case by case is the
load-bearing question, and a second panel answers it (@fig:covariation). For each of the six cases
the deconvolution immune fraction is plotted against the imaging fraction, at the total-immune
tier: the imaging pan-immune fraction against one minus the deconvolution residual fraction
[@finotello2019]. Cases scored immune-high by imaging were immune-high by deconvolution, and low by
low, so the two estimates place the six cases in a concordant order,
{{! the six paired deconvolution and imaging fractions }}. This is what supports the claim that the
imaging quantification is trustworthy: an imaging-only measurement and a molecular-only measurement
of the same immune content agree on the ranking.

Rank co-variation is the whole of the claim. The two axes use different denominators, because
imaging counts a fraction of segmented cells whereas deconvolution estimates a fraction of a bulk
expression mixture, so the points are not expected to fall on the identity line and no claim of
absolute-fraction agreement is made. No correlation coefficient, p-value or confidence interval is
reported either: at six cases any such statistic would overstate the precision of a six-point
visual. The mappable-lineage comparison and the catch-all comparison below it are directionally
consistent with the total-immune tier and appear as the same descriptive scatters in Additional
files.

<!-- obj: reader asks why imaging and deconvolution fractions do not agree in absolute value -->

Read together the two panels give two complementary lines of evidence that the imaging
quantification is trustworthy as a proof of concept: an imaging measurement recovers an orthogonal
transcriptomic contrast, and it co-varies with an orthogonal molecular estimate of the same immune
content. The two transcriptomic anchors are not independent of each other, since both come from the
same adjacent-section expression data, so the independence that carries weight is between the
imaging readout and the molecular proxies it is checked against. What both panels show is
concordance among proxies.

<!-- slot: limitations -->

The limitations set the terms on which the proof of concept should be read. Autofluorescence is the
first. The acquisition protocol did not capture a pre-stain blank image, so local background
subtraction was applied rather than per-pixel autofluorescence subtraction. The pipeline supports
blank-based subtraction when the image is available, so this is a run-condition limitation rather
than a design choice, and residual autofluorescence remains in the quantitative readout for this
dataset. Panel coverage is the second, and it shapes the concordance analysis directly: the
antibody panel carries a pan-immune gate on one marker and no myeloid or B-cell markers, so those
compartments resolve only in aggregate, never at single-cell level, and the catch-all comparison is
correspondingly coarse. Third, the segmentation model's generalisation [@schmidt2018] to this
tissue and scanner is assumed rather than independently benchmarked here.

The proof-of-concept statistics carry the heaviest caveat. With six cases and a contrast-enriched
selection, the design inflates both the group separation and the co-variation, and precludes any
inferential statistic, so the findings are descriptive and hypothesis-generating. The alignment
benchmark is likewise internal: it compares the pipeline's own configurations against baselines and
includes no competitor head-to-head, so it supports no relative-performance claim.

Those bounds are what a next cohort has to answer. A larger, unselected cohort would move the
analysis from proof-of-concept concordance toward quantitative agreement and would allow the
inferential statistics this study withholds, and a broader antibody panel adding myeloid and B-cell
markers would resolve those compartments at single-cell level rather than in the aggregate. Two
pipeline parameters warrant systematic study deferred here: the whole-cell mask expansion radius,
whose effect on downstream quantification has not been swept, and the robustness of gating where
marker intensities are unimodal rather than cleanly separated. Whether the concordance reported
here holds on an unselected cohort is the question this work leaves open.
