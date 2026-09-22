"""Amendment 6(b): LLM judges on the 100 physician-rated corpus items, scored against the physicians' labels.
Reads data/generated/judgeR_<slug>_physician100.jsonl (from judge_perrule.py --physician) and the ingested rating files
outputs/content_rating/ratings/main_R1.csv, main_R2.csv. Mappings (judge 'fail' verdict vs physician label):
  single_best_answer   -> Q1 not 'yes' (no or unsure)
  plausible_distractors-> Q2 'no'
  any of the four content rules -> composite defect (Q1 not yes, Q2 no, Q3 no or Q5 no); secondary: Q5 'no'
For each judge and each reference (R1, R2, both raters, either rater): tp/fp/fn/tn, precision, sensitivity, specificity,
Cohen's kappa with a bootstrap interval, plus judge-vs-judge agreement. Aggregate output only; no item text.
Usage: python3 scripts/validate_judge_physician.py [judge files...] [-o outputs/judge_physician100_validation_v1.txt]
"""
import sys, json, csv, pathlib, io, glob
root = pathlib.Path(__file__).resolve().parents[1]; sys.path.insert(0, str(root / "src"))
from mediwf.stats import kappa_ci, kappa_from_table
CONTENT = ["single_best_answer", "plausible_distractors", "no_extraneous_info", "focused_stem"]

def load_judge(path):
    j = {}
    for l in open(path):
        if l.strip():
            r = json.loads(l)
            if r.get("judgment"): j[r["uid"]] = r
    return j

def load_raters():
    R = {}
    for p in sorted((root / "outputs/content_rating/ratings").glob("main_R*.csv")):
        if p.stem.count("_") == 1: R[p.stem.split("_")[1]] = {r["item_id"]: r for r in csv.DictReader(open(p))}
    return R

def table(pred, gold):
    tp = sum(p and g for p, g in zip(pred, gold)); fp = sum(p and not g for p, g in zip(pred, gold))
    fn = sum((not p) and g for p, g in zip(pred, gold)); tn = len(pred) - tp - fp - fn
    return tp, fp, fn, tn

def line(name, tp, fp, fn, tn):
    prec = tp / (tp + fp) if tp + fp else float("nan"); sens = tp / (tp + fn) if tp + fn else float("nan"); spec = tn / (tn + fp) if tn + fp else float("nan")
    k = kappa_from_table(tp, fp, fn, tn); lo, hi = kappa_ci(tp, fp, fn, tn)
    return "  %-34s tp %2d fp %2d fn %2d tn %2d | precision %.2f sensitivity %.2f specificity %.2f | kappa %.2f [%.2f, %.2f]" % (name, tp, fp, fn, tn, prec, sens, spec, k, lo, hi)

def main():
    argv = sys.argv[1:]; out_path = None
    if "-o" in argv:
        k = argv.index("-o"); out_path = argv[k + 1]; argv = argv[:k] + argv[k + 2:]
    args = [a for a in argv if not a.startswith("-")]
    files = args or sorted(glob.glob(str(root / "data/generated/judgeR_*_physician100.jsonl")))
    buf = io.StringIO()
    def P(*a): print(*a); print(*a, file=buf)
    R = load_raters(); ids = sorted(next(iter(R.values())))
    defect = lambda r: r["q1"] in ("no", "unsure") or r["q2"] == "no" or r["q3"] == "no" or r["q5"] == "no"
    refs = {}
    for rn, rr in R.items():
        refs[rn] = {"single_best_answer": [rr[i]["q1"] != "yes" for i in ids], "plausible_distractors": [rr[i]["q2"] == "no" for i in ids],
                    "composite": [defect(rr[i]) for i in ids], "unacceptable (Q5 no)": [rr[i]["q5"] == "no" for i in ids]}
    if len(R) >= 2:
        names = sorted(R)
        for lab, fn in (("both raters", all), ("either rater", any)):
            refs[lab] = {k: [fn(refs[n][k][j] for n in names) for j in range(len(ids))] for k in refs[names[0]]}
    P("LLM judges on the %d physician-rated corpus items; references: %s" % (len(ids), ", ".join("%s (%d composite defects)" % (k, sum(v["composite"])) for k, v in refs.items())))
    judges = {}
    for f in files:
        j = load_judge(f); judges[pathlib.Path(f).stem.replace("judgeR_", "").replace("_physician100", "")] = j
        missing = [i for i in ids if i not in j or any(r not in j[i]["judgment"] for r in CONTENT)]
        P("\n== %s: %d of %d items with all four content verdicts%s; cost $%.2f" % (pathlib.Path(f).name, len(ids) - len(missing), len(ids), "" if not missing else " (missing: %s)" % ", ".join(missing[:8]), sum(float(json.loads(l).get("cost_usd") or 0) for l in open(f) if l.strip())))
        if missing:
            P("  items without all four verdicts are excluded from the comparisons below (scored on %d items); reason per item: %s" % (len(ids) - len(missing), "; ".join("%s: %s" % (i, ", ".join("%s=%s" % (r, str(j[i]["errors"].get(r, ""))[:40] or "no record") for r in CONTENT if r not in j.get(i, {}).get("judgment", {})) if i in j else "no record") for i in missing[:5])))
        use = [i for i in ids if i not in missing]; keep = [k for k, i in enumerate(ids) if i in use]
        pred = {r: [bool(j[i]["judgment"][r]) for i in use] for r in CONTENT}
        pred["any content rule"] = [any(pred[r][k] for r in CONTENT) for k in range(len(use))]
        P("  judge fail rates: " + ", ".join("%s %.0f%%" % (r, 100 * sum(pred[r]) / len(use)) for r in list(CONTENT) + ["any content rule"]))
        for ref_name, ref in refs.items():
            sub = {k: [v[x] for x in keep] for k, v in ref.items()}
            P("  vs %s:" % ref_name)
            P(line("single best answer vs Q1 not yes", *table(pred["single_best_answer"], sub["single_best_answer"])))
            P(line("plausible distractors vs Q2 no", *table(pred["plausible_distractors"], sub["plausible_distractors"])))
            P(line("any content rule vs composite", *table(pred["any content rule"], sub["composite"])))
            P(line("any content rule vs Q5 no", *table(pred["any content rule"], sub["unacceptable (Q5 no)"])))
    # A27: agreement with and without each judge's own generated items (generator recorded in the private selection key)
    keyf = root / "outputs/content_rating/main_key_DO_NOT_SEND.csv"
    if keyf.exists():
        gen = {r["item_id"]: r["model"] for r in csv.DictReader(open(keyf))}
        P("\n== Excluding each judge's own generated items (A27)")
        for jn, j in judges.items():
            own = [i for i in ids if any(tok in gen.get(i, "").lower().replace(" ", "-").replace(".", "-") for tok in [jn.split("_")[0].replace("anthropic-claude-", "").replace("openai-", "")])]
            ok_ids = [i for i in ids if i in j and all(r in j[i]["judgment"] for r in CONTENT) and i not in own]
            P("  %s: %d own items excluded (%s); scored on %d items" % (jn, len(own), ", ".join(sorted(set(gen[i] for i in own))) or "-", len(ok_ids)))
            for rn in [r for r in refs if r in R]:
                rr = R[rn]
                sba = table([bool(j[i]["judgment"]["single_best_answer"]) for i in ok_ids], [rr[i]["q1"] != "yes" for i in ok_ids])
                comp = table([any(bool(j[i]["judgment"][r]) for r in CONTENT) for i in ok_ids], [defect(rr[i]) for i in ok_ids])
                P(line("single best answer vs %s Q1" % rn, *sba)); P(line("any content rule vs %s composite" % rn, *comp))
    if len(judges) >= 2:
        (a, A), (b, B) = list(judges.items())[:2]
        common = [i for i in ids if i in A and i in B and all(r in A[i]["judgment"] and r in B[i]["judgment"] for r in CONTENT)]
        P("\n== Judge vs judge (%s vs %s) on %d items" % (a, b, len(common)))
        for r in CONTENT:
            P(line(r, *table([bool(A[i]["judgment"][r]) for i in common], [bool(B[i]["judgment"][r]) for i in common])))
    if out_path: pathlib.Path(out_path).write_text(buf.getvalue()); print("\nwritten ->", out_path)

if __name__ == "__main__":
    main()
