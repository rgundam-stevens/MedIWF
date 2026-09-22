# MedIWF Protocol Amendment 1 — 14 September 2026

Recorded after completion of the protocol's 8-model, 2-condition grid (the protocol was written before generation but was not registered with a registry; see Amendment 4) (6,400 items) and before any of the
additional arms below were generated. Analyses of the original grid are unchanged; the arms below are reported
as extensions.

## A1. Flagship-tier generators (leaderboard extension)
Seven additional models on the identical grid (8 specialties x 25 topics x 2 conditions x 2 repetitions = 800 items each),
reasoning disabled where the API allows: GPT-6 Astra, Claude Fable 5.1, Claude Opus 5, Gemini 3.1 Pro (reasoning cannot be
disabled), Grok 4.6, DeepSeek V4 Pro, Qwen 3.8 Max. Open-weight status of DeepSeek V4 Pro and Qwen 3.8 Max to be confirmed
from model cards; hosting providers pinned after a pilot. Rationale: readers and reviewers will ask about the current
flagship tier; a 15-model leaderboard is more useful and more citable.

## A2. Reasoning-mode replication
The five original models whose API allows toggling hidden reasoning (GPT-5.6 Terra, GPT-5.6 Luna, Claude Sonnet 5,
Qwen 3.6 27B, DeepSeek V4 Flash) re-run on the full grid with reasoning enabled (run name `full_reasoning`), giving a
2 x 2 design (guidelines x reasoning) per model. Hypothesis (stated before generation): reasoning reduces cueing flaws
modestly and does not change answer-position bias. Analysis: same logistic models with a reasoning indicator and its
interaction with condition.

## A3. Explicit answer-position instruction (third prompt condition)
Condition `guided_position`: the guided prompt with guideline 10 replaced by an instruction to place the key at a
position assigned by the pipeline (recorded as `target_position`). Assignment is a balanced cyclic design,
(global topic index + model index) mod 5, so that every model receives exactly 40 items per position (5 per
specialty) and every topic receives each position three times across the 15 models (changed on 2026-09-14, before
the arm was run, from the per-item pseudo-random assignment used in pilot 3, which was unbalanced: 27-50 items per
position per model). All 15 models, one repetition (200 items per model). Items that fail to parse are regenerated
with a new seed (seed + 1000 x attempt), as in the main corpus. Outcomes: compliance (key == target), key-position uniformity, and structural flaw
rates versus the guided condition. Rationale: tests whether the observed position bias is correctable by instruction.

## A4. Stability re-run
A 480-item subsample (the first 2 topics of each of the 8 specialties x 2 conditions x all 15 models, one repetition,
seed identical to repetition 0 of the main corpus; `python3 scripts/generate.py --stability`) regenerated >= 14 days
after the original run (main corpus generated 2026-09-14; flagship arm 2026-09-14), to estimate the stability of
flaw rates and key-position distributions over time. Extended on 2026-09-14 (before running) from the 256-item,
8-model design to cover the flagship tier as well.

## Budget
Estimated US $150-200 in API cost for A1-A4 combined; actual costs will be reported.

## Pilot 3 findings (recorded before the paid runs, 14 September 2026)
- All three arms parse cleanly; the position instruction was followed in 60/60 pilot items across all 15 models.
- Five flagship models reject the request to disable hidden reasoning (Claude Fable 5.1, Gemini 3.1 Pro, GPT-6 Astra,
  Qwen 3.8 Max, Grok 4.6) and therefore run in their default reasoning mode; reasoning tokens are recorded per item and
  reported. Claude Opus 5 and DeepSeek V4 Pro run with reasoning disabled.
- DeepSeek V4 Flash produces no reasoning tokens even when reasoning is requested; A2 therefore covers four models
  (GPT-5.6 Terra, GPT-5.6 Luna, Claude Sonnet 5, Qwen 3.6 27B).
- Providers pinned: DeepSeek V4 Pro -> GMICloud (AtlasCloud fallback); Qwen 3.8 Max -> Alibaba; Grok 4.6 -> xAI.
- Cost measured in pilots implies: A1 ~US$127, A2 ~US$26, A3 ~US$41 (15 models x 200 items), A4 ~US$2.
