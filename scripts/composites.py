"""Alternative flaw composites for the main corpus (added 17 Sep 2026, second audit):
  CORE        14 rules (primary outcome)
  SENSITIVITY 11 rules (CORE minus the three with poor external agreement)
  VALIDATED   10 rules (only rules tested against BenchMarker human labels)
  CORE, first repetition only (near-duplicate sensitivity)
For each: plain and guided prevalence with Wilson CIs, guided-vs-plain OR (adjusted for model and specialty, cluster-robust
by topic), per-model prevalence, and the same composites for the NBME reference items when outputs/flags_nbme.csv is present.
Usage: python3 scripts/composites.py outputs/flags_full.csv [outputs/analysis_composites_v1.txt]
"""
import sys, pathlib, io
import numpy as np, pandas as pd
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from mediwf.stats import logit_cluster, wilson
from mediwf.rules import CORE, SENSITIVITY, VALIDATED, UNVALIDATED, any_flaw

root = pathlib.Path(__file__).resolve().parents[1]


def main(path, out_path=None):
    buf = io.StringIO()
    def P(*a):
        print(*a); print(*a, file=buf)
    df = pd.read_csv(path)
    df = df[df.condition.isin(["plain", "guided"]) & (df.get("reasoning_mode", "off") == "off")].copy()
    df["topic"] = df.specialty + ":" + df.topic_index.astype(str); df["guided"] = (df.condition == "guided").astype(int)
    ref_m = sorted(df.model_label.unique())[0]; ref_s = sorted(df.specialty.unique())[0]
    nb = None
    if (root / "outputs" / "flags_nbme.csv").exists():
        nb = pd.read_csv(root / "outputs" / "flags_nbme.csv"); nb5 = nb[nb.n_options == 5]
    P("Composites on %d main-corpus items (plain + guided, reasoning off); detector %s" % (len(df), df.detector_version.iloc[0] if "detector_version" in df else "?"))
    P("  CORE (14):        %s" % ", ".join(CORE))
    P("  SENSITIVITY (11): CORE minus absolute_terms, vague_terms, grammatical_cue")
    P("  VALIDATED (10):   %s" % ", ".join(VALIDATED))
    P("  never externally validated: %s" % ", ".join(UNVALIDATED))
    sets = [("CORE (14 rules)", CORE, df), ("SENSITIVITY (11 rules)", SENSITIVITY, df), ("VALIDATED (10 rules)", VALIDATED, df),
            ("CORE, first repetition only", CORE, df[df.rep == 0] if "rep" in df else df)]
    P("\n%-30s %-24s %-24s %-24s %s" % ("composite", "plain % [CI]", "guided % [CI]", "OR guided vs plain", "NBME all / five-option %"))
    for name, rules, d in sets:
        d = d.copy(); d["y"] = any_flaw(d, rules)
        pp = wilson(d[d.guided == 0].y.sum(), (d.guided == 0).sum()); pg = wilson(d[d.guided == 1].y.sum(), (d.guided == 1).sum())
        r = logit_cluster(d, "y", ["guided"], {"model_label": ref_m, "specialty": ref_s}, "topic")["guided"]
        nbs = "%.1f / %.1f" % (100 * any_flaw(nb, rules).mean(), 100 * any_flaw(nb5, rules).mean()) if nb is not None else "n/a"
        P("%-30s %5.1f [%4.1f, %4.1f]      %5.1f [%4.1f, %4.1f]      %.2f [%.2f, %.2f] p=%.1e   %s" % (
            name, 100 * pp[0], 100 * pp[1], 100 * pp[2], 100 * pg[0], 100 * pg[1], 100 * pg[2], r["OR"], r["OR_lo"], r["OR_hi"], r["p"], nbs))
    P("\n== Share of flagged plain-prompt items flagged ONLY by never-validated rules")
    pl = df[df.guided == 0]
    flagged = any_flaw(pl, CORE) == 1; onlyunv = (any_flaw(pl, VALIDATED) == 0) & flagged
    P("  flagged %d of %d; flagged only by unvalidated rules %d (%.1f%% of flagged)" % (flagged.sum(), len(pl), onlyunv.sum(), 100 * onlyunv.sum() / flagged.sum()))
    P("\n== Per-model plain-prompt prevalence (%) under each composite")
    P("%-20s %8s %8s %8s" % ("model", "CORE14", "SENS11", "VALID10"))
    for m in sorted(df.model_label.unique()):
        s = pl[pl.model_label == m]
        P("%-20s %8.1f %8.1f %8.1f" % (m, 100 * any_flaw(s, CORE).mean(), 100 * any_flaw(s, SENSITIVITY).mean(), 100 * any_flaw(s, VALIDATED).mean()))
    if nb is not None:
        P("\n== NBME per-rule counts (all %d items / %d five-option items)" % (len(nb), len(nb5)))
        for f in CORE + ["option_length_outlier", "numeric_units_inconsistent", "options_not_alphabetical"]:
            P("  %-28s %4d / %4d" % (f, nb[f].sum(), nb5[f].sum()))
    if out_path:
        pathlib.Path(out_path).write_text(buf.getvalue()); print("\nwritten ->", out_path)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
