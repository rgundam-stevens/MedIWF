"""LLM-generated items versus the NBME reference items, done properly (added 17 Sep 2026, second audit).
Runs only on the machine holding the NBME data; prints aggregate statistics, never item text.
  1. Prevalence of any core flaw (14 rules), of any validated-rule flaw (10 rules) and of each rule: plain-prompt LLM
     items (all five-option) vs the 525 five-option NBME items, with Wilson CIs.
  2. Logistic regression of any core flaw on source (LLM vs NBME) adjusting for log stem length, with robust SEs, and the
     same for the clang cue alone (the rule most sensitive to stem length).
  3. Clang-cue prevalence by stem-length quintile, in both sources.
  4. Absolute-terms audit: which word fired and whether it sat in the key or in a distractor, for every flagged LLM item
     and every flagged NBME item (aggregate counts).
Usage: python3 scripts/nbme_comparison.py [-o outputs/analysis_nbme_comparison_v1.txt]
"""
import sys, json, pathlib, io, collections, math
import numpy as np, pandas as pd
root = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "src"))
from mediwf.stats import logit_fit, cluster_robust_cov, wilson, norm_sf
from mediwf.rules import CORE, VALIDATED, any_flaw
from mediwf.detector import Detector, VERSION
from mediwf.parsing import usable_record
sys.path.insert(0, str(root / "scripts"))
from detect import _cell_text


def load_nbme_items():
    d = root / "data" / "nbme"
    train = pd.read_excel(d / "train_final.xlsx")
    test = pd.read_excel(d / "test_final.xlsx").merge(pd.read_excel(d / "gold_final.xlsx"), on="ItemNum")
    df = pd.concat([train, test], ignore_index=True)
    for _, r in df.iterrows():
        opts = {L: _cell_text(r.get(f"Answer__{L}")) for L in "ABCDEFGHIJ" if _cell_text(r.get(f"Answer__{L}"))}
        yield {"stem": r["ItemStem_Text"], "options": opts, "answer": r["Answer_Key"]}


def load_llm_items():
    first = {}
    for line in (root / "data/generated/items_full.jsonl").read_text().splitlines():
        if not line.strip(): continue
        r = json.loads(line)
        if r.get("condition") != "plain": continue
        item = usable_record(r)
        if item and r["job_id"] not in first: first[r["job_id"]] = item
    return list(first.values())


def robust_logit(X, y, names):
    beta, cov_m = logit_fit(X, y)
    cov = cluster_robust_cov(X, y, beta, cov_m, np.arange(len(y)))
    se = np.sqrt(np.diag(cov)); z = beta / se; p = 2 * norm_sf(np.abs(z))
    return {n: (beta[i], se[i], p[i]) for i, n in enumerate(names)}


def main(out_path=None):
    buf = io.StringIO()
    def P(*a):
        print(*a); print(*a, file=buf)
    nb = pd.read_csv(root / "outputs/flags_nbme.csv"); nb5 = nb[nb.n_options == 5].copy()
    ll = pd.read_csv(root / "outputs/flags_full.csv"); ll = ll[(ll.condition == "plain") & (ll.get("reasoning_mode", "off") == "off")].copy()
    P("Detector %s. LLM plain-prompt items: %d (all five-option). NBME five-option items: %d of %d." % (VERSION, len(ll), len(nb5), len(nb)))
    P("\n== 1. Prevalence (%%) with Wilson 95%% CI: LLM plain vs NBME five-option")
    P("%-28s %-24s %-24s" % ("", "LLM plain", "NBME five-option"))
    for name, rules in (("any core flaw (14)", CORE), ("any validated-rule flaw (10)", VALIDATED)):
        a = wilson(any_flaw(ll, rules).sum(), len(ll)); b = wilson(any_flaw(nb5, rules).sum(), len(nb5))
        P("%-28s %5.1f [%4.1f, %4.1f]        %5.1f [%4.1f, %4.1f]" % (name, 100 * a[0], 100 * a[1], 100 * a[2], 100 * b[0], 100 * b[1], 100 * b[2]))
    for f in CORE + ["option_length_outlier", "options_not_alphabetical"]:
        a = wilson(ll[f].sum(), len(ll)); b = wilson(nb5[f].sum(), len(nb5))
        P("%-28s %5.1f [%4.1f, %4.1f]        %5.1f [%4.1f, %4.1f]" % (f, 100 * a[0], 100 * a[1], 100 * a[2], 100 * b[0], 100 * b[1], 100 * b[2]))
    P("  stem length (words): LLM median %.0f (IQR %.0f-%.0f); NBME median %.0f (IQR %.0f-%.0f)" % (
        ll.stem_words.median(), ll.stem_words.quantile(.25), ll.stem_words.quantile(.75), nb5.stem_words.median(), nb5.stem_words.quantile(.25), nb5.stem_words.quantile(.75)))

    P("\n== 2. Source effect adjusted for log stem length (logistic regression, robust SEs); OR for LLM vs NBME")
    both = pd.concat([ll.assign(llm=1), nb5.assign(llm=0)], ignore_index=True)
    both["log_stem"] = np.log(both.stem_words.clip(lower=1))
    for name, y in (("any core flaw (14)", any_flaw(both, CORE)), ("any validated-rule flaw (10)", any_flaw(both, VALIDATED)), ("clang_cue", both.clang_cue), ("longest_option_key", both.longest_option_key), ("absolute_terms", both.absolute_terms)):
        X = np.column_stack([np.ones(len(both)), both.llm.values.astype(float)]); r = robust_logit(X, y.values.astype(float), ["i", "llm"])["llm"]
        Xa = np.column_stack([np.ones(len(both)), both.llm.values.astype(float), both.log_stem.values]); ra = robust_logit(Xa, y.values.astype(float), ["i", "llm", "log_stem"])["llm"]
        P("  %-28s unadjusted OR %.2f [%.2f, %.2f] p=%.2g   adjusted for stem length OR %.2f [%.2f, %.2f] p=%.2g" % (
            name, math.exp(r[0]), math.exp(r[0] - 1.96 * r[1]), math.exp(r[0] + 1.96 * r[1]), r[2], math.exp(ra[0]), math.exp(ra[0] - 1.96 * ra[1]), math.exp(ra[0] + 1.96 * ra[1]), ra[2]))

    P("\n== 3. Clang-cue prevalence (%) by stem-length quintile (quintiles of the pooled distribution)")
    both["q"] = pd.qcut(both.stem_words, 5, labels=False, duplicates="drop")
    for q in sorted(both.q.unique()):
        a = both[(both.q == q) & (both.llm == 1)]; b = both[(both.q == q) & (both.llm == 0)]
        P("  quintile %d (stem %3.0f-%3.0f words): LLM %5.1f%% (n=%d)   NBME %5.1f%% (n=%d)" % (q + 1, both[both.q == q].stem_words.min(), both[both.q == q].stem_words.max(), 100 * a.clang_cue.mean() if len(a) else float("nan"), len(a), 100 * b.clang_cue.mean() if len(b) else float("nan"), len(b)))

    P("\n== 4. Absolute-terms audit: triggering word and position (key vs distractor); aggregate counts only")
    det = Detector()
    for name, items in (("LLM plain", load_llm_items()), ("NBME (all %d items)" % len(nb), list(load_nbme_items()))):
        words = collections.Counter(); pos = collections.Counter(); n_flag = 0
        for it in items:
            res = det.detect(it)
            if not res["flaws"]["absolute_terms"]: continue
            n_flag += 1; key = res["features"]["key"]
            for L, ws in res["evidence"]["absolute_hits"].items():
                for w in ws: words[w] += 1
                pos["key" if L == key else "distractor"] += 1
        P("  %-22s flagged items %d; hits by word: %s; hits in key vs distractor: %s" % (name, n_flag, dict(words.most_common()), dict(pos)))
    if out_path:
        pathlib.Path(out_path).write_text(buf.getvalue()); print("\nwritten ->", out_path)


if __name__ == "__main__":
    main(sys.argv[sys.argv.index("-o") + 1] if "-o" in sys.argv else None)
