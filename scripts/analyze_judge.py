"""Prevalence of Tier-B (judge) flaws by model x condition, and agreement between two judges on shared items.
Usage: python3 scripts/analyze_judge.py data/generated/judge_A_full.jsonl [data/generated/judge_B_full_sub1600.jsonl]
"""
import json, sys, collections, statistics
RULES = ["single_best_answer", "plausible_distractors", "no_extraneous_info", "focused_stem", "problem_in_stem", "clear_language", "no_absolute_terms", "no_vague_terms", "no_logical_cues"]
def load(p):
    d = {}
    for l in open(p):
        r = json.loads(l)
        if r.get("judgment"): d[r["uid"]] = r
    return d
A = load(sys.argv[1])
RULES = [k for k in RULES if all(k in r["judgment"] for r in A.values())]
print(f"{sys.argv[1]}: {len(A)} judged items, cost ${sum(float(r.get('cost_usd') or 0) for r in A.values()):.2f}")
groups = collections.defaultdict(list)
for r in A.values(): groups[(r["model_label"], r["condition"])].append(r["judgment"])
print("\n== Tier-B flaw prevalence (%) by model x condition (judge = %s)" % next(iter(A.values()))["judge"])
print("%-20s %-7s %4s | " % ("model", "cond", "n") + " ".join("%7s" % k[:7] for k in RULES) + " | any")
for (m, c), js in sorted(groups.items()):
    n = len(js); vals = [100 * sum(j[k] for j in js) / n for k in RULES]; anyf = 100 * sum(any(j[k] for k in RULES) for j in js) / n
    print("%-20s %-7s %4d | " % (m[:20], c, n) + " ".join("%7.1f" % v for v in vals) + " | %5.1f" % anyf)
print("\n== Guided vs plain, pooled: fail rate per rule")
for k in RULES:
    p = [j[k] for (m, c), js in groups.items() if c == "plain" for j in js]; g = [j[k] for (m, c), js in groups.items() if c == "guided" for j in js]
    print("  %-22s plain %5.1f%%  guided %5.1f%%" % (k, 100 * statistics.mean(p), 100 * statistics.mean(g)))
if len(sys.argv) > 2:
    B = load(sys.argv[2]); shared = set(A) & set(B)
    print(f"\n== Judge agreement on {len(shared)} shared items (judge B = {next(iter(B.values()))['judge']})")
    for k in RULES:
        a = [A[u]["judgment"][k] for u in shared]; b = [B[u]["judgment"][k] for u in shared]
        n = len(a); po = sum(x == y for x, y in zip(a, b)) / n
        pa = sum(a) / n; pb = sum(b) / n; pe = pa * pb + (1 - pa) * (1 - pb)
        kap = (po - pe) / (1 - pe) if pe < 1 else float("nan")
        print("  %-22s agreement %.2f  kappa %.2f  (fail rate A %.1f%%, B %.1f%%)" % (k, po, kap, 100 * pa, 100 * pb))
