# External validation data (not redistributed)

The detector was validated against the human writing-flaw labels released with BenchMarker (MIT license):
Balepur N, Rajasekaran B, Oh HJ, et al. BenchMarker: an education-inspired toolkit for highlighting flaws in
multiple-choice benchmarks. In: Proceedings of the 64th Annual Meeting of the Association for Computational Linguistics
(Volume 1: Long Papers). 2026:15793-15824 (doi:10.18653/v1/2026.acl-long.719). Copy `judge_experiments/validation_data/writing_flaws_judge.jsonl`
from the BenchMarker repository to `data/external/benchmarker/writing_flaws_judge.jsonl` before running
`scripts/validate_benchmarker.py`, `validate_judge.py` or `compare_reasoning.py --labels benchmarker`.
