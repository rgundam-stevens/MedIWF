"""Physician content ratings vs the detector's structural flags, by-condition comparison, rater-2 Step-1 list, and timing.
Reads the ingested rating CSVs, the (private) selection key and outputs/flags_full.csv; writes aggregate numbers only.
Usage: python3 scripts/content_rating_crosstab.py -> outputs/content_rating/main_ratings_crosstab_v1.txt
"""
import csv, collections, statistics, pathlib
from math import comb
root = pathlib.Path(__file__).resolve().parents[1]; CR = root / "outputs/content_rating"
CUE = ["negative_stem", "none_of_the_above", "all_of_the_above", "combination_options", "fill_in_blank", "true_false_stem", "longest_option_key",
       "absolute_terms", "vague_terms", "clang_cue", "grammatical_cue", "nonparallel_options", "numeric_not_ordered", "overlapping_options"]

def fisher(a, b, c, d):
    n = a + b + c + d; r1 = a + b; c1 = a + c
    p = lambda x: comb(r1, x) * comb(n - r1, c1 - x) / comb(n, c1)
    p0 = p(a); return sum(p(x) for x in range(max(0, c1 - (n - r1)), min(r1, c1) + 1) if p(x) <= p0 + 1e-12)

def main():
    key = {r["item_id"]: r for r in csv.DictReader(open(CR / "main_key_DO_NOT_SEND.csv"))}
    flags = {r["job_id"]: r for r in csv.DictReader(open(root / "outputs/flags_full.csv"))}
    raters = {}
    for p in sorted((CR / "ratings").glob("main_R*.csv")):
        if p.stem.count("_") == 1: raters[p.stem.split("_")[1]] = {r["item_id"]: r for r in csv.DictReader(open(p))}
    defect = lambda r: r["q1"] in ("no", "unsure") or r["q2"] == "no" or r["q3"] == "no" or r["q5"] == "no"
    out = ["Physician content ratings: %d raters (%s), %d items" % (len(raters), ", ".join(sorted(raters)), len(key))]
    out.append("\n== Content defect (composite) vs detector structural flag (any of the 14 Tier A rules) on the same items")
    tab = collections.defaultdict(collections.Counter)
    for iid, k in key.items():
        fl = any(flags[k["job_id"]][c] == "1" for c in CUE); g = "structurally flagged" if fl else "structurally clean"
        tab[g]["items"] += 1
        for rn, rr in raters.items(): tab[g][rn] += defect(rr[iid])
        tab[g]["all raters"] += all(defect(rr[iid]) for rr in raters.values()); tab[g]["any rater"] += any(defect(rr[iid]) for rr in raters.values())
    for g in ("structurally flagged", "structurally clean"):
        out.append("  %-21s items %3d | content defect by: %s | by all raters %d | by any rater %d" % (g, tab[g]["items"], ", ".join("%s %d" % (rn, tab[g][rn]) for rn in sorted(raters)), tab[g]["all raters"], tab[g]["any rater"]))
    out.append("\n== Agreement on the composite")
    rn = sorted(raters)
    if len(rn) == 2:
        a = sum(defect(raters[rn[0]][i]) and defect(raters[rn[1]][i]) for i in key); b = sum(defect(raters[rn[0]][i]) and not defect(raters[rn[1]][i]) for i in key)
        c = sum(not defect(raters[rn[0]][i]) and defect(raters[rn[1]][i]) for i in key); d = len(key) - a - b - c; n = len(key)
        po = (a + d) / n; pe = ((a + b) * (a + c) + (c + d) * (b + d)) / n / n
        out.append("  both %d, %s only %d, %s only %d, neither %d | raw agreement %.2f | kappa %.2f" % (a, rn[0], b, rn[1], c, d, po, (po - pe) / (1 - pe)))
    out.append("\n== By prompt condition")
    for rname, rr in raters.items():
        cc = collections.Counter(); nn = collections.Counter()
        for i, k in key.items(): nn[k["condition"]] += 1; cc[k["condition"]] += defect(rr[i])
        out.append("  %s: plain %d of %d, guided %d of %d" % (rname, cc["plain"], nn["plain"], cc["guided"], nn["guided"]))
    both = collections.Counter(); nn = collections.Counter()
    for i, k in key.items(): nn[k["condition"]] += 1; both[k["condition"]] += all(defect(rr[i]) for rr in raters.values())
    out.append("  flagged by all raters: plain %d of %d, guided %d of %d; Fisher exact two-sided p = %.3f" % (both["plain"], nn["plain"], both["guided"], nn["guided"], fisher(both["plain"], nn["plain"] - both["plain"], both["guided"], nn["guided"] - both["guided"])))
    q1 = collections.Counter(); q3 = collections.Counter(); q2 = collections.Counter()
    for i, k in key.items():
        q1[k["condition"]] += any(rr[i]["q1"] != "yes" for rr in raters.values()); q3[k["condition"]] += any(rr[i]["q3"] == "no" for rr in raters.values()); q2[k["condition"]] += any(rr[i]["q2"] == "no" for rr in raters.values())
    out.append("  by any rater: key not single best (Q1) plain %d guided %d (total %d); vignette inaccurate (Q3) plain %d guided %d (total %d); implausible distractor (Q2) plain %d guided %d (total %d)" % (q1["plain"], q1["guided"], sum(q1.values()), q3["plain"], q3["guided"], sum(q3.values()), q2["plain"], q2["guided"], sum(q2.values())))
    if len(rn) == 2:
        r1, r2 = raters[rn[0]], raters[rn[1]]
        uns = [i for i in key if r1[i]["q1"] == "unsure"]
        out.append("\n== Scale use: %s 'unsure' on Q1 for %d items; on those, %s Q1 %s and Q5 %s" % (rn[0], len(uns), rn[1], dict(collections.Counter(r2[i]["q1"] for i in uns)), dict(collections.Counter(r2[i]["q5"] for i in uns))))
    out.append("\n== Minutes per item (median): " + "; ".join("%s: defect items %.1f, other items %.1f" % (rname, statistics.median([float(rr[i]["minutes"]) for i in key if defect(rr[i]) and rr[i]["minutes"] != ""]), statistics.median([float(rr[i]["minutes"]) for i in key if not defect(rr[i]) and rr[i]["minutes"] != ""])) for rname, rr in raters.items()))
    s1 = CR / "ratings/step1_list_R2.csv"
    if s1.exists():
        ids = [r["item_id"] for r in csv.DictReader(open(s1))]
        cc = collections.Counter(key[i]["condition"] for i in ids); sp = collections.Counter(key[i]["specialty"] for i in ids); spn = collections.Counter(k["specialty"] for k in key.values())
        out.append("\n== Rater 2 post hoc 'Step 1-level' list: %d items; by condition %s; by specialty %s" % (len(ids), dict(cc), {s: "%d of %d" % (sp[s], spn[s]) for s in spn if sp[s]}))
    txt = "\n".join(out); print(txt); (CR / "main_ratings_crosstab_v1.txt").write_text(txt + "\n")

if __name__ == "__main__":
    main()
