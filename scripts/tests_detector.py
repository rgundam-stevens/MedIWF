"""Unit tests for the Tier-A detector (v1.2). Run: python3 tests_detector.py"""
import sys; sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "src"))
from mediwf.detector import detect
def item(stem, opts, key="A"): return {"stem": stem, "options": dict(zip("ABCDE", opts)), "answer": key}
Q = "A 40-year-old woman comes to the physician because of fatigue. Which of the following is the most appropriate next step in management?"
DRUGS = ["Amoxicillin", "Azithromycin", "Ciprofloxacin", "Doxycycline", "Metronidazole"]
T = []
def case(name, it, flaw, expected):
    got = detect(it)["flaws"][flaw]; T.append((name, flaw, expected, got))
# negative stem
case("NOT in lead-in", item("A woman has fever. Which of the following is NOT a recognised cause?", DRUGS), "negative_stem", True)
case("EXCEPT trailing", item("A woman has fever. All of the following are features EXCEPT:", DRUGS), "negative_stem", True)
case("least likely", item("A woman has fever. Which of the following findings is least likely?", DRUGS), "negative_stem", True)
case("not in vignette only", item("A woman who does not smoke has fever. Which of the following is the most likely diagnosis?", DRUGS), "negative_stem", False)
case("at least is not negative", item("A woman has had fever. Which of the following is the most appropriate management for a patient who has had at least three episodes?", DRUGS), "negative_stem", False)
# meta / combination
case("none of the above", item(Q, DRUGS[:4] + ["None of the above"]), "none_of_the_above", True)
case("no treatment needed is not meta", item(Q, DRUGS[:4] + ["No antibiotic treatment is needed"]), "none_of_the_above", False)
case("letter combos", item(Q, ["A and B", "B and C", "A and C", "A only", "B only"], "C"), "combination_options", True)
case("roman combos", item(Q, ["I and II", "I, II and III", "III and IV", "II and IV", "I, II, III and IV"], "B"), "combination_options", True)
case("arabic combos", item(Q, ["1 and 2", "2 and 3", "1 and 3", "1 only", "3 only"], "C"), "combination_options", True)
case("multi-drug regimens are not K-type", item(Q, ["Ceftriaxone, doxycycline, and metronidazole", "Ciprofloxacin and azithromycin", "Doxycycline alone", "Metronidazole and fluconazole", "Trimethoprim-sulfamethoxazole and doxycycline"]), "combination_options", False)
case("vaccine schedules are not K-type", item(Q, ["Administer DTaP, IPV, Hib, PCV13, rotavirus", "Administer DTaP, IPV, Hib", "Administer DTaP, IPV, Hib, PCV13", "Administer PCV13 and rotavirus", "Defer all vaccines"]), "combination_options", False)
# absolute terms
case("always", item(Q, ["Surgery is always required"] + DRUGS[1:]), "absolute_terms", True)
case("never", item(Q, ["Never use beta-blockers in this patient"] + DRUGS[1:]), "absolute_terms", True)
case("the only", item(Q, ["Surgery is the only effective treatment"] + DRUGS[1:]), "absolute_terms", True)
case("all patients", item(Q, ["All patients with this finding require surgery"] + DRUGS[1:]), "absolute_terms", True)
case("in every case", item(Q, ["Biopsy is indicated in every case"] + DRUGS[1:]), "absolute_terms", True)
case("is only seen in", item(Q, ["This finding is only seen in children"] + DRUGS[1:]), "absolute_terms", True)
case("supportive care only", item(Q, ["Supportive care only"] + DRUGS[1:]), "absolute_terms", True)  # lexical rule (v1.0 behaviour kept): word present
case("only if", item(Q, ["Immune globulin only if the mother is HBsAg-positive"] + DRUGS[1:]), "absolute_terms", True)  # lexical rule (v1.0 behaviour kept): word present
case("every 8 hours", item(Q, ["Amoxicillin every 8 hours for 10 days"] + DRUGS[1:]), "absolute_terms", False)
case("discontinue all heparin", item(Q, ["Discontinue all heparin products"] + DRUGS[1:]), "absolute_terms", True)  # lexical rule (v1.0 behaviour kept): word present
case("until all symptoms resolve", item(Q, ["Continue until all symptoms resolve"] + DRUGS[1:]), "absolute_terms", True)  # lexical rule (v1.0 behaviour kept): word present
case("all-cause", item(Q, ["Reduces all-cause mortality"] + DRUGS[1:]), "absolute_terms", False)
case("none of the above is meta not absolute", item(Q, DRUGS[:4] + ["None of the above"]), "absolute_terms", False)
case("only child", item(Q, ["Only child"] + DRUGS[1:]), "absolute_terms", False)
# vague
case("usually", item(Q, ["Usually resolves within 3 months"] + DRUGS[1:]), "vague_terms", True)
case("regular insulin is not vague", item(Q, ["Regular insulin before meals"] + DRUGS[1:]), "vague_terms", False)
case("vague word in stem not options", item("He often has headaches. " + Q, DRUGS), "vague_terms", False)
# longest option
case("key 12 words vs 3", item(Q, ["Start intravenous antibiotics and arrange urgent surgical washout of the knee joint", "Intra-articular corticosteroid injection", "Oral naproxen", "Colchicine", "Physiotherapy"]), "longest_option_key", True)
case("long distractor not key", item(Q, ["Oral naproxen", "Start intravenous antibiotics and arrange urgent surgical washout of the knee joint", "Colchicine", "Physiotherapy", "Rest"], "A"), "longest_option_key", False)
case("4 vs 5 words", item(Q, ["Obtain a chest radiograph", "Complete blood count now", "Reassurance", "Oral antihistamine daily dose", "Spirometry"]), "longest_option_key", False)
# clang
case("crackles clang", item("Examination shows crackles at the right lung base. Which of the following is the most appropriate next step?", ["Chest radiograph to evaluate the crackles", "Complete blood count", "Reassurance", "Oral antihistamine", "Spirometry"]), "clang_cue", True)
case("word also in distractor", item("She has pneumonia. Which of the following is the most appropriate next step?", ["Treat the pneumonia with amoxicillin", "Admit for observation of the pneumonia", "Reassurance", "Oral antihistamine", "Spirometry"]), "clang_cue", False)
case("generic serum/blood not clang", item("Serum potassium is 6.5 mEq/L and blood pressure is 150/95 mm Hg. Which of the following is the most appropriate next step?", ["Serum and blood recheck", "Calcium gluconate", "Insulin and dextrose", "Hemodialysis", "Furosemide"]), "clang_cue", False)
case("hepatitis clang (NBME example)", item("A man with hepatitis B has fatigue. Which of the following is the most likely cause?", ["Hepatitis B reactivation", "Iron deficiency", "Hypothyroidism", "Depression", "Sleep apnea"]), "clang_cue", True)
# grammatical
case("article an mismatch", item("A woman has pain and a positive urine hCG test. The most likely diagnosis is an", ["Ectopic pregnancy", "Ovarian torsion", "Ruptured appendix", "Threatened miscarriage", "Urinary tract infection"]), "grammatical_cue", True)
case("all fit an", item("The most likely diagnosis is an", ["Ectopic pregnancy", "Ovarian torsion", "Acute appendicitis", "Endometrioma", "Umbilical hernia"]), "grammatical_cue", False)
case("stress first word not plural", item(Q, ["Stress urinary incontinence", "Urge urinary incontinence", "Overflow urinary incontinence", "Functional urinary incontinence", "Mixed urinary incontinence"]), "grammatical_cue", False)
case("-ing start not a cue", item(Q, ["Bridging fibrous septa with regenerative nodules", "Centrilobular hepatocyte necrosis", "Diffuse macrovesicular fat accumulation", "Interface inflammation with portal expansion", "Periportal copper deposition"]), "grammatical_cue", False)
case("key alone full sentence", item(Q, ["No specific pharmacotherapy is indicated at this time.", "Lithium", "Fluoxetine", "Olanzapine", "Clonazepam"]), "grammatical_cue", True)
# nonparallel
case("sentence among fragments", item(Q, ["Apixaban", "Aspirin", "Metoprolol should be increased to the maximum tolerated dose and the ECG repeated in 6 weeks.", "Clopidogrel", "Digoxin"]), "nonparallel_options", True)
case("time intervals parallel-ish", item(Q, ["Less than 2 weeks", "Less than 6 weeks", "6 to 8 weeks", "12 weeks", "6 months"], "C"), "nonparallel_options", True)  # numeric/non-numeric mix: known v1 behaviour, documented
# overlapping
case("aspirin in aspirin+clopidogrel", item(Q, ["Aspirin", "Aspirin and clopidogrel", "Clopidogrel", "Warfarin", "Heparin"]), "overlapping_options", True)
case("800 mL not in 4800 mL", item(Q, ["800 mL", "4800 mL", "2400 mL", "1200 mL", "600 mL"]), "overlapping_options", False)
case("5 mg not in 7.5 mg", item(Q, ["5 mg orally once daily", "7.5 mg orally once daily", "10 mg orally once daily", "2.5 mg orally once daily", "15 mg orally once daily"]), "overlapping_options", False)
case("complete not in incomplete", item(Q, ["Complete abortion", "Incomplete abortion", "Missed abortion", "Threatened abortion", "Septic abortion"]), "overlapping_options", False)
case("fibroblasts not in myofibroblasts", item(Q, ["Fibroblasts", "Myofibroblasts", "Macrophages", "Neutrophils", "Lymphocytes"]), "overlapping_options", False)
case("multiple sclerosis in primary progressive MS", item(Q, ["Multiple sclerosis", "Primary progressive multiple sclerosis", "Neuromyelitis optica", "Transverse myelitis", "Guillain-Barre syndrome"]), "overlapping_options", True)
# key handling
case("6 options handled", {"stem": Q, "options": dict(zip("ABCDEF", DRUGS + ["Nitrofurantoin"])), "answer": "F"}, "longest_option_key", False)

# ---- v1.2 cases (second audit, 16-17 Sep 2026)
case("lone roman numeral is not K-type", item("Which stage?", ["I", "II", "III", "IV", "V"], "D"), "combination_options", False)
case("both I and III is K-type", item(Q, ["Both I and III", "I only", "II and III", "I, II and III", "III only"], "A"), "combination_options", True)
case("all ... because of is still absolute", item(Q, ["Discontinue all antihypertensive medications because of hypotension"] + DRUGS[1:]), "absolute_terms", True)
case("all of the medications exempt", item(Q, ["Stop all of the current medications"] + DRUGS[1:]), "absolute_terms", False)
case("unicode all-cause exempt", item(Q, ["Reduces all\u2011cause mortality"] + DRUGS[1:]), "absolute_terms", False)
case("every morning exempt", item(Q, ["Take one tablet every morning"] + DRUGS[1:]), "absolute_terms", False)
case("every other night exempt", item(Q, ["Apply every other night"] + DRUGS[1:]), "absolute_terms", False)
case("trailing period overlap", item(Q, ["Elevated troponin.", "Elevated troponin and ST elevation.", "Normal ECG", "Bradycardia", "Hypotension"]), "overlapping_options", True)
case("crackles lemmatised", item("Examination shows bibasilar crackles and an S3. Which of the following is the most likely diagnosis?", ["Heart failure with pulmonary crackle", "Asthma", "Pneumothorax", "Pulmonary embolism", "Pericarditis"], "A"), "clang_cue", True)
case("matches lemmatised", item("The rash matches the distribution of the nerve. Which is the diagnosis?", ["Dermatomal match with zoster", "Cellulitis", "Contact dermatitis", "Erysipelas", "Impetigo"], "A"), "clang_cue", True)
case("key '(C)' parsed", {"stem": Q, "options": dict(zip("ABCDE", ["Aspirin", "Clopidogrel", "Aspirin and clopidogrel for twelve months", "Warfarin", "Heparin"])), "answer": "(C)"}, "longest_option_key", True)
case("key 'Option C' parsed", {"stem": Q, "options": dict(zip("ABCDE", ["Aspirin", "Clopidogrel", "Aspirin and clopidogrel for twelve months", "Warfarin", "Heparin"])), "answer": "Option C"}, "longest_option_key", True)
case("unreadable key disables key rules", {"stem": Q, "options": dict(zip("ABCDE", ["Aspirin", "Clopidogrel", "Aspirin and clopidogrel for twelve months", "Warfarin", "Heparin"])), "answer": "the third one"}, "longest_option_key", False)
case("who is not a candidate is not negative", item("A 70-year-old man who is not a candidate for surgery presents with dyspnea. Which of the following is the most appropriate next step?", DRUGS), "negative_stem", False)
case("least invasive counts as LEAST lead-in", item("Which of the following is the least invasive test that confirms the diagnosis?", DRUGS), "negative_stem", True)
fails = [(n, f, e, g) for n, f, e, g in T if e != g]
print("%d tests, %d failures" % (len(T), len(fails)))
for n, f, e, g in fails: print("  FAIL %-40s %-22s expected %s got %s" % (n, f, e, g))
