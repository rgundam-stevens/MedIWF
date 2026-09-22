"""Near-duplicate items between the two repetitions of a cell (added 17 Sep 2026; the '24% for Llama 4 Maverick, <=7% for
other models' figures had no script). For every model x condition x topic, the two repetitions' stem+options text is
compared by word 3-gram Jaccard similarity; a pair is a near-duplicate at Jaccard >= 0.5. Item text is never printed.
Usage: python3 scripts/near_duplicates.py [-o outputs/analysis_duplicates_v1.txt]
"""
import sys, re, json, pathlib, io, collections
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from mediwf.parsing import usable_record
root = pathlib.Path(__file__).resolve().parents[1]


def grams(text, n=3):
    w = re.findall(r"[a-z0-9]+", text.lower())
    return {tuple(w[i:i + n]) for i in range(len(w) - n + 1)}


def main(out_path=None):
    buf = io.StringIO()
    def P(*a):
        print(*a); print(*a, file=buf)
    first = {}
    for line in (root / "data/generated/items_full.jsonl").read_text().splitlines():
        if not line.strip(): continue
        r = json.loads(line); item = usable_record(r)
        if item and r["job_id"] not in first: first[r["job_id"]] = (r, item)
    cells = collections.defaultdict(dict)
    for r, it in first.values():
        text = it["stem"] + " " + " ".join(str(v) for v in it["options"].values())
        cells[(r["model_label"], r["condition"], r["specialty"], r["topic_index"])][r["rep"]] = grams(text)
    per = collections.defaultdict(list)
    for (m, c, sp, t), reps in cells.items():
        if len(reps) == 2:
            a, b = reps.values(); j = len(a & b) / max(1, len(a | b)); per[(m, c)].append(j)
    P("Near-duplicate repetition pairs (word 3-gram Jaccard >= 0.5), main corpus")
    P("%-20s %-7s %5s %8s %8s %8s" % ("model", "cond", "pairs", ">=0.5 %", ">=0.8 %", "median J"))
    allj = collections.defaultdict(list)
    for (m, c), js in sorted(per.items()):
        allj[m] += js
        P("%-20s %-7s %5d %8.1f %8.1f %8.2f" % (m, c, len(js), 100 * sum(j >= 0.5 for j in js) / len(js), 100 * sum(j >= 0.8 for j in js) / len(js), sorted(js)[len(js) // 2]))
    P("\nPer model (both conditions):")
    for m, js in sorted(allj.items(), key=lambda kv: -sum(j >= 0.5 for j in kv[1]) / len(kv[1])):
        P("  %-20s pairs=%d  near-duplicates %.1f%%" % (m, len(js), 100 * sum(j >= 0.5 for j in js) / len(js)))
    tot = [j for js in allj.values() for j in js]
    P("  ALL: %d pairs, %.1f%% near-duplicates" % (len(tot), 100 * sum(j >= 0.5 for j in tot) / len(tot)))
    if out_path:
        pathlib.Path(out_path).write_text(buf.getvalue()); print("written ->", out_path)


if __name__ == "__main__":
    main(sys.argv[sys.argv.index("-o") + 1] if "-o" in sys.argv else None)
