# Changes

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
