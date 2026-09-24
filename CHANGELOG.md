# Changes

## 1.0.3 (24 September 2026)
- `docs/errata_2026-09-24.md`: note 4 added (where the generative-AI disclosure planned in Amendment 6 is made).
- `README.md`: the Withheld section names the internal review reports, manuscript drafts, screening-test items and scratch backups
  that the dated records in `docs/` cite by path.
- `CITATION.cff`: version 1.0.3.

## 1.0.2 (24 September 2026)
- `CITATION.cff`: `license` is a single string again (MIT, as in 1.0; the data license is described in LICENSE-DATA.md), so that
  Zenodo can read the metadata; version 1.0.2.
- `scripts/build_paper_data.py`: for an analysed attempt the item text is taken from the re-parse the detector used; in
  `MedIWF_Dataset1_items_full.csv` exactly 18 rows marked `analysed = True` that had empty item text gain their text, every other
  cell is unchanged.
- `scripts/independent_nbme_check.py` and `outputs/independent_nbme_check_output.txt`: 181 checks (162 in 1.0.1): the
  guided-prompt vs NBME comparison, the cells below the NBME rate, the share of the gap from the longest-option cue and the
  14-rule count regressions added, the v1.0-loader comparison split into 2 matching checks; 179 match, 2 differences explained
  in the output.
- `src/mediwf/detector.py`: the `n_flaws` column of `outputs/flags_*.csv` counted the 14 rules plus the 2 feature checks
  (`option_length_outlier`, `numeric_units_inconsistent`); it now counts the 14 rules, as `mediwf.rules.n_flaws` and the paper's
  Dataset 2 always did; the 6 flag files of the analysed runs were regenerated and only that column changed (the 4 pilot flag
  files are the pilot-time records and are unchanged). No analysis script reads the column.
- `docs/errata_2026-09-24.md`: note 1 rewritten (the disable request and the recorded reasoning tokens per judge), note 2
  names both protocol passages, note 3 added (the combined-prompt judge run of 14 September).
- `README.md`: the reproduction paragraph lists every non-identical file (tie order in `model_contrasts_v1.txt`, the SVG/PDF
  figures); the record fields of `data/generated/` described exactly; `DATASET_CARD.md` names the `judge_*` files;
  `data/external/README.md` gives the exact path of the BenchMarker label file.

## 1.0.1 (24 September 2026)
- README: the sentence describing the manuscript's status was removed; the reproduction commands were re-tested in a fresh
  environment and now write to `repro/` under the version names the paper uses; commands that need withheld files are listed separately.
- `scripts/model_level.py`: the SciPy-free path used a 2-decimal t table; it now uses 4-decimal quantiles. `outputs/model_level_v1.txt`
  was regenerated; one interval bound changed (17.1 -> 17.2).
- `scripts/validate_judge.py` (v2): duplicate BenchMarker label rows are collapsed exactly as in `validate_benchmarker.py`;
  `outputs/judge_validation_*_v2.txt` and `judge_validation_gpt54mini_v3.txt` added; the v1 logs are kept.
- Added `scripts/build_paper_data.py` and `scripts/make_figures_paper.py` (the paper's data files and figures) and
  `scripts/independent_nbme_check.py` with `outputs/independent_nbme_check_output.txt` (an independent recomputation of every
  NBME-dependent number in the paper; 162 checks, 159 match, 3 differences explained in the output).
- `outputs/content_rating/ratings/*.csv`: the per-item `minutes` column was removed; `analyze_content_ratings.py`,
  `content_rating_crosstab.py` and `score_calibration.py` run without it; `content_rating_crosstab.py`, `analyze_leadin.py` and
  `clang_sensitivity.py` accept an output path.
- `docs/errata_2026-09-24.md` added (clarifications to Amendment 5 and the protocol); `docs/multimedia_appendix_tables_v1.1.md` removed.
- LICENSE-DATA.md: exceptions for the BenchMarker prompts (MIT; notice added in `config/prompts/benchmarker_rules/`) and for the
  NBME-derived aggregates. CITATION.cff: version, date, both licenses. `requirements.txt`: Matplotlib added, versions and the
  SciPy note recorded. `data/nbme/README.md` extended.

## 1.0 (22 September 2026)
Initial release: corpus, detector, analysis code and outputs.
