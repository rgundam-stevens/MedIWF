"""Amendment 3: robustness of the guideline effect to the wording of the guidelines. Condition guided2 (a paraphrased,
re-ordered checklist of the same ten rules; same output template as guided) is compared with the plain and guided arms of
the main corpus on the same topics: any-flaw prevalence, guided2-vs-plain OR (cluster-robust by topic), per-flaw rates,
alphabetization compliance and key position.
Usage: python3 scripts/analyze_wording.py outputs/flags_wording.csv outputs/flags_full.csv [outputs/analysis_wording_v1.txt]
"""
import sys, pathlib, collections, io
import pandas as pd
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from mediwf.stats import logit_cluster, bh_fdr, wilson
from mediwf.rules import CORE   # the 14 Tier-A flaws; one definition for every script
def main(w_path, full_path, out_path=None):
    buf = io.StringIO()
    def P(*a): print(*a); print(*a, file=buf)
    w = pd.read_csv(w_path); f = pd.read_csv(full_path)
    w = w[w.condition == "guided2"].copy(); tops = sorted(w.topic_index.unique())
    base = f[f.condition.isin(["plain", "guided"]) & f.topic_index.isin(tops) & (f.get("reasoning_mode", "off") == "off")].copy()
    df = pd.concat([base, w], ignore_index=True)
    df["topic"] = df.specialty + ":" + df.topic_index.astype(str); df["core_any"] = (df[CORE].sum(axis=1) > 0).astype(int)
    df["guided_any"] = df.condition.isin(["guided", "guided2"]).astype(int); df["g2"] = (df.condition == "guided2").astype(int)
    ref_spec = sorted(df.specialty.unique())[0]; models = sorted(w.model_label.unique())
    P("Wording arm: %d guided2 items; comparison plain %d, guided %d items (same topics)" % (len(w), (df.condition == "plain").sum(), (df.condition == "guided").sum()))
    for c in ("plain", "guided", "guided2"):
        s = df[df.condition == c]; p, lo, hi = wilson(s.core_any.sum(), len(s))
        P("  %-8s any flaw %5.1f%% [%4.1f, %4.1f]  P(key=A)=%.2f  non-alphabetical=%.1f%%" % (c, 100 * p, 100 * lo, 100 * hi, (s.key == "A").mean(), 100 * s.options_not_alphabetical.mean()))
    r = logit_cluster(df[df.condition != "guided"], "core_any", ["guided_any"], {"model_label": models[0], "specialty": ref_spec}, "topic")["guided_any"]
    P("\nguided2 vs plain: OR = %.2f [%.2f, %.2f], p = %.2g   (compare guided vs plain in the main corpus, OR 0.50)" % (r["OR"], r["OR_lo"], r["OR_hi"], r["p"]))
    r = logit_cluster(df[df.condition != "plain"], "core_any", ["g2"], {"model_label": models[0], "specialty": ref_spec}, "topic")["g2"]
    P("guided2 vs guided: OR = %.2f [%.2f, %.2f], p = %.2g" % (r["OR"], r["OR_lo"], r["OR_hi"], r["p"]))
    P("\nPer model: any flaw plain / guided / guided2, and guided2-vs-plain OR (BH over %d models)" % len(models))
    rows = []
    for m in models:
        s = df[(df.model_label == m) & (df.condition != "guided")]
        rr = logit_cluster(s, "core_any", ["guided_any"], {"specialty": ref_spec}, "topic")["guided_any"]; rows.append((m, rr))
    adj = bh_fdr([rr["p"] for _, rr in rows])
    for (m, rr), q in zip(rows, adj):
        g = lambda c: 100 * df[(df.model_label == m) & (df.condition == c)].core_any.mean()
        P("  %-20s %5.1f%% / %5.1f%% / %5.1f%%   OR=%.2f [%.2f, %.2f] q=%.3g" % (m, g("plain"), g("guided"), g("guided2"), rr["OR"], rr["OR_lo"], rr["OR_hi"], q))
    P("\nPer-flaw prevalence (%): plain / guided / guided2")
    for fl in CORE + ["option_length_outlier", "options_not_alphabetical"]:
        v = [100 * df[df.condition == c][fl].mean() for c in ("plain", "guided", "guided2")]
        if sum(v): P("  %-26s %5.2f / %5.2f / %5.2f" % (fl, *v))
    if out_path: pathlib.Path(out_path).write_text(buf.getvalue()); print("\nwritten ->", out_path)
if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
