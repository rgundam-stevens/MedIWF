# MedIWF Protocol Amendment 2 — 16 September 2026

Recorded after a full audit of the code, data and analyses (all generation arms complete except the stability re-run;
before the author's hand-check and before any physician content rating had been analysed). Every change below is
reported in the paper as a deviation from, or extension of, the protocol.

## A5. Template-control arm (answer-position bias)
The required JSON template in the plain and guided prompts shows `"answer": "A"` as its example. Because the position
arm (A3) showed that models follow the letter written in the template 99.4% of the time, the key-at-A bias in the main
corpus may be partly induced by that example letter rather than by the models' own placement habit. Two control
conditions are added, on the first 5 topics of each specialty, all 15 models, one repetition (1,200 items, run name
`template`): `plain_neutral` (template shows `"answer": "..."`, like the other placeholders) and `plain_rotated`
(template shows a letter assigned by the balanced cyclic design of A3). Pre-stated interpretation: if P(key = A) under
the neutral template remains close to its value under the plain prompt, the bias is the model's own; if it falls
towards 0.2 and keys follow the rotated example letter, the main-corpus bias is largely an artefact of the template and
the paper will say so. Command: `bash scripts/run_with_watchdog.sh --template-control --workers 8`;
analysis: `scripts/analyze_template.py`. Estimated cost US$15.

## A6. Physician content rating replaces the LLM judge for Tier B
The LLM judges failed validation against human labels (kappa <= 0.43 on every rule; reported as a negative result).
Tier-B content flaws (wrong key, second defensible answer, implausible distractor, internally inconsistent vignette,
trivial question) are therefore rated by two physicians (MBBS, USMLE-examined) recruited through a freelance platform,
screened with a live two-item test, trained on a written guide, and qualified on a 20-item calibration set containing
8 planted and 2 natural defects (pass criterion, fixed in advance: at least 6 of 8 planted defects identified with a
specific justification and no indiscriminate flagging of sound items). Both then rate the same 100-item main set
(3-4 items per model x condition, drawn at random), blind to the generating model, independently and without AI
tools, for a fixed fee per item. Reported: prevalence of each content flaw with Wilson CIs, agreement between raters
(Cohen's kappa per question), and, for the 20 calibration items, each rater's detection of the planted defects.
The calibration items are excluded from prevalence estimates. Raters receive item-level feedback on the calibration
set before the main set.

## A7. Detector v1.1 and re-analysis
See docs/detector_changelog.md. The audit found that three v1.0 heuristics fired almost exclusively on non-flaws
(shared-component "combinations", plural/-ing "grammatical cues", substring "overlaps"); they were removed or corrected,
and a case-sensitivity bug in negative-stem detection was fixed. A narrower absolute-terms rule was tried and rejected
because it lowered agreement with the BenchMarker labels. All corpora and the NBME items were re-scored with v1.1; the
paper reports v1.1 results and gives the v1.0 composite prevalence for comparison (plain 27.6% -> 23.4%).

## A8. Analysis changes
1. Tier comparison (flagship vs base): the item-level regression with topic clusters overstates the evidence because
   models are nested in tiers and there are only 15 models. The primary tier comparison is now at the model level
   (`scripts/tier_model_level.py`): model-level prevalence, an exact permutation test over all 6,435 tier assignments,
   Welch's t-test, and a cluster-robust logistic regression with clusters = models. With v1.1 flags the difference
   (22.0% vs 24.6% under the plain prompt) is not distinguishable from between-model variation (permutation p = 0.40).
2. NBME comparison: the comparable reference set is the 525 five-option items; all 667 items are reported as a
   sensitivity analysis. Key-position tests are restricted to five-option items.
3. Validator: option keys must normalise to exactly A-E without collisions (7 affected items regenerated).
4. Hand-check sample (RQ4): re-drawn with v1.1 flags as 439 items in mutually exclusive strata (first flagging rule in
   a fixed order, or unflagged), with population counts on the same partition so that design-based precision and
   recall (`scripts/analyze_verification.py`, stratified bootstrap CIs) are exact. Pass 2 (150 items) >= 4 weeks later.
5. Pseudo-replication: exact or near-duplicate stems between the two repetitions were rare except for Llama 4 Maverick
   (24% of rep pairs with 3-gram Jaccard >= 0.5); a rep-0-only sensitivity analysis is reported (guided OR 0.49 vs 0.50).
6. Composite outcome: "any Tier-A flaw" (14 rules) remains primary; a sensitivity composite of the 11 rules with
   acceptable external validation (excluding absolute terms, vague terms and grammatical cues) is reported
   (plain 19.9%, guided 12.6%, guided OR 0.57).

## Deviations from the protocol recorded here
- Analysis used fixed-effects logistic regression with cluster-robust standard errors by topic instead of a
  mixed-effects model with a topic random intercept (no mixed-model library on the analysis machine; the sandwich
  estimator was checked against a topic-level bootstrap).
- External validation used the BenchMarker labels (7,542) only; SAQUET, Law 2025, Yao 2025 and Rush 2016 were not
  used (availability of item text and labels to be documented in the paper).
- The author's hand-check grew from 300 to 439 items and became a stratified, flag-enriched sample (v3).
- Five flagship models and Gemini 3.8 Flash cannot switch hidden reasoning off; the tier comparison is therefore
  partly confounded with reasoning and is reported as such.
- The protocol's "no human raters" statement no longer holds (A6).
