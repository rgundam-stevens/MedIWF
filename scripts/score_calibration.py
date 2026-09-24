"""Score the physician raters' 20-item calibration sheets against the planted-defect key (added 17 Sep 2026; the first
audit's scoring was done by hand, and the numeric threshold was recorded in Amendment 2 only after rater 1 had been scored).

Rule applied (the one used when the sheets were scored on 15-16 Sep, now written down):
  * a defective item counts as DETECTED when its PRIMARY question (the first question listed in the key's 'expected'
    field) is answered "no" or "unsure"; secondary expectations are reported but do not decide detection;
  * a sound ("clean") item counts as a FALSE ALARM when Q1 is answered "no" (a wrong-key claim on a sound item);
  * pass = at least 6 of the 8 planted defects detected AND no more than 2 false alarms on the 10 sound items
    (Amendment 2, A6; the guide sent to raters said "most of the defective items ... and must not flag sound items
    indiscriminately"). Both raters' outcomes are reported under the strict reading too (all expected answers required).
Usage: python3 scripts/score_calibration.py [-o outputs/content_rating/calibration_scores.txt]
"""
import csv, json, sys, pathlib, io, collections
root = pathlib.Path(__file__).resolve().parents[1]
KEY = root / "outputs/content_rating/calibration_key_DO_NOT_SEND.csv"
RATINGS = sorted((root / "outputs/content_rating/ratings").glob("calibration_R*.csv"))


def norm(v):
    v = (v or "").strip().lower()
    if v.startswith("y"): return "yes"
    if v.startswith("n"): return "no"
    if v.startswith("u"): return "unsure"
    if v.startswith("m"): return "minor edits"
    return v


def main(out_path=None):
    buf = io.StringIO()
    def P(*a):
        print(*a); print(*a, file=buf)
    key = list(csv.DictReader(open(KEY)))
    for path in RATINGS:
        rows = {r["item_id"]: r for r in csv.DictReader(open(path))}
        rater = next(iter(rows.values())).get("rater", path.stem)
        mins = [r["minutes"] for r in rows.values() if r.get("minutes") not in (None, "")]
        P("== %s (%s): %d items, %s" % (rater, path.name, len(rows), ("%s minutes" % sum(float(m) for m in mins)) if mins else "minutes not released"))
        det_planted = det_natural = strict_planted = 0; false_alarm = 0; lines = []
        for k in key:
            exp = json.loads(k["expected"] or "{}"); r = rows.get(k["item_id"], {})
            ans = {q: norm(r.get(q)) for q in ("q1", "q2", "q3", "q4", "q5")}
            if k["kind"] == "clean":
                fa = ans["q1"] == "no"; false_alarm += int(fa)
                lines.append("  %s clean    %s  %s" % (k["item_id"], " ".join("%s=%s" % (q, ans[q]) for q in ans), "FALSE ALARM" if fa else ""))
            else:
                primary = next(iter(exp)); ok = ans[primary] in ("no", "unsure")
                strict = all(ans[q] in v.split("/") for q, v in exp.items())
                if k["kind"] == "planted": det_planted += int(ok); strict_planted += int(strict)
                else: det_natural += int(ok)
                lines.append("  %s %-8s expected %-28s got %s  -> %s%s" % (k["item_id"], k["kind"], json.dumps(exp), " ".join("%s=%s" % (q, ans[q]) for q in exp), "detected" if ok else "MISSED", "" if strict or not ok else " (secondary expectation not met)"))
        for l in lines: P(l)
        n_pl = sum(k["kind"] == "planted" for k in key); n_nat = sum(k["kind"] == "natural" for k in key); n_cl = sum(k["kind"] == "clean" for k in key)
        passed = det_planted >= 6 and false_alarm <= 2
        P("  planted detected %d of %d (strict %d of %d); natural detected %d of %d; false alarms %d of %d sound items -> %s" % (
            det_planted, n_pl, strict_planted, n_pl, det_natural, n_nat, false_alarm, n_cl, "PASS" if passed else "FAIL"))
        P("")
    # agreement between raters on the 20 items
    if len(RATINGS) >= 2:
        A = {r["item_id"]: r for r in csv.DictReader(open(RATINGS[0]))}; B = {r["item_id"]: r for r in csv.DictReader(open(RATINGS[1]))}
        P("== Agreement between the two raters on the 20 calibration items (raw agreement; Cohen's kappa for yes vs not-yes)")
        for q in ("q1", "q2", "q3", "q4", "q5"):
            a = [norm(A[i][q]) for i in A if i in B]; b = [norm(B[i][q]) for i in A if i in B]
            agree = sum(x == y for x, y in zip(a, b)) / len(a)
            ya = [x == "yes" for x in a]; yb = [x == "yes" for x in b]
            po = sum(x == y for x, y in zip(ya, yb)) / len(a); pa = sum(ya) / len(a); pb = sum(yb) / len(a); pe = pa * pb + (1 - pa) * (1 - pb)
            kap = (po - pe) / (1 - pe) if pe < 1 else float("nan")
            P("  %s agreement %.2f  kappa %.2f" % (q, agree, kap))
    if out_path:
        pathlib.Path(out_path).write_text(buf.getvalue()); print("written ->", out_path)


if __name__ == "__main__":
    main(sys.argv[sys.argv.index("-o") + 1] if "-o" in sys.argv else None)
