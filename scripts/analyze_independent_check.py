"""Analyse the independent reader check against the detector.

Usage:
  python3 -I analyze_independent_check.py KEY.csv readerA.xlsx readerB.xlsx [--unsure no|yes|drop]

KEY.csv is independent_check_key_DO_NOT_SEND.csv (item_id, detector flags).
Each reader file is the returned rating sheet (sheet "ratings", columns I, J, K = Q1, Q2, Q3).

Reports, for each rule: counts per reader; Cohen's kappa between readers; the detector's agreement with
each reader and with the reader consensus (both say yes); the detector's precision and recall against the
consensus and against "either reader says yes"; 95% bootstrap intervals (2,000 resamples, seed 20261021).
"unsure" is treated as "no" by default; --unsure yes or --unsure drop give the sensitivity analyses.
The sample is enriched for flagged items, so prevalence cannot be read from it.
"""
import csv, sys, random
from openpyxl import load_workbook

RULES = [('longest_option_key', 'Q1 longest option', 8), ('clang_cue', 'Q2 word repetition', 9), ('absolute_terms', 'Q3 absolute terms', 10)]

def kappa(a, b):
    n = len(a)
    if n == 0: return float('nan')
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    pa1 = sum(a) / n; pb1 = sum(b) / n
    pe = pa1 * pb1 + (1 - pa1) * (1 - pb1)
    return float('nan') if pe == 1 else (po - pe) / (1 - pe)

def prec_rec(pred, truth):
    tp = sum(1 for p, t in zip(pred, truth) if p and t)
    fp = sum(1 for p, t in zip(pred, truth) if p and not t)
    fn = sum(1 for p, t in zip(pred, truth) if (not p) and t)
    prec = tp / (tp + fp) if tp + fp else float('nan')
    rec = tp / (tp + fn) if tp + fn else float('nan')
    return prec, rec

def boot(fn, *cols, B=2000, seed=20261021):
    rng = random.Random(seed); n = len(cols[0]); vals = []
    for _ in range(B):
        idx = [rng.randrange(n) for _ in range(n)]
        v = fn(*[[c[i] for i in idx] for c in cols])
        if v == v: vals.append(v)
    vals.sort()
    return (vals[int(0.025 * len(vals))], vals[int(0.975 * len(vals)) - 1]) if vals else (float('nan'), float('nan'))

def read_sheet(path):
    ws = load_workbook(path, data_only=True)['ratings']
    out = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row or not row[0]: continue
        out[str(row[0]).strip()] = [str(row[c]).strip().lower() if row[c] is not None else '' for c in (8, 9, 10)]
    return out

def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    unsure = 'no'
    if '--unsure' in sys.argv: unsure = sys.argv[sys.argv.index('--unsure') + 1]
    key_path, a_path, b_path = args[:3]
    key = {r['item_id']: r for r in csv.DictReader(open(key_path, encoding='utf-8'))}
    A = read_sheet(a_path); B = read_sheet(b_path)
    ids = [i for i in key if i in A and i in B]
    print(f'items with both readers: {len(ids)} of {len(key)}; unsure treated as: {unsure}')
    def code(v):
        if v == 'yes': return 1
        if v == 'no': return 0
        if v == 'unsure': return {'no': 0, 'yes': 1, 'drop': None}[unsure]
        return None
    for rule, label, _ in RULES:
        qi = [r for r, _, _ in RULES].index(rule)
        rows = [(int(key[i][rule]), code(A[i][qi]), code(B[i][qi])) for i in ids]
        missing = sum(1 for d, a, b in rows if a is None or b is None)
        rows = [(d, a, b) for d, a, b in rows if a is not None and b is not None]
        d = [r[0] for r in rows]; a = [r[1] for r in rows]; b = [r[2] for r in rows]
        cons = [int(x and y) for x, y in zip(a, b)]; either = [int(x or y) for x, y in zip(a, b)]
        print(f'\n== {label} (n={len(rows)}; dropped/blank {missing}) ==')
        print(f'  detector yes {sum(d)}; reader A yes {sum(a)}; reader B yes {sum(b)}; both yes {sum(cons)}; either yes {sum(either)}')
        k_ab = kappa(a, b); lo, hi = boot(kappa, a, b)
        print(f'  kappa reader A vs B: {k_ab:.2f} ({lo:.2f} to {hi:.2f})')
        for name, r in (('reader A', a), ('reader B', b), ('consensus (both yes)', cons), ('either reader yes', either)):
            k = kappa(d, r); lo, hi = boot(kappa, d, r)
            agree = sum(1 for x, y in zip(d, r) if x == y) / len(d)
            p, rc = prec_rec(d, r); plo, phi = boot(lambda x, y: prec_rec(x, y)[0], d, r); rlo, rhi = boot(lambda x, y: prec_rec(x, y)[1], d, r)
            print(f'  detector vs {name}: raw agreement {agree:.2f}; kappa {k:.2f} ({lo:.2f} to {hi:.2f}); precision {p:.2f} ({plo:.2f} to {phi:.2f}); recall {rc:.2f} ({rlo:.2f} to {rhi:.2f})')

if __name__ == '__main__':
    main()
