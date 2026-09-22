"""RQ2 model differences without a hand-picked reference model (added 17 Sep 2026, second audit).
The earlier manuscript compared every model with the lowest-prevalence model, which is comparison-with-the-best and
inflates the number of 'significant' differences. Here each model's plain-prompt log-odds of any core flaw is contrasted
with the mean over the 15 models (sum-to-zero coding), adjusted for specialty, cluster-robust by topic, BH over 15 tests.
Usage: python3 scripts/model_contrasts.py outputs/flags_full.csv [outputs/model_contrasts_v1.txt]
"""
import sys, pathlib, io
import numpy as np, pandas as pd
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from mediwf.stats import logit_fit, cluster_robust_cov, bh_fdr, norm_sf, wilson
from mediwf.rules import CORE, any_flaw


def contrasts(df, cond, P):
    d = df[df.condition == cond].copy(); d["y"] = any_flaw(d, CORE)
    models = sorted(d.model_label.unique()); specs = sorted(d.specialty.unique())
    # sum-to-zero (deviation) coding for model: columns for models[1:], with models[0] = -1 on all
    X = [np.ones(len(d))]; names = ["intercept"]
    for m in models[1:]:
        col = (d.model_label == m).astype(float).values - (d.model_label == models[0]).astype(float).values
        X.append(col); names.append(m)
    for sp in specs[1:]:
        X.append((d.specialty == sp).astype(float).values); names.append("specialty[%s]" % sp)
    X = np.column_stack(X); y = d.y.values.astype(float)
    beta, cov_m = logit_fit(X, y)
    cov = cluster_robust_cov(X, y, beta, cov_m, (d.specialty + ":" + d.topic_index.astype(str)).values)
    k = len(models)
    # deviation of each model from the grand mean: models[1:] = beta_j ; models[0] = -sum(beta_j)
    L = []
    for j, m in enumerate(models):
        l = np.zeros(len(names))
        if j == 0:
            for i in range(1, k): l[i] = -1.0
        else:
            l[j] = 1.0
        L.append(l)
    rows = []
    for m, l in zip(models, L):
        est = float(l @ beta); se = float(np.sqrt(l @ cov @ l)); z = est / se; p = float(2 * norm_sf(abs(z)))
        rows.append((m, est, se, p))
    q = bh_fdr([r[3] for r in rows])
    P("\n== %s prompt: each model's odds of any core flaw relative to the 15-model mean (adjusted for specialty; topic clusters; BH over 15)" % cond)
    P("%-20s %7s   %-22s %8s %8s   %s" % ("model", "prev %", "OR vs mean [95% CI]", "p", "q", ""))
    for (m, est, se, p), qq in sorted(zip(rows, q), key=lambda t: t[0][1]):
        s = d[d.model_label == m]; prev = 100 * s.y.mean()
        P("%-20s %6.1f   %5.2f [%4.2f, %4.2f]     %8.2g %8.2g   %s" % (m, prev, np.exp(est), np.exp(est - 1.96 * se), np.exp(est + 1.96 * se), p, qq, "*" if qq < 0.05 else ""))
    P("  models differing from the mean at q<0.05: %d of %d" % (sum(x < 0.05 for x in q), k))


def main(path, out_path=None):
    buf = io.StringIO()
    def P(*a):
        print(*a); print(*a, file=buf)
    df = pd.read_csv(path)
    df = df[df.condition.isin(["plain", "guided"]) & (df.get("reasoning_mode", "off") == "off")].copy()
    P("Model contrasts on %d items; %d models" % (len(df), df.model_label.nunique()))
    for cond in ("plain", "guided"):
        contrasts(df, cond, P)
    if out_path:
        pathlib.Path(out_path).write_text(buf.getvalue()); print("\nwritten ->", out_path)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
