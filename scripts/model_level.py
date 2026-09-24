"""Model-as-unit summaries (added 17 Sep 2026, second audit). Complements the item-level regressions:
  1. Guideline effect: per-model log-ORs (specialty-adjusted, topic clusters) pooled by DerSimonian-Laird random effects,
     with I^2, Cochran's Q and the 95% prediction interval for a new model.
  2. Reasoning arm: per-model ORs (reasoning on vs off, adjusted for condition and specialty) and the model-level summary
     over the four models (mean log-OR with a t interval; exact sign test).
  3. Tier rows of Table 3: model-level mean prevalence with t-based CIs (the item-level Wilson intervals treat 3,200 items as
     independent when the sampling unit is the model).
  4. Table 3 cells: topic-cluster bootstrap CIs for per-cell prevalence, which respect the correlation between the two
     repetitions of a topic (observed r ~ 0.3), next to the Wilson intervals.
Usage: python3 scripts/model_level.py outputs/flags_full.csv outputs/flags_full_reasoning.csv [outputs/model_level_v1.txt]
"""
import sys, pathlib, io, math
import numpy as np, pandas as pd
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from mediwf.stats import logit_cluster, wilson, t_sf
from mediwf.rules import CORE, any_flaw


def dl_pool(b, se):
    b = np.asarray(b, float); v = np.asarray(se, float) ** 2; w = 1 / v
    mu_f = (w * b).sum() / w.sum(); Q = float((w * (b - mu_f) ** 2).sum()); df = len(b) - 1
    tau2 = max(0.0, (Q - df) / (w.sum() - (w ** 2).sum() / w.sum())); I2 = max(0.0, (Q - df) / Q) if Q > 0 else 0.0
    wr = 1 / (v + tau2); mu = (wr * b).sum() / wr.sum(); se_mu = math.sqrt(1 / wr.sum())
    pi = math.sqrt(tau2 + se_mu ** 2)
    return dict(mu=mu, se=se_mu, tau2=tau2, I2=I2, Q=Q, df=df, pi_lo=mu - 1.96 * pi, pi_hi=mu + 1.96 * pi)


def t_ci(x):
    x = np.asarray(x, float); n = len(x); m = x.mean(); s = x.std(ddof=1) / math.sqrt(n)
    from math import sqrt
    try:
        from scipy import stats as sps; t = sps.t.ppf(0.975, n - 1)
    except ImportError:
        t = {1: 12.7062, 2: 4.3027, 3: 3.1824, 4: 2.7764, 5: 2.5706, 6: 2.4469, 7: 2.3646, 8: 2.3060, 9: 2.2622, 10: 2.2281, 11: 2.2010, 12: 2.1788, 13: 2.1604, 14: 2.1448}.get(n - 1, 1.96)
    return m, m - t * s, m + t * s


def main(full_path, reason_path, out_path=None):
    buf = io.StringIO()
    def P(*a):
        print(*a); print(*a, file=buf)
    rng = np.random.default_rng(20260917)
    df = pd.read_csv(full_path)
    df = df[df.condition.isin(["plain", "guided"]) & (df.get("reasoning_mode", "off") == "off")].copy()
    df["topic"] = df.specialty + ":" + df.topic_index.astype(str); df["guided"] = (df.condition == "guided").astype(int)
    df["y"] = any_flaw(df, CORE)
    models = sorted(df.model_label.unique()); ref_s = sorted(df.specialty.unique())[0]
    tier_of = df.groupby("model_label").tier.first().to_dict() if "tier" in df else {m: "base" for m in models}

    P("== 1. Guideline effect pooled over models (random effects); per-model estimates from specialty-adjusted, topic-clustered logistic regressions")
    b = []; se = []
    for m in models:
        r = logit_cluster(df[df.model_label == m], "y", ["guided"], {"specialty": ref_s}, "topic")["guided"]
        b.append(r["coef"]); se.append(r["se"])
        P("  %-20s OR=%.2f [%.2f, %.2f]" % (m, r["OR"], r["OR_lo"], r["OR_hi"]))
    d = dl_pool(b, se)
    P("  fixed-effect (inverse-variance) OR = %.3f" % math.exp((np.array(b) / np.array(se) ** 2).sum() / (1 / np.array(se) ** 2).sum()))
    P("  random-effects OR = %.2f [%.2f, %.2f]; tau^2 = %.3f; I^2 = %.0f%%; Q = %.1f on %d df" % (math.exp(d["mu"]), math.exp(d["mu"] - 1.96 * d["se"]), math.exp(d["mu"] + 1.96 * d["se"]), d["tau2"], 100 * d["I2"], d["Q"], d["df"]))
    P("  95%% prediction interval for the OR in a new model: [%.2f, %.2f]" % (math.exp(d["pi_lo"]), math.exp(d["pi_hi"])))

    P("\n== 2. Reasoning arm at the model level (four models)")
    rs = pd.read_csv(reason_path); rs = rs[rs.condition.isin(["plain", "guided"])].copy()
    base = df[df.model_label.isin(rs.model_label.unique())].copy()
    both = pd.concat([rs.assign(reason_on=1), base.assign(reason_on=0)], ignore_index=True)
    both["topic"] = both.specialty + ":" + both.topic_index.astype(str); both["guided"] = (both.condition == "guided").astype(int); both["y"] = any_flaw(both, CORE)
    lo = []; ses = []
    for m in sorted(rs.model_label.unique()):
        r = logit_cluster(both[both.model_label == m], "y", ["reason_on", "guided"], {"specialty": ref_s}, "topic")["reason_on"]
        lo.append(r["coef"]); ses.append(r["se"]); s = both[both.model_label == m]
        P("  %-20s off %.1f%% -> on %.1f%%  OR=%.2f [%.2f, %.2f] p=%.2g" % (m, 100 * s[s.reason_on == 0].y.mean(), 100 * s[s.reason_on == 1].y.mean(), r["OR"], r["OR_lo"], r["OR_hi"], r["p"]))
    m_, l_, h_ = t_ci(lo); neg = sum(x < 0 for x in lo); n = len(lo)
    P("  model-level mean OR = %.2f [%.2f, %.2f] (t interval, %d models); models with OR<1: %d of %d (exact two-sided sign test p=%.3f)" % (
        math.exp(m_), math.exp(l_), math.exp(h_), n, neg, n, min(1.0, 2 * sum(math.comb(n, k) for k in range(0, min(neg, n - neg) + 1)) / 2 ** n)))
    d = dl_pool(lo, ses)
    P("  random-effects OR = %.2f [%.2f, %.2f]; I^2 = %.0f%%" % (math.exp(d["mu"]), math.exp(d["mu"] - 1.96 * d["se"]), math.exp(d["mu"] + 1.96 * d["se"]), 100 * d["I2"]))

    P("\n== 3. Tier rows: model-level mean prevalence of any core flaw (t interval over models) vs item-level Wilson interval")
    for tier in sorted(set(tier_of.values())):
        for cond in ("plain", "guided"):
            ms = [m for m in models if tier_of[m] == tier]
            prev = [100 * df[(df.model_label == m) & (df.condition == cond)].y.mean() for m in ms]
            m_, l_, h_ = t_ci(prev); s = df[(df.model_label.isin(ms)) & (df.condition == cond)]; w = wilson(s.y.sum(), len(s))
            P("  %-9s %-7s model-level %.1f%% [%.1f, %.1f] (n=%d models)   item-level Wilson %.1f%% [%.1f, %.1f]" % (tier, cond, m_, l_, h_, len(ms), 100 * w[0], 100 * w[1], 100 * w[2]))

    P("\n== 4. Table 3 cells: prevalence with Wilson interval and with a topic-cluster bootstrap interval (2,000 resamples of the 200 topics)")
    P("%-20s %-7s %-22s %-22s" % ("model", "cond", "Wilson [CI]", "cluster bootstrap [CI]"))
    for m in models:
        for cond in ("plain", "guided"):
            s = df[(df.model_label == m) & (df.condition == cond)]
            g = s.groupby("topic").y.agg(["sum", "size"]); sums = g["sum"].values; sizes = g["size"].values; k = len(g)
            idx = rng.integers(0, k, size=(2000, k)); boots = sums[idx].sum(axis=1) / sizes[idx].sum(axis=1)
            w = wilson(s.y.sum(), len(s))
            P("%-20s %-7s %5.1f [%4.1f, %4.1f]     %5.1f [%4.1f, %4.1f]" % (m, cond, 100 * w[0], 100 * w[1], 100 * w[2], 100 * s.y.mean(), 100 * np.percentile(boots, 2.5), 100 * np.percentile(boots, 97.5)))
    if out_path:
        pathlib.Path(out_path).write_text(buf.getvalue()); print("\nwritten ->", out_path)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
