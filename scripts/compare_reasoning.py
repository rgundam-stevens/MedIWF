"""Amendment 6 A28: reasoning-enabled vs reasoning-disabled verdicts of the same judge on the same items.
For each rule: how often the two verdicts agree; McNemar's exact test on agreement with the human label (items where one
setting agrees with the human and the other does not); kappa against the human label under each setting; thinking usage.
Usage: python3 scripts/compare_reasoning.py <off.jsonl> <on.jsonl> --labels benchmarker|physician [-o out.txt]
"""
import sys, json, csv, ast, hashlib, pathlib, io
from math import comb
root = pathlib.Path(__file__).resolve().parents[1]; sys.path.insert(0, str(root / "src"))
from mediwf.stats import kappa_from_table, kappa_ci
RULES = ["single_best_answer", "plausible_distractors", "no_extraneous_info", "focused_stem"]
MAP = {"single_best_answer": "single_best_answer", "plausible_distractors": "plausible_distractors", "no_extraneous_info": "no_extraneous_info", "focused_stem": "focused_stem"}

def load(path):
    j = {}
    for l in open(path):
        if l.strip():
            r = json.loads(l)
            if r.get("judgment"): j[r["uid"]] = r
    return j

def human_benchmarker():
    """human label per (uid, rule) on the exam block; a rule may carry two label rows per item (both kept, as in validate_judge)."""
    rows = [json.loads(l) for l in (root / "data/external/benchmarker/writing_flaws_judge.jsonl").read_text().splitlines()]
    out = []
    for r in rows:
        if not (isinstance(r["label"], int) or str(r["dataset"]).startswith("human_")): continue
        if r["flaw_type"] not in MAP: continue
        ch = r["choices"] if isinstance(r["choices"], list) else ast.literal_eval(r["choices"])
        uid = hashlib.sha1((r["question"] + str(ch)).encode()).hexdigest()[:12]
        out.append((uid, MAP[r["flaw_type"]], bool(int(r["label"]))))
    return out

def human_physician():
    R = {}
    for p in sorted((root / "outputs/content_rating/ratings").glob("main_R*.csv")):
        if p.stem.count("_") == 1: R[p.stem.split("_")[1]] = {r["item_id"]: r for r in csv.DictReader(open(p))}
    out = []
    for rn, rr in R.items():
        for i, r in rr.items():
            out.append((i, "single_best_answer", r["q1"] != "yes", rn)); out.append((i, "plausible_distractors", r["q2"] == "no", rn))
            out.append((i, "composite", r["q1"] in ("no", "unsure") or r["q2"] == "no" or r["q3"] == "no" or r["q5"] == "no", rn))
    return out

def mcnemar(b, c):
    n = b + c
    if n == 0: return 1.0
    k = min(b, c); p = sum(comb(n, i) for i in range(0, k + 1)) / 2 ** n
    return min(1.0, 2 * p)

def main():
    args = [a for a in sys.argv[1:]]; out_path = None; labels = "benchmarker"
    if "-o" in args: k = args.index("-o"); out_path = args[k + 1]; del args[k:k + 2]
    if "--labels" in args: k = args.index("--labels"); labels = args[k + 1]; del args[k:k + 2]
    off, on = load(args[0]), load(args[1])
    buf = io.StringIO()
    def P(*a): print(*a); print(*a, file=buf)
    common = [u for u in off if u in on and all(r in off[u]["judgment"] and r in on[u]["judgment"] for r in RULES)]
    P("Reasoning disabled vs enabled, same judge, %d items with all four verdicts in both files (%s labels)" % (len(common), labels))
    metas = [m for u in common for m in ((on[u].get("reasoning") or {}).get("meta") or {}).values()]
    thought = [m["reasoning_tokens"] for m in metas if m.get("reasoning_tokens")]
    P("thinking used on %d of %d calls (%.0f%%); median %d, max %d thinking tokens when used; cost off $%.2f vs on $%.2f (records in the files)" % (
        len(thought), len(metas), 100 * len(thought) / max(1, len(metas)), sorted(thought)[len(thought) // 2] if thought else 0, max(thought) if thought else 0,
        sum(float(json.loads(l).get("cost_usd") or 0) for l in open(args[0]) if l.strip()), sum(float(json.loads(l).get("cost_usd") or 0) for l in open(args[1]) if l.strip())))
    P("\n== Verdict agreement between the two settings")
    for r in RULES:
        same = sum(off[u]["judgment"][r] == on[u]["judgment"][r] for u in common)
        flips_to_fail = sum((not off[u]["judgment"][r]) and on[u]["judgment"][r] for u in common); flips_to_pass = sum(off[u]["judgment"][r] and not on[u]["judgment"][r] for u in common)
        P("  %-22s identical on %3d of %3d items (%.0f%%); off->on: %d pass->fail, %d fail->pass; fail rate off %.0f%%, on %.0f%%" % (r, same, len(common), 100 * same / len(common), flips_to_fail, flips_to_pass, 100 * sum(off[u]["judgment"][r] for u in common) / len(common), 100 * sum(on[u]["judgment"][r] for u in common) / len(common)))
    P("\n== Agreement with the human label under each setting (kappa [95% CI]); McNemar exact test on items where only one setting agrees with the human")
    if labels == "benchmarker":
        H = human_benchmarker(); groups = {r: [(u, g) for u, rr, g in H if rr == r and u in common] for r in RULES}
        for r, lab in groups.items():
            t_off = [0, 0, 0, 0]; t_on = [0, 0, 0, 0]; b = c = 0
            for u, g in lab:
                po, pn = bool(off[u]["judgment"][r]), bool(on[u]["judgment"][r])
                for pred, t in ((po, t_off), (pn, t_on)):
                    t[0 if pred and g else 1 if pred else 2 if g else 3] += 1
                if (po == g) and (pn != g): b += 1
                if (pn == g) and (po != g): c += 1
            ko, kn = kappa_from_table(*t_off), kappa_from_table(*t_on); co, cn = kappa_ci(*t_off), kappa_ci(*t_on)
            P("  %-22s off kappa %.2f [%.2f, %.2f]  on kappa %.2f [%.2f, %.2f]  | only-off-correct %d, only-on-correct %d, McNemar p=%.3f" % (r, ko, co[0], co[1], kn, cn[0], cn[1], b, c, mcnemar(b, c)))
    else:
        H = human_physician(); raters = sorted(set(h[3] for h in H))
        for rn in raters:
            P("  vs %s:" % rn)
            for r in ("single_best_answer", "plausible_distractors", "composite"):
                lab = [(u, g) for u, rr, g, who in H if rr == r and who == rn and u in common]
                t_off = [0, 0, 0, 0]; t_on = [0, 0, 0, 0]; b = c = 0
                for u, g in lab:
                    po = any(off[u]["judgment"][x] for x in RULES) if r == "composite" else bool(off[u]["judgment"][r])
                    pn = any(on[u]["judgment"][x] for x in RULES) if r == "composite" else bool(on[u]["judgment"][r])
                    for pred, t in ((po, t_off), (pn, t_on)):
                        t[0 if pred and g else 1 if pred else 2 if g else 3] += 1
                    if (po == g) and (pn != g): b += 1
                    if (pn == g) and (po != g): c += 1
                ko, kn = kappa_from_table(*t_off), kappa_from_table(*t_on); co, cn = kappa_ci(*t_off), kappa_ci(*t_on)
                P("  %-22s off kappa %.2f [%.2f, %.2f] (tp %d fp %d fn %d)  on kappa %.2f [%.2f, %.2f] (tp %d fp %d fn %d)  | only-off-correct %d, only-on-correct %d, McNemar p=%.3f" % (r, ko, co[0], co[1], t_off[0], t_off[1], t_off[2], kn, cn[0], cn[1], t_on[0], t_on[1], t_on[2], b, c, mcnemar(b, c)))
    if out_path: pathlib.Path(out_path).write_text(buf.getvalue()); print("\nwritten ->", out_path)

if __name__ == "__main__":
    main()
