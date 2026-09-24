# Data license

The code in `src/` and `scripts/` is released under the MIT License (see LICENSE).

The labels, detector flags, generation metadata, analysis outputs, rating sheets and ratings, protocol and documents in
`outputs/`, `docs/` and `config/`, and the compilation of the corpus, are released under the Creative Commons Attribution 4.0
International license (CC BY 4.0): https://creativecommons.org/licenses/by/4.0/, with two exceptions:

- The per-rule judge prompts in `config/prompts/benchmarker_rules/` are from BenchMarker (Balepur et al., 2026),
  copyright Nishant Balepur, MIT License; the notice is in that folder.
- The aggregate statistics computed from the NBME items (`outputs/*nbme*.txt`, `outputs/nbme_aggregate_for_figures.json`,
  `outputs/independent_nbme_check_output.txt`, and the NBME lines of `analysis_composites_v1.txt`, `analysis_leadin_v1.txt`,
  `analysis_clang_sensitivity_v1.txt`, `analysis_reviewer_sensitivity_v1.txt` and `analysis_reviewer_addendum_v1.txt`) are
  published research results. The items and their item-level statistics belong to the NBME, were used under the BEA 2024
  data-use agreement, and are not part of this release.

The text of the generated items in `data/generated/` was produced by the fifteen models named in `config/models.json`
through the OpenRouter gateway. It is released as generated, without clinical validation, for research and educational use;
each model's terms of use may apply to its output. See DATASET_CARD.md.
