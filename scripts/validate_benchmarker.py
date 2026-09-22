"""Validate MedIWF Tier-A rules against BenchMarker's human writing-flaw labels (MIT).
Usage: python3 scripts/validate_benchmarker.py [path/to/writing_flaws_judge.jsonl] [-o outputs/validation_benchmarker_v2.txt]
Reports precision / recall / F1 / Cohen's kappa per rule, for the benchmark block (dev), the exam block (test) and the
healthcare subset of the exam block.
v2 (17 Sep 2026, second audit): (1) duplicate label rows are collapsed to one per (item, rule) - the exam file carries
233 (item, rule) pairs twice, 25 of them with conflicting labels; a conflicting pair is dropped, so every item counts once
(earlier runs counted one duplicated item twice, printing 217 rows for 216 items); (2) the detector version is printed;
(3) the default input path is data/external/benchmarker/writing_flaws_judge.jsonl.
"""
import json, sys, ast, pathlib, collections, io
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from mediwf.detector import Detector, VERSION

# BenchMarker flaw_type -> our rule(s). Only rules that a text-only detector can attempt.
MAP = {
    "avoid_negatives": "negative_stem",
    "no_none_of_the_above": "none_of_the_above",
    "no_all_of_the_above": "all_of_the_above",
    "avoid_k_type": "combination_options",
    "no_fill_in_blank": "fill_in_blank",
    "equal_length_options": "option_length_outlier",
    "no_absolute_terms": "absolute_terms",
    "no_vague_terms": "vague_terms",
    "avoid_repetition": "clang_cue",
    "grammatical_consistency": "grammatical_cue",
    "ordered_options": "numeric_not_ordered",
}

import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1] / 'src'))
from mediwf.stats import kappa_ci

def kappa(tp, fp, fn, tn):
    n = tp + fp + fn + tn
    if n == 0: return float("nan")
    po = (tp + tn) / n
    pe = ((tp + fp) * (tp + fn) + (fn + tn) * (fp + tn)) / (n * n)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")

def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f

def main(path, out_path=None):
    buf = io.StringIO()
    def P(*a):
        print(*a); print(*a, file=buf)
    det = Detector()
    raw = [json.loads(l) for l in open(path)]
    # collapse duplicate label rows: one row per (question, choices, flaw_type); conflicting duplicates are dropped
    groups = collections.OrderedDict()
    for r in raw:
        groups.setdefault((r["question"], str(r["choices"]), r["flaw_type"]), []).append(r)
    rows = []; dup = conflict = 0
    for k, rs in groups.items():
        if len(rs) > 1:
            dup += 1
            if len({int(float(x["label"])) for x in rs}) > 1: conflict += 1; continue
        rows.append(rs[0])
    P("detector version %s; %d label rows -> %d labels after collapsing %d (item, rule) groups with more than one row (%d groups with conflicting labels dropped)" % (VERSION, len(raw), len(rows), dup, conflict))
    blocks = {"benchmark_block(dev)": [], "exam_block(test)": [], "exam_healthcare(test)": []}
    for r in rows:
        if r["flaw_type"] not in MAP: continue
        blk = "exam_block(test)" if isinstance(r["label"], int) or str(r["dataset"]).startswith("human_") else "benchmark_block(dev)"
        blocks[blk].append(r)
        if str(r["dataset"]) == "human_healthcare": blocks["exam_healthcare(test)"].append(r)
    cache = {}
    for name, rs in blocks.items():
        P("\n==== %s: %d labels, %d items" % (name, len(rs), len({(r['question'], str(r['choices'])) for r in rs})))
        P("%-26s %5s %5s %5s %5s | %6s %6s %6s %6s | %s" % ("rule", "tp", "fp", "fn", "tn", "prec", "rec", "F1", "kappa", "prevalence(human)"))
        agg = collections.defaultdict(lambda: [0, 0, 0, 0])
        for r in rs:
            k = (r["question"], str(r["choices"]), r["answer"])
            if k not in cache:
                choices = r["choices"] if isinstance(r["choices"], list) else ast.literal_eval(r["choices"])
                item = {"stem": r["question"], "options": {chr(65 + i): c for i, c in enumerate(choices)}, "answer": r["answer"]}
                cache[k] = det.detect(item)["flaws"]
            pred = bool(cache[k].get(MAP[r["flaw_type"]]))
            gold = bool(int(float(r["label"])))
            a = agg[r["flaw_type"]]
            if pred and gold: a[0] += 1
            elif pred and not gold: a[1] += 1
            elif gold and not pred: a[2] += 1
            else: a[3] += 1
        for ft in MAP:
            if ft not in agg: continue
            tp, fp, fn, tn = agg[ft]
            p, rc, f = prf(tp, fp, fn)
            kc = kappa_ci(tp, fp, fn, tn)
            P("%-26s %5d %5d %5d %5d | %6.2f %6.2f %6.2f %6.2f [%.2f, %.2f] | %.2f" % (ft + "->" + MAP[ft][:10], tp, fp, fn, tn, p, rc, f, kappa(tp, fp, fn, tn), kc[0], kc[1], (tp + fn) / (tp + fp + fn + tn)))
    if out_path:
        pathlib.Path(out_path).write_text(buf.getvalue()); print("\nwritten ->", out_path)

if __name__ == "__main__":
    args = sys.argv[1:]; out = None
    if "-o" in args:
        i = args.index("-o"); out = args[i + 1]; args = args[:i] + args[i + 2:]
    path = args[0] if args else str(pathlib.Path(__file__).resolve().parents[1] / "data/external/benchmarker/writing_flaws_judge.jsonl")
    main(path, out)
