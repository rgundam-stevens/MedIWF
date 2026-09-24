"""Compare a Tier-B judge's pass/fail with BenchMarker human labels on the exam block (216 items).
Usage: python3 scripts/validate_judge.py data/generated/judge_<slug>_benchmarker.jsonl
v2 (24 Sep 2026): duplicate label rows are collapsed exactly as in validate_benchmarker.py (one row per item and rule; the 25
(item, rule) groups whose duplicate rows conflict are dropped), so that judges and detector are scored against the same labels.
BenchMarker's single-best-answer labels are all conflicting pairs (every positive row is paired with a negative row for the
same item), so that rule has no usable positive after collapsing and its kappa is reported as not interpretable.
"""
import json, sys, ast, hashlib, pathlib, collections
root = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'src'))
from mediwf.stats import kappa_ci
MAP = {"single_best_answer": "single_best_answer", "plausible_distractors": "plausible_distractors", "no_extraneous_info": "no_extraneous_info",
       "focused_stem": "focused_stem", "problem_in_stem": "problem_in_stem", "clear_language": "clear_language",
       "no_absolute_terms": "no_absolute_terms", "no_vague_terms": "no_vague_terms", "no_logical_cues": "no_logical_cues"}
def kappa(tp, fp, fn, tn):
    n = tp + fp + fn + tn; po = (tp + tn) / n
    pe = ((tp + fp) * (tp + fn) + (fn + tn) * (fp + tn)) / (n * n)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")
judg = {}
for l in open(sys.argv[1]):
    r = json.loads(l)
    if r.get("judgment"): judg[r["uid"]] = r
raw = [json.loads(l) for l in (root / "data/external/benchmarker/writing_flaws_judge.jsonl").read_text().splitlines()]
groups = collections.OrderedDict()
for r in raw:
    groups.setdefault((r["question"], str(r["choices"]), r["flaw_type"]), []).append(r)
rows = []; n_dup = n_conflict = 0
for k, rs in groups.items():
    if len(rs) > 1:
        n_dup += 1
        if len({int(float(x["label"])) for x in rs}) > 1:
            n_conflict += 1; continue
    rows.append(rs[0])
print("labels: %d rows -> %d after collapsing %d duplicated (item, rule) groups (%d conflicting groups dropped)" % (len(raw), len(rows), n_dup, n_conflict))
agg = collections.defaultdict(lambda: [0, 0, 0, 0]); agg_h = collections.defaultdict(lambda: [0, 0, 0, 0])
for r in rows:
    if not (isinstance(r["label"], int) or str(r["dataset"]).startswith("human_")): continue
    if r["flaw_type"] not in MAP: continue
    ch = r["choices"] if isinstance(r["choices"], list) else ast.literal_eval(r["choices"])
    uid = hashlib.sha1((r["question"] + str(ch)).encode()).hexdigest()[:12]
    if uid not in judg or MAP[r["flaw_type"]] not in judg[uid]["judgment"]: continue
    pred = bool(judg[uid]["judgment"][MAP[r["flaw_type"]]]); gold = bool(int(r["label"]))
    for a in ([agg, agg_h] if r["dataset"] == "human_healthcare" else [agg]):
        x = a[r["flaw_type"]]
        if pred and gold: x[0] += 1
        elif pred: x[1] += 1
        elif gold: x[2] += 1
        else: x[3] += 1
for title, a in [("exam block (216 items)", agg), ("healthcare subset (45 items)", agg_h)]:
    print(f"\n== Judge vs human labels, {title}")
    print("%-24s %4s %4s %4s %4s | %5s %5s %5s %6s %s" % ("rule", "tp", "fp", "fn", "tn", "prec", "rec", "F1", "kappa", "[95% bootstrap CI]"))
    for ft, (tp, fp, fn, tn) in a.items():
        p = tp / (tp + fp) if tp + fp else 0; rc = tp / (tp + fn) if tp + fn else 0; f = 2 * p * rc / (p + rc) if p + rc else 0
        if tp + fn == 0:
            print("%-24s %4d %4d %4d %4d | no human positive after collapsing: kappa not interpretable" % (ft, tp, fp, fn, tn)); continue
        kc = kappa_ci(tp, fp, fn, tn)
        print("%-24s %4d %4d %4d %4d | %5.2f %5.2f %5.2f %6.2f [%.2f, %.2f]" % (ft, tp, fp, fn, tn, p, rc, f, kappa(tp, fp, fn, tn), kc[0], kc[1]))
print("\njudged items:", len(judg), "| total cost $%.3f (all records in the file, including pilot and gap-filling runs)" % sum(float(json.loads(l).get("cost_usd") or 0) for l in open(sys.argv[1]) if l.strip()))
