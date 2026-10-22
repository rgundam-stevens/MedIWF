"""Design-weighted precision and recall for the independent reader check (post hoc; amendment 7, addendum).

Each sampled item is weighted by its stratum's count in the 12,000 analysed main-corpus items divided by the stratum's sample
size; intervals by stratified bootstrap (2,000 resamples, seed 20261021).
Usage: python3 scripts/independent_check_weighted.py DATA_DIR outputs/independent_check/MedIWF_independent_check_ratings.csv
  DATA_DIR holds MedIWF_Dataset2_detector_flags_part1_main_corpus.csv (or the one-file Dataset 2, restricted here to run = full).
"""
import csv, sys, os, collections, random
csv.field_size_limit(10**9)
D, RATINGS = sys.argv[1], sys.argv[2]
RULES = ['longest_option_key', 'clang_cue', 'absolute_terms']
Q = {'longest_option_key': 'q1_longest', 'clang_cue': 'q2_repetition', 'absolute_terms': 'q3_absolute'}


def stratum(f):
    p = tuple(int(f[k]) for k in RULES); s = sum(p)
    if s == 0: return 'none'
    if s >= 2: return 'multi'
    return {0: 'longest_only', 1: 'clang_only', 2: 'absolute_only'}[p.index(1)]


flag_file = os.path.join(D, 'MedIWF_Dataset2_detector_flags_part1_main_corpus.csv')
if not os.path.exists(flag_file): flag_file = os.path.join(D, 'MedIWF_Dataset2_detector_flags.csv')
pop = collections.Counter(stratum(r) for r in csv.DictReader(open(flag_file, encoding='utf-8-sig')) if r.get('run', 'full') == 'full')
rows = []
for r in csv.DictReader(open(RATINGS, encoding='utf-8-sig')):
    rows.append((r['stratum'], {ru: int(r['detector_' + ru]) for ru in RULES},
                 {ru: int(r['reader1_' + Q[ru]] == 'yes' and r['reader2_' + Q[ru]] == 'yes') for ru in RULES}))
n_s = collections.Counter(s for s, _, _ in rows); w = {s: pop[s] / n_s[s] for s in n_s}
print('stratum populations:', dict(pop)); print('sample per stratum:', dict(n_s)); print('weights:', {s: round(v, 1) for s, v in w.items()})


def wpr(rows, ru):
    tp = sum(w[s] for s, d, c in rows if d[ru] and c[ru]); fp = sum(w[s] for s, d, c in rows if d[ru] and not c[ru])
    fn = sum(w[s] for s, d, c in rows if (not d[ru]) and c[ru])
    return (tp / (tp + fp) if tp + fp else float('nan')), (tp / (tp + fn) if tp + fn else float('nan'))


rng = random.Random(20261021)
by_s = collections.defaultdict(list)
for row in rows: by_s[row[0]].append(row)
for ru in RULES:
    p, r_ = wpr(rows, ru); ps, rs = [], []
    for _ in range(2000):
        samp = []
        for s, lst in by_s.items(): samp += [lst[rng.randrange(len(lst))] for _ in lst]
        a, b = wpr(samp, ru); ps.append(a); rs.append(b)
    ps.sort(); rs.sort()
    misses = [s for s, d, c in rows if (not d[ru]) and c[ru]]; fps = [s for s, d, c in rows if d[ru] and not c[ru]]
    print(f'{ru}: design-weighted precision {p:.2f} ({ps[50]:.2f} to {ps[1949]:.2f}), recall {r_:.2f} ({rs[50]:.2f} to {rs[1949]:.2f}); '
          f'consensus misses in strata {misses}; false positives in strata {fps}')
