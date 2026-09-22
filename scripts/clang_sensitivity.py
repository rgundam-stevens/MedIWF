"""Sensitivity of the clang-cue prevalence to the rule's strictness.
v1.2 rule (reported): an exclusive stem-key content word AND (two such words OR key-stem overlap >= 2x the best distractor's).
One-word rule (the Rater Guide's definition): any content word shared by stem and key and absent from every distractor.
One-word, plural-folding only: the same with the hand-check helper's lemmatiser (singular/plural folding, no -ing/-ed).
Aggregate counts only. Usage: python3 scripts/clang_sensitivity.py -> outputs/analysis_clang_sensitivity_v1.txt
"""
import sys, re, json, pathlib, collections
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src")); sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from mediwf.detector import Detector, _content_words, _tokens, STOPWORDS, _key_letter
from mediwf.parsing import usable_record
root = pathlib.Path(__file__).resolve().parents[1]
det = Detector()

def fold(w):
    if len(w) > 4 and w.endswith("ies"): return w[:-3] + "y"
    if len(w) > 4 and w.endswith(("xes", "zes", "ches", "shes", "sses")): return w[:-2]
    if len(w) > 4 and w.endswith("s") and not w.endswith("ss"): return w[:-1]
    return w

def words_plural_only(s):
    return {fold(w.strip("-'")) for w in _tokens(s) if len(w.strip("-'")) >= 4 and w.strip("-'") not in STOPWORDS}

def variants(item):
    res = det.detect(item)
    key = res["features"]["key"]; opts = item["options"]
    if key not in opts: return {"v12": False, "one_word": False, "one_word_plural": False}
    ds = [o for l, o in opts.items() if l != key]
    a = (_content_words(item["stem"]) & _content_words(opts[key])) - set().union(*[_content_words(d) for d in ds])
    b = (words_plural_only(item["stem"]) & words_plural_only(opts[key])) - set().union(*[words_plural_only(d) for d in ds])
    return {"v12": bool(res["flaws"]["clang_cue"]), "one_word": bool(a), "one_word_plural": bool(b)}

def load_corpus(run):
    best = {}
    for line in (root / "data/generated" / f"items_{run}.jsonl").read_text().splitlines():
        if not line.strip(): continue
        r = json.loads(line)
        if r["job_id"] in best: continue
        it = usable_record(r)
        if it: best[r["job_id"]] = dict(r, parsed=it)
    return list(best.values())

def spearman(x, y):
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i]); r = [0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]: j += 1
            for k in range(i, j + 1): r[order[k]] = (i + j) / 2 + 1
            i = j + 1
        return r
    rx, ry = rank(x), rank(y); n = len(x); mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry)); den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return num / den if den else float("nan")

def main():
    out = []; V = ["v12", "one_word", "one_word_plural"]
    items = load_corpus("full")
    rows = [(r["model_label"], r["condition"], variants(r["parsed"])) for r in items]
    out.append("Clang-cue prevalence in the main corpus (12,000 items) under three rule variants")
    out.append("%-10s %8s %10s %16s" % ("condition", "v1.2", "one-word", "one-word/plural"))
    for c in ("plain", "guided"):
        sub = [v for m, cc, v in rows if cc == c]
        out.append("%-10s " % c + " ".join("%9.1f%%" % (100 * sum(v[k] for v in sub) / len(sub)) for k in V))
    for k in V:
        p = sum(v[k] for m, c, v in rows if c == "plain") / 6000; g = sum(v[k] for m, c, v in rows if c == "guided") / 6000
        out.append("  guided vs plain odds ratio, %-16s %.2f" % (k + ":", (g / (1 - g)) / (p / (1 - p))))
    models = sorted({m for m, c, v in rows})
    pm = {k: [sum(v[k] for m2, c, v in rows if m2 == m and c == "plain") / 400 for m in models] for k in V}
    out.append("Per-model plain-prompt rates (15 models): Spearman rank correlation with the v1.2 rule: one-word %.2f, one-word/plural %.2f" % (spearman(pm["v12"], pm["one_word"]), spearman(pm["v12"], pm["one_word_plural"])))
    out.append("  %-22s %6s %9s %16s" % ("model (plain)", "v1.2", "one-word", "one-word/plural"))
    for i, m in enumerate(models): out.append("  %-22s %5.1f%% %8.1f%% %15.1f%%" % (m, 100 * pm["v12"][i], 100 * pm["one_word"][i], 100 * pm["one_word_plural"][i]))
    # NBME
    try:
        import pandas as pd
        from detect import _cell_text
        d = root / "data" / "nbme"
        df = pd.concat([pd.read_excel(d / "train_final.xlsx"), pd.read_excel(d / "test_final.xlsx")], ignore_index=True)
        nb = []
        for _, r in df.iterrows():
            opts = {L: _cell_text(r.get(f"Answer__{L}")) for L in "ABCDEFGHIJ" if _cell_text(r.get(f"Answer__{L}"))}
            nb.append(variants({"stem": r["ItemStem_Text"], "options": opts, "answer": r["Answer_Key"]}))
        out.append("NBME reference items, all %d: " % len(nb) + ", ".join("%s %.1f%%" % (k, 100 * sum(v[k] for v in nb) / len(nb)) for k in V))
        nb5 = [v for v, (_, r) in zip(nb, df.iterrows()) if sum(1 for L in "ABCDEFGHIJ" if _cell_text(r.get(f"Answer__{L}"))) == 5]
        out.append("NBME five-option items, %d: " % len(nb5) + ", ".join("%s %.1f%%" % (k, 100 * sum(v[k] for v in nb5) / len(nb5)) for k in V))
    except Exception as e:
        out.append("NBME: not computed (%s)" % e)
    txt = "\n".join(out); print(txt); (root / "outputs" / "analysis_clang_sensitivity_v1.txt").write_text(txt + "\n")

if __name__ == "__main__":
    main()
