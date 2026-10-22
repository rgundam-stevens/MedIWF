"""Cohen's kappa with the repository's method (src/mediwf/stats.py: kappa_from_table, kappa_ci: percentile bootstrap of the
2x2 cell counts, 2,000 multinomial resamples, seed 20260921) for the analyses added in October 2026.

Usage: python3 scripts/kappa_reanalysis.py DATA_DIR [READER_CHECK_RATINGS.csv]
  DATA_DIR holds the paper's data files (MedIWF_Dataset3_physician_ratings.csv, MedIWF_Dataset3_item_key.csv,
  MedIWF_Dataset5_llm_judge_verdicts_part2_physician100.csv); the optional second argument is
  outputs/independent_check/MedIWF_independent_check_ratings.csv.
Covers: the physicians' acceptability dichotomies (q5 "no" vs other; q5 not "yes"); the LLM judges against the physicians on
the published composites, on the shared criteria (single best answer or implausible distractor) over the same items, and
with each generator judge's own items excluded; the independent reader check (3 rules, "unsure" as "no").
"""
import csv, sys, os, collections
import numpy as np
csv.field_size_limit(10**9)
D = sys.argv[1]

def kappa_from_table(tp, fp, fn, tn):
    n = tp + fp + fn + tn
    if n == 0: return float("nan")
    po = (tp + tn) / n; pe = ((tp + fp) * (tp + fn) + (fn + tn) * (fp + tn)) / (n * n)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")

def kappa_ci(tp, fp, fn, tn, B=2000, seed=20260921):
    n = tp + fp + fn + tn
    if n == 0: return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    draws = rng.multinomial(n, [tp / n, fp / n, fn / n, tn / n], size=B)
    ks = np.array([kappa_from_table(*d) for d in draws], dtype=float)
    ks = ks[np.isfinite(ks)]
    if len(ks) < B // 2: return float("nan"), float("nan")
    return float(np.percentile(ks, 2.5)), float(np.percentile(ks, 97.5))

def table(pred, truth):
    tp = sum(1 for p, t in zip(pred, truth) if p and t); fp = sum(1 for p, t in zip(pred, truth) if p and not t)
    fn = sum(1 for p, t in zip(pred, truth) if (not p) and t); tn = len(pred) - tp - fp - fn
    return tp, fp, fn, tn

def fmt(pred, truth):
    t = table(pred, truth); k = kappa_from_table(*t); lo, hi = kappa_ci(*t)
    tp, fp, fn, tn = t
    prec = tp / (tp + fp) if tp + fp else float('nan'); rec = tp / (tp + fn) if tp + fn else float('nan')
    return f'kappa {k:.2f} ({lo:.2f} to {hi:.2f}) [tp {tp} fp {fp} fn {fn} tn {tn}; precision {prec:.2f} recall {rec:.2f}]'

rat = list(csv.DictReader(open(os.path.join(D, 'MedIWF_Dataset3_physician_ratings.csv'), encoding='utf-8-sig')))
R = {}
for r in rat: R.setdefault(r['rater'], {})[r['item_id']] = r
items = sorted(R['R1'])
print('== Physicians: acceptability dichotomies')
for label, f in (("q5 = 'no' (counts 11 vs 8)", lambda r: r['q5'] == 'no'), ("q5 not 'yes' (counts 13 vs 24)", lambda r: r['q5'] != 'yes')):
    print(' ', label, fmt([f(R['R1'][i]) for i in items], [f(R['R2'][i]) for i in items]))
def composite(r): return r['q1'] in ('no', 'unsure') or r['q2'] == 'no' or r['q3'] == 'no' or r['q5'] == 'no'
def shared(r): return r['q1'] in ('no', 'unsure') or r['q2'] == 'no'
def sba(r): return r['q1'] in ('no', 'unsure')
print('  composite, raters:', fmt([composite(R['R1'][i]) for i in items], [composite(R['R2'][i]) for i in items]))

print('\n== Judges vs physicians (reasoning not requested unless stated)')
jud = list(csv.DictReader(open(os.path.join(D, 'MedIWF_Dataset5_llm_judge_verdicts_part2_physician100.csv'), encoding='utf-8-sig')))
key = {r['item_id']: r for r in csv.DictReader(open(os.path.join(D, 'MedIWF_Dataset3_item_key.csv'), encoding='utf-8-sig'))}
V = collections.defaultdict(dict)
for r in jud: V[(r['judge'], r['reasoning_requested'])].setdefault(r['uid'], {})[r['rule']] = (r['verdict_fail'] == 'True')
NAMES = {'openai/gpt-5.4-mini': ('GPT-5.4 Mini', None), 'google/gemini-3.1-pro-preview': ('Gemini 3.1 Pro', 'Gemini 3.1 Pro'),
         'anthropic/claude-fable-5.1': ('Claude Fable 5.1', 'Claude Fable 5.1'), 'openai/gpt-6-astra': ('GPT-6 Astra', 'GPT-6 Astra')}
C4 = ['single_best_answer', 'plausible_distractors', 'no_extraneous_info', 'focused_stem']
for (judge, reas), verd in sorted(V.items()):
    name, gen = NAMES[judge]
    for setname, rules, pf in (('published composites', C4, composite), ('shared criteria', ['single_best_answer', 'plausible_distractors'], shared), ('single best answer', ['single_best_answer'], sba)):
        ev = [i for i in items if all(k in verd.get(i, {}) for k in rules)]
        j = [any(verd[i][k] for k in rules) for i in ev]
        print(f'  {name}, reasoning {reas}, {setname}, n={len(ev)}, judge flags {sum(j)}:')
        for rn in ('R1', 'R2'): print(f'      vs {rn}: ' + fmt(j, [pf(R[rn][i]) for i in ev]))
        print('      raters with each other on these items: ' + fmt([pf(R['R1'][i]) for i in ev], [pf(R['R2'][i]) for i in ev]))
        if gen:
            ev2 = [i for i in ev if key[i]['model'] != gen]; j2 = [any(verd[i][k] for k in rules) for i in ev2]
            for rn in ('R1', 'R2'): print(f'      own items excluded (n={len(ev2)}) vs {rn}: ' + fmt(j2, [pf(R[rn][i]) for i in ev2]))

print('\n== Reader check (unsure as no), repository method for the kappa intervals')
rc_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(D, 'MedIWF_independent_check_ratings.csv')
rc = list(csv.DictReader(open(rc_path, encoding='utf-8-sig')))
for det, q, label in (('detector_longest_option_key', 'q1_longest', 'longest option'), ('detector_clang_cue', 'q2_repetition', 'word repetition'), ('detector_absolute_terms', 'q3_absolute', 'absolute terms')):
    d = [r[det] == '1' for r in rc]; a = [r['reader1_' + q] == 'yes' for r in rc]; b = [r['reader2_' + q] == 'yes' for r in rc]
    cons = [x and y for x, y in zip(a, b)]
    print(f'  {label}: readers with each other ' + fmt(a, b))
    print(f'      detector vs consensus ' + fmt(d, cons))
    print(f'      detector vs reader 1 ' + fmt(d, a)); print(f'      detector vs reader 2 ' + fmt(d, b))
