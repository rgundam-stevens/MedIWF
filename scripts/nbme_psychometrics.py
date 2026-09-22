"""RQ5: do automatically flagged flaws relate to real examinee statistics on the NBME/BEA 2024 items?
Runs ONLY on the local machine holding the NBME data; prints aggregate statistics, never item text.
Usage: python3 scripts/nbme_psychometrics.py
"""
import sys, pathlib
import numpy as np, pandas as pd
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from mediwf.stats import design, ols_robust, bh_fdr, wilson
from mediwf.rules import CORE as CORE14, CUEING, any_flaw, n_flaws

root = pathlib.Path(__file__).resolve().parents[1]
df = pd.read_csv(root / "outputs" / "flags_nbme.csv")
df["log_stem_words"] = np.log(df["stem_words"].clip(lower=1))
df["text_item"] = (df["ItemType"] == "Text").astype(int)
# v1.2 audit fix: "core_any" is the same 14-rule composite as everywhere else (an earlier version used six rules here,
# which printed 16.5% next to the manuscript's 17.1%); the flaw-count regressor counts the four answer-cueing flaws.
CORE = ["longest_option_key", "absolute_terms", "clang_cue", "grammatical_cue", "nonparallel_options", "overlapping_options",
        "option_length_outlier", "options_not_alphabetical"]   # rules/features tested one at a time (>= 10 flagged items)
df["core_any"] = any_flaw(df, CORE14)
df["n_core"] = n_flaws(df, CUEING)
five = df[df.n_options == 5]
print("NBME items:", len(df), "| any core flaw (14 rules): %.1f%%" % (100 * df.core_any.mean()), "| five-option items: %d, any core flaw %.1f%%" % (len(five), 100 * five.core_any.mean()), "| mean cueing flaws/item: %.3f" % df.n_core.mean())
print("Difficulty: mean %.3f sd %.3f | Response time: mean %.1f sd %.1f" % (df.Difficulty.mean(), df.Difficulty.std(), df.Response_Time.mean(), df.Response_Time.std()))

for outcome, label in [("Difficulty", "difficulty (transformed; higher = harder)"), ("Response_Time", "response time (s)")]:
    print("\n== OLS of %s on flaw flags, adjusting for exam step, item type and log stem length (HC1 robust SE)" % label)
    rows = []; pv = []
    for fl in ["n_core", "core_any"] + CORE:   # n_core = number of cueing flaws (0-4); core_any = any of the 14 rules
        if fl not in ("n_core",) and df[fl].sum() < 10: continue
        X, names = design(df, [fl, "log_stem_words", "text_item"], {"EXAM": "STEP 1"})
        res, r2 = ols_robust(X, df[outcome].values.astype(float), names)
        r = res[fl]; rows.append((fl, int(df[fl].sum()) if fl != "n_core" else int((df.n_core > 0).sum()), r, r2)); pv.append(r["p"])
    adj = bh_fdr(pv)
    for (fl, ev, r, r2), q in zip(rows, adj):
        print("  %-26s n_flagged=%3d  b=%+.3f [%+.3f, %+.3f]  p=%.3g  q=%.3g  (R2=%.3f)" % (fl, ev, r["coef"], r["lo"], r["hi"], r["p"], q, r2))

print("\n== Descriptive: mean difficulty and response time by number of cueing flaws (longest key, absolute terms, clang, grammatical)")
print(df.groupby("n_core").agg(n=("Difficulty", "size"), difficulty=("Difficulty", "mean"), response_time=("Response_Time", "mean")).round(3).to_string())
print("\n== Key position (all 667 items):", df["key"].value_counts().sort_index().to_dict())
