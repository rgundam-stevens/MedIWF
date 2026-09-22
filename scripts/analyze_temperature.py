"""Amendment 3: sensitivity of flaw rates and key position to the sampling temperature. The temperature run holds the plain
condition for the first 5 topics of each specialty at temperatures 0.0 and 1.0 (tagged jobs); the main corpus (0.7) supplies
the same cells for comparison.
Usage: python3 scripts/analyze_temperature.py outputs/flags_temperature.csv outputs/flags_full.csv [outputs/analysis_temperature_v1.txt]
"""
import sys, pathlib, collections, io
import pandas as pd
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from mediwf.stats import wilson
from mediwf.rules import CORE   # the 14 Tier-A flaws; one definition for every script
def main(t_path, full_path, out_path=None):
    buf = io.StringIO()
    def P(*a): print(*a); print(*a, file=buf)
    t = pd.read_csv(t_path); f = pd.read_csv(full_path)
    tops = sorted(t.topic_index.unique())
    base = f[(f.condition == "plain") & f.topic_index.isin(tops) & (f.rep == 0) & (f.get("reasoning_mode", "off") == "off")].copy(); base["temperature"] = 0.7
    df = pd.concat([base, t], ignore_index=True); df["core_any"] = (df[CORE].sum(axis=1) > 0).astype(int)
    P("Temperature arm: %s" % dict(collections.Counter(df.temperature)))
    for temp, s in df.groupby("temperature"):
        p, lo, hi = wilson(s.core_any.sum(), len(s))
        P("  T=%.1f n=%4d any flaw %5.1f%% [%4.1f, %4.1f]  P(key=A)=%.2f  keys=%s  mean stem words=%.0f" % (temp, len(s), 100 * p, 100 * lo, 100 * hi, (s.key == "A").mean(), dict(sorted(collections.Counter(s.key).items())), s.stem_words.mean()))
    P("\nPer model: any flaw at T=0.0 / 0.7 / 1.0")
    for m in sorted(df.model_label.unique()):
        v = [100 * df[(df.model_label == m) & (df.temperature == x)].core_any.mean() for x in (0.0, 0.7, 1.0)]
        P("  %-20s %5.1f%% / %5.1f%% / %5.1f%%" % (m, *v))
    if out_path: pathlib.Path(out_path).write_text(buf.getvalue()); print("\nwritten ->", out_path)
if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
