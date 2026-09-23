# MedIWF

Item-writing flaws and answer-position bias in large language model-generated medical multiple-choice questions:
an open corpus of 28,280 generated items, a rule-based detector for 14 structural flaws, physician content ratings of a
100-item sample, and the analysis code and outputs behind the paper (Gundam R., 2026; manuscript under review).

Author: Rohit Gundam, independent researcher (ORCID 0009-0001-3018-9663). Code: MIT License. Data and documents: CC BY 4.0
(see LICENSE-DATA.md and DATASET_CARD.md).

Archive: https://doi.org/10.5281/zenodo.22903818 (Zenodo, all versions). Corpus: https://huggingface.co/datasets/rgundam/MedIWF

## Layout
- `src/mediwf/`     detector (14 rules, version 1.2), composites, gateway client
- `scripts/`        generation, detection, validation, analysis and figure scripts; each writes a versioned file under `outputs/`
- `config/`         model list, specialty and topic grid, prompts (plain, guided, guided-position, neutral and rotated templates, paraphrased guidelines)
- `data/generated/` the corpus and the judge outputs, gzip-compressed (`gunzip data/generated/*.gz` before running the scripts)
- `data/external/`  instructions for obtaining the BenchMarker validation labels (not redistributed)
- `data/nbme/`      note on the NBME items (withheld under a data-use agreement)
- `outputs/`        detector flags, analysis outputs, figures, the hand-check workbooks and labels, the physician rating materials and ratings
- `docs/`           protocol and its six amendments, detector changelog, hand-check procedure log, rater guide, supplementary tables

## Reproducing the analyses (no network needed)
```
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
gunzip data/generated/*.gz
python3 scripts/tests_detector.py                                     # 65 unit tests for the detector
python3 scripts/detect.py generated full                              # -> outputs/flags_full.csv
python3 scripts/detect.py generated full_reasoning; python3 scripts/detect.py generated position
python3 scripts/detect.py generated template; python3 scripts/detect.py generated wording; python3 scripts/detect.py generated stability
python3 scripts/analyze_flags.py outputs/flags_full.csv
python3 scripts/model_effects.py outputs/flags_full.csv outputs/model_effects_v6.txt
python3 scripts/composites.py outputs/flags_full.csv outputs/analysis_composites_v1.txt
python3 scripts/model_contrasts.py outputs/flags_full.csv outputs/model_contrasts_v1.txt
python3 scripts/model_level.py outputs/flags_full.csv outputs/flags_full_reasoning.csv outputs/model_level_v1.txt
python3 scripts/tier_model_level.py outputs/flags_full.csv outputs/tier_model_level_v1.txt
python3 scripts/analyze_reasoning.py outputs/flags_full_reasoning.csv outputs/flags_full.csv outputs/analysis_reasoning_v1.txt
python3 scripts/analyze_position.py outputs/flags_position.csv outputs/flags_full.csv outputs/analysis_position_v2.txt
python3 scripts/analyze_template.py outputs/flags_template.csv outputs/flags_full.csv outputs/analysis_template_v3.txt
python3 scripts/analyze_wording.py outputs/flags_wording.csv outputs/flags_full.csv outputs/analysis_wording_v1.txt
python3 scripts/analyze_stability.py outputs/flags_stability.csv outputs/flags_full.csv outputs/analysis_stability_v1.txt
python3 scripts/provider_sensitivity.py outputs/flags_full.csv outputs/flags_full_reasoning.csv outputs/flags_position.csv outputs/flags_template.csv outputs/flags_wording.csv -o outputs/analysis_provider_v1.txt
python3 scripts/rationale_key_check.py full position template wording full_reasoning -o outputs/analysis_rationale_v1.txt
python3 scripts/near_duplicates.py -o outputs/analysis_duplicates_v1.txt
python3 scripts/analyze_leadin.py; python3 scripts/clang_sensitivity.py; python3 scripts/reviewer_sensitivity.py; python3 scripts/reviewer_addendum.py
python3 scripts/analyze_verification.py outputs/analysis_verification_v1.txt     # hand-check agreement (reads outputs/verification_sample_pass1_merged.xlsx)
python3 scripts/analyze_content_ratings.py report -o outputs/content_rating/main_ratings_report_v3.txt
python3 scripts/content_rating_crosstab.py
python3 scripts/validate_judge.py data/generated/judgeR_anthropic-claude-fable-5-1_benchmarker.jsonl
python3 scripts/validate_judge_physician.py -o outputs/judge_physician100_validation_v1.txt
python3 scripts/make_figures.py outputs/flags_full.csv outputs/nbme_aggregate_for_figures.json outputs/figures
```
`scripts/validate_benchmarker.py` needs the BenchMarker labels (see `data/external/README.md`); `scripts/nbme_comparison.py`
and `scripts/nbme_psychometrics.py` need the NBME items and cannot be run without them, but their outputs are included.

## Regenerating items (network and an OpenRouter key)
Copy `.env.example` to `.env` and set `OPENROUTER_API_KEY`. `python3 scripts/generate.py --pilot` runs a small pilot;
`bash scripts/run_with_watchdog.sh --full --workers 8` regenerates the main corpus (resumable; the wrapper relaunches after a
stall). The arms use `--run full_reasoning --reasoning on`, `--run position --conditions guided_position --reps 1`,
`--template-control`, `--run template --conditions plain_neutral|guided_neutral --reps 1`, `--run wording --conditions guided2 --reps 1`
and `--stability`. Judges: `python3 scripts/judge_perrule.py --judge <model> --validate|--physician [--reasoning]`.
Costs are recorded per attempt; `python3 scripts/costs.py -o outputs/costs_v2.txt` reproduces the ledger.

## Withheld
NBME items and item-level NBME statistics (data-use agreement); the OpenRouter key; the raters' contact and contract details;
the screening-test key for future structural raters. The files `outputs/content_rating/*_DO_NOT_SEND.csv` are the answer keys of the
physician-rating sets (planted defects and detector flags), named so that they were never sent to the raters; they are released now that
the ratings are complete.
