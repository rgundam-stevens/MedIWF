"""Amendment 2: template-control arm. Is the key-at-A bias induced by the example letter in the required JSON template?
Compares, per model, P(key = A) under the plain prompt (template shows "answer": "A"; main corpus, same 5 topics per
specialty), under plain_neutral ("answer": "...") and under plain_rotated ("answer": "<rotating A-E>"), plus the share of
rotated items whose key equals the example letter and the any-core-flaw rate in each arm.
Usage: python3 scripts/analyze_template.py outputs/flags_template.csv outputs/flags_full.csv [outputs/analysis_template_v1.txt]
"""
import sys, pathlib, collections, io
import pandas as pd
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from mediwf.stats import wilson, chi2_uniform, bh_fdr

from mediwf.rules import CORE   # the 14 Tier-A flaws; one definition for every script
def main(tpl_path, full_path, out_path=None):
    buf = io.StringIO()
    def P(*a): print(*a); print(*a, file=buf)
    t = pd.read_csv(tpl_path); f = pd.read_csv(full_path)
    neu_topics = sorted(t[t.condition == "plain_neutral"].topic_index.unique())   # 5 topics per specialty in A5, all 25 after A9
    plain = f[(f.condition == "plain") & f.topic_index.isin(neu_topics) & (f.get("reasoning_mode", "off") == "off")].copy()
    for d in (t, plain): d["core_any"] = (d[CORE].sum(axis=1) > 0).astype(int)
    neu = t[t.condition == "plain_neutral"]; rot = t[t.condition == "plain_rotated"].copy()
    rot["target"] = rot.target_position.astype(str).str.strip().str.upper().str[:1]; rot["follows"] = (rot.key == rot.target).astype(int)
    P("Template-control arm: %d neutral items, %d rotated items; plain comparison items (same topics): %d" % (len(neu), len(rot), len(plain)))
    P("\n%-20s | %-22s | %-22s | %-30s | any core flaw: plain / neutral / rotated" % ("model", "P(A) plain [CI]", "P(A) neutral [CI]", "rotated: P(key=example) [CI]"))
    tests = []
    for m in sorted(t.model_label.unique()):
        a = plain[plain.model_label == m]; b = neu[neu.model_label == m]; c = rot[rot.model_label == m]
        pa = wilson((a.key == "A").sum(), len(a)); pb = wilson((b.key == "A").sum(), len(b)); pc = wilson(c.follows.sum(), len(c))
        stat, pv = chi2_uniform(collections.Counter(b.key)); tests.append((m, stat, pv))
        P("%-20s | %.2f [%.2f, %.2f] n=%3d | %.2f [%.2f, %.2f] n=%3d | %.2f [%.2f, %.2f] n=%3d       | %5.1f%% / %5.1f%% / %5.1f%%" % (
            m, pa[0], pa[1], pa[2], len(a), pb[0], pb[1], pb[2], len(b), pc[0], pc[1], pc[2], len(c), 100 * a.core_any.mean(), 100 * b.core_any.mean(), 100 * c.core_any.mean()))
    P("\nKey distribution under the neutral template (chi-square vs uniform, BH over models):")
    adj = bh_fdr([x[2] for x in tests])
    for (m, stat, pv), q in zip(tests, adj):
        P("  %-20s keys=%s chi2=%6.1f p=%.2g q=%.2g" % (m, dict(sorted(collections.Counter(neu[neu.model_label == m].key).items())), stat, pv, q))
    P("\nPooled: P(A) plain=%.2f neutral=%.2f | rotated P(key=example)=%.2f; rotated key distribution=%s" % (
        (plain.key == "A").mean(), (neu.key == "A").mean(), rot.follows.mean(), dict(sorted(collections.Counter(rot.key).items()))))
    P("\nInterpretation guide: if P(A) under the neutral template stays high, the bias is the model's own; if it falls to ~0.2 and rotated")
    P("keys follow the example letter, the bias in the main corpus was largely induced by the example letter in the output template.")
    gn = t[t.condition == "guided_neutral"]
    if len(gn):
        # Amendment 3: guided prompt with the neutral template vs the guided arm (same template letter 'A') on the same topics
        gtop = sorted(gn.topic_index.unique()); guided = f[(f.condition == "guided") & (f.topic_index.isin(gtop)) & (f.get("reasoning_mode", "off") == "off")].copy()
        guided["core_any"] = (guided[CORE].sum(axis=1) > 0).astype(int); gn = gn.copy(); gn["core_any"] = (gn[CORE].sum(axis=1) > 0).astype(int)
        P("\n== Guided prompt with the neutral template (Amendment 3): %d items vs %d guided items on the same topics" % (len(gn), len(guided)))
        P("%-20s | %-26s | %-26s | non-alphabetical guided / guided-neutral | any flaw guided / guided-neutral" % ("model", "P(A) guided [CI]", "P(A) guided-neutral [CI]"))
        tests2 = []
        for m in sorted(gn.model_label.unique()):
            a = guided[guided.model_label == m]; b = gn[gn.model_label == m]
            pa = wilson((a.key == "A").sum(), len(a)); pb = wilson((b.key == "A").sum(), len(b)); stat, pv = chi2_uniform(collections.Counter(b.key)); tests2.append((m, stat, pv))
            P("%-20s | %.2f [%.2f, %.2f] n=%3d | %.2f [%.2f, %.2f] n=%3d | %5.1f%% / %5.1f%%                     | %5.1f%% / %5.1f%%" % (
                m, pa[0], pa[1], pa[2], len(a), pb[0], pb[1], pb[2], len(b), 100 * a.options_not_alphabetical.mean(), 100 * b.options_not_alphabetical.mean(), 100 * a.core_any.mean(), 100 * b.core_any.mean()))
        adj2 = bh_fdr([x[2] for x in tests2])
        P("  guided-neutral key distributions compatible with uniform (q >= 0.05): %d of %d; pooled keys=%s" % (sum(q >= 0.05 for q in adj2), len(adj2), dict(sorted(collections.Counter(gn.key).items()))))
        P("  pooled: P(A) guided=%.2f guided-neutral=%.2f; any flaw guided=%.1f%% guided-neutral=%.1f%%" % ((guided.key == "A").mean(), (gn.key == "A").mean(), 100 * guided.core_any.mean(), 100 * gn.core_any.mean()))
    if len(gn):
        # v1.2 (second audit): the regressions the manuscript quotes, now in the released script
        from mediwf.rules import SENSITIVITY
        from mediwf.stats import logit_cluster
        pn = t[t.condition == "plain_neutral"].copy(); pr = t[t.condition == "plain_rotated"].copy()
        for d in (guided, gn, pn, pr, plain):
            d["topic"] = d.specialty + ":" + d.topic_index.astype(str); d["sens_any"] = (d[SENSITIVITY].sum(axis=1) > 0).astype(int)
        ref_m = sorted(gn.model_label.unique())[0]; ref_s = sorted(gn.specialty.unique())[0]
        both = pd.concat([gn.assign(x=1), guided.assign(x=0)], ignore_index=True)
        r = logit_cluster(both, "core_any", ["x"], {"model_label": ref_m, "specialty": ref_s}, "topic")["x"]
        P("  any core flaw, guided-neutral vs guided: OR=%.2f [%.2f, %.2f] p=%.2g (adjusted for model and specialty; topic clusters)" % (r["OR"], r["OR_lo"], r["OR_hi"], r["p"]))
        both = pd.concat([gn.assign(x=1), pn.assign(x=0)], ignore_index=True)
        r = logit_cluster(both, "core_any", ["x"], {"model_label": ref_m, "specialty": ref_s}, "topic")["x"]
        r2 = logit_cluster(both, "sens_any", ["x"], {"model_label": ref_m, "specialty": ref_s}, "topic")["x"]
        P("  any core flaw, guided-neutral vs plain-neutral (the guideline effect with both templates neutral): %.1f%% vs %.1f%%; OR=%.2f [%.2f, %.2f] p=%.2g; 11-rule composite OR=%.2f [%.2f, %.2f]" % (
            100 * gn.core_any.mean(), 100 * pn.core_any.mean(), r["OR"], r["OR_lo"], r["OR_hi"], r["p"], r2["OR"], r2["OR_lo"], r2["OR_hi"]))
        P("  non-alphabetical items: guided %.1f%% -> guided-neutral %.1f%%" % (100 * guided.options_not_alphabetical.mean(), 100 * gn.options_not_alphabetical.mean()))
        P("  key at A among ALPHABETIZED items only (guided -> guided-neutral):")
        for m in sorted(gn.model_label.unique()):
            a = guided[(guided.model_label == m) & (guided.options_not_alphabetical == 0)]; b = gn[(gn.model_label == m) & (gn.options_not_alphabetical == 0)]
            P("    %-20s %.0f%% (n=%d) -> %.0f%% (n=%d)" % (m, 100 * (a.key == "A").mean(), len(a), 100 * (b.key == "A").mean(), len(b)))
        P("  any core flaw pooled: plain %.1f%% (n=%d), plain-neutral %.1f%% (n=%d), plain-rotated %.1f%% (n=%d)" % (100 * plain.core_any.mean(), len(plain), 100 * pn.core_any.mean(), len(pn), 100 * pr.core_any.mean(), len(pr)))
        both = pd.concat([pn.assign(x=1), plain.assign(x=0)], ignore_index=True)
        r = logit_cluster(both, "core_any", ["x"], {"model_label": ref_m, "specialty": ref_s}, "topic")["x"]
        P("  any core flaw, plain-neutral vs plain: OR=%.2f [%.2f, %.2f] p=%.2g" % (r["OR"], r["OR_lo"], r["OR_hi"], r["p"]))
    if out_path: pathlib.Path(out_path).write_text(buf.getvalue()); print("\nwritten ->", out_path)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
