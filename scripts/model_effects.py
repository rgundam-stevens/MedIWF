"""Inferential analysis for RQ2/RQ3 on the MedIWF corpus flags (no item text needed). Handles the 15-model corpus
(8 base + 7 flagship). Cluster-robust logistic regressions (clusters = topics) for the effect of the guided prompt,
per model and per flaw; base-vs-flagship tier comparison; key-position chi-square tests with BH-FDR correction;
exploratory association between hidden-reasoning tokens and flaws.
Usage: python3 scripts/model_effects.py outputs/flags_full.csv [outputs/model_effects_v3.txt]
"""
import sys, pathlib, collections, io
import numpy as np, pandas as pd
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from mediwf.stats import logit_cluster, bh_fdr, chi2_uniform, wilson

from mediwf.rules import CORE   # the 14 Tier-A flaws; one definition for every script

def main(path, out_path=None):
    buf = io.StringIO()
    def P(*a):
        print(*a); print(*a, file=buf)
    df = pd.read_csv(path)
    df = df[df["condition"].isin(["plain", "guided"]) & (df.get("reasoning_mode", "off") == "off")].copy()
    if "tier" not in df: df["tier"] = "base"
    df["topic"] = df["specialty"] + ":" + df["topic_index"].astype(str)
    df["guided"] = (df["condition"] == "guided").astype(int)
    df["flagship"] = (df["tier"] == "flagship").astype(int)
    df["core_any"] = (df[CORE].sum(axis=1) > 0).astype(int)
    df["keyA"] = (df["key"] == "A").astype(int)
    models = sorted(df["model_label"].unique())
    tier_of = df.groupby("model_label")["tier"].first().to_dict()
    ref_model = models[0]; ref_spec = sorted(df.specialty.unique())[0]
    P("N items = %d; models = %d (%d base, %d flagship); topics = %d" % (len(df), len(models), sum(v == "base" for v in tier_of.values()),
                                                                      sum(v == "flagship" for v in tier_of.values()), df["topic"].nunique()))
    P("items per model x condition:"); P(df.groupby(["model_label", "condition"]).size().unstack().to_string())

    P("\n== Prevalence of ANY core structural flaw (validated rules), with Wilson 95% CI")
    for cond in ("plain", "guided"):
        for m in models:
            s = df[(df.model_label == m) & (df.condition == cond)]
            p, lo, hi = wilson(s.core_any.sum(), len(s))
            P("  %-7s %-20s %-9s %5.1f%% [%4.1f, %4.1f]  n=%d" % (cond, m, tier_of[m], 100 * p, 100 * lo, 100 * hi, len(s)))
    for t in ("base", "flagship"):
        for cond in ("plain", "guided"):
            s = df[(df.tier == t) & (df.condition == cond)]
            p, lo, hi = wilson(s.core_any.sum(), len(s))
            P("  %-7s %-20s %-9s %5.1f%% [%4.1f, %4.1f]  n=%d" % (cond, "ALL " + t.upper(), "", 100 * p, 100 * lo, 100 * hi, len(s)))

    P("\n== Effect of the guided prompt on any core flaw, adjusted for model and specialty (cluster-robust by topic)")
    r = logit_cluster(df, "core_any", ["guided"], {"model_label": ref_model, "specialty": ref_spec}, "topic")
    g = r["guided"]
    P("  overall OR (guided vs plain) = %.2f [%.2f, %.2f], p = %.2e" % (g["OR"], g["OR_lo"], g["OR_hi"], g["p"]))
    for t in ("base", "flagship"):
        s = df[df.tier == t]
        rr = logit_cluster(s, "core_any", ["guided"], {"model_label": sorted(s.model_label.unique())[0], "specialty": ref_spec}, "topic")["guided"]
        P("  %-9s OR (guided vs plain) = %.2f [%.2f, %.2f], p = %.2e" % (t, rr["OR"], rr["OR_lo"], rr["OR_hi"], rr["p"]))

    P("\n== Tier comparison: flagship vs base, any core flaw (adjusted for condition and specialty; cluster-robust by topic)")
    P("   note: models are nested in tiers, so this compares the two groups of models, not a within-model change")
    r = logit_cluster(df, "core_any", ["flagship", "guided"], {"specialty": ref_spec}, "topic")
    P("  flagship OR = %.2f [%.2f, %.2f], p = %.2e   (guided OR in same model = %.2f)" % (r["flagship"]["OR"], r["flagship"]["OR_lo"], r["flagship"]["OR_hi"], r["flagship"]["p"], r["guided"]["OR"]))
    df["flagship_x_guided"] = df["flagship"] * df["guided"]
    r = logit_cluster(df, "core_any", ["flagship", "guided", "flagship_x_guided"], {"specialty": ref_spec}, "topic")
    P("  interaction flagship x guided: OR = %.2f [%.2f, %.2f], p = %.2g" % (r["flagship_x_guided"]["OR"], r["flagship_x_guided"]["OR_lo"], r["flagship_x_guided"]["OR_hi"], r["flagship_x_guided"]["p"]))
    for cond in ("plain", "guided"):
        s = df[df.condition == cond]
        rr = logit_cluster(s, "core_any", ["flagship"], {"specialty": ref_spec}, "topic")["flagship"]
        P("  %-7s flagship vs base OR = %.2f [%.2f, %.2f], p = %.2g" % (cond, rr["OR"], rr["OR_lo"], rr["OR_hi"], rr["p"]))

    P("\n== Per-model effect of the guided prompt on any core flaw (separate models per generator, adjusted for specialty); BH over %d tests" % len(models))
    pv = []; rows = []
    for m in models:
        s = df[df.model_label == m]
        r = logit_cluster(s, "core_any", ["guided"], {"specialty": ref_spec}, "topic")["guided"]
        rows.append((m, r)); pv.append(r["p"])
    adj = bh_fdr(pv)
    for (m, r), q in zip(rows, adj):
        P("  %-20s %-9s OR=%.2f [%.2f, %.2f]  p=%.3g  q(BH)=%.3g" % (m, tier_of[m], r["OR"], r["OR_lo"], r["OR_hi"], r["p"], q))

    P("\n== Per-flaw effect of the guided prompt, pooled over models (adjusted for model and specialty); flaws with >= 30 events")
    pv = []; rows = []
    for fl in CORE + ["option_length_outlier", "options_not_alphabetical", "keyA"]:
        if df[fl].sum() < 30: continue
        r = logit_cluster(df, fl, ["guided"], {"model_label": ref_model, "specialty": ref_spec}, "topic")["guided"]
        rows.append((fl, int(df[fl].sum()), r)); pv.append(r["p"])
    adj = bh_fdr(pv)
    for (fl, ev, r), q in zip(rows, adj):
        pp = 100 * df[df.guided == 0][fl].mean(); pg = 100 * df[df.guided == 1][fl].mean()
        P("  %-26s events=%4d  plain %5.1f%% -> guided %5.1f%%  OR=%.2f [%.2f, %.2f]  p=%.2g  q=%.2g" % (fl, ev, pp, pg, r["OR"], r["OR_lo"], r["OR_hi"], r["p"], q))

    P("\n== Per-flaw prevalence by tier (plain / guided), %")
    tab = df.groupby(["tier", "condition"])[CORE + ["option_length_outlier"]].mean().T * 100
    P(tab.round(1).to_string())

    P("\n== Model differences in any core flaw, plain condition (reference = %s), adjusted for specialty" % ref_model)
    s = df[df.condition == "plain"]
    r = logit_cluster(s, "core_any", [], {"model_label": ref_model, "specialty": ref_spec}, "topic")
    for k, v in r.items():
        if k.startswith("model_label["):
            P("  %-30s OR=%.2f [%.2f, %.2f] p=%.2g" % (k, v["OR"], v["OR_lo"], v["OR_hi"], v["p"]))

    P("\n== Key position: share at A and chi-square vs uniform (A-E), by model x condition; BH-FDR over the %d tests" % (2 * len(models)))
    tests = []
    for m in models:
        for cond in ("plain", "guided"):
            s = df[(df.model_label == m) & (df.condition == cond)]
            cnt = collections.Counter(s["key"])
            stat, p = chi2_uniform(cnt)
            tests.append((m, cond, len(s), cnt.get("A", 0) / len(s), stat, p, dict(sorted(cnt.items()))))
    adj = bh_fdr([t[5] for t in tests])
    for t, q in zip(tests, adj):
        P("  %-20s %-9s %-7s n=%3d  P(key=A)=%.2f  chi2=%7.1f  p=%.2g  q=%.2g  %s" % (t[0], tier_of[t[0]], t[1], t[2], t[3], t[4], t[5], q, t[6]))
    for tname in ("base", "flagship"):
        for cond in ("plain", "guided"):
            s = df[(df.tier == tname) & (df.condition == cond)]
            cnt = collections.Counter(s["key"]); stat, p = chi2_uniform(cnt)
            P("  %-20s %-9s %-7s n=%4d  P(key=A)=%.2f  chi2=%7.1f  p=%.2g  %s" % ("ALL", tname, cond, len(s), cnt.get("A", 0) / len(s), stat, p, dict(sorted(cnt.items()))))
    P("  number of model x condition cells whose key distribution is not distinguishable from uniform (q >= 0.05): %d of %d" % (sum(q >= 0.05 for q in adj), len(adj)))

    if "reasoning_tokens" in df and (df.reasoning_tokens > 0).any():
        P("\n== Exploratory: hidden reasoning tokens (models where reasoning could not be disabled) and any core flaw")
        P("   per model: median reasoning tokens; OR per doubling of reasoning tokens (log2), adjusted for condition and specialty, cluster-robust by topic")
        df["log2_reason"] = np.log2(1 + df["reasoning_tokens"].astype(float))
        for m in models:
            s = df[df.model_label == m]
            if (s.reasoning_tokens > 0).mean() < 0.5: continue
            r = logit_cluster(s, "core_any", ["log2_reason", "guided"], {"specialty": ref_spec}, "topic")["log2_reason"]
            P("  %-20s median tokens=%6.0f (IQR %5.0f-%5.0f)  OR per doubling=%.2f [%.2f, %.2f]  p=%.2g" % (
                m, s.reasoning_tokens.median(), s.reasoning_tokens.quantile(.25), s.reasoning_tokens.quantile(.75), r["OR"], r["OR_lo"], r["OR_hi"], r["p"]))

    P("\n== Specialty: any core flaw prevalence (plain / guided)")
    P(df.groupby(["specialty", "condition"]).core_any.mean().unstack().round(3).to_string())

    if out_path:
        pathlib.Path(out_path).write_text(buf.getvalue()); print("\nwritten ->", out_path)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
