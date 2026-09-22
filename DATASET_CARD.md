# MedIWF dataset card

**Summary.** 28,280 medical single-best-answer multiple-choice questions generated in September 2026 by 15 large language
models (8 base-tier, 7 flagship) across 8 specialties and 200 topics, with prompts, generation metadata (model, provider,
seed, cost, reasoning tokens), and structural item-writing-flaw labels from a rule-based detector (14 rules, version 1.2).
The main corpus is 12,000 items (two prompts x two repetitions); five experimental arms add 15,800 items; a 480-item
stability re-run made eight days later is included.

**Files.** `data/generated/items_<run>.jsonl.gz`, one JSON object per generation attempt (`gunzip` before use):
`items_full` (main corpus), `items_full_reasoning` (reasoning arm), `items_position` (position arm), `items_template`
(template-control and guided-neutral arms), `items_wording` (paraphrase arm), `items_stability` (re-run), `items_pilot*`
(pilots, not analysed). Judge outputs: `judgeR_<judge>_<set>.jsonl.gz`. Detector flags: `outputs/flags_<run>.csv`.

**Intended use.** Research on item quality, prompt effects, answer-position bias and detector validation. The items are
not clinically validated and are not intended for use in examinations or teaching without expert review; two physicians
found a content defect in about one item in eight of a 100-item sample (see the paper).

**Provenance and license.** Generated through the OpenRouter gateway under the prompts in `config/prompts/`; item text is
released as generated and each model's terms of use may apply; labels, metadata and the compilation are CC BY 4.0.
No human subjects data; the physician ratings in `outputs/content_rating/` are released with both raters' written consent.

**Known limitations.** Snapshot of model versions and hosts recorded in the metadata; 2.7% of repetition pairs are
near-identical; the detector's rules are surface-form rules with the validation reported in the paper.
