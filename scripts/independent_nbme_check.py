#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
independent_nbme_check.py -- independent re-computation of every NBME-dependent number in the MedIWF manuscript and
Supplement 1, with code written separately from the analysis scripts and without access to the NBME files.

The NBME/BEA 2024 item files are under a data-use agreement and were not available when this script was written. It is
meant to be run on the machine that holds them. It re-reads the three Excel files, runs the released detector
(src/mediwf/detector.py, v1.2; and v1.0/v1.1 for the version history), and recomputes the statistics with its own code.

WHAT IT PRINTS: aggregates only -- counts, proportions with Wilson intervals, medians, chi-square, regression coefficients
with robust standard errors, P and Benjamini-Hochberg q values, group means. It never prints item text, item numbers,
the key of an individual item or any other per-item value. Group means are suppressed for groups of fewer than
--min-group items (default 5; the minimum allowed is 5) and single-flaw regressions need at least --min-flagged flagged
and unflagged items (default 10, as in the author's script). Dictionaries of counts are printed in alphabetical order.
As a last safeguard, every printed line is checked against the NBME stems and options (strings of 12 or more characters)
and the script stops if one would be printed.

WHAT IT WRITES: nothing. sys.dont_write_bytecode is set before the detector package is imported, so no __pycache__
folder is created; no plot, cache or output file is written. (Redirecting the console output to a file is up to you.)

REQUIREMENTS: Python >= 3.9, numpy, pandas, openpyxl. No scipy, no statsmodels, no network. The normal, t and chi-square
tail probabilities, the logistic regression (Newton-Raphson/IRLS), OLS with HC1 errors, Wilson intervals and the
Benjamini-Hochberg adjustment are implemented below.

USAGE (from the MedIWF project root):
    python3 -B scripts/independent_nbme_check.py  data/nbme/train_final.xlsx  data/nbme/test_final.xlsx  data/nbme/gold_final.xlsx \
            src  outputs/flags_full.csv  --llm-items data/generated/items_full.jsonl  > outputs/independent_nbme_check_output.txt
  * The 5th argument may also be Dataset 2 (MedIWF_Dataset2_detector_flags.csv); rows with run != "full" are dropped
    (Dataset 2 also holds the stability re-run, whose 240 plain rows would otherwise be counted).
  * --llm-items (data/generated/items_full.jsonl[.gz] or Dataset 1 MedIWF_Dataset1_items_full.csv) is needed for the
    option-length spread (CV) adjustments, the longest-option threshold sweep and the LLM side of the absolute-terms
    audit. Without it, mean option length of the LLM items is approximated from key_chars and mean_distractor_chars.
  * Options: --min-group N (>=5), --min-flagged N (>=5).

COLUMN NAMES ASSUMED (and where they come from):
  train_final.xlsx and test_final.xlsx: ItemNum, ItemStem_Text, Answer__A ... Answer__J (double underscore), Answer_Key,
  ItemType ("Text" / "PIX"), EXAM (levels including "STEP 1"); train_final.xlsx also Difficulty and Response_Time;
  gold_final.xlsx: ItemNum, Difficulty, Response_Time; test is joined to gold on ItemNum (inner join).
  Sources: scripts/detect.py run_nbme() lines 62-81 (file names, merge on ItemNum, Answer__{L} for L in A-J,
  ItemStem_Text, Answer_Key, EXAM, ItemType, Difficulty, Response_Time); scripts/inspect_nbme.py line 11;
  scripts/nbme_psychometrics.py lines 14 and 30 ("Text", "STEP 1"); Yaneva et al. 2024 (BEA 2024 findings paper, section
  3), which lists ItemNum, ItemStem_Text, Answer_A ... Answer_J (single underscore), Answer_Key, Answer_Text, ItemType,
  EXAM, Difficulty, Response_Time. Because the paper and the code disagree on the underscore, the script accepts either
  "Answer__A" or "Answer_A" and says which it found. If gold_final.xlsx repeats test columns, test values are kept and
  gold values fill gaps.
"""
import sys
sys.dont_write_bytecode = True          # importing the detector must not create __pycache__ folders (no file writes)

import argparse
import collections
import csv
import datetime
import gzip
import json
import math
import os
import re
import statistics
from decimal import Decimal, ROUND_HALF_UP

import numpy as np
import pandas as pd

# ------------------------------------------------------------------------------------------------ rule sets (own copy)
CORE = ["negative_stem", "none_of_the_above", "all_of_the_above", "combination_options", "fill_in_blank", "true_false_stem",
        "longest_option_key", "absolute_terms", "vague_terms", "clang_cue", "grammatical_cue", "nonparallel_options",
        "numeric_not_ordered", "overlapping_options"]
FEATURES = ["option_length_outlier", "options_not_alphabetical", "numeric_units_inconsistent"]
VALIDATED = ["negative_stem", "none_of_the_above", "all_of_the_above", "combination_options", "fill_in_blank",
             "absolute_terms", "vague_terms", "clang_cue", "grammatical_cue", "numeric_not_ordered"]
POOR_AGREEMENT = ["absolute_terms", "vague_terms", "grammatical_cue"]
SENS11 = [r for r in CORE if r not in POOR_AGREEMENT]
CUEING = ["longest_option_key", "absolute_terms", "clang_cue", "grammatical_cue"]
LEGACY6 = ["longest_option_key", "absolute_terms", "clang_cue", "grammatical_cue", "nonparallel_options", "overlapping_options"]
AUTHOR_SINGLE = ["longest_option_key", "absolute_terms", "clang_cue", "grammatical_cue", "nonparallel_options",
                 "overlapping_options", "option_length_outlier", "options_not_alphabetical"]   # nbme_psychometrics.py l.17-18
LETTERS = "ABCDEFGHIJ"
Z = 1.96                                 # the author's code uses 1.96 for every Wald interval and for Wilson


# ------------------------------------------------------------------------------------------------ guarded printing
class Printer:
    def __init__(self):
        self.forbidden = []
        self.lines = 0

    def forbid(self, texts):
        for t in texts:
            t = str(t).strip()
            if len(t) >= 12:
                self.forbidden.append(t)

    def __call__(self, *args):
        line = " ".join(str(a) for a in args)
        for t in self.forbidden:
            if t in line:
                raise SystemExit("STOPPED: a line about to be printed contains NBME item text; nothing further printed.")
        print(line, flush=True)
        self.lines += 1


P = Printer()


# ------------------------------------------------------------------------------------------------ distributions
_FPMIN = 1e-300


def norm_sf(x):
    return 0.5 * math.erfc(x / math.sqrt(2.0))


def _betacf(a, b, x):
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > _FPMIN else _FPMIN)
    h = d
    for m in range(1, 1000):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > _FPMIN else _FPMIN)
        c = 1.0 + aa / c
        c = c if abs(c) > _FPMIN else _FPMIN
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > _FPMIN else _FPMIN)
        c = 1.0 + aa / c
        c = c if abs(c) > _FPMIN else _FPMIN
        de = d * c
        h *= de
        if abs(de - 1.0) < 1e-15:
            break
    return h


def betainc_reg(a, b, x):
    """Regularized incomplete beta I_x(a, b) (continued fraction, Numerical Recipes 6.4)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbt = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log1p(-x)
    if x < (a + 1.0) / (a + b + 2.0):
        return math.exp(lbt) * _betacf(a, b, x) / a
    return 1.0 - math.exp(lbt) * _betacf(b, a, 1.0 - x) / b


def t_sf(t, df):
    """P(T > t) for Student's t with df degrees of freedom."""
    if df <= 0 or not math.isfinite(df):
        return norm_sf(t)
    x = df / (df + t * t)
    tail = 0.5 * betainc_reg(df / 2.0, 0.5, x)
    return tail if t >= 0 else 1.0 - tail


def chi2_sf(x, k):
    """P(X > x) for a chi-square with k degrees of freedom (regularized upper incomplete gamma)."""
    if x <= 0:
        return 1.0
    a, y = k / 2.0, x / 2.0
    lpre = -y + a * math.log(y) - math.lgamma(a)
    if y < a + 1.0:
        ap, s, d = a, 1.0 / a, 1.0 / a
        for _ in range(10000):
            ap += 1.0
            d *= y / ap
            s += d
            if abs(d) < abs(s) * 1e-16:
                break
        return max(0.0, 1.0 - math.exp(lpre) * s)
    b = y + 1.0 - a
    c, d = 1.0 / _FPMIN, 1.0 / b
    h = d
    for i in range(1, 10000):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        d = 1.0 / (d if abs(d) > _FPMIN else _FPMIN)
        c = b + an / c
        c = c if abs(c) > _FPMIN else _FPMIN
        de = d * c
        h *= de
        if abs(de - 1.0) < 1e-16:
            break
    return math.exp(lpre) * h


# ------------------------------------------------------------------------------------------------ estimators
def wilson(k, n, z=Z):
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    p = k / n
    d = 1.0 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4.0 * n * n)) / d
    return p, max(0.0, c - h), min(1.0, c + h)


def bh(pvals):
    p = np.asarray(pvals, float)
    m = len(p)
    if m == 0:
        return np.array([])
    order = np.argsort(p)
    q = np.empty(m)
    running = 1.0
    for rank in range(m, 0, -1):
        i = order[rank - 1]
        running = min(running, p[i] * m / rank)
        q[i] = running
    return q


def ols_hc1(X, y):
    n, k = X.shape
    if np.linalg.matrix_rank(X) < k:
        raise ValueError("design matrix is rank deficient")
    xtx_inv = np.linalg.inv(X.T @ X)
    beta = xtx_inv @ (X.T @ y)
    e = y - X @ beta
    meat = (X * (e ** 2)[:, None]).T @ X
    V = (n / (n - k)) * (xtx_inv @ meat @ xtx_inv)
    se = np.sqrt(np.diag(V))
    tt = beta / se
    pv = np.array([2.0 * t_sf(abs(v), n - k) for v in tt])
    sst = float(((y - y.mean()) ** 2).sum())
    r2 = 1.0 - float(e @ e) / sst if sst > 0 else float("nan")
    return beta, se, tt, pv, r2, n - k


def _expit(v):
    return 1.0 / (1.0 + np.exp(-v))


def logit_fit(X, y, max_iter=200, tol=1e-10):
    """Maximum likelihood by Newton-Raphson (= IRLS) with step halving. Returns beta, inverse information, converged."""
    n, k = X.shape
    beta = np.zeros(k)

    def loglik(b):
        eta = X @ b
        return float(np.sum(y * eta - np.logaddexp(0.0, eta)))
    ll = loglik(beta)
    converged = False
    for _ in range(max_iter):
        mu = _expit(X @ beta)
        W = mu * (1.0 - mu)
        info = (X * W[:, None]).T @ X
        step = np.linalg.solve(info, X.T @ (y - mu))
        s = 1.0
        while True:
            cand = beta + s * step
            ll_c = loglik(cand)
            if ll_c >= ll - 1e-12 or s < 1e-6:
                break
            s /= 2.0
        beta, ll = cand, ll_c
        if np.max(np.abs(s * step)) < tol:
            converged = True
            break
    mu = _expit(X @ beta)
    info = (X * (mu * (1.0 - mu))[:, None]).T @ X
    return beta, np.linalg.inv(info), converged


def logit_robust(X, y, clusters=None):
    """Sandwich covariance. clusters=None: HC1 (each item its own cluster, factor n/(n-k)); otherwise Liang-Zeger with
    factor G/(G-1)*(n-1)/(n-k), as in the author's stats.cluster_robust_cov."""
    beta, bread, conv = logit_fit(X, y)
    n, k = X.shape
    S = (y - _expit(X @ beta))[:, None] * X
    if clusters is None:
        meat = S.T @ S
        V = (n / (n - k)) * (bread @ meat @ bread)
    else:
        sums = collections.OrderedDict()
        for c, s in zip(clusters, S):
            sums[c] = sums.get(c, 0.0) + s
        G = len(sums)
        meat = sum(np.outer(v, v) for v in sums.values())
        V = (G / (G - 1.0)) * ((n - 1.0) / (n - k)) * (bread @ meat @ bread)
    return beta, np.sqrt(np.diag(V)), conv


# ------------------------------------------------------------------------------------------------ formatting helpers
def half_up(x, nd):
    q = Decimal(1).scaleb(-nd)
    return float(Decimal(repr(float(x))).quantize(q, rounding=ROUND_HALF_UP))


def sig_round(x, s):
    if x == 0 or not math.isfinite(x):
        return x
    nd = s - 1 - int(math.floor(math.log10(abs(x))))
    return half_up(x, nd)


def fp(x, s=4):
    """P value / q value with s significant digits."""
    if x is None or not math.isfinite(x):
        return "nan"
    if x < 1e-4:
        return "%.3e" % x
    return ("%." + str(max(s - 1 - int(math.floor(math.log10(x))), 0)) + "f") % sig_round(x, s)


def pct(k, n, nd=3):
    p, lo, hi = wilson(k, n)
    return "%4d/%-4d %s%% [%s, %s]" % (k, n, ("%." + str(nd) + "f") % (100 * p), ("%." + str(nd) + "f") % (100 * lo),
                                    ("%." + str(nd) + "f") % (100 * hi))


# ------------------------------------------------------------------------------------------------ self-check registry
CHECKS = []


def check(label, computed, expected, nd=None, sig=None, source=""):
    """Compare a computed value with the value printed in the manuscript/logs at the printed precision (half up)."""
    if isinstance(expected, bool):
        ok = (bool(computed) == expected)
        shown = str(bool(computed))
    elif computed is None or (isinstance(computed, float) and not math.isfinite(computed)):
        ok, shown = False, "not computed"
    else:
        if sig is not None:
            r = sig_round(float(computed), sig)
        else:
            r = half_up(float(computed), nd or 0)
        ok = abs(r - float(expected)) < 1e-9
        shown = repr(round(float(computed), 6))
    CHECKS.append((label, ok, shown, expected, source))


# ------------------------------------------------------------------------------------------------ loading helpers
def cell_text(v, tally):
    """Excel cell -> option text, mirroring scripts/detect.py _cell_text(); conversions are tallied (counts only)."""
    if v is None:
        return ""
    try:
        if pd.isna(v):
            return ""
    except (TypeError, ValueError):
        pass
    if isinstance(v, datetime.datetime):                  # includes pandas.Timestamp
        tally["date cells written back as month-day"] += 1
        return "%d-%d" % (v.month, v.day)
    if isinstance(v, (datetime.date, datetime.time)):
        tally["date/time cells kept as text"] += 1
        return str(v).strip()
    if isinstance(v, (bool, np.bool_)):
        tally["boolean cells"] += 1
        return str(v).strip()
    if isinstance(v, (int, np.integer)):
        tally["integer-valued numeric cells"] += 1
        return str(int(v))
    if isinstance(v, (float, np.floating)):
        if float(v).is_integer():
            tally["integer-valued numeric cells"] += 1
            return str(int(v))
        tally["non-integer numeric cells"] += 1
        return str(v).strip()
    return str(v).strip()


def to_float(v):
    try:
        f = float(v)
        return f if math.isfinite(f) else float("nan")
    except (TypeError, ValueError):
        return float("nan")


def legacy_cell_text(v):
    """Emulation of the v1.0 loader described in docs/detector_changelog.md: non-text cells were treated as missing."""
    return v.strip() if isinstance(v, str) else ""


def find_option_pattern(columns):
    for pat in ("Answer__%s", "Answer_%s"):
        if any((pat % L) in columns for L in LETTERS):
            return pat
    raise SystemExit("No option columns (Answer__A ... or Answer_A ...) found. Columns: %s" % list(columns))


def has_leadin(stem):
    """Re-implementation of scripts/analyze_leadin.py has_leadin() (the author's definition of a posed question)."""
    s = " ".join(str(stem or "").split())
    unfinished = not re.search(r"[.!?:]$", s)
    lead = re.search(r"(?:^|[.?!:]\s+)(which|what|who|where|when|how|why|identify|select|choose)\b", s, re.I)
    return ("?" in s) or s.endswith(":") or unfinished or bool(lead)


def option_length_stats(opts, key):
    """Author's definition (scripts/reviewer_sensitivity.py feats()): lengths of the stripped option texts."""
    lens = {L: len(o.strip()) for L, o in opts.items()}
    allv = list(lens.values())
    m = statistics.mean(allv) if allv else float("nan")
    cv = (statistics.pstdev(allv) / m) if allv and m else 0.0
    if key in lens:
        d = [v for L, v in lens.items() if L != key]
        return m, cv, lens[key], (max(d) if d else 0), len(opts[key].split())
    return m, cv, float("nan"), float("nan"), float("nan")


def absolute_audit(results):
    """results: list of (detector result). Counts only: flagged items, options per word, options key vs distractor."""
    out = collections.Counter()
    words_opt = collections.Counter()
    words_pos = collections.Counter()
    for res in results:
        if not res["flaws"]["absolute_terms"]:
            continue
        out["flagged items"] += 1
        key = res["features"]["key"]
        hits = res["evidence"]["absolute_hits"]
        pos_here = set()
        only_here = set()
        for L, ws in hits.items():
            pos = "key" if L == key else "distractor"
            out["flagged options: " + pos] += 1
            pos_here.add(pos)
            for w in ws:
                words_opt[w] += 1
                words_pos[(w, pos)] += 1
                out["word hits: " + pos] += 1
                if w == "only":
                    only_here.add(pos)
        if pos_here == {"distractor"}:
            out["items whose flagged options are all distractors"] += 1
        if only_here:
            out["items with 'only' in a flagged option"] += 1
        if "distractor" in only_here:
            out["items with 'only' in a flagged distractor"] += 1
    return out, words_opt, words_pos


# ------------------------------------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("train_xlsx")
    ap.add_argument("test_xlsx")
    ap.add_argument("gold_xlsx")
    ap.add_argument("src_dir", help="the folder that contains the mediwf package (the project's src/)")
    ap.add_argument("llm_flags", help="outputs/flags_full.csv or Dataset 2 (MedIWF_Dataset2_detector_flags.csv)")
    ap.add_argument("--llm-items", default=None, help="data/generated/items_full.jsonl[.gz] or Dataset 1 items_full CSV")
    ap.add_argument("--min-group", type=int, default=5)
    ap.add_argument("--min-flagged", type=int, default=10)
    a = ap.parse_args()
    min_group = max(5, a.min_group)
    min_flagged = max(5, a.min_flagged)

    sys.path.insert(0, os.path.abspath(a.src_dir))
    from mediwf.detector import Detector, VERSION
    from mediwf import rules as author_rules
    import mediwf.detector as det_mod
    det = Detector()

    P("=" * 110)
    P("INDEPENDENT NBME CHECK. Aggregates only. Detector version loaded: %s (%s)" % (VERSION, os.path.basename(det_mod.__file__)))
    P("numpy %s, pandas %s, Python %s" % (np.__version__, pd.__version__, sys.version.split()[0]))
    same = (list(author_rules.CORE) == CORE and list(author_rules.VALIDATED) == VALIDATED and list(author_rules.CUEING) == CUEING
            and list(author_rules.SENSITIVITY) == SENS11)
    P("Composite definitions in this script identical to src/mediwf/rules.py (CORE, VALIDATED, SENSITIVITY, CUEING): %s" % same)

    # ---------------------------------------------------------------- 0. load NBME files
    P("\n== 0. NBME files (structure and loading; counts only)")
    tr = pd.read_excel(a.train_xlsx)
    te = pd.read_excel(a.test_xlsx)
    go = pd.read_excel(a.gold_xlsx)
    for name, df in (("train_final", tr), ("test_final", te), ("gold_final", go)):
        P("  %-12s rows %4d, columns %2d: %s" % (name, len(df), df.shape[1], ", ".join(map(str, df.columns))))
    overlap = [c for c in go.columns if c in te.columns and c != "ItemNum"]
    tem = te.merge(go, on="ItemNum", how="inner", suffixes=("", "__gold"))
    for c in overlap:
        tem[c] = tem[c].where(tem[c].notna(), tem[c + "__gold"])
        tem = tem.drop(columns=[c + "__gold"])
    P("  test rows %d, gold rows %d, joined on ItemNum (inner) %d; gold columns also present in test: %s" % (
        len(te), len(go), len(tem), overlap if overlap else "none"))
    for name, df in (("train", tr), ("test", te), ("gold", go)):
        P("  ItemNum unique within %-5s: %s" % (name, df["ItemNum"].is_unique))
    P("  ItemNum values shared by train and test: %d" % len(set(tr["ItemNum"]) & set(te["ItemNum"])))
    pat_tr, pat_te = find_option_pattern(tr.columns), find_option_pattern(tem.columns)
    P("  option columns found: train '%s', test '%s' (the author's code reads 'Answer__%%s')" % (pat_tr, pat_te))
    tr = tr.assign(_split="train")
    tem = tem.assign(_split="test")

    tally = collections.Counter()
    items, rows, stems_opts = [], [], []
    for pat, df in ((pat_tr, tr), (pat_te, tem)):
        for rec in df.to_dict("records"):
            opts = {}
            legacy = {}
            for L in LETTERS:
                raw = rec.get(pat % L)
                t = cell_text(raw, tally)
                if t:
                    opts[L] = t
                lt = legacy_cell_text(raw)
                if lt:
                    legacy[L] = lt
            stem = rec.get("ItemStem_Text")
            if stem is None or (isinstance(stem, float) and math.isnan(stem)):
                tally["missing stems"] += 1
                stem = ""
            stem = str(stem)
            item = {"stem": stem, "options": opts, "answer": rec.get("Answer_Key")}
            items.append((item, {"stem": stem, "options": legacy, "answer": rec.get("Answer_Key")}))
            stems_opts.append(stem)
            stems_opts.extend(opts.values())
            rows.append({"split": rec["_split"], "EXAM": str(rec.get("EXAM")), "ItemType": str(rec.get("ItemType")),
                         "Difficulty": to_float(rec.get("Difficulty")), "Response_Time": to_float(rec.get("Response_Time")),
                         "answer_raw": str(rec.get("Answer_Key") or "").strip().upper()})
    P.forbid(stems_opts)
    P("  cell conversions (counts): %s" % (dict(sorted(tally.items())) if tally else "none"))

    # detector v1.2 on every item
    results = []
    recs = []
    for (item, _), meta in zip(items, rows):
        res = det.detect(item)
        results.append(res)
        f = res["features"]
        m, cv, kc, ld, kw = option_length_stats(item["options"], f["key"])
        r = dict(meta)
        r.update({k: int(bool(res["flaws"][k])) for k in CORE + FEATURES})
        r.update({"n_options": f["n_options"], "key": f["key"], "stem_words": f["stem_words"], "mean_opt": m, "cv_opt": cv,
                  "key_chars_raw": kc, "longest_d_raw": ld, "key_words": kw,
                  "n_opt_indep": len(item["options"]), "stem_words_indep": len(item["stem"].split()),
                  "leadin": int(has_leadin(item["stem"]))})
        recs.append(r)
    nb = pd.DataFrame(recs)
    nb["any14"] = (nb[CORE].sum(axis=1) > 0).astype(int)
    nb["any10"] = (nb[VALIDATED].sum(axis=1) > 0).astype(int)
    nb["any11"] = (nb[SENS11].sum(axis=1) > 0).astype(int)
    nb["any13_no_longest"] = (nb[[r for r in CORE if r != "longest_option_key"]].sum(axis=1) > 0).astype(int)
    nb["count14"] = nb[CORE].sum(axis=1)
    nb["cueing_count"] = nb[CUEING].sum(axis=1)
    nb["legacy6_count"] = nb[LEGACY6].sum(axis=1)
    nb["log_stem_words"] = np.log(nb["stem_words"].clip(lower=1))
    nb["text_item"] = (nb["ItemType"] == "Text").astype(int)
    nb["log_mean_opt"] = np.log(nb["mean_opt"].clip(lower=1))
    P("  detector features vs independent counts: n_options differ in %d items, stem word counts differ in %d, key letter "
      "differs from the Answer_Key cell in %d" % ((nb.n_options != nb.n_opt_indep).sum(), (nb.stem_words != nb.stem_words_indep).sum(),
                                                  (nb.key != nb.answer_raw).sum()))
    P("  items with an unreadable key (key-dependent rules disabled): %d" % (nb.key == "").sum())

    # ---------------------------------------------------------------- 1. counts
    P("\n== 1. Counts")
    n_all = len(nb)
    five = nb[nb.n_options == 5]
    n5 = len(five)
    dist = dict(sorted(collections.Counter(nb.n_options).items()))
    P("  items: %d (train %d, test %d); five-option items: %d; other: %d" % (n_all, (nb.split == "train").sum(), (nb.split == "test").sum(), n5, n_all - n5))
    P("  number of options per item (count of items): %s" % dist)
    P("  by split: train %s | test %s" % (dict(sorted(collections.Counter(nb[nb.split == "train"].n_options).items())),
                                          dict(sorted(collections.Counter(nb[nb.split == "test"].n_options).items()))))
    P("  EXAM levels (all / five-option): %s / %s" % (dict(sorted(collections.Counter(nb.EXAM).items())), dict(sorted(collections.Counter(five.EXAM).items()))))
    P("  ItemType (all / five-option): %s / %s" % (dict(sorted(collections.Counter(nb.ItemType).items())), dict(sorted(collections.Counter(five.ItemType).items()))))
    P("  missing Difficulty: %d, missing Response_Time: %d" % (nb.Difficulty.isna().sum(), nb.Response_Time.isna().sum()))
    check("items, all", n_all, 667, nd=0, source="main text, Supplement 1; analysis_nbme_v3.txt l.1")
    check("items, five-option", n5, 525, nd=0, source="main text, Table 2, Supplement 1")
    check("items not five-option", n_all - n5, 142, nd=0, source="Supplement 1")
    others = sorted(k for k in dist if k != 5)
    check("'4 or 6 to 10 options': non-five counts are all in {4, 6..10}", set(others) <= {4, 6, 7, 8, 9, 10}, True, source="Supplement 1")
    check("'4 or 6 to 10 options': at least one 4-option and one 10-option item", (4 in dist) and (10 in dist), True, source="Supplement 1")

    # ---------------------------------------------------------------- 2. prevalence
    P("\n== 2. Prevalence with Wilson 95%% CI (z = %.2f), %% with 3 decimals" % Z)
    P("  %-34s %-30s %-30s" % ("rule / composite", "five-option items (n=%d)" % n5, "all items (n=%d)" % n_all))
    for r in CORE + ["any14", "any10", "any11", "any13_no_longest"] + FEATURES:
        P("  %-34s %-30s %-30s" % (r, pct(int(five[r].sum()), n5), pct(int(nb[r].sum()), n_all)))
    ds6 = {"negative_stem": 0, "none_of_the_above": 0, "all_of_the_above": 0, "combination_options": 0, "fill_in_blank": 0,
           "true_false_stem": 0, "longest_option_key": 15, "absolute_terms": 16, "vague_terms": 3, "clang_cue": 44,
           "grammatical_cue": 0, "nonparallel_options": 17, "numeric_not_ordered": 1, "overlapping_options": 3,
           "option_length_outlier": 207, "options_not_alphabetical": 95, "numeric_units_inconsistent": 2}
    for r, v in ds6.items():
        check("five-option count, %s" % r, five[r].sum(), v, nd=0, source="Dataset 6 / nbme_aggregate_for_figures.json")
    check("five-option count, any of 14", five.any14.sum(), 91, nd=0, source="Dataset 6")
    p, lo, hi = wilson(five.any14.sum(), n5)
    check("five-option any of 14, %", 100 * p, 17.3, nd=1, source="main text, Supplement 1")
    check("five-option any of 14, CI low", 100 * lo, 14.3, nd=1, source="main text, Supplement 1")
    check("five-option any of 14, CI high", 100 * hi, 20.8, nd=1, source="main text, Supplement 1")
    for r, v in (("longest_option_key", 2.9), ("absolute_terms", 3.0), ("clang_cue", 8.4), ("nonparallel_options", 3.2),
                 ("overlapping_options", 0.6), ("grammatical_cue", 0.0)):
        check("five-option %s, %%" % r, 100 * five[r].mean(), v, nd=1, source="Supplement 1 (and main text for longest)")
    p, lo, hi = wilson(five.any10.sum(), n5)
    check("five-option any validated (10), %", 100 * p, 11.4, nd=1, source="Supplement 1; analysis_nbme_comparison_v1.txt l.6")
    check("five-option any validated, CI low", 100 * lo, 9.0, nd=1, source="Supplement 1")
    check("five-option any validated, CI high", 100 * hi, 14.4, nd=1, source="Supplement 1")
    check("five-option any of 13 (no longest-option rule), %", 100 * five.any13_no_longest.mean(), 15.0, nd=1, source="Supplement 1; analysis_reviewer_sensitivity_v1.txt l.44")
    check("all items, any of 14, %", 100 * nb.any14.mean(), 17.5, nd=1, source="analysis_nbme_v3.txt l.21; detector_changelog v1.2")
    for r, v, src in (("longest_option_key", 20, "main text, Supplement 1"), ("absolute_terms", 21, "main text, Supplement 1"),
                      ("clang_cue", 51, "main text, Supplement 1"), ("option_length_outlier", 243, "Supplement 1")):
        check("all items, n flagged %s" % r, nb[r].sum(), v, nd=0, source=src)

    # ---------------------------------------------------------------- 3. option-length features and lengths
    P("\n== 3. Option-length features and item lengths")
    for r in FEATURES:
        P("  %-28s five-option %s | all %s" % (r, pct(int(five[r].sum()), n5), pct(int(nb[r].sum()), n_all)))

    def q3(s):
        s = pd.Series(s, dtype=float).dropna()
        return "median %.3f (IQR %.3f-%.3f)" % (s.median(), s.quantile(.25), s.quantile(.75))
    P("  NBME five-option: stem words %s; mean option characters %s; option-length CV %s" % (q3(five.stem_words), q3(five.mean_opt), q3(five.cv_opt)))
    check("NBME five-option stem words, median", five.stem_words.median(), 112, nd=0, source="Supplement 1; analysis_nbme_comparison_v1.txt l.23")
    check("NBME five-option mean option chars, median", five.mean_opt.median(), 23, nd=0, source="Supplement 1; analysis_reviewer_sensitivity_v1.txt l.47")
    check("NBME five-option option-length CV, median", five.cv_opt.median(), 0.28, nd=2, source="Supplement 1 ('more variable'); reviewer_sensitivity l.47")

    # ---------------------------------------------------------------- 4. key position
    P("\n== 4. Key position")
    kc5 = collections.Counter(five.key)
    obs = np.array([kc5.get(L, 0) for L in "ABCDE"], float)
    chi5 = float(((obs - obs.sum() / 5) ** 2 / (obs.sum() / 5)).sum())
    p5 = chi2_sf(chi5, 4)
    P("  five-option items, counts A-E: %s (other letters: %d)" % (dict(zip("ABCDE", obs.astype(int).tolist())), n5 - int(obs.sum())))
    P("  shares %%: %s" % ", ".join("%s %.3f" % (L, 100 * v / obs.sum()) for L, v in zip("ABCDE", obs)))
    P("  chi-square vs uniform over A-E: %.4f, df 4, P = %.5f" % (chi5, p5))
    kca = collections.Counter(nb.key)
    P("  all items, counts by key letter: %s" % dict(sorted(kca.items())))
    oa = np.array([kca.get(L, 0) for L in "ABCDE"], float)
    chia = float(((oa - oa.sum() / 5) ** 2 / (oa.sum() / 5)).sum())
    P("  all items keyed A-E (n=%d): chi-square %.4f, df 4, P = %.5f (the author's log prints this chi-square as 5.4)" % (oa.sum(), chia, chi2_sf(chia, 4)))
    for L, v in zip("ABCDE", (110, 99, 89, 118, 109)):
        check("five-option key count %s" % L, kc5.get(L, 0), v, nd=0, source="Dataset 6; Fig. 2")
    check("five-option key chi-square", chi5, 4.8, nd=1, source="main text, Supplement 1; analysis_nbme_v3.txt l.24")
    check("five-option key chi-square P", p5, 0.31, nd=2, source="main text, Supplement 1 (P is in no log)")
    check("five-option share of keys at A, %", 100 * obs[0] / obs.sum(), 21, nd=0, source="Table 2, Fig. 2")

    # ---------------------------------------------------------------- 5. LLM side
    P("\n== 5. LLM plain-prompt items (comparison set)")
    fl = pd.read_csv(a.llm_flags)
    n_read = len(fl)
    if "run" in fl.columns:
        fl = fl[fl["run"] == "full"]
    fl = fl[fl["condition"] == "plain"]
    if "reasoning_mode" in fl.columns:
        fl = fl[fl["reasoning_mode"].fillna("off") == "off"]
    fl = fl.copy()
    P("  flags file rows %d; main-corpus plain rows kept %d (five-option %d); detector versions %s" % (
        n_read, len(fl), (fl.n_options == 5).sum(), sorted(fl.detector_version.astype(str).unique()) if "detector_version" in fl else "?"))
    fl["any14"] = (fl[CORE].sum(axis=1) > 0).astype(int)
    fl["any10"] = (fl[VALIDATED].sum(axis=1) > 0).astype(int)
    fl["any11"] = (fl[SENS11].sum(axis=1) > 0).astype(int)
    fl["any13_no_longest"] = (fl[[r for r in CORE if r != "longest_option_key"]].sum(axis=1) > 0).astype(int)
    fl["log_stem_words"] = np.log(fl.stem_words.clip(lower=1))
    exact_len = False
    llm_results = None
    if a.llm_items:
        from mediwf.parsing import usable_record
        want = dict(zip(fl.job_id, range(len(fl))))
        feats = {}
        llm_results = []
        mism = 0
        if a.llm_items.endswith(".jsonl") or a.llm_items.endswith(".jsonl.gz"):
            opener = gzip.open if a.llm_items.endswith(".gz") else open
            first = {}
            with opener(a.llm_items, "rt", encoding="utf-8") as fh:
                for line in fh:
                    if not line.strip():
                        continue
                    r = json.loads(line)
                    j = r.get("job_id")
                    if j not in want or j in first:
                        continue
                    it = usable_record(r)
                    if it:
                        first[j] = it
            chosen = first
        else:                                            # Dataset 1 CSV: first attempt whose detector output matches Dataset 2
            chosen = {}
            fl_idx = fl.set_index("job_id")
            csv.field_size_limit(10 ** 8)
            with open(a.llm_items, newline="", encoding="utf-8") as fh:
                for r in csv.DictReader(fh):
                    j = r.get("job_id")
                    if j not in want or j in chosen or not (r.get("stem") or "").strip():
                        continue
                    opts = {L: (r.get("option_" + L) or "").strip() for L in "ABCDE" if (r.get("option_" + L) or "").strip()}
                    it = {"stem": r["stem"], "options": opts, "answer": (r.get("answer") or "").strip()}
                    res = det.detect(it)
                    row = fl_idx.loc[j]
                    if res["features"]["key"] == row["key"] and res["features"]["stem_words"] == row["stem_words"] and \
                            all(int(bool(res["flaws"][k])) == int(row[k]) for k in CORE):
                        chosen[j] = it
        for j, it in chosen.items():
            res = det.detect(it)
            row = fl.iloc[want[j]]
            if res["features"]["key"] != row["key"] or res["features"]["stem_words"] != row["stem_words"] or \
                    any(int(bool(res["flaws"][k])) != int(row[k]) for k in CORE):
                mism += 1
            m, cv, kc, ld, kw = option_length_stats(it["options"], res["features"]["key"])
            feats[j] = (m, cv, kc, ld, kw)
            llm_results.append(res)
        P("  --llm-items: items found for %d of %d plain jobs; detector output differs from the flags file for %d" % (len(chosen), len(fl), mism))
        if chosen:
            exact_len = True
            nanf = (float("nan"),) * 5
            approx = (fl.key_chars + (fl.n_options - 1) * fl.mean_distractor_chars) / fl.n_options
            fl["mean_opt"] = [feats[j][0] if j in feats else a_ for j, a_ in zip(fl.job_id, approx)]
            fl["cv_opt"] = [feats.get(j, nanf)[1] for j in fl.job_id]
            fl["key_chars_raw"] = [feats.get(j, nanf)[2] for j in fl.job_id]
            fl["longest_d_raw"] = [feats.get(j, nanf)[3] for j in fl.job_id]
            fl["key_words"] = [feats.get(j, nanf)[4] for j in fl.job_id]
            if len(chosen) < len(fl):
                P("  NOTE: %d plain job(s) have no item text in --llm-items that reproduces the flags file: their mean option length"
                  " is approximated from the flags file and they are left out of the CV-adjusted models and the threshold sweep"
                  " (use data/generated/items_full.jsonl for an exact run)" % (len(fl) - len(chosen)))
    if not exact_len:
        fl["mean_opt"] = (fl.key_chars + (fl.n_options - 1) * fl.mean_distractor_chars) / fl.n_options
        fl["cv_opt"] = np.nan
        P("  option lengths of LLM items APPROXIMATED from key_chars and mean_distractor_chars (rounded to 0.1); CV unavailable")
    fl["log_mean_opt"] = np.log(fl.mean_opt.clip(lower=1))
    P("  LLM plain: stem words %s; mean option characters %s; option-length CV %s" % (q3(fl.stem_words), q3(fl.mean_opt), q3(fl.cv_opt)))
    for r in ("any14", "any10", "any13_no_longest", "longest_option_key", "clang_cue", "absolute_terms", "nonparallel_options") + tuple(FEATURES):
        P("  LLM plain %-28s %s" % (r, pct(int(fl[r].sum()), len(fl))))
    check("LLM plain stem words, median", fl.stem_words.median(), 89, nd=0, source="Supplement 1")
    check("LLM plain mean option chars, median", fl.mean_opt.median(), 36, nd=0, source="Supplement 1")
    if exact_len:
        check("LLM plain option-length CV, median", fl.cv_opt.median(), 0.23, nd=2, source="reviewer_sensitivity l.47")
    check("LLM plain any of 13 (no longest-option rule), %", 100 * fl.any13_no_longest.mean(), 16.2, nd=1, source="Supplement 1")

    # ---------------------------------------------------------------- 6. LLM vs NBME odds ratios
    P("\n== 6. LLM plain (all five-option) vs NBME five-option items: logistic regression on source, OR for LLM, HC1 sandwich SEs")
    both = pd.concat([fl.assign(llm=1, cluster=fl.model_label.astype(str)),
                      five.assign(llm=0, cluster=["nbme_%d" % i for i in range(n5)])], ignore_index=True)
    outcomes = ["any14", "any10", "any11", "any13_no_longest", "longest_option_key", "clang_cue", "absolute_terms", "nonparallel_options"]
    adjust = [("unadjusted", []), ("log stem", ["log_stem_words"]), ("log stem + log mean option chars", ["log_stem_words", "log_mean_opt"]),
              ("log stem + option CV", ["log_stem_words", "cv_opt"]), ("log stem + log mean option chars + option CV", ["log_stem_words", "log_mean_opt", "cv_opt"])]
    ORS = {}
    for o in outcomes:
        P("  %s  (LLM %d/%d, NBME %d/%d)" % (o, both[both.llm == 1][o].sum(), (both.llm == 1).sum(), both[both.llm == 0][o].sum(), (both.llm == 0).sum()))
        for lab, cols in adjust:
            sub = both.dropna(subset=cols) if cols else both
            if (sub.llm == 1).sum() == 0 or (sub.llm == 0).sum() == 0:
                P("    %-46s not computed (needs --llm-items for exact option lengths)" % lab)
                continue
            y = sub[o].values.astype(float)
            if y.sum() == 0 or y.sum() == len(y):
                P("    %-46s not estimable (no variation)" % lab)
                continue
            X = np.column_stack([np.ones(len(sub)), sub.llm.values.astype(float)] + [sub[c].values.astype(float) for c in cols])
            b, se, conv = logit_robust(X, y)
            orr, lo, hi = math.exp(b[1]), math.exp(b[1] - Z * se[1]), math.exp(b[1] + Z * se[1])
            pv = 2 * norm_sf(abs(b[1] / se[1]))
            ORS[(o, lab)] = (orr, lo, hi)
            approx = "" if exact_len or "option" not in lab else "  [LLM option length approximated]"
            dropped = "" if len(sub) == len(both) else "  [n=%d: %d item(s) without option texts left out]" % (len(sub), len(both) - len(sub))
            P("    %-46s OR %.4f [%.4f, %.4f]  P=%s%s%s%s" % (lab, orr, lo, hi, fp(pv), "" if conv else "  NOT CONVERGED", approx, dropped))
        if o in ("any14", "longest_option_key"):
            X = np.column_stack([np.ones(len(both)), both.llm.values.astype(float)])
            b, se, conv = logit_robust(X, both[o].values.astype(float), clusters=both.cluster.values)
            P("    %-46s OR %.4f [%.4f, %.4f]  (EXTRA, not in the manuscript: LLM items clustered by generator model)" % (
                "unadjusted, model-clustered SE", math.exp(b[1]), math.exp(b[1] - Z * se[1]), math.exp(b[1] + Z * se[1])))
    exp_or = [(("any14", "unadjusted"), (1.46, 1.15, 1.84), 2, "main text, Supplement 1"),
              (("any10", "unadjusted"), (1.14, 0.86, 1.51), 2, "main text, Supplement 1"),
              (("longest_option_key", "unadjusted"), (4.2, 2.5, 7.0), 1, "main text, Supplement 1"),
              (("clang_cue", "unadjusted"), (0.99, 0.72, 1.37), 2, "analysis_nbme_comparison_v1.txt l.28"),
              (("absolute_terms", "unadjusted"), (1.53, 0.92, 2.55), 2, "analysis_nbme_comparison_v1.txt l.30"),
              (("any14", "log stem"), (1.55, 1.23, 1.96), 2, "Supplement 1; analysis_nbme_comparison_v1.txt l.26"),
              (("any10", "log stem"), (1.17, 0.88, 1.55), 2, "Supplement 1; analysis_nbme_comparison_v1.txt l.27"),
              (("longest_option_key", "log stem"), (4.51, 2.67, 7.61), 2, "analysis_nbme_comparison_v1.txt l.29"),
              (("any14", "log stem + log mean option chars"), (1.11, 0.87, 1.42), 2, "main text, Supplement 1"),
              (("any10", "log stem + log mean option chars"), (0.80, 0.60, 1.07), 2, "Supplement 1"),
              (("longest_option_key", "log stem + log mean option chars"), (3.2, 1.9, 5.5), 1, "main text, Supplement 1"),
              (("any14", "log stem + option CV"), (1.91, 1.48, 2.46), 2, "Supplement 1; reviewer_sensitivity l.52"),
              (("any14", "log stem + log mean option chars + option CV"), (1.26, 0.96, 1.65), 2, "Supplement 1"),
              (("longest_option_key", "log stem + log mean option chars + option CV"), (4.2, 2.3, 7.6), 1, "Supplement 1")]
    for key, lab_e, e in ((("any10", "log stem + option CV"), "OR any10 [log stem + option CV] OR", 1.20),
                          (("any10", "log stem + log mean option chars + option CV"), "OR any10 [log stem + log mean option chars + option CV] OR", 0.82)):
        got = ORS.get(key)
        check(lab_e, got[0] if got else None, e, nd=2, source="Supplement 1")
    for key, ev, nd, src in exp_or:
        got = ORS.get(key)
        for part, e, g in zip(("OR", "CI low", "CI high"), ev, got if got else (None, None, None)):
            check("OR %s [%s] %s" % (key[0], key[1], part), g, e, nd=nd, source=src)

    # longest-option threshold sweep (needs the raw option lengths of both sources)
    if exact_len:
        fls = fl.dropna(subset=["key_chars_raw", "longest_d_raw", "key_words"])
        P("\n  Longest-option threshold sweep (key chars > ratio x longest distractor chars and key words >= min): prevalence and")
        P("  unadjusted OR, LLM plain (n=%d) vs NBME five-option (n=%d); any-core = the other 13 rules fixed. Agreement of the" % (len(fls), n5))
        rule_llm = ((fls.key_chars_raw > 1.25 * fls.longest_d_raw) & (fls.key_words >= 4)).astype(int)
        rule_nb = ((five.key_chars_raw > 1.25 * five.longest_d_raw) & (five.key_words >= 4)).astype(int)
        P("  recomputed rule at (1.25, 4) with the detector's flag: LLM %.4f, NBME %.4f" % ((rule_llm.values == fls.longest_option_key.values).mean(),
                                                                                         (rule_nb.values == five.longest_option_key.values).mean()))
        other = [r for r in CORE if r != "longest_option_key"]
        all_gt1, ci1_at_max = True, []
        for ratio in (1.10, 1.15, 1.20, 1.25, 1.30, 1.40, 1.50, 1.75, 2.00):
            for mw in (1, 4, 6):
                rl = ((fls.key_chars_raw > ratio * fls.longest_d_raw) & (fls.key_words >= mw)).astype(int).values
                rn = ((five.key_chars_raw > ratio * five.longest_d_raw) & (five.key_words >= mw)).astype(int).values
                al = ((fls[other].sum(axis=1).values + rl) > 0).astype(int)
                an = ((five[other].sum(axis=1).values + rn) > 0).astype(int)
                X = np.column_stack([np.ones(len(rl) + len(rn)), np.r_[np.ones(len(rl)), np.zeros(len(rn))]])
                txt = ""
                if rl.sum() > 0 and rn.sum() > 0:
                    b, se, _ = logit_robust(X, np.r_[rl, rn].astype(float))
                    o_, l_, h_ = math.exp(b[1]), math.exp(b[1] - Z * se[1]), math.exp(b[1] + Z * se[1])
                    all_gt1 &= o_ > 1
                    if ratio == 2.00:
                        ci1_at_max.append(l_ <= 1 <= h_)
                    txt = "rule OR %.2f [%.2f, %.2f]" % (o_, l_, h_)
                else:
                    txt = "rule OR not estimable (a zero count)"
                    all_gt1 = False
                b, se, _ = logit_robust(X, np.r_[al, an].astype(float))
                P("   ratio %.2f min words %d: LLM %5.2f%%, NBME %5.2f%% | %s | any-core LLM %5.2f%% vs NBME %5.2f%%, OR %.2f [%.2f, %.2f]" % (
                    ratio, mw, 100 * rl.mean(), 100 * rn.mean(), txt, 100 * al.mean(), 100 * an.mean(), math.exp(b[1]),
                    math.exp(b[1] - Z * se[1]), math.exp(b[1] + Z * se[1])))
        check("longest-option OR > 1 at every threshold examined", all_gt1, True, source="main text, Supplement 1")
        check("unadjusted longest-option CI includes 1 at the most extreme ratio (2.00), all min-word settings", bool(ci1_at_max) and all(ci1_at_max), True, source="Supplement 1")

    # ---------------------------------------------------------------- 7. RQ5 regressions
    P("\n== 7. RQ5: OLS of Difficulty and Response_Time on one flaw variable at a time, adjusting for EXAM (dummies), item type")
    P("   (Text vs other) and log stem words; HC1 SEs; P from t(n-k); 95% CI = coef +/- 1.96 SE (as in the author's code).")
    rq = nb.dropna(subset=["Difficulty", "Response_Time"]).copy()
    ref = "STEP 1" if "STEP 1" in set(rq.EXAM) else sorted(rq.EXAM.unique())[0]
    levels = [lv for lv in sorted(rq.EXAM.unique()) if lv != ref]
    P("  items in the regressions: %d (dropped for missing outcome: %d); EXAM reference level '%s', other levels %s" % (len(rq), n_all - len(rq), ref, levels))
    P("  Difficulty: mean %.4f, SD %.4f | Response_Time: mean %.4f s, SD %.4f s" % (rq.Difficulty.mean(), rq.Difficulty.std(), rq.Response_Time.mean(), rq.Response_Time.std()))
    check("Difficulty SD", rq.Difficulty.std(), 0.31, nd=2, source="Supplement 1")
    check("Response time mean (s)", rq.Response_Time.mean(), 86, nd=0, source="Supplement 1")
    check("Response time SD (s)", rq.Response_Time.std(), 30, nd=0, source="Supplement 1 (log prints 29.5)")

    def fit(df, var, outcome, extra=()):
        cols = [np.ones(len(df)), df[var].values.astype(float), df.log_stem_words.values, df.text_item.values.astype(float)]
        cols += [df[c].values.astype(float) for c in extra]
        cols += [(df.EXAM == lv).values.astype(float) for lv in levels]
        if np.std(cols[1]) == 0:
            raise ValueError("regressor has no variation")
        keep = [0, 1] + [i for i in range(2, len(cols)) if np.std(cols[i]) > 0]   # drop covariates constant in this subset
        X = np.column_stack([cols[i] for i in keep])
        b, se, tt, pv, r2, dfree = ols_hc1(X, df[outcome].values.astype(float))
        return b[1], se[1], tt[1], pv[1], r2

    singles = CORE + FEATURES
    variables = ["cueing_count", "count14", "legacy6_count", "any14", "any10", "any11"] + singles
    labels = {"cueing_count": "cueing count (4 rules: longest, absolute, clang, grammatical)", "count14": "flaw count (14 rules)",
              "legacy6_count": "6-rule count used in psychometrics v1/v2", "any14": "any of 14 (composite)", "any10": "any of 10 validated",
              "any11": "any of 11 (sensitivity)"}
    RQ = {}
    for outcome in ("Difficulty", "Response_Time"):
        P("\n  outcome %s" % outcome)
        P("  %-58s %6s %9s %8s %22s %8s %10s %10s %10s %6s" % ("variable", "n>0", "coef", "SE", "95% CI", "t", "P", "q(author)", "q(all)", "R2"))
        est = []
        for v in variables:
            npos = int((rq[v] > 0).sum())
            if v in singles and (npos < min_flagged or len(rq) - npos < min_flagged):
                est.append((v, npos, None))
                continue
            try:
                est.append((v, npos, fit(rq, v, outcome)))
            except (ValueError, np.linalg.LinAlgError):
                est.append((v, npos, None))
        fam_author = ["cueing_count", "any14"] + [f for f in AUTHOR_SINGLE if int(rq[f].sum()) >= 10]
        ok = [(v, n_, r) for v, n_, r in est if r is not None]
        q_all = dict(zip([v for v, _, _ in ok], bh([r[3] for _, _, r in ok])))
        fam = [(v, r) for v, _, r in ok if v in fam_author]
        q_auth = dict(zip([v for v, _ in fam], bh([r[3] for _, r in fam])))
        for v, npos, r in est:
            name = labels.get(v, v)
            if r is None:
                P("  %-58s %6d   not estimated: fewer than %d flagged or unflagged items, or no variation (an estimate would approach an item-level value)" % (name, npos, min_flagged))
                continue
            b, se, tt, pv, r2 = r
            RQ[(outcome, v)] = (b, b - Z * se, b + Z * se, pv, q_auth.get(v, float("nan")))
            P("  %-58s %6d %+9.4f %8.4f [%+9.4f, %+9.4f] %+8.3f %10s %10s %10s %6.3f" % (
                name, npos, b, se, b - Z * se, b + Z * se, tt, fp(pv), fp(q_auth[v]) if v in q_auth else "-", fp(q_all[v]), r2))
        P("  author's BH family (scripts/nbme_psychometrics.py): %s" % ", ".join(fam_author))

    def ck(outcome, v, part, e, nd=None, sig=None, src=""):
        r = RQ.get((outcome, v))
        idx = {"b": 0, "lo": 1, "hi": 2, "p": 3, "q": 4}[part]
        check("RQ5 %s %s %s" % (outcome, v, part), r[idx] if r else None, e, nd=nd, sig=sig, source=src)
    ck("Response_Time", "cueing_count", "b", -6.9, 1, src="main text, Supplement 1; nbme_psychometrics_v3.txt l.15")
    ck("Response_Time", "cueing_count", "lo", -11.8, 1, src="main text, Supplement 1")
    ck("Response_Time", "cueing_count", "hi", -2.0, 1, src="main text, Supplement 1")
    ck("Response_Time", "cueing_count", "q", 0.012, 3, src="main text, Supplement 1")
    ck("Difficulty", "cueing_count", "b", -0.056, 3, src="Supplement 1; nbme_psychometrics_v3.txt l.5")
    ck("Difficulty", "cueing_count", "p", 0.09, 2, src="main text, Supplement 1")
    ck("Response_Time", "count14", "b", -1.5, 1, src="main text, Supplement 1")
    ck("Response_Time", "count14", "lo", -6.5, 1, src="Supplement 1")
    ck("Response_Time", "count14", "hi", 3.4, 1, src="Supplement 1")
    ck("Response_Time", "count14", "p", 0.55, 2, src="main text, Supplement 1")
    ck("Difficulty", "count14", "b", -0.056, 3, src="main text, Supplement 1")
    ck("Difficulty", "count14", "lo", -0.109, 3, src="Supplement 1")
    ck("Difficulty", "count14", "hi", -0.004, 3, src="Supplement 1")
    ck("Difficulty", "count14", "p", 0.04, 2, src="main text, Supplement 1")
    ck("Difficulty", "absolute_terms", "b", -0.204, 3, src="Supplement 1; nbme_psychometrics_v3.txt l.8")
    ck("Difficulty", "absolute_terms", "lo", -0.329, 3, src="Supplement 1")
    ck("Difficulty", "absolute_terms", "hi", -0.079, 3, src="Supplement 1")
    ck("Difficulty", "absolute_terms", "q", 0.011, 3, src="Supplement 1")
    ck("Response_Time", "absolute_terms", "b", -14.3, 1, src="main text, Supplement 1; l.18")
    ck("Response_Time", "absolute_terms", "lo", -21.4, 1, src="Supplement 1")
    ck("Response_Time", "absolute_terms", "hi", -7.2, 1, src="Supplement 1")
    check("RQ5 Response_Time absolute_terms q < 0.001", RQ.get(("Response_Time", "absolute_terms"), (0, 0, 0, 1, 1))[4] < 0.001, True, source="Supplement 1")
    ck("Response_Time", "clang_cue", "b", -10.4, 1, src="main text, Supplement 1; l.19")
    ck("Response_Time", "clang_cue", "lo", -16.9, 1, src="Supplement 1")
    ck("Response_Time", "clang_cue", "hi", -3.8, 1, src="Supplement 1")
    ck("Response_Time", "clang_cue", "q", 0.006, 3, src="Supplement 1")
    ck("Response_Time", "option_length_outlier", "b", -7.7, 1, src="Supplement 1; l.21")
    check("RQ5 Response_Time option_length_outlier q < 0.001", RQ.get(("Response_Time", "option_length_outlier"), (0, 0, 0, 1, 1))[4] < 0.001, True, source="Supplement 1")
    for outc in ("Difficulty", "Response_Time"):
        r = RQ.get((outc, "longest_option_key"))
        check("RQ5 %s longest_option_key not significant (P >= 0.05)" % outc, (r[3] >= 0.05) if r else None, True, source="main text, Supplement 1")
        r = RQ.get((outc, "clang_cue"))
        if outc == "Difficulty":
            check("RQ5 Difficulty clang_cue not significant (S1: 'no difference in difficulty')", (r[3] >= 0.05) if r else None, True, source="Supplement 1")
    ck("Difficulty", "any14", "b", -0.049, 3, src="Supplement 1; nbme_psychometrics_v3.txt l.6")
    ck("Difficulty", "any14", "p", 0.12, sig=2, src="Supplement 1; nbme_psychometrics_v3.txt l.6")
    ck("Response_Time", "any14", "b", -0.612, 3, src="Supplement 1 (-0.6 s); nbme_psychometrics_v3.txt l.16")
    ck("Response_Time", "any14", "p", 0.843, sig=3, src="Supplement 1 (0.84); nbme_psychometrics_v3.txt l.16")
    ck("Response_Time", "nonparallel_options", "b", 7.878, 3, src="nbme_psychometrics_v3.txt l.20 (not reported)")
    ck("Response_Time", "longest_option_key", "b", 6.752, 3, src="nbme_psychometrics_v3.txt l.17")
    ck("Difficulty", "longest_option_key", "b", 0.069, 3, src="nbme_psychometrics_v3.txt l.7")
    ck("Difficulty", "clang_cue", "p", 0.297, sig=3, src="nbme_psychometrics_v3.txt l.9")
    pos_sig = [v for (o, v), r in RQ.items() if o == "Difficulty" and r[0] > 0 and r[3] < 0.05]
    check("RQ5 no flaw variable associated with harder items (no positive difficulty coefficient with P < 0.05)", len(pos_sig) == 0, True, source="Supplement 1")

    P("\n  Same regressions adding log mean option characters and option-length CV (Supplement 1; 'Adding option length and its spread')")
    RQo = {}
    for outcome in ("Difficulty", "Response_Time"):
        for v in ["cueing_count", "count14", "any14", "absolute_terms", "clang_cue", "longest_option_key", "option_length_outlier"]:
            npos = int((rq[v] > 0).sum())
            if v in singles and (npos < min_flagged or len(rq) - npos < min_flagged) or (outcome, v) not in RQ:
                continue
            try:
                b, se, tt, pv, r2 = fit(rq, v, outcome, extra=("log_mean_opt", "cv_opt"))
            except (ValueError, np.linalg.LinAlgError):
                continue
            RQo[(outcome, v)] = (b, pv)
            base = RQ[(outcome, v)]
            P("  %-14s %-58s %+9.4f [%+9.4f, %+9.4f] P=%-10s (without option length: %+9.4f, P=%s)" % (
                outcome, labels.get(v, v), b, b - Z * se, b + Z * se, fp(pv), base[0], fp(base[3])))
    r = RQo.get(("Response_Time", "option_length_outlier"))
    check("RQ5 + option length: Response_Time option_length_outlier coef", r[0] if r else None, -5.3, nd=1, source="Supplement 1")
    r = RQo.get(("Difficulty", "count14"))
    check("RQ5 + option length: Difficulty flaw count (14 rules) coef", r[0] if r else None, -0.035, nd=3, source="main text, Supplement 1")
    check("RQ5 + option length: Difficulty flaw count (14 rules) P", r[1] if r else None, 0.20, nd=2, source="main text, Supplement 1")
    r = RQo.get(("Difficulty", "cueing_count"))
    check("RQ5 + option length: Difficulty cueing count coef", r[0] if r else None, -0.038, nd=3, source="Supplement 1")
    check("RQ5 + option length: Difficulty cueing count P", r[1] if r else None, 0.25, nd=2, source="Supplement 1")

    P("\n  Cueing count as categories (dose-response check, Supplement 1; contrasts need >= %d items)" % min_group)
    CAT = {}
    cc_counts = collections.Counter(rq.cueing_count)
    top = max(cc_counts)
    for outcome in ("Difficulty", "Response_Time"):
        for k in range(1, top + 1):
            lab = ">=%d" % k if k == top and k > 1 else "%d" % k
            grp = (rq.cueing_count >= k) if k == top else (rq.cueing_count == k)
            ind = "_cue_cat_%d" % k
            rq[ind] = grp.astype(int)
        cols_cat = ["_cue_cat_%d" % k for k in range(1, top + 1) if rq["_cue_cat_%d" % k].sum() >= min_group]
        if not cols_cat:
            continue
        Xc = [np.ones(len(rq))] + [rq[c].values.astype(float) for c in cols_cat] + [rq.log_stem_words.values, rq.text_item.values.astype(float)]
        Xc += [(rq.EXAM == lv).values.astype(float) for lv in levels]
        Xc = np.column_stack([c for i, c in enumerate(Xc) if i == 0 or np.std(c) > 0])
        try:
            b, se, tt, pv, r2, _ = ols_hc1(Xc, rq[outcome].values.astype(float))
            for i, c in enumerate(cols_cat, start=1):
                P("  %-14s cueing count %-4s vs 0 (n=%d)  %+9.4f [%+9.4f, %+9.4f] P=%s" % (
                    outcome, c.rsplit("_", 1)[1] + ("+" if c.endswith(str(top)) and top > 1 else ""), int(rq[c].sum()), b[i], b[i] - Z * se[i], b[i] + Z * se[i], fp(pv[i])))
                CAT[(outcome, c.rsplit("_", 1)[1])] = (b[i], pv[i], int(rq[c].sum()))
        except (ValueError, np.linalg.LinAlgError):
            P("  %-14s categorical model not estimable" % outcome)

    r = CAT.get(("Response_Time", "1"))
    check("RQ5 categories: Response_Time, 1 cueing flaw vs none, coef (s)", r[0] if r else None, -4.9, nd=1, source="Supplement 1")
    check("RQ5 categories: Response_Time, 1 cueing flaw vs none, P", r[1] if r else None, 0.13, nd=2, source="Supplement 1")
    r = CAT.get(("Response_Time", "2"))
    check("RQ5 categories: Response_Time, 2 cueing flaws vs none, coef (s)", r[0] if r else None, -24.2, nd=1, source="Supplement 1")
    check("RQ5 categories: Response_Time, 2 cueing flaws vs none, P < 0.001", (r[1] < 0.001) if r else None, True, source="Supplement 1")
    check("RQ5 categories: items with 2 cueing flaws", r[2] if r else None, 7, nd=0, source="Supplement 1")

    P("\n  The same regressions on the five-option items only (Supplement 1 reports the cueing count)")
    r5 = rq[rq.n_options == 5]
    for outcome in ("Difficulty", "Response_Time"):
        for v in ["cueing_count", "count14", "any14", "absolute_terms", "clang_cue", "longest_option_key"]:
            npos = int((r5[v] > 0).sum())
            if v in singles and (npos < min_flagged or len(r5) - npos < min_flagged):
                continue
            try:
                b, se, tt, pv, r2 = fit(r5, v, outcome)
            except (ValueError, np.linalg.LinAlgError):
                continue
            P("  %-14s %-58s n=%d n>0=%d %+9.4f [%+9.4f, %+9.4f] P=%s" % (outcome, labels.get(v, v), len(r5), npos, b, b - Z * se, b + Z * se, fp(pv)))
            if outcome == "Response_Time" and v == "cueing_count":
                check("RQ5 five-option items only: Response_Time cueing count coef (s)", b, -4.3, nd=1, source="Supplement 1")
                check("RQ5 five-option items only: Response_Time cueing count P", pv, 0.14, nd=2, source="Supplement 1")

    P("\n  Descriptive means by number of cueing flags (as in nbme_psychometrics_v3.txt; groups of fewer than %d items are pooled" % min_group)
    P("  with the next lower group) and by any of the 14 rules (0 vs >= 1 only, so that no difference between the two tables")
    P("  isolates fewer than %d items)" % min_group)
    counts = collections.Counter(rq["cueing_count"])
    groups, cur = [], []
    for k in sorted(counts, reverse=True):              # pool small top groups downward
        cur.append(k)
        if sum(counts[x] for x in cur) >= min_group:
            groups.append(sorted(cur))
            cur = []
    if cur:
        if groups:
            groups[-1] = sorted(groups[-1] + cur)
        else:
            groups.append(sorted(cur))
    desc = [("cueing count", str(g[0]) if len(g) == 1 else "%d-%d" % (g[0], g[-1]), rq[rq.cueing_count.isin(g)]) for g in sorted(groups)]
    desc += [("any of 14", "0", rq[rq.any14 == 0]), ("any of 14", ">=1", rq[rq.any14 == 1]), ("all items", "", rq)]
    for name, lab, sub in desc:
        if len(sub) < min_group:
            P("  %-14s %-5s n=%4d  suppressed (fewer than %d items)" % (name, lab, len(sub), min_group))
            continue
        P("  %-14s %-5s n=%4d  Difficulty mean %.4f (SD %.4f)  Response_Time mean %.3f (SD %.3f)" % (
            name, lab, len(sub), sub.Difficulty.mean(), sub.Difficulty.std(), sub.Response_Time.mean(), sub.Response_Time.std()))
    check("Difficulty mean", rq.Difficulty.mean(), 0.488, nd=3, source="nbme_psychometrics_v3.txt l.2")
    cc = collections.Counter(rq.cueing_count)
    for k, v in ((0, 582), (1, 78), (2, 7)):
        check("items with %d cueing flags" % k, cc.get(k, 0), v, nd=0, source="nbme_psychometrics_v3.txt l.27-29")

    # ---------------------------------------------------------------- 8. absolute-terms audit
    P("\n== 8. Absolute-terms audit (counts only). 'flagged options' counts options; 'word hits' counts option x word")
    out, words_opt, words_pos = absolute_audit(results)
    P("  NBME all items: %s" % dict(sorted(out.items())))
    P("  NBME options per triggering word: %s" % dict(sorted(words_opt.items())))
    P("  NBME word x position: %s" % {"%s/%s" % k: v for k, v in sorted(words_pos.items())})
    check("NBME absolute-terms flagged items", out["flagged items"], 21, nd=0, source="Supplement 1")
    check("NBME options containing 'only'", words_opt.get("only", 0), 19, nd=0, source="Supplement 1 ('only' in 19 cases)")
    check("NBME flagged options (hits) in total", out["flagged options: key"] + out["flagged options: distractor"], 29, nd=0, source="Supplement 1")
    check("NBME flagged options in a distractor", out["flagged options: distractor"], 23, nd=0, source="Supplement 1")
    if llm_results is not None:
        o2, w2, wp2 = absolute_audit(llm_results)
        P("  LLM plain: %s" % dict(sorted(o2.items())))
        P("  LLM plain options per word: %s" % dict(sorted(w2.items())))
        sh = o2["flagged options: distractor"] / max(1, o2["flagged options: distractor"] + o2["flagged options: key"])
        P("  LLM plain share of flagged options that are distractors: %.4f; share of word hits in distractors: %.4f" % (
            sh, o2["word hits: distractor"] / max(1, o2["word hits: distractor"] + o2["word hits: key"])))
        check("LLM plain share of flagged options in a distractor, %", 100 * sh, 95, nd=0, source="Supplement 1")

    # ---------------------------------------------------------------- 9. other NBME-dependent numbers
    P("\n== 9. Other NBME-dependent numbers")
    P("  stems without a lead-in (author's definition, scripts/analyze_leadin.py): %d of %d" % ((nb.leadin == 0).sum(), n_all))
    check("NBME stems without a lead-in", (nb.leadin == 0).sum(), 0, nd=0, source="Supplement 1 ('absent from all 667 NBME items')")
    try:
        from mediwf.detector_v1_0 import Detector as D10
        from mediwf.detector_v1_1 import Detector as D11
        P("  any of 14 under each detector version (five-option denominator from the same loader):")
        vals = {}
        for vname, D in (("v1.0", D10), ("v1.1", D11), ("v1.2", Detector)):
            d = D()
            for lname, which in (("current loader", 0), ("v1.0 loader (non-text cells dropped)", 1)):
                a14, a14_5, n5_ = 0, 0, 0
                for pair in items:
                    res = d.detect(pair[which])
                    hit = any(bool(res["flaws"][k]) for k in CORE)
                    a14 += hit
                    if res["features"]["n_options"] == 5:
                        n5_ += 1
                        a14_5 += hit
                vals[(vname, which)] = (a14, a14_5, n5_)
                P("    %-5s %-40s all: %s | five-option: %s" % (vname, lname, pct(a14, n_all, 2), pct(a14_5, n5_, 2)))
        P("  RQ5 single-rule regressions under each detector version (current loader; same covariates as section 7). Supplement 1 says")
        P("  the v1.0 -> v1.1 revision, which was made after tabulating what each rule fired on in the corpus and the NBME items,")
        P("  changed no qualitative conclusion; the author's logs show word repetition vs response time p=0.079 (v1.0) -> 0.0013 (v1.1).")
        for vname, D in (("v1.0", D10), ("v1.1", D11), ("v1.2", Detector)):
            d = D()
            fr = pd.DataFrame([{k: int(bool(d.detect(pair[0])["flaws"][k])) for k in CORE} for pair in items])
            tmp = nb[["EXAM", "text_item", "log_stem_words", "Difficulty", "Response_Time"]].copy()
            for k in CORE:
                tmp[k] = fr[k].values
            tmp["cueing_count"] = tmp[CUEING].sum(axis=1)
            tmp["any14"] = (tmp[CORE].sum(axis=1) > 0).astype(int)
            tmp = tmp.dropna(subset=["Difficulty", "Response_Time"])
            for v in ("clang_cue", "absolute_terms", "longest_option_key", "grammatical_cue", "nonparallel_options", "overlapping_options", "cueing_count", "any14"):
                npos = int((tmp[v] > 0).sum())
                if v not in ("cueing_count", "any14") and (npos < min_flagged or len(tmp) - npos < min_flagged):
                    P("    %-5s %-22s n>0=%3d  not estimated (fewer than %d flagged)" % (vname, v, npos, min_flagged))
                    continue
                parts = []
                for outcome in ("Difficulty", "Response_Time"):
                    try:
                        b, se, tt, pv, r2 = fit(tmp, v, outcome)
                        parts.append("%s %+8.3f [%+8.3f, %+8.3f] P=%s" % (outcome[:4], b, b - Z * se, b + Z * se, fp(pv)))
                    except (ValueError, np.linalg.LinAlgError):
                        parts.append("%s not estimable" % outcome[:4])
                P("    %-5s %-22s n>0=%3d  %s" % (vname, v, npos, " | ".join(parts)))
        check("NBME five-option any of 14 under v1.0 (current loader), %", 100 * vals[("v1.0", 0)][1] / vals[("v1.0", 0)][2], 21.5, nd=1, source="not printed; Supplement 1 gives the v1.0-loader value")
        check("NBME five-option any of 14 under v1.0 (v1.0 loader), %", 100 * vals[("v1.0", 1)][1] / vals[("v1.0", 1)][2], 21.9, nd=1, source="Supplement 1")
        check("NBME five-option any of 14 under v1.1, %", 100 * vals[("v1.1", 0)][1] / vals[("v1.1", 0)][2], 16.8, nd=1, source="Supplement 1; reviewer_addendum l.16")
        check("NBME all-item any of 14 under v1.1, %", 100 * vals[("v1.1", 0)][0] / n_all, 17.1, nd=1, source="detector_changelog v1.2; Amendment 4 A15")
        check("NBME all-item any of 14 under v1.0, %", 100 * vals[("v1.0", 0)][0] / n_all, 22.0, nd=1, source="detector_changelog v1.1")
    except ImportError as e:
        P("  earlier detector versions not found (%s)" % e)

    # ---------------------------------------------------------------- 9b. guided-prompt items vs NBME; cells; share of the gap
    P("\n== 9b. Guided-prompt items vs NBME five-option items (unadjusted; Woolf interval; Fisher exact test), cells below the NBME rate,")
    P("  and the share of the plain-prompt LLM vs NBME gap that the longest-option cue accounts for (risk-difference scale)")
    fg = pd.read_csv(a.llm_flags)
    if "run" in fg.columns:
        fg = fg[fg["run"] == "full"]
    if "reasoning_mode" in fg.columns:
        fg = fg[fg["reasoning_mode"].fillna("off") == "off"]
    fg = fg.copy()
    fg["any14"] = (fg[CORE].sum(axis=1) > 0).astype(int)
    fgu = fg[fg["condition"] == "guided"]
    k_g, n_g = int(fgu.any14.sum()), len(fgu)
    k_n, n_n = int(five.any14.sum()), int(len(five))
    p_g, p_n = k_g / n_g, k_n / n_n
    lor = math.log((k_g / (n_g - k_g)) / (k_n / (n_n - k_n)))
    se_lor = math.sqrt(1 / k_g + 1 / (n_g - k_g) + 1 / k_n + 1 / (n_n - k_n))
    orr, lo, hi = math.exp(lor), math.exp(lor - Z * se_lor), math.exp(lor + Z * se_lor)
    # two-sided Fisher exact test: sum of hypergeometric probabilities not exceeding the observed one
    N = n_g + n_n; K = k_g + k_n
    def hyp(x):
        return math.comb(K, x) * math.comb(N - K, n_g - x) / math.comb(N, n_g)
    p_obs = hyp(k_g)
    p_fisher = sum(hyp(x) for x in range(max(0, K - n_n), min(K, n_g) + 1) if hyp(x) <= p_obs * (1 + 1e-9))
    P("  guided any of 14: %s | NBME five-option: %s | OR %.4f [%.4f, %.4f] | Fisher exact P = %s" % (pct(k_g, n_g, 2), pct(k_n, n_n, 2), orr, lo, hi, fp(p_fisher)))
    check("guided-prompt any of 14, %", 100 * p_g, 13.6, nd=1, source="main text, Supplement 1")
    check("OR guided vs NBME five-option, unadjusted", orr, 0.75, nd=2, source="main text, Supplement 1")
    check("OR guided vs NBME, CI low", lo, 0.59, nd=2, source="main text, Supplement 1")
    check("OR guided vs NBME, CI high", hi, 0.95, nd=2, source="main text, Supplement 1")
    check("guided vs NBME, Fisher exact P", p_fisher, 0.02, nd=2, source="main text, Supplement 1")
    below_g = below_g_ub = below_p = 0
    for cond, lab_ in (("guided", "guided"), ("plain", "plain")):
        sub = fg[fg["condition"] == cond]
        col = "model_label" if "model_label" in sub.columns else ("model" if "model" in sub.columns else "model_id")
        for mname, grp in sub.groupby(col):
            k, n = int(grp.any14.sum()), len(grp)
            pr, wlo, whi = wilson(k, n)
            if pr < p_n:
                if cond == "guided":
                    below_g += 1
                    if whi < p_n:
                        below_g_ub += 1
                else:
                    below_p += 1
                    P("    plain cell below the NBME rate: %s %s" % (mname, pct(k, n, 1)))
    P("  guided cells below the NBME rate: %d of 15 (%d with the Wilson upper bound below it); plain cells below it: %d" % (below_g, below_g_ub, below_p))
    check("guided-prompt cells below the NBME rate", below_g, 11, nd=0, source="Supplement 1")
    check("guided-prompt cells with the upper bound below the NBME rate", below_g_ub, 7, nd=0, source="Supplement 1")
    check("plain-prompt cells below the NBME rate", below_p, 2, nd=0, source="Supplement 1")
    p_plain = fl.any14.mean(); p_plain13 = fl.any13_no_longest.mean(); p_n13 = five.any13_no_longest.mean()
    share = 1 - (p_plain13 - p_n13) / (p_plain - p_n)
    P("  plain vs NBME gap %.4f points; without the longest-option rule %.4f points; share attributable to the longest-option cue %.3f" % (
        100 * (p_plain - p_n), 100 * (p_plain13 - p_n13), share))
    check("share of the plain-NBME gap from the longest-option cue is 'about 80%' (0.75-0.85)", 0.75 <= share <= 0.85, True, source="main text, Supplement 1")

    # ---------------------------------------------------------------- self-check summary
    P("\n== SELF-CHECK against the values printed in the manuscript, Supplement 1, Dataset 6 and the logs (rounded half up)")
    n_ok = sum(1 for c in CHECKS if c[1])
    for label, ok, shown, expected, source in CHECKS:
        P("  %-5s %-92s computed %-12s printed %-8s [%s]" % ("MATCH" if ok else "DIFF", label, shown, expected, source))
    P("\n  %d checks: %d MATCH, %d DIFF" % (len(CHECKS), n_ok, len(CHECKS) - n_ok))
    P("  Differences explained: (1) q for absolute terms on difficulty: Supplement 1 states that t tails were computed by a normal")
    P("  approximation (q=0.011); this script uses the exact t distribution (q=0.012). (2) nbme_psychometrics_v3.txt prints P=0.297")
    P("  for the clang cue on difficulty where the value is 0.2978 (log formatting; the value is not in the paper).")
    P("  Lines printed: %d. No item text, item number or per-item value was printed; no file was written." % (P.lines + 1))


if __name__ == "__main__":
    main()
