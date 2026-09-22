"""Amendment 1, A2: reasoning-on arm for the models whose hidden reasoning can be switched on and off through the API.
Compares reasoning on (run full_reasoning) with reasoning off (run full) for the same models, conditions and topics:
prevalence of any validated Tier-A flaw, per-flaw prevalence, key position, cluster-robust logistic regressions by topic.
Usage: python3 scripts/analyze_reasoning.py outputs/flags_full_reasoning.csv outputs/flags_full.csv [outputs/analysis_reasoning_v1.txt]
"""
import sys, pathlib, collections, io
import numpy as np, pandas as pd
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from mediwf.stats import logit_cluster, bh_fdr, chi2_uniform, wilson

from mediwf.rules import CORE   # the 14 Tier-A flaws; one definition for every script
def main(on_path, off_path, out_path=None):
    buf = io.StringIO()
    def P(*a):
        print(*a); print(*a, file=buf)
    on = pd.read_csv(on_path); off = pd.read_csv(off_path)
    on = on[on.condition.isin(["plain", "guided"])].copy()
    models = sorted(on.model_label.unique())
    off = off[off.model_label.isin(models) & off.condition.isin(["plain", "guided"]) & (off.get("reasoning_mode", "off") == "off")].copy()
    on["reason_on"] = 1; off["reason_on"] = 0
    df = pd.concat([on, off], ignore_index=True)
    df["topic"] = df["specialty"] + ":" + df["topic_index"].astype(str)
    df["guided"] = (df.condition == "guided").astype(int)
    df["core_any"] = (df[CORE].sum(axis=1) > 0).astype(int)
    ref_spec = sorted(df.specialty.unique())[0]
    P("Reasoning arm: %d items with reasoning on, %d matched items with reasoning off; models: %s" % (len(on), len(off), ", ".join(models)))
    P("items per model x condition x reasoning:"); P(df.groupby(["model_label", "condition", "reason_on"]).size().unstack().to_string())
    P("\nreasoning tokens when on (median [IQR]) / when off:")
    for m in models:
        a = on[on.model_label == m].reasoning_tokens; b = off[off.model_label == m].reasoning_tokens
        P("  %-20s on: %6.0f [%5.0f-%5.0f]  share>0=%.2f | off: median %5.0f share>0=%.2f" % (m, a.median(), a.quantile(.25), a.quantile(.75), (a > 0).mean(), b.median(), (b > 0).mean()))

    P("\n== Any validated Tier-A flaw, reasoning on vs off, Wilson 95% CI")
    for m in models:
        for c in ("plain", "guided"):
            for r_ in (0, 1):
                s = df[(df.model_label == m) & (df.condition == c) & (df.reason_on == r_)]
                p, lo, hi = wilson(s.core_any.sum(), len(s))
                P("  %-20s %-7s reasoning=%s  %5.1f%% [%4.1f, %4.1f] n=%d" % (m, c, "on " if r_ else "off", 100 * p, 100 * lo, 100 * hi, len(s)))

    P("\n== Effect of reasoning on any core flaw (adjusted for condition, model, specialty; cluster-robust by topic)")
    r = logit_cluster(df, "core_any", ["reason_on", "guided"], {"model_label": models[0], "specialty": ref_spec}, "topic")
    P("  pooled OR (on vs off) = %.2f [%.2f, %.2f], p = %.2g   | guided OR in same model = %.2f" % (r["reason_on"]["OR"], r["reason_on"]["OR_lo"], r["reason_on"]["OR_hi"], r["reason_on"]["p"], r["guided"]["OR"]))
    df["reason_x_guided"] = df.reason_on * df.guided
    r = logit_cluster(df, "core_any", ["reason_on", "guided", "reason_x_guided"], {"model_label": models[0], "specialty": ref_spec}, "topic")
    P("  interaction reasoning x guided: OR = %.2f [%.2f, %.2f], p = %.2g" % (r["reason_x_guided"]["OR"], r["reason_x_guided"]["OR_lo"], r["reason_x_guided"]["OR_hi"], r["reason_x_guided"]["p"]))
    pv = []; rows = []
    for m in models:
        s = df[df.model_label == m]
        rr = logit_cluster(s, "core_any", ["reason_on", "guided"], {"specialty": ref_spec}, "topic")["reason_on"]
        rows.append((m, rr)); pv.append(rr["p"])
    adj = bh_fdr(pv)
    for (m, rr), q in zip(rows, adj):
        P("  %-20s OR (on vs off)=%.2f [%.2f, %.2f] p=%.2g q=%.2g" % (m, rr["OR"], rr["OR_lo"], rr["OR_hi"], rr["p"], q))

    P("\n== Per-flaw effect of reasoning, pooled (adjusted for condition, model, specialty); flaws with >= 20 events")
    pv = []; rows = []
    for fl in CORE + ["option_length_outlier", "options_not_alphabetical"]:
        if df[fl].sum() < 20: continue
        rr = logit_cluster(df, fl, ["reason_on", "guided"], {"model_label": models[0], "specialty": ref_spec}, "topic")["reason_on"]
        rows.append((fl, 100 * df[df.reason_on == 0][fl].mean(), 100 * df[df.reason_on == 1][fl].mean(), rr)); pv.append(rr["p"])
    adj = bh_fdr(pv)
    for (fl, a, b, rr), q in zip(rows, adj):
        P("  %-26s off %5.1f%% -> on %5.1f%%  OR=%.2f [%.2f, %.2f] p=%.2g q=%.2g" % (fl, a, b, rr["OR"], rr["OR_lo"], rr["OR_hi"], rr["p"], q))

    P("\n== Key position by model x condition x reasoning (chi-square vs uniform; BH over the reasoning-on cells)")
    tests = []
    for m in models:
        for c in ("plain", "guided"):
            for r_ in (0, 1):
                s = df[(df.model_label == m) & (df.condition == c) & (df.reason_on == r_)]
                cnt = collections.Counter(s["key"]); stat, p = chi2_uniform(cnt)
                tests.append((m, c, r_, len(s), cnt.get("A", 0) / max(1, len(s)), stat, p, dict(sorted(cnt.items()))))
    adj = bh_fdr([t[6] for t in tests if t[2] == 1]); qi = iter(adj)
    for t in tests:
        q = next(qi) if t[2] == 1 else float("nan")
        P("  %-20s %-7s reasoning=%s n=%3d P(key=A)=%.2f chi2=%6.1f p=%.2g q=%s %s" % (t[0], t[1], "on " if t[2] else "off", t[3], t[4], t[5], t[6], ("%.2g" % q) if t[2] else "  -  ", t[7]))
    if out_path:
        pathlib.Path(out_path).write_text(buf.getvalue()); print("\nwritten ->", out_path)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
