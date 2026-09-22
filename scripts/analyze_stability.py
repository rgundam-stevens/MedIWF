"""A4 stability re-run: the same 480 jobs (first 2 topics per specialty x plain/guided x 15 models, rep-0 seed) regenerated
>= 14 days after the main corpus. Compares flaw prevalence and key position between the original rep-0 items and the re-run.
Usage: python3 scripts/analyze_stability.py outputs/flags_stability.csv outputs/flags_full.csv [outputs/analysis_stability_v1.txt]
"""
import sys, pathlib, collections, io
import pandas as pd
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from mediwf.stats import wilson, chi2_uniform
from mediwf.rules import CORE   # the 14 Tier-A flaws; one definition for every script
def main(stab_path, full_path, out_path=None):
    buf = io.StringIO()
    def P(*a): print(*a); print(*a, file=buf)
    s = pd.read_csv(stab_path); f = pd.read_csv(full_path)
    o = f[(f.topic_index < 2) & (f.rep == 0) & f.condition.isin(["plain", "guided"]) & (f.get("reasoning_mode", "off") == "off")].copy()
    for d in (s, o): d["core_any"] = (d[CORE].sum(axis=1) > 0).astype(int)
    P("Stability: %d re-run items vs %d original rep-0 items on the same model x specialty x topic x condition cells" % (len(s), len(o)))
    P("\n%-20s | any flaw original -> re-run | P(key=A) original -> re-run" % "model")
    for m in sorted(s.model_label.unique()):
        a = o[o.model_label == m]; b = s[s.model_label == m]
        P("%-20s | %5.1f%% -> %5.1f%%  (n=%d/%d)   | %.2f -> %.2f" % (m, 100 * a.core_any.mean(), 100 * b.core_any.mean(), len(a), len(b), (a.key == "A").mean(), (b.key == "A").mean()))
    for c in ("plain", "guided"):
        a = o[o.condition == c]; b = s[s.condition == c]
        pa = wilson(a.core_any.sum(), len(a)); pb = wilson(b.core_any.sum(), len(b))
        P("\n%-7s any flaw: original %.1f%% [%.1f, %.1f] -> re-run %.1f%% [%.1f, %.1f]" % (c, 100 * pa[0], 100 * pa[1], 100 * pa[2], 100 * pb[0], 100 * pb[1], 100 * pb[2]))
        P("        key distribution original %s -> re-run %s" % (dict(sorted(collections.Counter(a.key).items())), dict(sorted(collections.Counter(b.key).items()))))
    P("\nPer-rule prevalence (%), original vs re-run:")
    for r in CORE + ["option_length_outlier", "options_not_alphabetical"]:
        if o[r].sum() + s[r].sum(): P("  %-26s %5.2f -> %5.2f" % (r, 100 * o[r].mean(), 100 * s[r].mean()))
    # item-level: same cell, same seed -> is the item text identical? (compare stem word counts as a cheap proxy)
    key = ["model_label", "specialty", "topic_index", "condition"]
    m = o.merge(s, on=key, suffixes=("_o", "_s"))
    P("\nCells matched: %d; identical stem word count (proxy for identical item): %.1f%%; identical key letter: %.1f%%" % (
        len(m), 100 * (m.stem_words_o == m.stem_words_s).mean(), 100 * (m.key_o == m.key_s).mean()))
    if out_path: pathlib.Path(out_path).write_text(buf.getvalue()); print("\nwritten ->", out_path)
if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
