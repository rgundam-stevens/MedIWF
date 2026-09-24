"""Physician content ratings of the 100-item main set (Amendment 2, A6).

Step 1 - normalise a returned workbook into a CSV (one per rater), with a format-compliance report that can be sent back to
         the rater: every row present, only a rating word in each Q column (free text is normalised by its first word and
         reported), a justification for every no/unsure/minor-edits rating, minutes per item.
Step 2 - analyse the normalised CSVs: prevalence of each content flaw with Wilson 95% CIs, overall and by prompt condition
         and by model (via the hidden key, which maps item ids to jobs; item text is never printed); Cohen's kappa between
         raters per question when two files are present; internal-consistency notes (Q1 = no with Q5 = yes, etc.).

Usage:
  python3 scripts/analyze_content_ratings.py ingest path/to/returned.xlsx R1      # -> outputs/content_rating/ratings/main_R1.csv + format report
  python3 scripts/analyze_content_ratings.py report [-o outputs/content_rating/main_ratings_report.txt]
"""
import sys, csv, io, json, pathlib, collections, datetime, math
root = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "src"))
from mediwf.stats import wilson
RAT = root / "outputs/content_rating/ratings"
KEY = root / "outputs/content_rating/main_key_DO_NOT_SEND.csv"
QS = ["q1", "q2", "q3", "q4", "q5"]
ALLOWED = {"q1": {"yes", "no", "unsure"}, "q2": {"yes", "no", "unsure"}, "q3": {"yes", "no", "unsure"}, "q4": {"yes", "no", "unsure"}, "q5": {"yes", "minor edits", "no"}}


def norm(v):
    s = str(v if v is not None else "").strip().lower().replace("’", "'")
    if not s: return ""
    first = s.split()[0].strip(".,;:()-")
    if first.startswith("y"): return "yes"
    if first.startswith("n"): return "no"
    if first.startswith("u"): return "unsure"
    if first.startswith("m") or s.startswith("minor"): return "minor edits"
    return s


def _read_xlsx(path):
    from openpyxl import load_workbook
    ws = load_workbook(path, data_only=True).active
    hdr = [str(c.value or "").strip() for c in ws[1]]
    def col(prefix):
        for i, h in enumerate(hdr):
            if h.lower().startswith(prefix.lower()): return i
        raise KeyError(prefix)
    ci = {"item_id": col("item_id"), "key": col("keyed_answer"), "q1": col("Q1"), "q2": col("Q2"), "q3": col("Q3"), "q4": col("Q4"), "q5": col("Q5"), "just": col("justification"), "min": col("minutes")}
    out = []
    for r in ws.iter_rows(min_row=2, values_only=True):
        if r[ci["item_id"]] is None: continue
        out.append({k: r[i] for k, i in ci.items()})
    return out


def _read_json(path):
    """Rows exported from a returned workbook as [item_id, keyed_answer, q1..q5, justification, minutes] lists."""
    out = []
    for a in json.load(open(path)):
        out.append({"item_id": a[0], "key": a[1], "q1": a[2], "q2": a[3], "q3": a[4], "q4": a[5], "q5": a[6], "just": a[7], "min": a[8]})
    return out


def ingest(path, rater):
    recs = _read_json(path) if str(path).endswith(".json") else _read_xlsx(path)
    rows = []; problems = []
    for rec in recs:
        iid = str(rec["item_id"]).strip()
        raw = {q: rec[q] for q in QS}
        vals = {q: norm(raw[q]) for q in QS}
        just = str(rec["just"] or "").strip()
        mins = rec["min"]
        try: mins = float(str(mins).strip().split()[0]) if mins not in (None, "") else None
        except ValueError: mins = None
        for q in QS:
            if vals[q] == "": problems.append((iid, "%s is blank" % q.upper()))
            elif vals[q] not in ALLOWED[q]: problems.append((iid, "%s has an unrecognised value: %r" % (q.upper(), str(raw[q])[:40])))
            elif str(raw[q]).strip().lower() != vals[q]: problems.append((iid, "%s contains extra text (%r); only the rating word should be in the cell" % (q.upper(), str(raw[q])[:60])))
        needs_just = any(vals[q] in ("no", "unsure") for q in QS[:4]) or vals["q5"] in ("no", "minor edits")
        if needs_just and not just: problems.append((iid, "justification missing for a no/unsure/minor-edits rating"))
        if mins is None: problems.append((iid, "minutes spent is blank or not a number"))
        rows.append({"item_id": iid, "keyed_answer": rec["key"], **vals, "justification": just, "minutes": mins if mins is not None else "", "rater": rater,
                     "submitted_utc": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M"), **{q + "_raw": str(raw[q] or "") for q in QS}})
    expected = [k["item_id"] for k in csv.DictReader(open(KEY))]
    got = {r["item_id"] for r in rows}
    missing = [i for i in expected if i not in got]
    if missing: problems.append(("(sheet)", "%d items missing: %s" % (len(missing), ", ".join(missing[:10]))))
    extra = [i for i in got if i not in set(expected)]
    if extra: problems.append(("(sheet)", "%d unexpected item ids: %s" % (len(extra), ", ".join(extra[:10]))))
    out = RAT / ("main_%s.csv" % rater)
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    rep = RAT / ("main_%s_format_report.txt" % rater)
    lines = ["Format check of %s (%s): %d rows read; %d problems" % (path, rater, len(rows), len(problems))]
    for iid, msg in problems: lines.append("  %s: %s" % (iid, msg))
    cnt = {q: collections.Counter(r[q] for r in rows) for q in QS}
    lines.append("Rating counts: " + "; ".join("%s %s" % (q.upper(), dict(cnt[q])) for q in QS))
    mins = [r["minutes"] for r in rows if r["minutes"] != ""]
    if mins: lines.append("Minutes: total %.0f, median %.1f, min %.1f, max %.1f, items with < 1 minute: %d" % (sum(mins), sorted(mins)[len(mins) // 2], min(mins), max(mins), sum(m < 1 for m in mins)))
    # internal consistency (for the reviewer, not necessarily errors)
    inc = []
    for r in rows:
        if r["q1"] == "no" and r["q5"] == "yes": inc.append("%s: Q1 = no (key not the best answer) but Q5 = yes (accept as written)" % r["item_id"])
        if r["q5"] == "no" and all(r[q] == "yes" for q in QS[:4]): inc.append("%s: Q5 = no but Q1-Q4 all yes (what makes it unusable?)" % r["item_id"])
        if r["q3"] == "no" and r["q5"] == "yes": inc.append("%s: Q3 = no (inaccurate/inconsistent vignette) but Q5 = yes" % r["item_id"])
    lines.append("Internal-consistency notes (%d):" % len(inc)); lines += ["  " + x for x in inc]
    rep.write_text("\n".join(lines) + "\n"); print("\n".join(lines)); print("written ->", out, "and", rep)


def kappa(a, b):
    n = len(a); cats = sorted(set(a) | set(b))
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in cats)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def report(out_path=None):
    buf = io.StringIO()
    def P(*a):
        print(*a); print(*a, file=buf)
    key = {k["item_id"]: k for k in csv.DictReader(open(KEY))}
    files = sorted(RAT.glob("main_R*.csv"))
    raters = {p.stem.split("_")[1]: {r["item_id"]: r for r in csv.DictReader(open(p))} for p in files}
    P("Physician content ratings, main set: %d rater file(s): %s; %d items in key" % (len(raters), ", ".join(raters), len(key)))
    labels = {"q1": "keyed answer is the single best answer", "q2": "every distractor plausible", "q3": "vignette accurate and consistent", "q4": "tests a meaningful decision", "q5": "acceptable as written"}
    for rn, rows in raters.items():
        mins = [r["minutes"] for r in rows.values() if r.get("minutes") not in (None, "")]
        P("\n== %s: %d items rated; minutes total %s" % (rn, len(rows), ("%.0f" % sum(float(m) for m in mins)) if mins else "not released (per-item minutes are not in the public rating files)"))
        for q in QS:
            neg = "no" if q != "q5" else "no"
            n = len(rows); k_no = sum(r[q] == "no" for r in rows.values()); k_uns = sum(r[q] == "unsure" for r in rows.values()); k_min = sum(r[q] == "minor edits" for r in rows.values())
            p, lo, hi = wilson(k_no, n)
            P("  %s %-40s no %3d (%.0f%% [%.0f, %.0f])  unsure %d  minor edits %d" % (q.upper(), labels[q], k_no, 100 * p, 100 * lo, 100 * hi, k_uns, k_min))
        anyflaw = [iid for iid, r in rows.items() if r["q1"] in ("no", "unsure") or r["q2"] == "no" or r["q3"] == "no" or r["q5"] == "no"]
        p, lo, hi = wilson(len(anyflaw), len(rows))
        P("  any content defect (Q1 no/unsure, Q2 no, Q3 no or Q5 no): %d of %d (%.0f%% [%.0f, %.0f])" % (len(anyflaw), len(rows), 100 * p, 100 * lo, 100 * hi))
        for cond in ("plain", "guided"):
            ids = [i for i in rows if key.get(i, {}).get("condition") == cond]
            k = sum(i in anyflaw for i in ids); p, lo, hi = wilson(k, len(ids))
            P("    %-7s any defect %d of %d (%.0f%% [%.0f, %.0f]); Q1 not best %d; Q5 unusable %d" % (cond, k, len(ids), 100 * p, 100 * lo, 100 * hi, sum(rows[i]["q1"] in ("no", "unsure") for i in ids), sum(rows[i]["q5"] == "no" for i in ids)))
        bym = collections.defaultdict(lambda: [0, 0])
        for i, r in rows.items():
            m = key.get(i, {}).get("model", "?"); bym[m][1] += 1; bym[m][0] += int(i in anyflaw)
        P("    by model (defects/items): " + ", ".join("%s %d/%d" % (m, v[0], v[1]) for m, v in sorted(bym.items())))
    if len(raters) >= 2:
        (a, A), (b, B) = list(raters.items())[:2]
        common = [i for i in A if i in B]
        P("\n== Agreement between %s and %s on %d items" % (a, b, len(common)))
        for q in QS:
            x = [A[i][q] for i in common]; y = [B[i][q] for i in common]
            xb = ["yes" if v == "yes" else "not-yes" for v in x]; yb = ["yes" if v == "yes" else "not-yes" for v in y]
            P("  %s raw agreement %.2f  kappa (all categories) %.2f  kappa (yes vs not-yes) %.2f  positives %s: %d, %s: %d" % (q.upper(), sum(p == q_ for p, q_ in zip(x, y)) / len(x), kappa(x, y), kappa(xb, yb), a, xb.count("not-yes"), b, yb.count("not-yes")))
        both = [i for i in common if (A[i]["q1"] in ("no", "unsure")) and (B[i]["q1"] in ("no", "unsure"))]
        either = [i for i in common if (A[i]["q1"] in ("no", "unsure")) or (B[i]["q1"] in ("no", "unsure"))]
        P("  Q1 not-best flagged by both: %d; by either: %d" % (len(both), len(either)))
        # composite defect: 2x2 table, kappa with bootstrap CI, positive specific agreement (added 21 Sep 2026)
        import sys as _sys; _sys.path.insert(0, str(root / "src"))
        from mediwf.stats import kappa_ci, kappa_from_table
        def defect(r): return r["q1"] in ("no", "unsure") or r["q2"] == "no" or r["q3"] == "no" or r["q5"] == "no"
        tp = sum(defect(A[i]) and defect(B[i]) for i in common); fp = sum(defect(A[i]) and not defect(B[i]) for i in common)
        fn = sum((not defect(A[i])) and defect(B[i]) for i in common); tn = len(common) - tp - fp - fn
        kc = kappa_ci(tp, fp, fn, tn); psa = 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) else float("nan")
        P("  composite defect: both %d, %s only %d, %s only %d, neither %d | raw agreement %.2f | kappa %.2f [95%% bootstrap CI %.2f, %.2f] | positive specific agreement %.2f" % (tp, a, fp, b, fn, tn, (tp + tn) / len(common), kappa_from_table(tp, fp, fn, tn), kc[0], kc[1], psa))
        for q in QS:
            xb = [A[i][q] != "yes" for i in common]; yb = [B[i][q] != "yes" for i in common]
            tp_ = sum(x and y for x, y in zip(xb, yb)); fp_ = sum(x and not y for x, y in zip(xb, yb)); fn_ = sum((not x) and y for x, y in zip(xb, yb)); tn_ = len(common) - tp_ - fp_ - fn_
            if tp_ + fp_ + fn_ == 0: continue
            kc = kappa_ci(tp_, fp_, fn_, tn_)
            P("    %s (yes vs not-yes): kappa %.2f [%.2f, %.2f]; positive specific agreement %.2f" % (q.upper(), kappa_from_table(tp_, fp_, fn_, tn_), kc[0], kc[1], 2 * tp_ / (2 * tp_ + fp_ + fn_)))
    if out_path:
        pathlib.Path(out_path).write_text(buf.getvalue()); print("\nwritten ->", out_path)


if __name__ == "__main__":
    if sys.argv[1] == "ingest": ingest(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "report": report(sys.argv[sys.argv.index("-o") + 1] if "-o" in sys.argv else None)
