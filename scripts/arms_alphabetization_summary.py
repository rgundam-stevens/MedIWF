"""Summaries from the paper's public data files (Datasets 2, 3, 5 and 6), added in October 2026: answer-key position by
alphabetization under each prompt; the LLM-NBME gap with and without the longest-option rule; the reasoning and guided-neutral
arms against their controls; the physicians' acceptability dichotomies; the LLM judges against the physicians on the published
composites, on shared criteria over the same items, and with each generator judge's own items excluded.

Usage: python3 scripts/arms_alphabetization_summary.py DATA_DIR
Prints every number with its definition so each can be traced. (Kappa intervals here are item-level bootstraps; the
intervals used in the paper are the cell-count bootstraps of scripts/kappa_reanalysis.py.)
"""
import csv, sys, os, random, collections, math
csv.field_size_limit(10**9)
D = sys.argv[1]
SEED = 20261021

def kappa(a, b):
    n = len(a); po = sum(1 for x, y in zip(a, b) if x == y) / n
    pa = sum(a) / n; pb = sum(b) / n; pe = pa * pb + (1 - pa) * (1 - pb)
    return float('nan') if pe == 1 else (po - pe) / (1 - pe)

def boot(fn, *cols, B=2000, seed=SEED):
    rng = random.Random(seed); n = len(cols[0]); vals = []
    for _ in range(B):
        idx = [rng.randrange(n) for _ in range(n)]
        v = fn(*[[c[i] for i in idx] for c in cols])
        if v == v: vals.append(v)
    vals.sort()
    return vals[int(0.025 * len(vals))], vals[int(0.975 * len(vals)) - 1]

def wilson(k, n, z=1.959964):
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h

def pct(k, n): return f'{100*k/n:.1f}% ({k}/{n})'

RULES14 = ['negative_stem','none_of_the_above','all_of_the_above','combination_options','fill_in_blank','true_false_stem',
           'longest_option_key','absolute_terms','vague_terms','clang_cue','grammatical_cue','nonparallel_options',
           'numeric_not_ordered','overlapping_options']

main = list(csv.DictReader(open(os.path.join(D, 'MedIWF_Dataset2_detector_flags_part1_main_corpus.csv'), encoding='utf-8-sig')))
arms = list(csv.DictReader(open(os.path.join(D, 'MedIWF_Dataset2_detector_flags_part2_arms.csv'), encoding='utf-8-sig')))
print('main corpus rows', len(main), '| arm rows', len(arms))

# ---- A. Key position and alphabetical ordering ----
print('\n== A. Answer-key position and alphabetical ordering (main corpus) ==')
for cond in ('plain', 'guided'):
    sub = [r for r in main if r['condition'] == cond]
    keyA = sum(r['key'] == 'A' for r in sub)
    alpha = [r for r in sub if r['options_not_alphabetical'] == '0']
    nonalpha = [r for r in sub if r['options_not_alphabetical'] == '1']
    print(f'{cond}: key at A pooled {pct(keyA, len(sub))}; alphabetized {pct(len(alpha), len(sub))}; '
          f'key at A among alphabetized {pct(sum(r["key"]=="A" for r in alpha), len(alpha))}; '
          f'among non-alphabetized {pct(sum(r["key"]=="A" for r in nonalpha), len(nonalpha))}')
    dist = collections.Counter(r['key'] for r in sub)
    print('   key distribution:', {k: f'{100*v/len(sub):.1f}' for k, v in sorted(dist.items())})
# per-model alphabetization under the guided prompt
g = [r for r in main if r['condition'] == 'guided']
bym = collections.defaultdict(list)
for r in g: bym[r['model_label']].append(r)
print('   guided, per model: alphabetized % / key at A %')
for m, rs in sorted(bym.items(), key=lambda kv: -sum(x['options_not_alphabetical']=='0' for x in kv[1])):
    a = sum(x['options_not_alphabetical']=='0' for x in rs); k = sum(x['key']=='A' for x in rs)
    print(f'     {m:18s} {100*a/len(rs):5.1f}  {100*k/len(rs):5.1f}')

# ---- B. The LLM-NBME gap: composite with and without the longest-option rule ----
print('\n== B. LLM-NBME gap with and without the longest-option rule ==')
plain = [r for r in main if r['condition'] == 'plain']
any14 = sum(r['any_flaw_14'] == '1' for r in plain)
any13 = sum(any(r[k] == '1' for k in RULES14 if k != 'longest_option_key') for r in plain)
lo = sum(r['longest_option_key'] == '1' for r in plain)
print(f'plain: any of 14 {pct(any14, len(plain))}; any of the other 13 {pct(any13, len(plain))}; longest option {pct(lo, len(plain))}')
nb = {(r['quantity'], r['name']): r['value'] for r in csv.DictReader(open(os.path.join(D, 'MedIWF_Dataset6_nbme_aggregate.csv'), encoding='utf-8-sig'))}
n_nb = int(nb[('n_items_five_option', '')]); any_nb = int(nb[('items_with_any_of_14_flaws', '')]); lo_nb = int(nb[('flaw_count', 'longest_option_key')])
print(f'NBME 5-option: any of 14 {pct(any_nb, n_nb)}; longest option {pct(lo_nb, n_nb)}; '
      f'(13-rule NBME rate is item-level and comes from the local file: 15.0% per Supplement 1)')
gap14 = 100*any14/len(plain) - 100*any_nb/n_nb
gap13 = 100*any13/len(plain) - 15.05
print(f'gap on 14 rules {gap14:.2f} points; gap on the other 13 rules {gap13:.2f} points (using NBME 15.05%); share removed {(gap14-gap13)/gap14:.3f}')
def oddsratio(a, na, b, nb_):  # a of na vs b of nb_
    return (a/(na-a)) / (b/(nb_-b))
print(f'unadjusted OR 14 rules: {oddsratio(any14, len(plain), any_nb, n_nb):.2f}; 13 rules: {oddsratio(any13, len(plain), 79, 525):.2f} (NBME 79/525 assumed = 15.05%)')

# ---- C. Reasoning arm and guided-neutral arm ----
print('\n== C. Reasoning arm and guided-neutral arm ==')
reas = [r for r in arms if r['run'] == 'full_reasoning']
models4 = sorted(set(r['model_label'] for r in reas))
base4 = [r for r in main if r['model_label'] in models4]
print('reasoning arm models:', models4)
for cond in ('plain', 'guided', 'both'):
    a = [r for r in reas if cond == 'both' or r['condition'] == cond]
    b = [r for r in base4 if cond == 'both' or r['condition'] == cond]
    print(f'  {cond}: any flaw with reasoning {pct(sum(r["any_flaw_14"]=="1" for r in a), len(a))} vs. without (main corpus, same models) {pct(sum(r["any_flaw_14"]=="1" for r in b), len(b))}; '
          f'key at A {pct(sum(r["key"]=="A" for r in a), len(a))} vs. {pct(sum(r["key"]=="A" for r in b), len(b))}')
for m in models4:
    for cond in ('plain', 'guided'):
        a = [r for r in reas if r['model_label']==m and r['condition']==cond]; b = [r for r in base4 if r['model_label']==m and r['condition']==cond]
        print(f'     {m:16s} {cond:6s} any flaw {100*sum(r["any_flaw_14"]=="1" for r in a)/len(a):5.1f} vs {100*sum(r["any_flaw_14"]=="1" for r in b)/len(b):5.1f}; key A {100*sum(r["key"]=="A" for r in a)/len(a):5.1f} vs {100*sum(r["key"]=="A" for r in b)/len(b):5.1f}')
gn = [r for r in arms if r['condition'] == 'guided_neutral']
pn = [r for r in arms if r['condition'] == 'plain_neutral']
pr = [r for r in arms if r['condition'] == 'plain_rotated']
gd = [r for r in main if r['condition'] == 'guided']
print(f'  guided-neutral: any flaw {pct(sum(r["any_flaw_14"]=="1" for r in gn), len(gn))} vs guided (standard template) {pct(sum(r["any_flaw_14"]=="1" for r in gd), len(gd))}; '
      f'key at A {pct(sum(r["key"]=="A" for r in gn), len(gn))} vs {pct(sum(r["key"]=="A" for r in gd), len(gd))}')
print(f'  plain-neutral: any flaw {pct(sum(r["any_flaw_14"]=="1" for r in pn), len(pn))}; key at A {pct(sum(r["key"]=="A" for r in pn), len(pn))}; '
      f'plain-rotated: any flaw {pct(sum(r["any_flaw_14"]=="1" for r in pr), len(pr))}; key at A {pct(sum(r["key"]=="A" for r in pr), len(pr))}')
print(f'  guided-neutral vs plain-neutral unadjusted OR {oddsratio(sum(r["any_flaw_14"]=="1" for r in gn), len(gn), sum(r["any_flaw_14"]=="1" for r in pn), len(pn)):.2f}')
runs = collections.Counter(r['run'] for r in arms)
print('  arm item counts by run:', dict(runs), '| arms total excluding stability:', sum(v for k, v in runs.items() if k != 'stability'))

# ---- D. Physicians: acceptability dichotomies ----
print('\n== D. Physician ratings: acceptability dichotomizations ==')
rat = list(csv.DictReader(open(os.path.join(D, 'MedIWF_Dataset3_physician_ratings.csv'), encoding='utf-8-sig')))
R = {}
for r in rat: R.setdefault(r['rater'], {})[r['item_id']] = r
items = sorted(R['R1'])
assert len(items) == 100 and set(items) == set(R['R2'])
def col(rater, f): return [f(R[rater][i]) for i in items]
for label, f in (('q5 = no', lambda r: int(r['q5'] == 'no')), ('q5 = no or minor edits (not yes)', lambda r: int(r['q5'] != 'yes'))):
    a, b = col('R1', f), col('R2', f)
    lo_, hi_ = boot(kappa, a, b)
    print(f'  {label}: R1 {sum(a)} (Wilson {", ".join(f"{100*x:.1f}" for x in wilson(sum(a),100))}), R2 {sum(b)} (Wilson {", ".join(f"{100*x:.1f}" for x in wilson(sum(b),100))}); kappa {kappa(a,b):.2f} ({lo_:.2f}-{hi_:.2f})')
print('  q5 values R1:', collections.Counter(r['q5'] for r in R['R1'].values()), 'R2:', collections.Counter(r['q5'] for r in R['R2'].values()))
def composite(r): return int(r['q1'] in ('no', 'unsure') or r['q2'] == 'no' or r['q3'] == 'no' or r['q5'] == 'no')
a, b = col('R1', composite), col('R2', composite); lo_, hi_ = boot(kappa, a, b)
print(f'  composite (published definition): R1 {sum(a)}, R2 {sum(b)}, both {sum(x and y for x,y in zip(a,b))}; kappa {kappa(a,b):.2f} ({lo_:.2f}-{hi_:.2f})')
print('  q1 values R1:', collections.Counter(r['q1'] for r in R['R1'].values()), 'R2:', collections.Counter(r['q1'] for r in R['R2'].values()))
print('  q2 values R1:', collections.Counter(r['q2'] for r in R['R1'].values()), 'R2:', collections.Counter(r['q2'] for r in R['R2'].values()))
print('  q3 values R1:', collections.Counter(r['q3'] for r in R['R1'].values()), 'R2:', collections.Counter(r['q3'] for r in R['R2'].values()))

# ---- E. Judges vs physicians: published composite, shared-criteria composite, own items excluded ----
print('\n== E. LLM judges on the physician-rated items ==')
jud = list(csv.DictReader(open(os.path.join(D, 'MedIWF_Dataset5_llm_judge_verdicts_part2_physician100.csv'), encoding='utf-8-sig')))
key = {r['item_id']: r for r in csv.DictReader(open(os.path.join(D, 'MedIWF_Dataset3_item_key.csv'), encoding='utf-8-sig'))}
JUDGES = {'openai/gpt-5.4-mini': ('GPT-5.4 Mini', None), 'google/gemini-3.1-pro-preview': ('Gemini 3.1 Pro', 'Gemini 3.1 Pro'),
          'anthropic/claude-fable-5.1': ('Claude Fable 5.1', 'Claude Fable 5.1'), 'openai/gpt-6-astra': ('GPT-6 Astra', 'GPT-6 Astra')}
V = collections.defaultdict(dict)  # (judge, reasoning) -> item -> {rule: fail}
for r in jud:
    V[(r['judge'], r['reasoning_requested'])].setdefault(r['uid'], {})[r['rule']] = (r['verdict_fail'] == 'True')
CONTENT4 = ['single_best_answer', 'plausible_distractors', 'no_extraneous_info', 'focused_stem']
rules_seen = collections.Counter(r['rule'] for r in jud); print('  rules in file:', dict(rules_seen))
CONTENT4 = [x for x in rules_seen if x in ('single_best_answer', 'plausible_distractors') or 'extraneous' in x or 'focused' in x]
print('  4 content rules used:', CONTENT4)
SHARED = ['single_best_answer', 'plausible_distractors']
def phys_shared(r): return int(r['q1'] in ('no', 'unsure') or r['q2'] == 'no')
def phys_sba(r): return int(r['q1'] in ('no', 'unsure'))
for (judge, reas_), verdicts in sorted(V.items()):
    name, gen = JUDGES[judge]
    for setname, rules, pf in (('published composite (4 judge rules vs physician composite)', CONTENT4, composite),
                                ('shared criteria (single best answer or implausible distractor, both sides)', SHARED, phys_shared),
                                ('single best answer only', ['single_best_answer'], phys_sba)):
        ev = [i for i in items if all(k in verdicts.get(i, {}) for k in rules)]
        j = [int(any(verdicts[i][k] for k in rules)) for i in ev]
        out = []
        for rater in ('R1', 'R2'):
            p = [pf(R[rater][i]) for i in ev]; lo_, hi_ = boot(kappa, j, p)
            out.append(f'vs {rater} kappa {kappa(j,p):.2f} ({lo_:.2f}-{hi_:.2f})')
        p1 = [pf(R['R1'][i]) for i in ev]; p2 = [pf(R['R2'][i]) for i in ev]; lo_, hi_ = boot(kappa, p1, p2)
        line = f'  {name} (reasoning requested: {reas_}) [{setname}] n={len(ev)}, judge flags {sum(j)}: ' + '; '.join(out) + f' | raters with each other on these items: kappa {kappa(p1,p2):.2f} ({lo_:.2f}-{hi_:.2f}); R1 {sum(p1)}, R2 {sum(p2)}'
        print(line)
        if gen:
            ev2 = [i for i in ev if key[i]['model'] != gen]
            j2 = [int(any(verdicts[i][k] for k in rules)) for i in ev2]
            out2 = []
            for rater in ('R1', 'R2'):
                p = [pf(R[rater][i]) for i in ev2]; lo_, hi_ = boot(kappa, j2, p)
                out2.append(f'vs {rater} kappa {kappa(j2,p):.2f} ({lo_:.2f}-{hi_:.2f})')
            print(f'      own items excluded ({len(ev)-len(ev2)} items by {gen}; n={len(ev2)}): ' + '; '.join(out2))
