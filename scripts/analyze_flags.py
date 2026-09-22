"""Descriptive analysis of flaw flags: prevalence with Wilson 95% CIs by model and condition, key-position chi-square,
and (for NBME) flagged vs unflagged difficulty / response time.

Usage:
  python3 scripts/analyze_flags.py outputs/flags_full.csv
  python3 scripts/analyze_flags.py outputs/flags_nbme.csv --nbme
"""
import sys, math, csv, collections, statistics, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from mediwf.rules import CORE, any_flaw   # "any flaw" = the 14 core rules (v1.2 audit fix: earlier versions used n_flaws, which
# also counted option_length_outlier and numeric_units_inconsistent, giving a different number from Table 3)
def _any(r): return any(int(r[f]) for f in CORE)
def _n(r): return sum(int(r[f]) for f in CORE)

FLAWS = ["negative_stem", "none_of_the_above", "all_of_the_above", "combination_options", "fill_in_blank", "true_false_stem",
         "longest_option_key", "option_length_outlier", "absolute_terms", "vague_terms", "clang_cue", "grammatical_cue",
         "nonparallel_options", "numeric_not_ordered", "numeric_units_inconsistent", "overlapping_options", "options_not_alphabetical"]

def wilson(k, n, z=1.96):
    if n == 0: return (float("nan"), float("nan"), float("nan"))
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0.0, c - h), min(1.0, c + h)

def chi2_uniform(counts, letters="ABCDE"):
    # v1.2 audit fix: always five cells (A-E); a letter with zero observed count used to shrink k
    n = sum(counts.get(l, 0) for l in letters)
    if n == 0: return float("nan")
    e = n / len(letters)
    return sum((counts.get(l, 0) - e) ** 2 / e for l in letters)

def main(path, nbme=False):
    rows = list(csv.DictReader(open(path)))
    print(f"{len(rows)} items in {path}\n")
    if nbme:
        print("== NBME: prevalence of each flaw (all %d retired USMLE items)" % len(rows))
        for fl in FLAWS:
            k = sum(int(r[fl]) for r in rows); p, lo, hi = wilson(k, len(rows))
            print(f"  {fl:<28} {k:4d}  {100*p:5.1f}%  [{100*lo:4.1f}, {100*hi:4.1f}]")
        k = sum(1 for r in rows if _any(r)); p, lo, hi = wilson(k, len(rows))
        print(f"  {'ANY CORE FLAW (14 rules)':<28} {k:4d}  {100*p:5.1f}%  [{100*lo:4.1f}, {100*hi:4.1f}]")
        print("\n== NBME: key position", dict(collections.Counter(r["key"] for r in rows)), "chi2 vs uniform (all items, A-E) =", round(chi2_uniform(collections.Counter(r["key"] for r in rows if r["key"] in "ABCDE")), 1))
        five = [r for r in rows if r["n_options"] == "5"]
        print("== NBME: five-option items only (n=%d, the comparable set): key position %s chi2 vs uniform = %.1f" % (
            len(five), dict(sorted(collections.Counter(r["key"] for r in five).items())), chi2_uniform(collections.Counter(r["key"] for r in five if r["key"] in "ABCDE"))))
        k = sum(1 for r in five if _any(r)); p, lo, hi = wilson(k, len(five))
        print(f"== NBME: five-option items: ANY CORE FLAW (14 rules) {k:4d}  {100*p:5.1f}%  [{100*lo:4.1f}, {100*hi:4.1f}]")
        print("== NBME: prevalence of each flaw, five-option items only")
        for fl in FLAWS:
            k = sum(int(r[fl]) for r in five); p, lo, hi = wilson(k, len(five))
            print(f"  {fl:<28} {k:4d}  {100*p:5.1f}%  [{100*lo:4.1f}, {100*hi:4.1f}]")
        print("\n== NBME: mean difficulty / response time, flagged vs unflagged (any core flaw = 14 rules)")
        for fl in ["any_core"] + FLAWS:
            if fl == "options_not_alphabetical": continue
            if fl == "any_core": a = [r for r in rows if _any(r)]; b = [r for r in rows if not _any(r)]
            else: a = [r for r in rows if int(r[fl]) > 0]; b = [r for r in rows if int(r[fl]) == 0]
            if len(a) < 5 or len(b) < 5: continue
            md = statistics.mean(float(r["Difficulty"]) for r in a) - statistics.mean(float(r["Difficulty"]) for r in b)
            mt = statistics.mean(float(r["Response_Time"]) for r in a) - statistics.mean(float(r["Response_Time"]) for r in b)
            print(f"  {fl:<28} n_flagged={len(a):4d}  d(difficulty)={md:+.3f}  d(response_time)={mt:+.1f}s")
        return
    groups = collections.defaultdict(list)
    for r in rows: groups[(r["model_label"], r["condition"])].append(r)
    print("== Prevalence (%) of each flaw by model x condition  [Wilson 95% CI in brackets for 'any flaw']")
    header = "%-22s %-7s %4s | any-flaw%% [CI]         | " % ("model", "cond", "n") + " ".join("%6s" % f[:6] for f in FLAWS)
    print(header)
    for (m, c), rs in sorted(groups.items()):
        n = len(rs); anyk = sum(1 for r in rs if _any(r)); p, lo, hi = wilson(anyk, n)
        vals = " ".join("%6.1f" % (100 * sum(int(r[f]) for r in rs) / n) for f in FLAWS)
        print("%-22s %-7s %4d | %5.1f [%4.1f,%4.1f]      | %s" % (m[:22], c, n, 100 * p, 100 * lo, 100 * hi, vals))
    print("\n== Mean core flaws (14 rules) per item by model (plain -> guided) and relative change")
    for m in sorted({k[0] for k in groups}):
        a = groups.get((m, "plain"), []); b = groups.get((m, "guided"), [])
        if a and b:
            ma = statistics.mean(_n(r) for r in a); mb = statistics.mean(_n(r) for r in b)
            print("  %-22s %.2f -> %.2f  (%+.0f%%)" % (m[:22], ma, mb, 100 * (mb - ma) / ma if ma else float("nan")))
    print("\n== Key position by model x condition (chi-square vs uniform over A-E; df=4, 9.49 = p<.05, 18.5 = p<.001)")
    for (m, c), rs in sorted(groups.items()):
        cnt = collections.Counter(r["key"] for r in rs if r["key"] in "ABCDE")
        print("  %-22s %-7s %s chi2=%.1f" % (m[:22], c, dict(sorted(cnt.items())), chi2_uniform(cnt)))

if __name__ == "__main__":
    main(sys.argv[1], nbme="--nbme" in sys.argv)
