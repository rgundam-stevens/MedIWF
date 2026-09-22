
# MedIWF Study Protocol {#mediwf-study-protocol .title}

Item-writing flaws in LLM-generated medical multiple-choice questions: a benchmark, detector, and generator leaderboard · Protocol v0.1 · 13 September 2026 · Author: Rohit Gundam (independent researcher) · Drafted with AI assistance (Claude); all decisions to be confirmed by the author

## What this document is {#what-this-document-is}

A protocol is the written plan of a study, fixed before any data is generated. It states what question we are asking, exactly how we will answer it, and how we will analyze the results. Writing it first protects the study from a common failure: changing the method after seeing the results, which reviewers treat as a red flag. Once you approve this protocol, we follow it, and any deviation is recorded and reported in the paper. Everything below is a proposal for you to read, question, and confirm. Terms you may not know are defined in the glossary at the end.

## Summary {#summary}

Medical educators are using large language models (LLMs) to write multiple-choice questions (MCQs). Roughly fifty published studies have evaluated the quality of such questions, but almost every one uses its own home-made rating scale, evaluates a few dozen items from one model in one specialty, and does not release the items. Meanwhile, assessment science has a validated rulebook of item-writing flaws (IWFs), and two recent automated detectors exist, but neither has been applied to LLM-generated items or to medicine. MedIWF will produce (1) a released corpus of several thousand LLM-generated medical MCQs across models, specialties, and two prompting conditions; (2) flaw labels from a documented, validated automated pipeline; (3) an open-source detector; (4) a generator leaderboard and the first controlled test of whether including the item-writing guidelines in the prompt reduces flaws; and (5) a link between automated flaw labels and real examinee statistics. The study is fully computational and single-authored, with a target of a public preprint in about three months and journal submission shortly after.

## Background and gap {#background-and-gap}

The literature scan (see the accompanying tracker workbook, 59 papers) supports six claims that will form the introduction of the paper.

First, quality measurement is not standardized. Most studies rate items on bespoke 5-point scales; only a handful anchor to a published IWF taxonomy (Wu 2025, Feizi 2025, Mitra 2026, Morton 2025, Lopiano 2026, Camarata 2025). Two 2026 systematic reviews (Riehm et al., PLOS ONE; Kıyak et al., Postgraduate Medical Journal) name this as the barrier to synthesis.

Second, generated items are rarely released. Only Law 2025 (Mendeley), Kiyani 2025 (OSF), Yao 2025 (GitHub) and a 30-item subset of Al-Najafi 2026 share their items.

Third, samples are small and reliability is weak. The median study evaluates about 60 items from one model version; inter-rater reliability is often unreported or near zero (ICC 0.07–0.18 in Linde 2026; Krippendorff's alpha 0.016 in Abouzeid 2025).

Fourth, no study has run a controlled prompt experiment comparing generation with and without explicit item-writing guidelines. The closest are Lopiano 2026 (prompt iteration) and Al Shuraiqi 2026 (prompting paradigms with no guideline arm).

Fifth, automated detectors exist but not for this population. SAQUET (Moore et al., 2024) and BenchMarker (Balepur et al., ACL 2026) operationalize the Tarrant 19-rule rubric, but BenchMarker audits existing NLP benchmarks, explicitly excludes medicine, and its accuracy drops sharply out of domain (F1 0.37 on educator-written exams). Neither examines LLM-generated items, uses the NBME medical taxonomy, or links flaws to examinee statistics in medicine.

Sixth, flaws are known to matter. Downing 2005, Tarrant & Ware 2008, Rush 2016 and Pham 2018 show that flawed items distort difficulty and discrimination, and Schmucker & Moore 2026 show the same at scale with automated labels, but on K-12 science items. Where LLM-generated medical items have been checked by experts, flaw rates are high: 49% (Camarata 2025) and 56% (Feizi 2025).

## Research questions {#research-questions}

RQ1. How prevalent is each item-writing flaw in LLM-generated medical MCQs, overall and by flaw type?

RQ2. Do flaw rates differ across generator models and across medical specialties?

RQ3. Does including the item-writing guidelines in the generation prompt reduce flaw rates, and for which flaws?

RQ4. How accurately can an automated pipeline (rules plus an LLM judge) reproduce human flaw labels, per flaw type, on existing human-annotated corpora?

RQ5. Do automatically flagged flaws relate to real examinee statistics (difficulty, response time) on a public corpus of retired licensing-exam items?

## Design {#design}

### Flaw taxonomy {#flaw-taxonomy}

The primary taxonomy is the NBME Item-Writing Guide's 13 technical flaws, which medical educators recognize, cross-referenced to Haladyna, Downing & Rodriguez (2002) guideline numbers so that NLP readers can map to the Tarrant rubric used by SAQUET and BenchMarker. Each flaw is assigned to a tier by how it can be detected without medical judgment.

| Flaw (NBME family) | Haladyna 2002 | Tier | Detection method |
| --- | --- | --- | --- |
| Negatively phrased lead-in (irrelevant difficulty) | 17 | A | Rule: NOT / EXCEPT / LEAST in stem |
| "None of the above" option | 25 | A | Rule: string match |
| "All of the above" option | 26 | A | Rule: string match |
| Long or complex options / longest option is key | 24 | A | Rule: key length vs. distractor lengths (80% threshold, SAQUET convention) |
| Absolute terms (always, never) in options | 28a | A | Rule: lexicon match, key vs. distractors |
| Word repetition / clang cue (stem word in key only) | 28b | A | Rule: token overlap stem–key vs. stem–distractors |
| Grammatical cue (option does not fit stem) | 28c | A | Rule \+ parser: article/number agreement |
| Non-parallel options (heterogeneous form/length) | 23 | A | Rule: length variance, part-of-speech pattern |
| Numeric data presented inconsistently | NBME | A | Rule: unit/format consistency across numeric options |
| Convergence / grouped or collectively exhaustive options | 28e | A/B | Rule for overlaps of terms; LLM judge for semantic pairs |
| Key position distribution (corpus-level) | 20 | A | Rule: chi-square on key letter by model |
| Vague frequency terms (usually, often) | NBME | A | Rule: lexicon match |
| Correct option stands out (most specific / most qualified) | 28d | B | LLM judge |
| Complicated or unfocused stem; window dressing | 14–16 | B | LLM judge |
| Implausible distractors | 29 | B | LLM judge |
| More than one defensible correct answer | 19 | B | LLM judge (ensemble); reported as secondary |

Tier A flaws are labeled deterministically by code and validated against existing human labels (see Validation). Tier B flaws are labeled by an LLM judge and reported separately with explicit uncertainty, because no clinician validation is available within this study. The paper's primary claims rest on Tier A.

### Generation corpus {#generation-corpus}

| Design factor | Levels | Rationale |
| --- | --- | --- |
| Generator models | 6–8: two to three frontier API models (e.g., current OpenAI, Anthropic, Google) plus three to five open-weight models (e.g., Llama, Qwen, Mistral, a medical fine-tune such as OpenBioLLM) | Leaderboard across commercial and open models; open-weight ensures reproducibility |
| Specialties | 8: internal medicine, surgery, pediatrics, obstetrics/gynecology, psychiatry, neurology, pharmacology, pathology | Broad coverage; emergency medicine deliberately excluded (employer proximity) |
| Topics | 25 per specialty, drawn from public curricular outlines (e.g., USMLE content outline headings) | Controls content so model comparisons are fair |
| Prompt condition | 2: plain request vs. request that includes the NBME/Haladyna guidelines | RQ3 experiment |
| Repetitions | 2 items per model × topic × condition (temperature fixed, seeds logged) | Captures within-model variability |
| Format | Single-best-answer, clinical vignette, 5 options (A–E), key and one-line rationale | The standard board format |

Approximate corpus size: 8 models × 8 specialties × 25 topics × 2 conditions × 2 repetitions = 6,400 items. All prompts, parameters, model versions, dates, and raw outputs are stored with each item.

### Human-written comparison set {#human-written-comparison-set}

A comparison set of human-written items is included only from sources whose license permits research reuse and redistribution, verified individually: candidates are MedMCQA (Apache 2.0), the Law 2025 human items (Mendeley), and the Kiyani 2025 items (OSF). MedQA's license will be checked before use. No items from ABEM, commercial question banks, or copyrighted review books will be used.

### Validation of the labeling pipeline (RQ4) {#validation-of-the-labeling-pipeline-rq4}

Because this study has no human raters of its own, the detector is validated on corpora that already carry human flaw labels: the BenchMarker human annotations (3,419 writing-error labels, MIT license), the SAQUET dataset (271 items including 47 healthcare items), the Law 2025 items (expert IWF judgments on 100 LLM-generated emergency-medicine items), the Yao 2025 MedQG set (758 LLM-generated USMLE-style items with expert ratings), and, if item text is included, the Rush 2016 Zenodo record (1,925 items with 14 flaw labels and psychometrics). Precision, recall, F1 and Cohen's kappa are reported per flaw and per corpus. In addition, the author will hand-label a random sample of 300 MedIWF items for Tier A flaws following a written guide, twice with a four-week gap, and report intra-rater agreement; disagreements between rules and the author are adjudicated and documented.

### Psychometric linkage (RQ5) {#psychometric-linkage-rq5}

The detector is run over a public corpus of retired licensing-exam items with real examinee statistics. Primary: the NBME/BEA 2024 dataset (667 USMLE items with transformed difficulty and mean response time), obtained through NBME's data-use agreement. Fallbacks, in order: the Polish CEM licensing-exam database (per-item difficulty and discrimination; terms to be read), Brazil's ENADE health-course items (INEP microdata, Portuguese), and the Rush 2016 veterinary items. Flagged and unflagged items are compared on difficulty and response time with regression adjusting for exam step and item length.

### Analysis plan {#analysis-plan}

Prevalence (RQ1) is reported per flaw as a proportion with 95% Wilson confidence intervals, overall and by model, specialty, and condition. Model, specialty and condition effects (RQ2, RQ3) are tested with mixed-effects logistic regression: flaw present (yes/no) as outcome; model, condition, specialty and their two-way interactions as fixed effects; topic as a random intercept. Key-position bias is tested with a chi-square goodness-of-fit per model. Detector performance (RQ4) is reported as precision, recall, F1 and kappa per flaw with bootstrap confidence intervals. The psychometric link (RQ5) uses linear regression of difficulty and of response time on flaw count and flaw type, adjusting for step and item length. Multiple comparisons are handled with Benjamini–Hochberg false discovery rate control. All analysis code is released; the analysis plan is frozen at protocol approval.

### Release plan {#release-plan}

The corpus, labels, prompts, and per-item metadata are released on Hugging Face and archived on Zenodo with a DOI, under CC BY 4.0 (subject to a check of each model provider's terms on output redistribution). The detector and analysis code are released on GitHub under MIT. A leaderboard table (flaw rate per model, per condition) is published in the repository README and updated as new models are added. Paper preprint on arXiv (cs.CL, cross-listed cs.CY), then journal submission.

## Ethics, employer, and disclosure {#ethics-employer-and-disclosure}

No human participants are involved; the study analyzes machine-generated text and public datasets. The paper's ethics statement will explain that no ethics review was sought and why, as JMIR's author guide requires. Affiliation will be "Independent researcher." No ABEM materials, data, systems, time, or staff will be used, and emergency medicine is excluded from the specialty list. Rohit will read his employment agreement for outside-activity and intellectual-property clauses before generation begins and, if anything is ambiguous, obtain a short written acknowledgement from ABEM. Generative-AI assistance in design, code, and writing will be disclosed in the manuscript at the level of detail the target journal requires; JMIR requires the AI conversations used in manuscript preparation to be submitted as a supplementary appendix, so all working sessions will be retained.

## Timeline {#timeline}

| Weeks | Milestone | Rohit's part | Claude's part |
| --- | --- | --- | --- |
| 1–2 | Protocol approved; accounts created; NBME data request submitted; licenses verified | Read protocol and tracker; create accounts; submit NBME form; read employment agreement | Finalize flaw definitions and rater guide; draft prompts |
| 3–5 | Generation pipeline built and run; corpus complete | Provide API keys; run pipeline; report costs and failures | Write pipeline code, tests, storage schema |
| 5–7 | Tier A rules built and validated on external corpora; author hand-labels 300 items (pass 1) | Hand-label 300 items using the guide | Write detector, validation harness, results tables |
| 8–9 | Tier B LLM judge run; psychometric linkage run | Run jobs; hand-label pass 2 | Analysis code, figures |
| 10–12 | Manuscript drafted; repository, dataset card, leaderboard published | Read every section; confirm understanding; edit in own words | Draft manuscript, dataset card, README |
| 13 | arXiv preprint posted (endorsement obtained); JMIR Medical Education submission | Request arXiv endorsement; submit | Submission package, cover letter, reviewer suggestions |
| 14–26 | Peer review; revisions; start paper two | Respond to reviewers with Claude's help | Draft responses; plan paper two |

## Budget {#budget}

| Item | Estimate (USD) | Notes |
| --- | --- | --- |
| API generation, 6,400 items × \~600 output tokens, across 3–4 commercial models | 100–300 | Depends on model prices at run time |
| LLM judge for Tier B, 6,400 items × 5 flaws | 100–400 | Use a mid-tier model; batch APIs cut cost |
| Open-weight models on a rented GPU | 50–150 | Hourly rental; a few hours per model |
| Journal APC (JMIR Medical Education) | 2,750 | Payable on acceptance; optional fast-track \+950 |
| Total | 3,000–3,600 | Excluding optional fast-track |

## Risks and mitigations {#risks-and-mitigations}

| Risk | Likelihood | Mitigation |
| --- | --- | --- |
| NBME declines or delays data access | Medium | Submit week 1; fallbacks (CEM Poland, ENADE, Rush 2016) designed in |
| Reviewers object to absence of clinician validation | Medium | Primary claims limited to Tier A (objective flaws); Tier B clearly labeled as secondary; external human-labeled corpora used for validation |
| Model output licenses restrict redistribution | Low | Check each provider's terms; drop any model whose terms forbid redistribution |
| arXiv endorsement not obtained | Low–medium | Request early from authors of related papers; fallback to JMIR Preprints or Zenodo preprint |
| Employer objection | Low | Employment-agreement check; no EM specialty; independent affiliation |
| Model versions change mid-study | Certain | Pin versions and dates; frame corpus as a dated snapshot |
| Scope creep | High | Protocol frozen at approval; extras go to paper two |

## What I need from you now {#what-i-need-from-you-now}

1. Read this protocol and the tracker workbook. Reply with anything you do not understand or disagree with; nothing proceeds until you confirm.
2. Read your ABEM employment agreement and handbook for outside-activity, publication, and intellectual-property clauses, and tell me what they say.
3. Create accounts on GitHub, Hugging Face, Zenodo, and arXiv (arXiv will need an endorsement later).
4. Submit the NBME BEA 2024 data request form (https://www.nbme.org/bea-2024-shared-task-data) describing the study in two or three sentences; forward me the response.
5. Open the Polish CEM question database and read the terms of use; tell me whether research use and local downloading are permitted.
6. Set up API access with OpenAI, Anthropic, and Google, and a small prepaid balance (about $200 to start).
7. Tell me which programming environment you prefer (Python version, local machine vs. cloud notebook) so the pipeline code fits your setup.

## Glossary {#glossary}

Item: a multiple-choice question. Stem: the question text. Key: the correct option. Distractor: an incorrect option. Item-writing flaw (IWF): a violation of published guidelines for writing MCQs. Tier A / Tier B: flaws detectable by rules alone / flaws requiring judgment. Detector: our software that labels flaws. LLM judge: a language model asked to label a flaw, used where rules cannot. Precision / recall / F1: how many flagged items are truly flawed / how many truly flawed items are flagged / their harmonic mean. Cohen's kappa: agreement between two labelers corrected for chance. Intra-rater agreement: the same person's agreement with themselves across time. Difficulty (p-value): proportion of examinees answering correctly. Discrimination: how well an item separates strong from weak examinees. Mixed-effects logistic regression: a model for yes/no outcomes that accounts for items being grouped (here, by topic). Wilson interval: a confidence interval for a proportion. Benjamini–Hochberg: a correction for testing many hypotheses. Preprint: a public, citable version of a paper before peer review. APC: article processing charge, the fee an open-access journal charges on acceptance.
::::
