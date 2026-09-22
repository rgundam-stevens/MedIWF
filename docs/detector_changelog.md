# MedIWF Tier-A detector — changelog

## v1.2 (17 September 2026) — second-audit release

Made after an independent code audit (docs/reviews_2026-09-16/03_code_audit_opus.md) that constructed adversarial items for
every rule. v1.1 is kept as `src/mediwf/detector_v1_1.py`; v1.1 flag files are archived in `outputs/v1_1_archive/`.
Unit tests: `python3 scripts/tests_detector.py` (65 cases). Corpus estimates moved by at most 0.1 points; the NBME any-flaw rate by 0.4 points (four clang-cue items).

| Rule | Change | Why | Cells changed, main corpus (12,000 items) |
|---|---|---|---|
| combination_options | a lone roman numeral ("IV") no longer matches; a combination needs two numerals | a disease stage written as a numeral was a K-type option | 0 |
| absolute_terms | the "all ... of" exemption (any later "of") replaced by "all of"; dosing idioms "every morning/night/evening/bedtime/meal/dose/visit" exempt; Unicode hyphens and dashes normalised so "all-cause" is exempt however typed | "Discontinue all antihypertensive medications because of hypotension" was exempt while "Discontinue all heparin products" was flagged; "every morning" was flagged | 2 |
| overlapping_options | trailing punctuation ignored before the containment test | "Elevated troponin." was not found inside "Elevated troponin and ST elevation." | 2 |
| clang_cue | lemmatiser strips "-es" only after x, ch, sh, ss, z; otherwise "-s" | "crackles" became "crackl" while "crackle" stayed "crackle" | 13 |
| answer letter | "(C)", "C.", "Option C", "c" are read as C; an unreadable key disables the key-dependent rules instead of using its first character | protection for external datasets (BenchMarker's keys are letters; NBME keys are letters) | 0 |
| numeric_not_ordered | unchanged; Table 1 wording corrected to "all options numeric" (the code never required only three) | description/implementation mismatch | 0 |
| negative_stem | unchanged; "least invasive test" fires on LEAST, which is intended | | 0 |

Composite "any Tier-A flaw" (14 rules, `src/mediwf/rules.py`): plain 23.4% -> 23.4%; guided 13.5% -> 13.6%; NBME (all 667) 17.1% -> 17.5%; NBME five-option 16.8% -> 17.3%.

Also in this release, outside the detector: `src/mediwf/rules.py` is the single definition of the composites (CORE 14, SENSITIVITY 11,
VALIDATED 10) used by every script; `analyze_flags.py` (which had counted option_length_outlier in "any flaw"), `nbme_psychometrics.py`
(six rules) and `make_figures.py` now use it; BenchMarker duplicate label rows are collapsed in `validate_benchmarker.py`; the
hand-verification sample was re-drawn on the whole corpus (v4); `analyze_verification.py` maps pass-2 ids back to pass-1 ids.

## v1.1 (16 September 2026) — audit release

Made after an audit that tallied, for every rule, exactly which words and patterns it fired on in the 12,000-item main
corpus and in the 667 NBME items, and re-checked agreement with the BenchMarker human labels (dev block = benchmark items,
test block = human-written exam items). v1.0 is kept as `src/mediwf/detector_v1_0.py`; v1.0 flag files are archived in
`outputs/v1_0_archive/`. Unit tests: `python3 scripts/tests_detector.py` (50 cases).

| Rule | Change | Why | Prevalence, main corpus (v1.0 -> v1.1) |
|---|---|---|---|
| combination_options | "shared components" clause removed; K-type letter/roman/arabic combinations only | all 133 v1.0 flags were multi-drug regimens or vaccine schedules sharing an ingredient, none was a K-type item | 1.11% -> 0.00% |
| grammatical_cue | "-ing start" and "plural first word" heuristics removed; article mismatch and key-alone-is-a-full-sentence kept | 266 of 368 flags came from the plural heuristic firing on words such as "Stress", "Intravenous"; 101 from "-ing" adjectives ("Bridging", "Smoking"); BenchMarker kappa was 0.01/0.14 | 3.07% -> 0.03% |
| overlapping_options | containment must respect word boundaries | v1.0 substring test flagged "800 mL" inside "4800 mL", "5 mg" inside "7.5 mg", "Complete" inside "Incomplete", "Fibroblasts" inside "Myofibroblasts" | 1.38% -> 0.97% |
| clang_cue | stop-word list extended with generic clinical words (serum, blood, level, hour, week, right, left, normal, oral, intravenous, ...) | the most frequent "exclusive" words were generic; BenchMarker agreement unchanged (dev kappa 0.60 -> 0.58, test 0.31 -> 0.33) | 8.37% -> 7.21% |
| negative_stem | wh-clause and "does not ...?" branches made case-insensitive; a "not" counts only when it negates the question's predicate; "at least" / "not only" excluded | v1.0 required a lower-case "which", so "Which ... is least likely?" and "Each ... except" were missed (BenchMarker test recall 0.57 -> 0.67) | 0.01% -> 0.00% |
| absolute_terms | unchanged | a narrower "universal claim" variant was tried and rejected: BenchMarker dev kappa fell from 0.29 to 0.07. The lexical rule is kept and its modest agreement with human judgement (kappa 0.29) is reported as a limitation | 2.83% -> 2.83% |
| all other rules | unchanged | | |

Composite "any Tier-A flaw" (14 rules): plain 27.6% -> 23.4%; guided 18.6% -> 13.5%; NBME 22.0% -> 17.1%.

### Validator (src/mediwf/parsing.py, shared by generate.py and detect.py)
A response is usable only if its option keys normalise to exactly A-E without collisions and the answer is one of them.
The audit found two responses in which a malformed key ("date", "ed") silently overwrote a real option after
normalisation (one item was left with option D = "x"), and four responses with six or four options. detect.py now
re-parses every stored response with the current validator and excludes the 7 affected jobs (4 main corpus, 1 reasoning
arm, 2 position arm) until they are regenerated with a new seed by re-launching the same generate.py command.

### NBME loader (scripts/detect.py)
Eight NBME items have purely numeric option cells, which pandas reads as numbers; v1.0 treated them as missing (0 options).
They are now converted to text. One cell is an Excel date (a range such as "1-2" mis-read by Excel) and is written back as
"month-day".

### BenchMarker agreement, v1.0 vs v1.1 (test block = human-written exam items; tp/fp/fn, precision, recall, kappa)
| rule | v1.0 | v1.1 |
|---|---|---|
| avoid_negatives | 12/4/9, 0.75, 0.57, 0.62 | 14/7/7, 0.67, 0.67, 0.63 |
| avoid_k_type | 4/7/12, 0.36, 0.25, 0.25 | 2/1/14, 0.67, 0.12, 0.19 |
| no_absolute_terms | 9/22/9, 0.29, 0.50, 0.29 | unchanged |
| avoid_repetition (clang) | 5/9/9, 0.36, 0.36, 0.31 | 5/8/9, 0.38, 0.36, 0.33 |
| grammatical_consistency | 4/15/14, 0.21, 0.22, 0.14 | 0/5/18, 0.00, 0.00, -0.04 |
| none/all of the above, fill-in-blank, ordered options, vague terms, option length | unchanged | unchanged |

## v1.0 (13 September 2026)
Initial release used for the pilots, the main corpus, the reasoning arm and the position arm.
