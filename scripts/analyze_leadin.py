"""Stems without a question sentence (missing lead-in) in the main corpus and in the NBME reference items.
A stem counts as having a lead-in if it contains a question mark, ends with a colon or with an unfinished sentence (completion
form, e.g. "The most likely diagnosis is"), or has a sentence that begins with an interrogative or imperative lead-in word
(which, what, who, where, when, how, why, identify, select, choose).
Everything else is 'no lead-in': the options follow a vignette that never poses a question. Aggregate counts only.
Usage: python3 scripts/analyze_leadin.py [out.txt]   (default: outputs/analysis_leadin_v1.txt)
"""
import re, json, sys, pathlib, collections
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from mediwf.parsing import usable_record
root = pathlib.Path(__file__).resolve().parents[1]
LEAD = re.compile(r"(?:^|[.?!:]\s+)(which|what|who|where|when|how|why|identify|select|choose)\b", re.I)

def has_leadin(stem):
    s = " ".join(str(stem or "").split())
    unfinished = not re.search(r"[.!?:]$", s)   # completion form without a colon
    return ("?" in s) or s.endswith(":") or unfinished or bool(LEAD.search(s))

def load_corpus(run):
    best = {}
    for line in (root / "data/generated" / f"items_{run}.jsonl").read_text().splitlines():
        if not line.strip(): continue
        r = json.loads(line)
        if r["job_id"] in best: continue
        item = usable_record(r)
        if item: best[r["job_id"]] = dict(r, parsed=item)
    return list(best.values())

def main():
    out = []
    items = load_corpus("full")
    n = len(items); miss = [r for r in items if not has_leadin(r["parsed"]["stem"])]
    out.append("Main corpus (items_full): %d items; stems with no lead-in: %d (%.1f%%)" % (n, len(miss), 100 * len(miss) / n))
    bc = collections.Counter(r["condition"] for r in items); mc = collections.Counter(r["condition"] for r in miss)
    for c in sorted(bc): out.append("  %-7s %4d of %d (%.1f%%)" % (c, mc[c], bc[c], 100 * mc[c] / bc[c]))
    bm = collections.Counter((r["model_label"], r["condition"]) for r in items); mm = collections.Counter((r["model_label"], r["condition"]) for r in miss)
    out.append("  by model (plain / guided):")
    for m in sorted({k[0] for k in bm}, key=lambda m: -mm[(m, "plain")]):
        out.append("    %-22s plain %3d of %d (%.1f%%)   guided %3d of %d (%.1f%%)" % (m, mm[(m, "plain")], bm[(m, "plain")], 100 * mm[(m, "plain")] / bm[(m, "plain")], mm[(m, "guided")], bm[(m, "guided")], 100 * mm[(m, "guided")] / bm[(m, "guided")]))
    # NBME
    try:
        import pandas as pd
        d = root / "data" / "nbme"
        df = pd.concat([pd.read_excel(d / "train_final.xlsx"), pd.read_excel(d / "test_final.xlsx")], ignore_index=True)
        nb = [not has_leadin(s) for s in df["ItemStem_Text"]]
        out.append("NBME reference items: %d; stems with no lead-in: %d (%.1f%%)" % (len(nb), sum(nb), 100 * sum(nb) / len(nb)))
    except Exception as e:
        out.append("NBME: not computed (%s)" % e)
    txt = "\n".join(out); print(txt)
    (pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else root / "outputs" / "analysis_leadin_v1.txt").write_text(txt + "\n")

if __name__ == "__main__":
    main()
