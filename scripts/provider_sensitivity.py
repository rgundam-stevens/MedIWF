"""Serving-provider mix and sensitivity (added 17 Sep 2026, second audit).
The Methods had said every model was pinned to one provider; the records show that four models were served by a second
upstream for part of the main corpus (and Claude Opus 5 by four in the position arm). This script reports the provider mix
per model and arm, tests whether provider is associated with the two main outcomes within DeepSeek V4 Pro (the only model
with a material second-provider share), and recomputes the headline estimates with secondary-provider items excluded.
Usage: python3 scripts/provider_sensitivity.py outputs/flags_full.csv [outputs/flags_position.csv ...] [-o outputs/analysis_provider_v1.txt]
"""
import sys, pathlib, io, collections, math
import numpy as np, pandas as pd
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from mediwf.stats import logit_cluster, wilson, chi2_uniform
from mediwf.rules import CORE, any_flaw


def fisher_2x2(a, b, c, d):
    """Two-sided Fisher exact p for [[a, b], [c, d]] (sum of probabilities <= observed)."""
    n = a + b + c + d; r1 = a + b; c1 = a + c
    def pmf(x): return math.comb(r1, x) * math.comb(n - r1, c1 - x) / math.comb(n, c1)
    p_obs = pmf(a); lo = max(0, c1 - (n - r1)); hi = min(r1, c1)
    return min(1.0, sum(pmf(x) for x in range(lo, hi + 1) if pmf(x) <= p_obs * (1 + 1e-9)))


def main(paths, out_path=None):
    buf = io.StringIO()
    def P(*a):
        print(*a); print(*a, file=buf)
    for path in paths:
        d = pd.read_csv(path)
        P("== Provider mix: %s (%d items)" % (pathlib.Path(path).name, len(d)))
        tab = d.groupby(["model_label", "provider"]).size()
        for m in sorted(d.model_label.unique()):
            t = tab[m]
            if len(t) > 1:
                P("  %-20s %s" % (m, ", ".join("%s %d (%.1f%%)" % (p, n, 100 * n / t.sum()) for p, n in t.sort_values(ascending=False).items())))
        P("  (models not listed were served by a single provider)")
    df = pd.read_csv(paths[0])
    df = df[df.condition.isin(["plain", "guided"]) & (df.get("reasoning_mode", "off") == "off")].copy()
    df["topic"] = df.specialty + ":" + df.topic_index.astype(str); df["guided"] = (df.condition == "guided").astype(int); df["y"] = any_flaw(df, CORE)
    main_prov = df.groupby("model_label").provider.agg(lambda s: s.value_counts().index[0]).to_dict()
    df["primary"] = df.apply(lambda r: r.provider == main_prov[r.model_label], axis=1)
    P("\n== Main corpus: items served by each model's primary provider: %d of %d" % (df.primary.sum(), len(df)))
    P("\n== Within DeepSeek V4 Pro (two providers): outcomes by provider and condition")
    for m in sorted(df.model_label.unique()):
        s = df[df.model_label == m]
        if s.provider.nunique() < 2 or s.groupby("provider").size().min() < 20: continue
        for cond in ("plain", "guided"):
            sc = s[s.condition == cond]; provs = sorted(sc.provider.unique(), key=lambda p: -(sc.provider == p).sum())
            if len(provs) < 2: continue
            a = sc[sc.provider == provs[0]]; b = sc[sc.provider == provs[1]]
            pA = fisher_2x2(int((a.key == "A").sum()), int((a.key != "A").sum()), int((b.key == "A").sum()), int((b.key != "A").sum()))
            pF = fisher_2x2(int(a.y.sum()), int((a.y == 0).sum()), int(b.y.sum()), int((b.y == 0).sum()))
            P("  %-20s %-7s %s n=%d key-at-A %.1f%% any-flaw %.1f%%  |  %s n=%d key-at-A %.1f%% any-flaw %.1f%%  |  Fisher p (key-at-A) = %.3f, (any-flaw) = %.3f" % (
                m, cond, provs[0], len(a), 100 * (a.key == "A").mean(), 100 * a.y.mean(), provs[1], len(b), 100 * (b.key == "A").mean(), 100 * b.y.mean(), pA, pF))
    P("\n== Headline estimates, all items vs primary-provider items only")
    ref_m = sorted(df.model_label.unique())[0]; ref_s = sorted(df.specialty.unique())[0]
    for label, d in (("all items", df), ("primary provider only", df[df.primary])):
        r = logit_cluster(d, "y", ["guided"], {"model_label": ref_m, "specialty": ref_s}, "topic")["guided"]
        P("  %-22s n=%5d  plain any-flaw %.1f%%  guided %.1f%%  OR=%.2f [%.2f, %.2f]  plain key-at-A %.1f%%  guided key-at-A %.1f%%" % (
            label, len(d), 100 * d[d.guided == 0].y.mean(), 100 * d[d.guided == 1].y.mean(), r["OR"], r["OR_lo"], r["OR_hi"], 100 * (d[d.guided == 0].key == "A").mean(), 100 * (d[d.guided == 1].key == "A").mean()))
    P("\n== Per-model plain-prompt prevalence and key-at-A, all vs primary-provider items (models with a second provider only)")
    for m in sorted(df.model_label.unique()):
        s = df[(df.model_label == m) & (df.guided == 0)]
        if s.provider.nunique() < 2: continue
        sp = s[s.primary]
        P("  %-20s all n=%d any-flaw %.1f%% key-at-A %.1f%%  |  primary n=%d any-flaw %.1f%% key-at-A %.1f%%" % (m, len(s), 100 * s.y.mean(), 100 * (s.key == "A").mean(), len(sp), 100 * sp.y.mean(), 100 * (sp.key == "A").mean()))
    if out_path:
        pathlib.Path(out_path).write_text(buf.getvalue()); print("\nwritten ->", out_path)


if __name__ == "__main__":
    args = sys.argv[1:]; out = None
    if "-o" in args:
        i = args.index("-o"); out = args[i + 1]; args = args[:i] + args[i + 2:]
    main(args, out)
