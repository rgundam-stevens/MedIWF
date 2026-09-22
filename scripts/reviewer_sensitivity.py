"""Sensitivity analyses requested by the v0.6 reviews (21 Sep 2026). Runs on the machine holding the NBME data; prints
aggregate statistics only.
  1. Threshold sweep for the longest-option rule (length ratio x minimum key words): prevalence in LLM plain, LLM guided
     and NBME five-option items, any-core-flaw prevalence with the other 13 rules fixed at v1.2, and the LLM-vs-NBME OR.
  2. Threshold sweep for the non-parallel rule's word-count CV cut.
  3. Marginal contribution of the longest-option rule to the any-flaw composite.
  4. LLM-vs-NBME source comparison adjusted for option length (mean option characters, option-length CV) as well as stem length.
  5. Longest-option prevalence within tertiles of mean option length, both sources.
  6. NBME examinee-statistics regressions with option-length covariates added.
Usage: python3 scripts/reviewer_sensitivity.py -> outputs/analysis_reviewer_sensitivity_v1.txt
"""
import sys, json, pathlib, io, math, statistics
import numpy as np, pandas as pd
root = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "src")); sys.path.insert(0, str(root / "scripts"))
from mediwf.stats import logit_fit, cluster_robust_cov, design, ols_robust, wilson, norm_sf
from mediwf.rules import CORE, VALIDATED, CUEING
from mediwf.detector import Detector, _key_letter
from mediwf.parsing import usable_record
from detect import _cell_text

def feats(item):
    opts = item["options"]; key = _key_letter(item["answer"])
    lens = {l: len(o.strip()) for l, o in opts.items()}
    if key not in lens: return None
    d = [v for l, v in lens.items() if l != key]
    allv = list(lens.values())
    return dict(key_chars=lens[key], longest_d=max(d) if d else 0, key_words=len(opts[key].split()),
                mean_opt=statistics.mean(allv), cv_opt=(statistics.pstdev(allv) / statistics.mean(allv)) if statistics.mean(allv) else 0.0,
                max_opt=max(allv), n_opt=len(allv))

def load_llm():
    rows = []; seen = set()
    for line in (root / "data/generated/items_full.jsonl").read_text().splitlines():
        if not line.strip(): continue
        r = json.loads(line)
        if r["job_id"] in seen: continue
        it = usable_record(r)
        if not it: continue
        f = feats(it)
        if f is None: continue
        seen.add(r["job_id"]); rows.append(dict(job_id=r["job_id"], condition=r["condition"], model_label=r["model_label"], item=it, **f))
    return pd.DataFrame(rows)

def load_nbme():
    d = root / "data" / "nbme"
    train = pd.read_excel(d / "train_final.xlsx"); test = pd.read_excel(d / "test_final.xlsx").merge(pd.read_excel(d / "gold_final.xlsx"), on="ItemNum")
    df = pd.concat([train, test], ignore_index=True); rows = []
    for _, r in df.iterrows():
        opts = {L: _cell_text(r.get(f"Answer__{L}")) for L in "ABCDEFGHIJ" if _cell_text(r.get(f"Answer__{L}"))}
        it = {"stem": r["ItemStem_Text"], "options": opts, "answer": r["Answer_Key"]}
        f = feats(it)
        if f is None: continue
        rows.append(dict(ItemNum=int(r["ItemNum"]), item=it, **f))
    return pd.DataFrame(rows)

def robust_or(X, y, idx=1):
    beta, cov_m = logit_fit(X, y); cov = cluster_robust_cov(X, y, beta, cov_m, np.arange(len(y)))
    se = math.sqrt(cov[idx, idx]); return math.exp(beta[idx]), math.exp(beta[idx] - 1.96 * se), math.exp(beta[idx] + 1.96 * se)

def main():
    buf = io.StringIO()
    def P(*a): print(*a); print(*a, file=buf)
    det = Detector()
    ll = load_llm(); nb = load_nbme()
    fl = pd.read_csv(root / "outputs/flags_full.csv"); fl = fl[(fl.condition.isin(["plain", "guided"])) & (fl.get("reasoning_mode", "off") == "off")]
    ll = ll.merge(fl[["job_id"] + CORE], on="job_id", how="inner")
    fn = pd.read_csv(root / "outputs/flags_nbme.csv"); nb = nb.merge(fn[["ItemNum", "n_options"] + CORE], on="ItemNum", how="inner")
    nb5 = nb[nb.n_options == 5].copy(); plain = ll[ll.condition == "plain"].copy(); guided = ll[ll.condition == "guided"].copy()
    OTHER = [r for r in CORE if r != "longest_option_key"]
    P("Detector %s. LLM plain %d, guided %d; NBME five-option %d of %d." % (det.__class__.__name__ and "v1.2", len(plain), len(guided), len(nb5), len(nb)))
    # check that the recomputed rule reproduces v1.2 flags
    rep = ((plain.key_chars > 1.25 * plain.longest_d) & (plain.key_words >= 4)).astype(int)
    P("recomputed longest-option rule agrees with flags_full.csv on %.4f of plain items" % (rep.values == plain.longest_option_key.values).mean())

    P("\n== 1. Longest-option rule: threshold sweep (prevalence %%; any-core = any of the 14 rules with the other 13 fixed at v1.2)")
    P("%-9s %-9s | %-11s %-11s %-11s | %-22s | %-22s | %-24s" % ("ratio", "min words", "LLM plain", "LLM guided", "NBME-5", "rule OR LLM vs NBME", "any-core: LLM / NBME", "any-core OR LLM vs NBME"))
    for ratio in (1.10, 1.15, 1.20, 1.25, 1.30, 1.40, 1.50, 1.75, 2.00):
        for mw in (1, 4, 6):
            def rule(df): return ((df.key_chars > ratio * df.longest_d) & (df.key_words >= mw)).astype(int)
            rp, rg, rn = rule(plain), rule(guided), rule(nb5)
            ap = ((plain[OTHER].sum(axis=1) + rp) > 0).astype(int); an = ((nb5[OTHER].sum(axis=1) + rn) > 0).astype(int)
            y = np.concatenate([rp.values, rn.values]).astype(float); X = np.column_stack([np.ones(len(y)), np.concatenate([np.ones(len(rp)), np.zeros(len(rn))])])
            o = robust_or(X, y) if rn.sum() > 0 and rp.sum() > 0 else (float("nan"),) * 3
            ya = np.concatenate([ap.values, an.values]).astype(float); oa = robust_or(X, ya)
            P("%-9.2f %-9d | %10.1f%% %10.1f%% %10.1f%% | %5.2f (%5.2f-%5.2f)      | %5.1f%% / %5.1f%%          | %5.2f (%5.2f-%5.2f)" % (ratio, mw, 100 * rp.mean(), 100 * rg.mean(), 100 * rn.mean(), o[0], o[1], o[2], 100 * ap.mean(), 100 * an.mean(), oa[0], oa[1], oa[2]))

    P("\n== 2. Non-parallel rule: word-count CV cut (numeric/text and sentence/fragment mixes unchanged)")
    for cv in (0.40, 0.50, 0.60, 0.70, 0.80):
        det.NONPARALLEL_CV = cv
        vals = {}
        for name, df in (("plain", plain), ("guided", guided), ("nbme5", nb5)):
            vals[name] = np.array([int(det._nonparallel(it["options"])[0]) for it in df.item])
        p_, g_, n_ = vals["plain"].mean(), vals["guided"].mean(), vals["nbme5"].mean()
        orgp = ((g_ / (1 - g_)) / (p_ / (1 - p_))) if 0 < p_ < 1 and 0 < g_ < 1 else float("nan")
        P("  CV > %.2f: LLM plain %5.1f%%  guided %5.1f%%  NBME-5 %5.1f%%  | guided vs plain OR %.2f" % (cv, 100 * p_, 100 * g_, 100 * n_, orgp))
    det.NONPARALLEL_CV = 0.60

    P("\n== 3. Marginal contribution of the longest-option rule to the any-core composite")
    for name, df in (("LLM plain", plain), ("LLM guided", guided), ("NBME-5", nb5)):
        with_ = (df[CORE].sum(axis=1) > 0).mean(); without = (df[OTHER].sum(axis=1) > 0).mean()
        P("  %-10s any core flaw %5.1f%% -> without the longest-option rule %5.1f%% (difference %.1f points)" % (name, 100 * with_, 100 * without, 100 * (with_ - without)))

    P("\n== 4. Source comparison, LLM plain vs NBME five-option, adjusted for option length (logistic regression, robust SEs; OR for LLM)")
    both = pd.concat([plain.assign(llm=1), nb5.assign(llm=0)], ignore_index=True)
    both["log_stem"] = np.log(np.array([len(it["stem"].split()) for it in both.item]).clip(1)); both["log_mean_opt"] = np.log(both.mean_opt.clip(lower=1))
    P("  stem words: LLM median %.0f, NBME median %.0f | mean option chars: LLM median %.0f, NBME median %.0f | option-length CV: LLM median %.2f, NBME median %.2f" % (
        np.median(np.exp(both.log_stem[both.llm == 1])), np.median(np.exp(both.log_stem[both.llm == 0])), plain.mean_opt.median(), nb5.mean_opt.median(), plain.cv_opt.median(), nb5.cv_opt.median()))
    outcomes = {"any core flaw (14)": (both[CORE].sum(axis=1) > 0).astype(float), "any validated-rule flaw (10)": (both[VALIDATED].sum(axis=1) > 0).astype(float), "longest_option_key": both.longest_option_key.astype(float), "clang_cue": both.clang_cue.astype(float)}
    adjust = {"unadjusted": [], "log stem": ["log_stem"], "log stem + log mean option chars": ["log_stem", "log_mean_opt"], "log stem + option CV": ["log_stem", "cv_opt"], "log stem + mean option chars + option CV": ["log_stem", "log_mean_opt", "cv_opt"]}
    for oname, y in outcomes.items():
        P("  " + oname)
        for aname, cols in adjust.items():
            X = np.column_stack([np.ones(len(both)), both.llm.values.astype(float)] + [both[c].values.astype(float) for c in cols])
            o = robust_or(X, y.values)
            P("    %-44s OR %.2f (%.2f-%.2f)" % (aname, *o))

    P("\n== 5. Longest-option prevalence within tertiles of mean option length (pooled tertiles)")
    both["tert"] = pd.qcut(both.mean_opt, 3, labels=False)
    for t in sorted(both.tert.unique()):
        a = both[(both.tert == t) & (both.llm == 1)]; b = both[(both.tert == t) & (both.llm == 0)]
        P("  tertile %d (mean option %3.0f-%3.0f chars): LLM %5.1f%% (n=%d)   NBME %5.1f%% (n=%d)" % (t + 1, both[both.tert == t].mean_opt.min(), both[both.tert == t].mean_opt.max(), 100 * a.longest_option_key.mean(), len(a), 100 * b.longest_option_key.mean() if len(b) else float("nan"), len(b)))

    P("\n== 6. NBME examinee statistics with option-length covariates (OLS, HC1; adjusting for step, item type, log stem words, log mean option chars, option-length CV)")
    full = pd.read_csv(root / "outputs/flags_nbme.csv").merge(nb[["ItemNum", "mean_opt", "cv_opt"]], on="ItemNum")
    full["log_stem_words"] = np.log(full.stem_words.clip(lower=1)); full["text_item"] = (full.ItemType == "Text").astype(int)
    full["log_mean_opt"] = np.log(full.mean_opt.clip(lower=1)); full["n_core"] = full[CUEING].sum(axis=1)
    P("  difficulty SD %.3f; response time mean %.1f s, SD %.1f" % (full.Difficulty.std(), full.Response_Time.mean(), full.Response_Time.std()))
    for outcome in ("Difficulty", "Response_Time"):
        P("  outcome: " + outcome)
        for flaw in ("n_core", "absolute_terms", "clang_cue", "longest_option_key", "option_length_outlier"):
            for label, extra in (("stem length only (as reported)", []), ("+ option length and CV", ["log_mean_opt", "cv_opt"])):
                X, names = design(full, [flaw, "log_stem_words", "text_item"] + extra, {"EXAM": "STEP 1"})
                res, r2 = ols_robust(X, full[outcome].values.astype(float), names); r = res[flaw]
                P("    %-22s %-32s b=%+.3f [%+.3f, %+.3f] p=%.3g" % (flaw, label, r["coef"], r["lo"], r["hi"], r["p"]))
    (root / "outputs/analysis_reviewer_sensitivity_v1.txt").write_text(buf.getvalue()); print("\nwritten -> outputs/analysis_reviewer_sensitivity_v1.txt")

if __name__ == "__main__":
    main()
