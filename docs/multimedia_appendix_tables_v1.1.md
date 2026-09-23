# MedIWF: supplementary tables for Multimedia Appendix 1 (manuscript v1.1)

Tables S1–S4 form Multimedia Appendix 1. They are the tables of manuscript v1.0 (Tables 2, 3, 6 and 7) moved out of the main text unchanged; every value comes from the released output files.

## Multimedia Appendix 1

**Table S1. Agreement of detector v1.2 with the BenchMarker human labels.**

| Rule (BenchMarker label → our rule) | Development set (604 items) κ | Examination set (216 items) precision / recall / κ (95% CI) | Health-sciences items (45) κ |
| ---------------- | ---------- | ------------- | ---------- |
| Negative lead-in | 0.40 | 0.67 / 0.67 / 0.63 (0.44–0.79) | 0.64 |
| "None of the above" | 0.81 | 1.00 / 0.50 / 0.66 (0.30–0.91) | — (no positives) |
| "All of the above" | 0.75 | 1.00 / 0.57 / 0.72 (0.28–1.00) | 0.66 |
| Combination (K-type) options | 0.54 | 0.75 / 0.19 / 0.28 (−0.01 to 0.53) | 0.65 |
| Fill-in-the-blank | 0.30 | 1.00 / 0.88 / 0.93 (0.75–1.00) | 1.00 |
| Numeric options not ordered | 0.50 | 0.93 / 0.74 / 0.81 (0.64–0.94) | — (no positives) |
| Clang cue (avoid repetition) | 0.58 | 0.42 / 0.36 / 0.35 (0.07–0.58) | 0.45 |
| Absolute terms | 0.31 | 0.29 / 0.53 / 0.30 (0.11–0.48) | −0.10 |
| Vague terms | 0.11 | 0.00 / 0.00 / −0.01 (−0.03 to 0.00) | −0.06 |
| Grammatical cue | 0.00 | 0.00 / 0.00 / −0.04 (−0.06 to −0.01) | 0.00 |
| Option-length outlier (feature) | 0.39 | 0.25 / 0.39 / 0.14 (0.00–0.29) | 0.26 |
| Longest option is the key; non-parallel; overlapping; true/false | — (no BenchMarker counterpart) | — | — |

[7,282 labels after collapsing duplicates, of which 1,797 development and 2,376 examination labels (495 on health-sciences items) concern the ten mapped rules and the option-length feature. Item–rule pairs without a human label are excluded, not treated as negatives. κ intervals: percentile bootstrap. Confusion matrices are in the released output file validation_benchmarker_v3.txt.]{.caption}

**Table S2. Hand-check of detector v1.2 against the author's blind labels (439 items; precision and recall design-weighted to the whole corpus with 95% CI by stratified bootstrap; where every sampled item agreed, the exact lower 95% bound on the unweighted count is given instead).**

| Rule | Det. + | Hum. + | Both | Precision (95% CI) | Recall (95% CI) | κ (95% CI) |
| ------------------ | ------- | ------- | ------ | ----------------- | ----------------- | ------------- |
| Negative lead-in | 0 | 0 | 0 | — | — | — |
| "All/none of the above" | 0 | 0 | 0 | — | — | — |
| Combination options | 0 | 0 | 0 | — | — | — |
| Longest option is the key [a] | 50 | 50 | 50 | 1.00 (≥0.93) | 1.00 (≥0.93) | 1.00 |
| Absolute terms | 53 | 53 | 52 | 0.94 (0.83–1.00) | 0.87 (0.66–1.00) | 0.98 (0.94–1.00) |
| Vague terms [a] | 4 | 4 | 4 | 1.00 (n<10) | 1.00 (n<10) | — |
| Clang cue | 60 | 69 | 48 | 0.79 (0.68–0.89) | 0.52 (0.42–0.66) | 0.70 (0.59–0.79) |
| Grammatical cue | 1 | 1 | 1 | 1.00 (n<10) | 1.00 (n<10) | — |
| Non-parallel options | 34 | 35 | 33 | 0.98 (0.92–1.00) | 0.90 (0.75–1.00) | 0.95 (0.89–1.00) |
| Overlapping options [a] | 33 | 33 | 33 | 1.00 (≥0.89) | 1.00 (≥0.89) | 1.00 |
| Any of the ten rules | | | | 0.95 (0.91–0.98) | 0.79 (0.70–0.88) | |
| Any rule except the clang cue | | | | 1.00 (0.99–1.00) | 0.97 (0.92–1.00) | |

[Det. + and Hum. +: unweighted numbers of sample items flagged by the detector and labeled positive by the author; Both: flagged by both; κ: unweighted sample Cohen's κ with a bootstrap interval (omitted where every item agreed). [a] Arithmetic rules; labels after comparison with the rule's computation (nine longest-option cells corrected, none for the other two rules). Strata, mutually exclusive and assigned in the order longest option, clang cue, absolute terms, then the rarer rules: 50 items each for the three common rules, 30 each for the non-parallel and overlapping rules, all 15 numeric-order items (sampled but not hand-labeled), all 4 vague-term items, and 210 unflagged items; an item flagged by several rules counts as detector-positive for each, so Det. + can exceed the stratum size; each item is weighted by its stratum's corpus population divided by its sample size. Rules with no detector-positive item in the corpus have no estimable precision. Clang cue: human standard is the rater guide's one-word definition.]{.caption}

**Table S3. The two physicians' judgments on the five rubric questions for the 100 corpus items: items rated negative (Wilson 95% CI in percent) and agreement.**

| Question (negative rating counted) | Rater 1 | Rater 2 | κ (95% CI) |
| ---------------------------- | ---------- | ---------- | ------------ |
| Keyed answer is not the single best answer ("no" or "unsure") | 11 (6.3–18.6) | 3 (1.0–8.5) | 0.40 (0.00–0.71) |
| At least one distractor implausible | 2 (0.6–7.0) | 2 (0.6–7.0) | — (two positives each) |
| Vignette inaccurate or internally inconsistent | 4 (1.6–9.8) | 7 (3.4–13.7) | 0.52 (−0.01 to 0.85) |
| Item does not test a meaningful clinical decision | 0 | 0 | — (no variance) |
| Not acceptable as written ("no"; items wanting minor edits in parentheses) | 11 (2) (6.3–18.6) | 8 (16) (4.1–15.0) | 0.38 (0.15–0.59) |
| Composite defect (any of the first three, or "no" on acceptability) | 13 (7.8–21.0) | 12 (7.0–19.8) | 0.59 (0.31–0.80) |

[Rater 1 gave 1 "no" and 10 "unsure" on the single-best-answer question. Composite: raw agreement 0.91, positive specific agreement 0.64.]{.caption}


**Table S4. Departures from the protocol.**

| Planned | Done |
| ------------------------------ | ------------------------------ |
| Mixed-effects regression | Fixed-effects regression with topic-clustered errors |
| Pre-specified two-way interactions | Separate per-model estimates |
| Validation on five external label corpora | BenchMarker only. SAQUET (Moore et al., 2024) released its code but not its labeled items; Law et al. (2025) deposited aggregate flaw counts without item text; MCQG-SRefine (Yao et al., 2025) releases items with GPT-4 judgments rather than human flaw labels; the Rush et al. (2016) Zenodo record is access-restricted |
| Hand-check on a simple random sample of 300 items | Flag-enriched sample of 439 items |
| Tier comparison at the item level | Moved to the model level after the item-level analysis was found to overstate the evidence |
| Faculty-written comparison set | Replaced by the NBME items |
| Second labeling pass by the author; later, raters independent of the study | Neither carried out |
| Stronger-judge arm with a per-judge cost threshold | Run under an overall cost cap set after a pilot |
| Stability re-run after at least fourteen days | Run after eight days |
| Optional arms: flagship models with reasoning; sampling temperature | Not run |
| Conversation transcripts of the AI assistance submitted as a supplementary appendix | Retained by the author; available to the editor on request |
