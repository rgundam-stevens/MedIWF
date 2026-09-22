"""Amendment 1, A3: explicit answer-position instruction arm (condition = guided_position).
For each model: compliance (key placed at the requested position), key distribution and chi-square vs uniform,
prevalence of any validated Tier-A flaw compared with the guided arm (same models; cluster-robust logistic by topic).
Usage: python3 scripts/analyze_position.py outputs/flags_position.csv outputs/flags_full.csv [outputs/analysis_position_v1.txt]
"""
import sys, pathlib, collections, io
import numpy as np, pandas as pd
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from mediwf.stats import logit_cluster, bh_fdr, chi2_uniform, wilson

from mediwf.rules import CORE   # the 14 Tier-A flaws; one definition for every script
def main(pos_path, full_path, out_path=None):
    buf = io.StringIO()
    def P(*a):
        print(*a); print(*a, file=buf)
    pos = pd.read_csv(pos_path); full = pd.read_csv(full_path)
    pos = pos[pos.condition == "guided_position"].copy()
    guided = full[(full.condition == "guided") & (full.get("reasoning_mode", "off") == "off")].copy()
    for d in (pos, guided):
        d["topic"] = d["specialty"] + ":" + d["topic_index"].astype(str)
        d["core_any"] = (d[CORE].sum(axis=1) > 0).astype(int)
    pos["target"] = pos["target_position"].astype(str).str.strip().str.upper().str[:1]
    pos["compliant"] = (pos["key"] == pos["target"]).astype(int)
    models = sorted(pos.model_label.unique()); tier_of = pos.groupby("model_label")["tier"].first().to_dict() if "tier" in pos else {}
    ref_spec = sorted(pos.specialty.unique())[0]
    P("Position arm: %d items, %d models; requested positions: %s" % (len(pos), len(models), dict(sorted(collections.Counter(pos.target).items()))))

    P("\n== Compliance with the requested key position (key == target), Wilson 95% CI; BH over chi-square tests of the realised key distribution")
    tests = []
    for m in models:
        s = pos[pos.model_label == m]
        p, lo, hi = wilson(s.compliant.sum(), len(s))
        cnt = collections.Counter(s["key"]); stat, pv = chi2_uniform(cnt)
        tests.append((m, len(s), p, lo, hi, cnt, stat, pv))
    adj = bh_fdr([t[7] for t in tests])
    for t, q in zip(tests, adj):
        P("  %-20s %-9s n=%3d  compliance=%5.1f%% [%4.1f, %4.1f]  keys=%s  chi2=%5.1f p=%.2g q=%.2g" % (
            t[0], tier_of.get(t[0], ""), t[1], 100 * t[2], 100 * t[3], 100 * t[4], dict(sorted(t[5].items())), t[6], t[7], q))
    p, lo, hi = wilson(pos.compliant.sum(), len(pos)); cnt = collections.Counter(pos["key"]); stat, pv = chi2_uniform(cnt)
    P("  %-20s %-9s n=%3d  compliance=%5.1f%% [%4.1f, %4.1f]  keys=%s  chi2=%5.1f p=%.2g" % ("ALL", "", len(pos), 100 * p, 100 * lo, 100 * hi, dict(sorted(cnt.items())), stat, pv))

    P("\n== Compliance by requested position (pooled over models)")
    for t in sorted(pos.target.unique()):
        s = pos[pos.target == t]; p, lo, hi = wilson(s.compliant.sum(), len(s))
        P("  target %s  n=%4d  compliance=%5.1f%% [%4.1f, %4.1f]  realised keys=%s" % (t, len(s), 100 * p, 100 * lo, 100 * hi, dict(sorted(collections.Counter(s["key"]).items()))))

    P("\n== Where non-compliant items put the key (pooled)")
    nc = pos[pos.compliant == 0]
    P("  n=%d; realised keys=%s" % (len(nc), dict(sorted(collections.Counter(nc["key"]).items()))))

    P("\n== Any validated Tier-A flaw: position arm vs guided arm (same models), adjusted for specialty; cluster-robust by topic")
    P("   (the position prompt replaces the alphabetical-ordering guideline with the explicit position instruction; other 9 guidelines identical)")
    both = pd.concat([pos.assign(posarm=1), guided[guided.model_label.isin(models)].assign(posarm=0)], ignore_index=True)
    r = logit_cluster(both, "core_any", ["posarm"], {"model_label": models[0], "specialty": ref_spec}, "topic")["posarm"]
    pp = 100 * both[both.posarm == 1].core_any.mean(); pg = 100 * both[both.posarm == 0].core_any.mean()
    P("  pooled: guided %.1f%% -> position %.1f%%  OR=%.2f [%.2f, %.2f] p=%.2g" % (pg, pp, r["OR"], r["OR_lo"], r["OR_hi"], r["p"]))
    pv = []; rows = []
    for m in models:
        s = both[both.model_label == m]
        r = logit_cluster(s, "core_any", ["posarm"], {"specialty": ref_spec}, "topic")["posarm"]
        rows.append((m, 100 * s[s.posarm == 0].core_any.mean(), 100 * s[s.posarm == 1].core_any.mean(), r)); pv.append(r["p"])
    adj = bh_fdr(pv)
    for (m, g, p_, r), q in zip(rows, adj):
        P("  %-20s guided %5.1f%% -> position %5.1f%%  OR=%.2f [%.2f, %.2f] p=%.2g q=%.2g" % (m, g, p_, r["OR"], r["OR_lo"], r["OR_hi"], r["p"], q))

    P("\n== Per-flaw prevalence (%), guided arm vs position arm, pooled over the same models")
    g = guided[guided.model_label.isin(models)]
    tab = pd.DataFrame({"guided": g[CORE + ["option_length_outlier", "options_not_alphabetical"]].mean() * 100,
                        "position": pos[CORE + ["option_length_outlier", "options_not_alphabetical"]].mean() * 100})
    P(tab.round(2).to_string())

    P("\n== Longest-option-is-key by requested position (does forcing the key to a position change its length?)")
    for t in sorted(pos.target.unique()):
        s = pos[pos.target == t]
        P("  target %s  longest_option_key=%.1f%%  key_chars mean=%.0f  mean_distractor_chars=%.0f" % (t, 100 * s.longest_option_key.mean(), s.key_chars.mean(), s.mean_distractor_chars.mean()))
    if out_path:
        pathlib.Path(out_path).write_text(buf.getvalue()); print("\nwritten ->", out_path)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
