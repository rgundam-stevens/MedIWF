# NBME items (withheld)

The 667 retired USMLE items with examinee statistics were obtained from the NBME under the data-use agreement of the
BEA 2024 shared task (Yaneva et al., 2024) and are not redistributed; they are available from the NBME on application.
Item-level NBME outputs are withheld. The aggregate outputs are released: `outputs/nbme_aggregate_for_figures.json`
(reproduces the figures), `outputs/analysis_nbme*.txt`, `outputs/nbme_psychometrics_v*.txt`, `outputs/analysis_reviewer_*.txt`,
the NBME lines of `analysis_composites_v1.txt`, `analysis_leadin_v1.txt` and `analysis_clang_sensitivity_v1.txt`, and
`outputs/independent_nbme_check_output.txt` (an independent recomputation of every NBME-dependent number in the paper).
The scripts that need the item files (`scripts/detect.py nbme`, `inspect_nbme.py`, `nbme_comparison.py`, `nbme_psychometrics.py`,
`reviewer_sensitivity.py`, `reviewer_addendum.py`, `independent_nbme_check.py`) expect them as `data/nbme/train_final.xlsx`,
`test_final.xlsx` and `gold_final.xlsx`.
