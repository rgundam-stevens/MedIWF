"""Further reviewer-requested numbers (21 Sep 2026): (1) tier difference with its own CI and the detectable difference at
80% power; the cluster-robust tier OR with t(G-1) critical values; (2) key-at-A with second-provider items excluded, main
corpus and template arms; (3) headline estimates under detector v1.0, v1.1 and v1.2; (4) clang-definition sensitivity on the
525 five-option NBME items. Usage: python3 scripts/reviewer_addendum.py -> outputs/analysis_reviewer_addendum_v1.txt
"""
import sys, pathlib, io, math, json
import numpy as np, pandas as pd
root = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "src")); sys.path.insert(0, str(root / "scripts"))
from mediwf.stats import logit_fit, cluster_robust_cov, design, t_sf
from mediwf.rules import CORE
try:
    from scipy import stats as sps
    tq = lambda q, df: sps.t.ppf(q, df)
except Exception:
    tq = None

def main():
    buf = io.StringIO()
    def P(*a): print(*a); print(*a, file=buf)
    fl = pd.read_csv(root / "outputs/flags_full.csv"); fl = fl[fl.condition.isin(["plain", "guided"]) & (fl.get("reasoning_mode", "off") == "off")].copy()
    fl["core_any"] = (fl[CORE].sum(axis=1) > 0).astype(int); fl["flagship"] = (fl.tier == "flagship").astype(int); fl["guided"] = (fl.condition == "guided").astype(int)
    # 1. tier difference
    P("== 1. Flagship vs base tier, model as the unit (plain prompt)")
    m = fl[fl.condition == "plain"].groupby(["model_label", "tier"]).core_any.mean().reset_index()
    a = m[m.tier == "flagship"].core_any.values * 100; b = m[m.tier == "base"].core_any.values * 100
    d = a.mean() - b.mean(); se = math.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    dfw = (a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b)) ** 2 / ((a.var(ddof=1) / len(a)) ** 2 / (len(a) - 1) + (b.var(ddof=1) / len(b)) ** 2 / (len(b) - 1))
    tcrit = tq(0.975, dfw) if tq else 2.16
    P("  flagship mean %.1f%% (SD %.1f, n=%d) vs base mean %.1f%% (SD %.1f, n=%d): difference %.1f points, 95%% CI %.1f to %.1f (Welch, df=%.1f)" % (a.mean(), a.std(ddof=1), len(a), b.mean(), b.std(ddof=1), len(b), d, d - tcrit * se, d + tcrit * se, dfw))
    sp = math.sqrt(((len(a) - 1) * a.var(ddof=1) + (len(b) - 1) * b.var(ddof=1)) / (len(a) + len(b) - 2))
    t_a = tq(0.975, len(a) + len(b) - 2) if tq else 2.16; t_b = tq(0.80, len(a) + len(b) - 2) if tq else 0.87
    se_p = sp * math.sqrt(1 / len(a) + 1 / len(b)); power = 0.5 * math.erfc((1.96 - abs(d) / se_p) / math.sqrt(2))   # normal approximation
    P("  pooled SD %.1f points; smallest difference detectable with 80%% power at alpha 0.05 (two-sided, 7 vs 8 models): %.1f points; power for the observed %.1f-point difference: about %.0f%% (normal approximation)" % (
        sp, (t_a + t_b) * se_p, abs(d), 100 * power))
    X, names = design(fl, ["flagship", "guided"], {"specialty": sorted(fl.specialty.unique())[0]}); y = fl.core_any.values.astype(float)
    beta, cov_m = logit_fit(X, y); cov = cluster_robust_cov(X, y, beta, cov_m, fl.model_label.values); i = names.index("flagship"); se_b = math.sqrt(cov[i, i])
    G = fl.model_label.nunique(); tc = tq(0.975, G - 1) if tq else 2.145
    P("  cluster-robust logistic regression (clusters = %d models, adjusted for condition and specialty): OR %.2f; 95%% CI with normal critical value %.2f-%.2f; with t(G-1 = %d) critical value %.2f-%.2f" % (
        G, math.exp(beta[i]), math.exp(beta[i] - 1.96 * se_b), math.exp(beta[i] + 1.96 * se_b), G - 1, math.exp(beta[i] - tc * se_b), math.exp(beta[i] + tc * se_b)))
    # 2. provider sensitivity for key-at-A
    P("\n== 2. Share of keys at A, all items vs primary-provider items only (primary = the most frequent provider of the model in that arm)")
    arms = [("main corpus, plain", fl[fl.condition == "plain"]), ("main corpus, guided", fl[fl.condition == "guided"])]
    tp = root / "outputs/flags_template.csv"
    if tp.exists():
        t = pd.read_csv(tp)
        for c in ("plain_neutral", "plain_rotated", "guided_neutral"): arms.append(("template arm, " + c, t[t.condition == c]))
    for label, d in arms:
        if len(d) == 0: continue
        prim = d.groupby("model_label").provider.agg(lambda s: s.value_counts().index[0])
        dp = d[d.provider == d.model_label.map(prim)]
        line = "  %-28s all n=%5d key-at-A %.1f%% | primary-provider n=%5d key-at-A %.1f%%" % (label, len(d), 100 * (d.key == "A").mean(), len(dp), 100 * (dp.key == "A").mean())
        mixed = [mdl for mdl in prim.index if (d.model_label == mdl).sum() != (dp.model_label == mdl).sum()]
        extra = "; ".join("%s %.0f%% -> %.0f%% (n %d -> %d)" % (mdl, 100 * (d[d.model_label == mdl].key == "A").mean(), 100 * (dp[dp.model_label == mdl].key == "A").mean(), (d.model_label == mdl).sum(), (dp.model_label == mdl).sum()) for mdl in mixed)
        P(line + ("  | models with a second provider: " + extra if extra else "  | no second provider"))
    # 3. detector versions
    P("\n== 3. Headline estimates under each detector version (crude, unadjusted; same items)")
    P("  %-8s %-16s %-16s %-14s %-14s %-14s %-14s %-12s" % ("version", "plain any-flaw", "guided any-flaw", "OR guided/plain", "plain longest", "plain clang", "plain absolute", "NBME-5 any"))
    for ver, folder in (("v1.0", "outputs/v1_0_archive"), ("v1.1", "outputs/v1_1_archive"), ("v1.2", "outputs")):
        f = pd.read_csv(root / folder / "flags_full.csv"); f = f[f.condition.isin(["plain", "guided"]) & (f.get("reasoning_mode", "off") == "off")]
        rules = [r for r in CORE if r in f.columns]; anyf = (f[rules].sum(axis=1) > 0)
        p = anyf[f.condition == "plain"].mean(); g = anyf[f.condition == "guided"].mean()
        n = pd.read_csv(root / folder / "flags_nbme.csv"); n5 = n[n.n_options == 5]; nrules = [r for r in CORE if r in n5.columns]
        P("  %-8s %15.1f%% %15.1f%% %14.2f %13.1f%% %13.1f%% %13.1f%% %11.1f%%   (%d of 14 rules present)" % (ver, 100 * p, 100 * g, (g / (1 - g)) / (p / (1 - p)), 100 * f[f.condition == "plain"].longest_option_key.mean(), 100 * f[f.condition == "plain"].clang_cue.mean(), 100 * f[f.condition == "plain"].absolute_terms.mean(), 100 * (n5[nrules].sum(axis=1) > 0).mean(), len(rules)))
    (root / "outputs/analysis_reviewer_addendum_v1.txt").write_text(buf.getvalue()); print("\nwritten -> outputs/analysis_reviewer_addendum_v1.txt")

if __name__ == "__main__":
    main()
