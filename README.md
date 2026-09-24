# MedIWF

Item-writing flaws and answer-position bias in large language model-generated medical multiple-choice questions:
an open corpus of 28,280 generated items, a rule-based detector for 14 structural flaws, physician content ratings of a
100-item sample, and the analysis code and outputs of the study.

Author: Rohit Gundam, independent researcher (ORCID 0009-0001-3018-9663). Code: MIT License. Data and documents: CC BY 4.0
with the exceptions listed in LICENSE-DATA.md (see also DATASET_CARD.md).

Archive: https://doi.org/10.5281/zenodo.22903818 (Zenodo, all versions). Corpus: https://huggingface.co/datasets/rgundam/MedIWF
Version 1.0.3; the changes since 1.0 are listed in CHANGELOG.md.

## Layout
- `src/mediwf/`     detector (14 rules, version 1.2; versions 1.0 and 1.1 kept for the version history), composites, statistics, gateway client
- `scripts/`        generation, detection, validation, analysis and figure scripts
- `config/`         model list, specialty and topic grid, prompts (plain, guided, guided-position, neutral and rotated templates, paraphrased guidelines), BenchMarker's per-rule judge prompts (MIT)
- `data/generated/` the corpus and the judge outputs, gzip-compressed (`gunzip data/generated/*.gz` before running the scripts)
- `data/external/`  instructions for obtaining the BenchMarker validation labels (not redistributed)
- `data/nbme/`      note on the NBME items (withheld under a data-use agreement)
- `outputs/`        detector flags, analysis outputs, figures, the hand-check workbooks and labels, the physician rating materials and ratings
- `docs/`           protocol and its six amendments, detector changelog, hand-check procedure log, rater guide, errata

## Reproducing the analyses (no network needed)
The logs in `outputs/` are the record. The commands below write to a separate folder, `repro/`, so that nothing released is
overwritten; each result can then be compared with the released file of the same name. Python 3.9 or 3.10; the released
logs were produced without SciPy (see requirements.txt).
```
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
gunzip data/generated/*.gz
mkdir -p repro
python3 scripts/tests_detector.py                                   # 65 unit tests for the detector
for r in full full_reasoning position template wording stability; do python3 scripts/detect.py generated $r; done
                                   # rewrites outputs/flags_<run>.csv, byte-identical to the released files (md5 in MANIFEST.txt)
python3 scripts/analyze_flags.py outputs/flags_full.csv > repro/analysis_full_v6.txt
python3 scripts/model_effects.py outputs/flags_full.csv repro/model_effects_v6.txt
python3 scripts/model_contrasts.py outputs/flags_full.csv repro/model_contrasts_v1.txt
python3 scripts/model_level.py outputs/flags_full.csv outputs/flags_full_reasoning.csv repro/model_level_v1.txt
python3 scripts/tier_model_level.py outputs/flags_full.csv repro/tier_model_level_v3.txt
python3 scripts/analyze_reasoning.py outputs/flags_full_reasoning.csv outputs/flags_full.csv repro/analysis_reasoning_v4.txt
python3 scripts/analyze_position.py outputs/flags_position.csv outputs/flags_full.csv repro/analysis_position_v4.txt
python3 scripts/analyze_template.py outputs/flags_template.csv outputs/flags_full.csv repro/analysis_template_v4.txt
python3 scripts/analyze_wording.py outputs/flags_wording.csv outputs/flags_full.csv repro/analysis_wording_v2.txt
python3 scripts/analyze_stability.py outputs/flags_stability.csv outputs/flags_full.csv repro/analysis_stability_v1.txt
python3 scripts/provider_sensitivity.py outputs/flags_full.csv outputs/flags_template.csv outputs/flags_wording.csv -o repro/analysis_provider_v2.txt
python3 scripts/rationale_key_check.py full position template wording full_reasoning -o repro/analysis_rationale_v1.txt
python3 scripts/near_duplicates.py -o repro/analysis_duplicates_v1.txt
python3 scripts/analyze_leadin.py repro/analysis_leadin_v1.txt
python3 scripts/clang_sensitivity.py repro/analysis_clang_sensitivity_v1.txt
python3 scripts/composites.py outputs/flags_full.csv repro/analysis_composites_v1.txt
python3 scripts/parse_report.py full repro/parse_report_full_v4.txt
python3 scripts/costs.py -o repro/costs_v2.txt
python3 scripts/analyze_verification.py repro/analysis_verification_v1.txt   # hand-check agreement; reads outputs/verification_sample_pass1_merged.xlsx
python3 scripts/analyze_content_ratings.py report -o repro/main_ratings_report_v3.txt
python3 scripts/content_rating_crosstab.py repro/main_ratings_crosstab_v1.txt
python3 scripts/score_calibration.py -o repro/calibration_scores.txt
python3 scripts/check_content_rating_selection.py
python3 scripts/validate_judge_physician.py -o repro/judge_physician100_validation_v1.txt
python3 scripts/compare_reasoning.py data/generated/judgeR_anthropic-claude-fable-5-1_physician100.jsonl data/generated/judgeR_anthropic-claude-fable-5-1_physician100_reasoning.jsonl --labels physician -o repro/judge_reasoning_comparison_physician_v1.txt
python3 scripts/compare_reasoning.py data/generated/judgeR_openai-gpt-6-astra_physician100.jsonl data/generated/judgeR_openai-gpt-6-astra_physician100_reasoning.jsonl --labels physician -o repro/judge_reasoning_comparison_physician_astra_v1.txt
python3 scripts/make_figures.py outputs/flags_full.csv outputs/nbme_aggregate_for_figures.json repro/figures
python3 scripts/make_figures_paper.py outputs/flags_full.csv outputs/nbme_aggregate_for_figures.json repro/figures_paper   # the paper's figure files (600 dpi TIFF)
python3 scripts/build_paper_data.py repro/paper_data                                                                        # the paper's Datasets 1-6 and their MANIFEST
```
In a fresh environment (Python 3.10.12, NumPy 2.2.6, pandas 2.3.3, no SciPy) every command above reproduced the released
file byte for byte, with these exceptions: rows with equal counts may print in a different order in `analysis_leadin_v1.txt`
and `model_contrasts_v1.txt` (2 models with an exactly tied estimate); the NBME columns and section of `analysis_composites_v1.txt`
(n/a) and the NBME lines of `analysis_leadin_v1.txt` and `analysis_clang_sensitivity_v1.txt` ("not computed") need the NBME items;
the rating scripts print "minutes not released" where the released logs give per-rater totals (the per-item minutes were removed
from the public rating files in version 1.0.1); and the SVG and PDF figure files carry a Matplotlib timestamp and random ids (the
PNG and TIFF files are byte-identical).

Scripts that need files not in the repository. With the BenchMarker labels in `data/external/benchmarker/`
(see `data/external/README.md`): `validate_benchmarker.py` (-> validation_benchmarker_v3.txt), `validate_judge.py
data/generated/judgeR_<judge>_benchmarker.jsonl` (-> judge_validation_*_v2.txt and gpt54mini_v3.txt; prints to the
console) and `compare_reasoning.py ... --labels benchmarker` (-> judge_reasoning_comparison_benchmarker_*_v1.txt). With the
NBME items (see `data/nbme/README.md`): `nbme_comparison.py`, `nbme_psychometrics.py`, `reviewer_sensitivity.py`,
`reviewer_addendum.py`, `independent_nbme_check.py` and `detect.py nbme`. Their released outputs are the record.

## Regenerating items (network and an OpenRouter key)
Copy `.env.example` to `.env` and set `OPENROUTER_API_KEY`. `python3 scripts/generate.py --pilot` runs a small pilot;
`bash scripts/run_with_watchdog.sh --full --workers 8` regenerates the main corpus (resumable; the wrapper relaunches the
generator after a stall and calls macOS `caffeinate`; elsewhere run `python3 scripts/generate.py --full --workers 8`
directly). The arms correspond to these options of the same script: `--full --run full_reasoning --reasoning on --models
openai/gpt-5.6-terra openai/gpt-5.6-luna anthropic/claude-sonnet-5 qwen/qwen3.6-27b` (reasoning arm); `--full --run
position --conditions guided_position --reps 1` (position arm); `--template-control` (rotating example letter, 5 topics
per specialty) together with `--full --run template --conditions plain_neutral --reps 1` and `--full --run template
--conditions guided_neutral --reps 1` (neutral template); `--full --run wording --conditions guided2 --reps 1`
(paraphrased guidelines); `--stability` (re-run). Every record in `data/generated/` carries its condition, topic, seed and
model (the run is the file name; provider and token fields are absent on failed requests; temperature is recorded from the
template arm onward), so the parameters of each arm can be read from the data. Judges: `python3
scripts/judge_perrule.py --judge <model id> --validate` (216 course items) or `--physician` (100 physician-rated items),
with `--reasoning` for the reasoning-requested runs. Models change over time, so regenerated items will not reproduce
the released corpus; the analyses above run on the released files. Costs are recorded per attempt; `costs.py` (above)
reproduces the ledger.

## Withheld
NBME items and item-level NBME statistics (data-use agreement); the OpenRouter key; the raters' contact and contract details
and their per-item rating times; the screening-test key for future structural raters; the internal review reports, manuscript
drafts, screening-test items and scratch backups that the dated records in `docs/` cite by path. The files `outputs/content_rating/*_DO_NOT_SEND.csv`
are the answer keys of the physician-rating sets (planted defects and detector flags), named so that they were never sent to the
raters; they are released now that the ratings are complete.
