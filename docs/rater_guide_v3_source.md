:::: page {margins=1.1in size=letter}
::: footer {text-align=center}
[@page] of [@pages]
:::

# MedIWF Rater Guide {#mediwf-rater-guide .title}

[Hand-check of structural item-writing flaws · Version 3.0 · 17 September 2026 · matches detector v1.2 (supersedes v2.0 of 15 September, whose rules 3, 4, 8, 9 and 10 described the detector as it was in v1.0)]{.muted}

## What you are doing, in one paragraph {#what-you-are-doing}

You will read 439 multiple-choice questions and, for each one, answer ten yes/no questions about its *form*: is the question phrased negatively, is the correct option the longest, does a word from the question reappear only in the correct option, and so on. None of the ten needs any medical knowledge. Think of it as proof-reading a form for a missing signature: you do not need to understand what the form is about to see that the signature line is empty. The medical words in the items are just words to you; you compare, count and look for patterns. Every rule below is deliberately mechanical so that two careful readers reach the same answer.

Your labels are the "truth" against which the automated checker is scored, so the only thing that matters is that you apply the rules exactly as written, item by item, without guessing what the checker might have said.

## The routine for every item {#the-routine}

Do the same three steps in the same order for every item. The number in front of each rule is its column number in the spreadsheet.

**Step 1 – read the question sentence.** This is the last sentence of the stem, the one ending in a question mark or a colon (for example "Which of the following is the most appropriate next step?"). Ignore the story before it for now. Answer:

- **Column 1** `negative_stem` – does this sentence ask for the wrong, false or excluded option?

Also note whether the sentence ends in "a" or "an"; you will need that for column 8.

**Step 2 – read the five options as a list, without looking at the key yet.** Answer:

- **Column 2** `meta_option` – does any option say "all of the above", "none of the above" or "neither of the above"?
- **Column 3** `combination_options` – are options built out of other options ("A and B", "I and III", "both A and C")?
- **Column 5** `absolute_terms` – does any option contain a sweeping word such as always, never, all, only?
- **Column 6** `vague_terms` – does any option contain a frequency word such as usually, often, rarely?
- **Column 9** `nonparallel_options` – are the options different kinds of things or very different shapes?
- **Column 10** `overlapping_options` – is one option contained inside another?

**Step 3 – now look at the key letter and compare the correct option with the four wrong ones.** Answer:

- **Column 4** `longest_option_key` – is the correct option a quarter longer than every wrong option?
- **Column 7** `clang_cue` – is there a specific word in the stem that appears in the correct option and in none of the wrong ones?
- **Column 8** `grammatical_cue` – does the correct option alone fit the grammar, or alone differ in form?

Type **1** for yes and **0** for no in every one of the ten columns. Never leave a cell blank. Use the `notes` column only for something odd (six options, a missing key, an item that is not a question, or the date at the start of a session).

## Quick reference card {#quick-reference}

| Column | Ask yourself | Mark 1 when |
| --- | --- | --- |
| 1 `negative_stem` | Does the question sentence ask for the wrong one? | NOT, EXCEPT, LEAST, FALSE or INCORRECT in the question sentence makes the examinee pick the option that does not apply |
| 2 `meta_option` | Any "all / none / neither of the above"? | Any option is one of these, whether or not it is the key |
| 3 `combination_options` | Options made from other options? | Any option refers to two or more other options by letter or numeral (A and B, I and III, 1 and 3). A lone numeral (a stage "IV") and ordinary two-drug regimens do not count |
| 4 `longest_option_key` | Is the key a quarter longer than every distractor? | Key has at least 4 words and MORE than 1.25 × the characters of the longest wrong option (table in the rule) |
| 5 `absolute_terms` | Sweeping words in any option? | always, never, all, none, only, every, completely, entirely, absolutely, totally, definitely, impossible, invariably, exclusively – except in fixed phrases such as "every 8 hours" |
| 6 `vague_terms` | Frequency words in any option? | usually, often, frequently, sometimes, rarely, seldom, occasionally, generally, regularly, infrequently, commonly |
| 7 `clang_cue` | A specific stem word only in the key? | A distinctive word (drug, disease, body part, finding) is in the stem and in the key and in none of the wrong options |
| 8 `grammatical_cue` | Does grammar or form single out the key? | Question ends in "a"/"an" and only some options fit it; or the key alone is written as a full sentence (at least four words, ending with a full stop) while no wrong option is |
| 9 `nonparallel_options` | Same shape? | Two or more numeric options mixed with text options; full sentences mixed with fragments; word counts wildly uneven (spread ÷ average > 0.6, see the rule). Mixed categories go in the notes column, not here |
| 10 `overlapping_options` | One option inside another? | One option's whole text (at least 6 characters) appears inside another option as whole words, ignoring capitals and a final full stop. Logical overlap without shared text ("less than 5 mg" / "less than 10 mg") goes in the notes column |

## The ten rules, each with a flag example and a look-alike that is not flagged {#the-ten-rules}

All examples are invented. Read each pair side by side: the second example in every pair is the trap that looks like a flaw but is not.

### Rule 1: negative_stem {#negative_stem}

**What it is.** The question sentence asks the examinee to find the option that is wrong, false, or does not belong.

**How to check.** Find the question sentence (the last one, ending "?" or ":"). Look in that sentence only for NOT, EXCEPT, LEAST, FALSE, INCORRECT, in any capitalisation. If the word turns the task into "pick the one that does not apply", mark 1.

**Flag it (1).** Question sentence: "Which of the following is NOT a recognised cause of her condition?" Also flagged: "All of the following are features of this condition EXCEPT:" and "Which of the following findings is LEAST likely?"

**Do not flag (0).** Stem: "A 45-year-old woman who does not smoke has had a cough for 3 weeks. Which of the following is the most likely diagnosis?" The "not" sits in the story, not in the question sentence, and the question asks for the most likely option. A "not" inside an *option* ("apply moisturiser but not between the toes") also does not count.

### Rule 2: meta_option (all, none or neither of the above) {#meta_option}

**What it is.** An option that refers to the other options instead of giving an answer of its own.

**How to check.** Scan the five options for the phrases "all of the above", "none of the above", "all of these", "neither of the above". Any letter counts, key or not.

**Flag it (1).** Options: A. Oral dexamethasone · B. Nebulised epinephrine · C. Intravenous ceftriaxone · D. Inhaled salbutamol · E. None of the above.

**Do not flag (0).** Options: A. Amoxicillin · B. Azithromycin · C. Ciprofloxacin · D. Doxycycline · E. No antibiotic treatment is needed. "No treatment is needed" is a real answer about the patient, not a reference to the other options.

### Rule 3: combination_options {#combination_options}

**What it is.** Options assembled from other options or from numbered statements (the old "K-type" format).

**How to check.** Mark 1 if any option points at two or more other options by letter or numeral ("A and B", "Both A and C", "I, II and III", "1 and 3"). A single numeral on its own ("IV" as a disease stage) is not a combination, and options that are ordinary multi-drug regimens ("Aspirin and clopidogrel") are never combinations, even when several options share a drug.

**Flag it (1).** Options: A. I and II · B. I, II and III · C. III and IV · D. II and IV · E. I, II, III and IV.

**Do not flag (0).** Options: A. Amoxicillin and clavulanate · B. Ciprofloxacin · C. Doxycycline · D. Metronidazole · E. Nitrofurantoin. A two-drug combination is a normal answer. Also 0: A. Aspirin and heparin · B. Aspirin and clopidogrel · C. Heparin and clopidogrel · D. Warfarin · E. Apixaban, which reuse drugs but do not refer to other options. Also 0: stages A. I · B. II · C. III · D. IV · E. V.

### Rule 4: longest_option_key {#longest_option_key}

**What it is.** The correct option is clearly longer and more detailed than every wrong option, which test-wise examinees know to pick.

**How to check.** The checker counts *characters* (letters, digits, spaces and punctuation), not words. Count the characters of the correct option and of the *longest wrong* option (the one with the most characters). Mark 1 only if the key has at least 4 words **and** its character count is MORE than 1.25 times the longest wrong option's count. Word counts are a quick screen: when the key has clearly more than a quarter more words than every wrong option, it will pass the character test too; when it is close, count characters.

| Longest wrong option has | Key needs at least (characters) |
| --- | --- |
| 20 characters | 26 |
| 30 characters | 38 |
| 40 characters | 51 |
| 50 characters | 63 |
| 60 characters | 76 |
| 80 characters | 101 |
| 100 characters | 126 |
| 120 characters | 151 |

**Flag it (1).** Options: A. Oral naproxen · B. Intra-articular corticosteroid injection · C. Start intravenous antibiotics and arrange urgent surgical washout of the knee joint · D. Colchicine · E. Physiotherapy. Key: C. The key has 12 words and 79 characters; the longest wrong option, B, has 40 characters, and 79 is more than 50.

**Do not flag (0).** Same options but the key is B, "Intra-articular corticosteroid injection" (3 words). A long *wrong* option never triggers this rule; that situation belongs to Rule 9. Also 0: key "Obtain a chest radiograph" (25 characters) against a longest wrong option of 24 characters, because 25 is not more than 1.25 × 24 = 30.

### Rule 5: absolute_terms {#absolute_terms}

**What it is.** An option makes a sweeping, all-or-nothing claim, which examinees have learnt to distrust.

**How to check.** Look in the five options (not the stem) for: always, never, all, none, only, every, completely, entirely, absolutely, totally, definitely, impossible, invariably, exclusively. Mark 1 if any option contains one of them, **unless** the word is part of a fixed phrase that is not a claim: "every 8 hours", "every other day", "once daily", "only child", "all-cause mortality", "at all", "only one/two/a few", and the "all/none of the above" options that belong to Rule 2.

**Flag it (1).** Option: "C. Calluses should always be removed at home with a blade." Also flagged: "D. Never use beta-blockers in this patient" and "A. Surgery is the only effective treatment."

**Do not flag (0).** Option: "B. Amoxicillin every 8 hours for 10 days." The word "every" here is a dosing interval, not a claim. Likewise "E. None of the above" is Rule 2, not Rule 5, and "does not smoke at all" in the stem is ignored because the stem is never checked for this rule.

### Rule 6: vague_terms {#vague_terms}

**What it is.** An option hedges with a frequency word, which makes it sound safe and is a known giveaway.

**How to check.** Look in the options only for: usually, often, frequently, sometimes, rarely, seldom, occasionally, generally, regularly, infrequently, commonly. Mark 1 if any option contains one. Judge only these words; do not mark an option for being vague in a general sense.

**Flag it (1).** Option: "C. Usually resolves within 3 months."

**Do not flag (0).** Stem: "He often has headaches in the afternoon…" with options that contain none of the listed words. The stem does not count. Also 0: "Regular insulin before meals", because "regular" is not "regularly", and "Common bile duct exploration", because "common" is not "commonly".

### Rule 7: clang_cue {#clang_cue}

**What it is.** A distinctive word from the stem is echoed in the correct option and in no wrong option, so an examinee can match words instead of thinking.

**How to check.** List the distinctive words of the correct option: names of drugs, diseases, organisms, body parts, findings, procedures, mechanisms – anything specific with four or more letters. Skip generic words (patient, treatment, management, therapy, diagnosis, cause, test, study, appropriate, initial, next, step, likely, most, following). For each distinctive word ask two questions: is it in the stem, and is it absent from all four wrong options? If both are true for at least one word, mark 1. Treat singular and plural as the same word (infection / infections, crackle / crackles).

**Flag it (1).** Stem ends "…examination shows crackles at the right lung base. Which of the following is the most appropriate next step?" Options: A. Complete blood count · B. Chest radiograph to evaluate the crackles · C. Reassurance · D. Oral antihistamine · E. Spirometry. Key: B. "Crackles" is in the stem, in the key, and in no wrong option.

**Do not flag (0).** Stem mentions "pneumonia"; key "Treat the pneumonia with amoxicillin"; wrong option "Admit for observation of the pneumonia". The word also appears in a wrong option, so it does not single out the key. Also 0: stem says "…the most appropriate treatment?" and the key says "Begin treatment with…", because "treatment" is a generic word.

### Rule 8: grammatical_cue {#grammatical_cue}

**What it is.** Grammar or form gives the key away: the question only reads correctly with the key, or the key is the odd one out in shape.

**How to check.** Two separate checks, either one is enough for a 1.

*Article check.* If the question sentence ends in "a" or "an" (for example "The most likely diagnosis is an"), read each option after that word. "An" needs an option starting with a vowel sound (a, e, i, o, u); "a" needs a consonant sound. If some options fit and some do not, mark 1.

*Sentence check.* Mark 1 if the correct option **alone** is written as a full sentence, meaning it has at least four words and ends with a full stop, while no wrong option does. If even one wrong option is also a full sentence, mark 0. (An -ing word or a plural at the start of the key is NOT a cue in this version of the rules: "Starting warfarin" among "Aspirin, Clopidogrel, Heparin, Enoxaparin" is 0.) Only the key matters here; a wrong option that is the odd one out belongs to Rule 9.

**Flag it (1, article).** Question sentence: "The most likely diagnosis is an". Options: A. Ectopic pregnancy · B. Ovarian torsion · C. Ruptured appendix · D. Threatened miscarriage · E. Urinary tract infection. "An ruptured appendix" and "an threatened miscarriage" do not fit, so the article points away from C and D.

**Flag it (1, sentence).** Options: A. No specific pharmacotherapy is indicated at this time. · B. Lithium · C. Fluoxetine · D. Olanzapine · E. Clonazepam. Key: A. The key alone is a full sentence with a full stop; the wrong options are single words.

**Do not flag (0).** Options: A. Start aspirin · B. Start clopidogrel · C. Start warfarin · D. Start heparin · E. Start enoxaparin. All the same form. Also 0 when the question ends in "a" or "an" and every option fits it, 0 when the key is a full sentence but so is at least one wrong option, and 0 for A. Aspirin · B. Clopidogrel · C. Starting warfarin · D. Heparin · E. Enoxaparin (key C): the -ing word is not a cue.

### Rule 9: nonparallel_options {#nonparallel_options}

**What it is.** The options are not the same kind of thing or not the same shape, so one or more stand out for the wrong reason.

**How to check.** Mark 1 if any of these is true: (a) two or more options begin with a number ("12 weeks", "6 months", "0.5 mg/kg") while at least one option does not; (b) some options are full sentences (four or more words, ending with a full stop) and others are fragments; (c) the word counts are wildly uneven. For (c) the checker's rule is: the spread of the five word counts (their population standard deviation) divided by their average is greater than 0.6, and the average is at least 3 words. In practice this fires when one option has several times the words of the others: counts 1, 1, 2, 3 and 12 give a spread of 4.2 against an average of 3.8, a ratio of 1.1, so mark 1; counts 3, 4, 4, 5 and 6 give a spread of 1.0 against an average of 4.4, a ratio of 0.23, so mark 0. When you are unsure, type the five counts into a spreadsheet cell as =STDEV.P(a,b,c,d,e)/AVERAGE(a,b,c,d,e) and mark 1 if the result is above 0.6. Mixed *categories* (diagnoses alongside treatments) are not part of this rule: leave the cell at 0 and write "category mix" in the notes column.

**Flag it (1).** Options: A. Apixaban · B. Aspirin · C. Metoprolol should be increased to the maximum tolerated dose and the ECG repeated in 6 weeks. · D. Clopidogrel · E. Digoxin. One full sentence among single words (rule b), and word counts 1, 1, 16, 1, 1 (rule c: spread 6.0, average 4.0, ratio 1.5). Note that if C is *not* the key, Rule 4 stays 0; if C *is* the key, Rules 4 and 9 are both 1.

**Do not flag (0).** Options: A. Oral amoxicillin · B. Intravenous ampicillin · C. Oral doxycycline · D. Intravenous ceftriaxone · E. Oral nitrofurantoin. Same shape, similar length. Note that A. Less than 2 weeks · B. Less than 6 weeks · C. 6 to 8 weeks · D. 12 weeks · E. 6 months IS flagged under rule (a): three options begin with a number and two do not.

### Rule 10: overlapping_options {#overlapping_options}

**What it is.** Two options are not independent because one option's text is contained in another's.

**How to check.** Compare the options pairwise. Mark 1 if one option's whole text (at least 6 characters long) appears inside another option as whole words, ignoring capital letters and a final full stop: "Aspirin" inside "Aspirin and clopidogrel"; "Multiple sclerosis" inside "Primary progressive multiple sclerosis". Part of a word does not count ("800 mL" is not inside "4800 mL"; "complete" is not inside "incomplete"). Logical overlap without shared text, such as "less than 5 mg" and "less than 10 mg", is not part of this rule: leave the cell at 0 and write "logical overlap" in the notes column.

**Flag it (1).** Options: A. Aspirin · B. Aspirin and clopidogrel · C. Clopidogrel · D. Warfarin · E. Heparin. A sits inside B (and C sits inside B). Also flagged: "Elevated troponin." alongside "Elevated troponin and ST elevation."; the final full stop is ignored.

**Do not flag (0).** Options: A. Oral amoxicillin · B. Intravenous ampicillin · C. One-time abdominal ultrasonography · D. Annual abdominal ultrasonography. Sharing a word is not overlapping; neither contains the other's full text. Also 0: "Less than 2 weeks" alongside "Less than 6 weeks" (logical overlap only; note it).

## Six traps that cause most disagreements {#traps}

1. A "not" or "no" inside the story ("does not smoke", "no history of") is never `negative_stem`; only the question sentence counts.
2. "None of the above" is Rule 2, not Rule 5, even though "none" is on the absolute list.
3. "Every 8 hours", "once daily" and "only child" are fixed phrases, not absolute claims.
4. A long *wrong* option is Rule 9 (`nonparallel_options`), not Rule 4; Rule 4 is only ever about the key.
5. Shared generic words ("treatment", "patient", "management") are never a `clang_cue`; the word must be specific, and it must be absent from all four wrong options.
6. The sentence check in Rule 8 is about the key alone; if any wrong option is also a full sentence, it is 0. An -ing word or a plural is never a cue.

## Practice set: ten items to try before you start {#practice-set}

Label these ten items on paper first, using the routine and the reference card, then compare with the answer key at the end of this guide. If you disagree with the key on more than three cells in total, re-read the rules involved before starting the real sheet. All items are invented and none of them is in your spreadsheet.

**P1.** A 30-year-old man has had 3 days of sore throat, fever and tender anterior cervical lymph nodes. A rapid streptococcal antigen test is positive. Which of the following is the most appropriate treatment?

- A. Amoxicillin
- B. Azithromycin
- C. Ciprofloxacin
- D. Doxycycline
- E. Metronidazole
- Key: A

**P2.** A 58-year-old woman with type 2 diabetes asks about foot care. Which of the following statements is NOT correct?

- A. Feet should be inspected daily
- B. Shoes should be checked for foreign objects before wearing
- C. Calluses should always be removed at home with a blade
- D. Nails should be trimmed straight across
- E. Moisturiser should be applied to dry skin but not between the toes
- Key: C

**P3.** A 6-year-old boy is brought in with a barking cough and inspiratory stridor at rest. Which of the following is the most appropriate initial treatment?

- A. Oral dexamethasone
- B. Nebulised epinephrine
- C. Intravenous ceftriaxone
- D. Inhaled salbutamol
- E. None of the above
- Key: B

**P4.** A 72-year-old man has a 2-day history of a painful, swollen right knee. He is febrile. Aspiration of the knee joint yields cloudy fluid with a leukocyte count of 80,000/mm³. Which of the following is the most appropriate next step?

- A. Oral naproxen
- B. Intra-articular corticosteroid injection
- C. Start intravenous antibiotics and arrange urgent surgical washout of the knee joint
- D. Colchicine
- E. Physiotherapy
- Key: C

**P5.** A 24-year-old woman has sudden severe right lower abdominal pain and a positive urine hCG test. Transvaginal ultrasonography shows no intrauterine gestational sac. The most likely diagnosis is an

- A. Ectopic pregnancy
- B. Ovarian torsion
- C. Ruptured appendix
- D. Threatened miscarriage
- E. Urinary tract infection
- Key: A

**P6.** A 66-year-old man with atrial fibrillation and a CHA₂DS₂-VASc score of 4 is seen for follow-up. Which of the following is the most appropriate long-term therapy to reduce his risk of stroke?

- A. Apixaban
- B. Aspirin
- C. Metoprolol should be increased to the maximum tolerated dose and the ECG repeated in 6 weeks.
- D. Clopidogrel
- E. Digoxin
- Key: A

**P7.** A 35-year-old woman with newly diagnosed hypothyroidism is started on levothyroxine. Which of the following is the most appropriate interval before rechecking serum TSH?

- A. Less than 2 weeks
- B. Less than 6 weeks
- C. 6 to 8 weeks
- D. 12 weeks
- E. 6 months
- Key: C

**P8.** A 40-year-old woman asks about the natural course of her recently diagnosed condition. Which of the following best describes the prognosis of Bell palsy?

- A. Permanent facial weakness in most patients
- B. Recurrence in more than half of patients
- C. Usually resolves within 3 months
- D. Progression to bilateral weakness
- E. Requires surgical decompression
- Key: C

**P9.** A 28-year-old man has a 2-cm painless testicular mass. Which of the following investigations should be obtained before orchiectomy? I. Serum alpha-fetoprotein; II. Serum beta-hCG; III. Scrotal ultrasonography; IV. Trans-scrotal needle biopsy.

- A. I and II
- B. I, II and III
- C. III and IV
- D. II and IV
- E. I, II, III and IV
- Key: B

**P10.** A 61-year-old man who does not smoke has a 2-month history of a productive cough. He takes amoxicillin every 8 hours for a dental infection prescribed last week. A chest radiograph shows a 3-cm mass in the right upper lobe. Which of the following is the most appropriate next step in management?

- A. Bronchoscopy with biopsy
- B. Repeat chest radiograph in 6 weeks
- C. Course of oral corticosteroids
- D. Sputum culture
- E. Spirometry
- Key: A

## Ground rules for the real sheet {#ground-rules}

Work from `outputs/verification_sample_pass1.xlsx`. Never open `outputs/verification_sample_key.csv`, which holds the checker's output for the same items; the comparison only means something if you label blind. Do not use ChatGPT or any other AI tool on the items, and do not ask anyone else; the point is one careful human reading. Work in sessions of at most 40 items so attention stays even, type the date in the `notes` column of the first item of each session, and save the file after every session under the same name. Expect one to two minutes per item once the routine is familiar, so about 8 to 10 hours in total, comfortably spread over one or two weeks.

The sample is deliberately enriched: roughly six items in ten were flagged by the checker for at least one rule and four in ten were not, and the order is shuffled so you cannot tell which is which. Do not try to guess. Many items will have all ten columns at 0, and some will have three or four at 1.

## After pass 1 {#after-pass-1}

Tell Claude the sheet is done. The comparison with the checker and the per-rule agreement table will be generated for you, and a pass-2 workbook (150 of the same items in a new random order) will be prepared for a date at least four weeks later.

## Answer key for the practice set {#practice-answer-key}

Columns in spreadsheet order: 1 negative, 2 meta, 3 combination, 4 longest key, 5 absolute, 6 vague, 7 clang, 8 grammatical, 9 nonparallel, 10 overlapping.

| Item | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| P2 | 1 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| P3 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| P4 | 0 | 0 | 0 | 1 | 0 | 0 | 1 | 0 | 1 | 0 |
| P5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 |
| P6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| P7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| P8 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| P9 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| P10 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Why:

- **P1** – nothing to flag: positive question, five single-word drug names, key not in the stem.
- **P2** – Rule 1: "NOT correct" in the question sentence. Rule 5: "always" in option C. Rule 4 stays 0 because the key is shorter than option E. The "not" inside option E is ignored.
- **P3** – Rule 2: "None of the above". Rule 5 stays 0 because that phrase is a fixed exception.
- **P4** – Rule 4: key 12 words against a longest wrong option of 3. Rule 7: "knee" and "joint" are in the stem and the key and in no wrong option. Rule 9: word counts 1, 1, 2, 3, 12 (spread 4.2, average 3.8, ratio 1.1).
- **P5** – Rule 8, article check: "an" fits Ectopic, Ovarian and Urinary but not Ruptured or Threatened. Rule 1 stays 0: "no intrauterine sac" is in the story. Rule 7 stays 0: no word of the key is in the stem.
- **P6** – Rule 9: a full sentence with a full stop among single words. Rule 4 stays 0 because the long option is not the key. Rule 8 stays 0 because the odd-one-out is a wrong option, not the key.
- **P7** – Rule 9: three options begin with a number ("6 to 8 weeks", "12 weeks", "6 months") and two do not. Rule 10 stays 0: "Less than 2 weeks" is not textually inside "Less than 6 weeks"; write "logical overlap" in the notes if you like.
- **P8** – Rule 6: "usually" in option C. Rule 5 stays 0: "most" is not on the absolute list.
- **P9** – Rule 3: options built from numbered statements. Rule 10 as well: "III and IV" sits word for word inside "I, II, III and IV". Combination lists almost always overlap too, so expect to mark both columns together.
- **P10** – nothing to flag: "does not smoke" is in the story (Rule 1 is 0), "every 8 hours" is in the story and is a fixed phrase anyway (Rule 5 is 0), "chest radiograph" is shared by the stem and a *wrong* option, not the key (Rule 7 is 0), and the word counts 1, 2, 3, 4, 6 give a ratio of 0.54, below 0.6 (Rule 9 is 0).
::::
