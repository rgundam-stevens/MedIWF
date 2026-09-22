"""Flagship-vs-base comparison with the MODEL as the unit of inference (audit of 16 Sep 2026).

model_effects.py compares tiers with items as units and topics as clusters; because models are nested in tiers and only
15 models exist, that interval is too narrow. This script reports the model-level rates, an exact permutation test over
all C(15,7) = 6435 tier assignments, Welch's t-test, and a cluster-robust logistic regression with clusters = models.
Usage: python3 scripts/tier_model_level.py outputs/flags_full.csv [outputs/tier_model_level_v1.txt]
"""
import sys, pathlib, itertools, io, math
import numpy as np, pandas as pd
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from mediwf.stats import logit_cluster, wilson

from mediwf.rules import CORE
def welch(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    va, vb = a.var(ddof=1) / len(a), b.var(ddof=1) / len(b)
    t = (a.mean() - b.mean()) / math.sqrt(va + vb)
    df = (va + vb) ** 2 / (va ** 2 / (len(a) - 1) + vb ** 2 / (len(b) - 1))
    try:
        from scipy import stats; p = 2 * stats.t.sf(abs(t), df)
    except ImportError:
        p = 2 * (1 - 0.5 * (1 + math.erf(abs(t) / math.sqrt(2))))   # normal approximation if scipy is absent
    return t, df, p

def main(path, out_path=None):
    buf = io.StringIO()
    def P(*a): print(*a); print(*a, file=buf)
    df = pd.read_csv(path)
    df = df[df.condition.isin(["plain", "guided"]) & (df.get("reasoning_mode", "off") == "off")].copy()
    df["core_any"] = (df[CORE].sum(axis=1) > 0).astype(int)
    rates = df.groupby(["model_label", "tier", "condition"]).core_any.mean().unstack("condition")
    rates["both"] = df.groupby(["model_label", "tier"]).core_any.mean()
    P("Model-level prevalence of any core flaw (detector %s):" % df.get("detector_version", pd.Series(["?"])).iloc[0])
    P((100 * rates).round(1).to_string())
    for col in ["plain", "guided", "both"]:
        fl = rates.xs("flagship", level="tier")[col].values; ba = rates.xs("base", level="tier")[col].values
        obs = fl.mean() - ba.mean()
        allv = np.concatenate([fl, ba]); k = len(fl); n = len(allv)
        diffs = np.array([allv[list(c)].mean() - np.delete(allv, list(c)).mean() for c in itertools.combinations(range(n), k)])
        p_perm = np.mean(np.abs(diffs) >= abs(obs) - 1e-12)
        t, dfree, p_w = welch(fl, ba)
        P("\n%-7s flagship mean %.1f%% (n=%d models) vs base mean %.1f%% (n=%d): difference %+.1f points" % (col, 100 * fl.mean(), k, 100 * ba.mean(), n - k, 100 * obs))
        P("        exact permutation test over %d assignments: p = %.3f | Welch t = %.2f, df = %.1f, p = %.3f" % (len(diffs), p_perm, t, dfree, p_w))
    P("\nCluster-robust logistic regression with clusters = models (G = 15), adjusted for condition and specialty:")
    df["flagship"] = (df.tier == "flagship").astype(int); df["guided"] = (df.condition == "guided").astype(int)
    r = logit_cluster(df, "core_any", ["flagship", "guided"], {"specialty": sorted(df.specialty.unique())[0]}, "model_label")["flagship"]
    P("  flagship OR = %.2f [%.2f, %.2f], p = %.3f   (compare model_effects.py, clusters = topics)" % (r["OR"], r["OR_lo"], r["OR_hi"], r["p"]))
    if out_path: pathlib.Path(out_path).write_text(buf.getvalue()); print("\nwritten ->", out_path)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
