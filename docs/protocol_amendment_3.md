# MedIWF Protocol Amendment 3 — 16 September 2026

Written after the template-control arm (A5) had been analysed and before any of the arms below was generated. Purpose:
strengthen the position finding and test the robustness of the main prompt effect, at the author's request that API cost
not be a constraint. Hypotheses are stated before generation.

## A9. Neutral-template arm extended to the full grid
`plain_neutral` on all 25 topics per specialty for all 15 models (2,400 new items, 3,000 in total; run name `template`).
Hypothesis: per-model shares of keys at A stay in the 5-35% range seen on the first 5 topics, except Claude Opus 5; the
pooled share stays near 0.2; the middle-position preference (B and C over D and E) persists.

## A10. Guided prompt with the neutral template
`guided_neutral`: the guided prompt with the example letter replaced by "..." (3,000 items, one per topic per model; same
run file). Hypotheses: (i) the any-flaw rate does not differ from the guided arm (the template does not affect structural
flaws); (ii) key position under guided_neutral is closer to uniform than under either guided or plain_neutral, because
alphabetization and the absence of an example letter act together; (iii) models that ignore the alphabetization guideline
(Llama 4 Maverick, GPT-5.6 Luna, Mistral Small, Qwen 3.6 27B) lose the A bias under the neutral template even so.

## A11. Robustness of the guideline effect to wording
`guided2`: a paraphrased, re-ordered checklist stating the same ten rules, with the original output template (3,000
items; run name `wording`). Hypothesis: the any-flaw OR of guided2 versus plain lies within the 95% interval of the
guided-versus-plain OR (0.45-0.56), and the same per-flaw pattern appears (largest reductions for absolute terms,
longest-option keys and non-parallel options; little change in overlapping options).

## A12. Reasoning arm extended to two flagship models
`full_reasoning` for Claude Opus 5 and DeepSeek V4 Pro, the two flagship models whose API allows reasoning to be
toggled (1,600 items). Hypothesis: as for A2, a modest reduction in structural flaws (OR 0.7-1.0) and no change in key
position under the plain prompt.

## A13. Sampling-temperature sensitivity
`plain` at temperatures 0.0 and 1.0 on the first 5 topics per specialty for all 15 models (1,200 items; run name
`temperature`; jobs tagged so they never collide with the main corpus at 0.7). Hypothesis: any-flaw rates within 5
points of the 0.7 rates for every model; key-position shares unchanged.

## A14. Stronger LLM judges for the Tier-B negative result
BenchMarker per-rule prompts with GPT-6 Astra and Claude Fable 5.1 as judges on the same 216 human-labelled examination
items. Hypothesis (pre-stated): agreement remains weak (kappa < 0.5 on every rule), extending the negative result to the
strongest models available.

## Budget
Estimated US $28 (A9) + $40 (A10) + $40 (A11) + $50 (A12) + $15 (A13) + $30 (A14) = about $205; actual costs will be
reported. Commands are listed in README.md.

## Analysis
A9-A10: scripts/analyze_template.py. A11: scripts/analyze_wording.py. A12: scripts/analyze_reasoning.py (unchanged).
A13: scripts/analyze_temperature.py. A14: scripts/validate_judge.py (unchanged).
