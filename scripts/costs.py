"""Recorded API cost per generation run and condition, summed over every stored attempt (including failed and regenerated
ones) from data/generated/items_<run>.jsonl (added 17 Sep 2026 so that the cost figures in the paper have a source).
Tier is taken from the record when present and otherwise from config/models.json (early records carry no tier field).
Usage: python3 scripts/costs.py [-o outputs/costs_v1.txt]
"""
import json, sys, pathlib, collections, io
root = pathlib.Path(__file__).resolve().parents[1]


def main(out_path=None):
    buf = io.StringIO()
    def P(*a):
        print(*a); print(*a, file=buf)
    tier_of = {m["id"]: m.get("tier", "?") for m in json.load(open(root / "config/models.json"))["models"]}
    total = 0.0
    for path in sorted((root / "data/generated").glob("items_*.jsonl")):
        run = path.stem[len("items_"):]
        if run.startswith("pilot"): continue
        cost = collections.defaultdict(float); n = collections.Counter(); tiers = collections.defaultdict(float)
        for line in path.read_text().splitlines():
            if not line.strip(): continue
            r = json.loads(line); c = float(r.get("cost_usd") or 0)
            cost[r.get("condition", "?")] += c; n[r.get("condition", "?")] += 1
            tiers[r.get("tier") or tier_of.get(r.get("model_id") or r.get("model"), "?")] += c
        run_total = sum(cost.values()); total += run_total
        P("%-16s US$%7.2f  by condition: %s  by tier: %s" % (run, run_total, {k: "%.2f (%d attempts)" % (v, n[k]) for k, v in sorted(cost.items())}, {k: round(v, 2) for k, v in sorted(tiers.items())}))
    P("TOTAL recorded generation cost (all non-pilot runs, all attempts): US$%.2f" % total)
    other = collections.OrderedDict()
    for pat, label in (("judgeR_*_benchmarker.jsonl", "per-rule judge validations, BenchMarker items (reported)"), ("judgeR_*_physician100.jsonl", "per-rule judges on the physician-rated items (Amendment 6, reasoning off)"), ("judgeR_*_reasoning*.jsonl", "per-rule judge with reasoning enabled (Amendment 6, A28, incl. pilots)"), ("judge_*_benchmarker.jsonl", "single-prompt judge pilots (superseded)"), ("items_pilot*.jsonl", "generation pilots")):
        c = 0.0
        for p in sorted((root / "data/generated").glob(pat)):
            for line in p.read_text().splitlines():
                if line.strip():
                    try: c += float(json.loads(line).get("cost_usd") or 0)
                    except Exception: pass
        other[label] = c
    for k, v in other.items(): P("%-42s US$%6.2f" % (k, v))
    P("TOTAL recorded API cost: US$%.2f" % (total + sum(other.values())))
    if out_path:
        pathlib.Path(out_path).write_text(buf.getvalue()); print("written ->", out_path)


if __name__ == "__main__":
    main(sys.argv[sys.argv.index("-o") + 1] if "-o" in sys.argv else None)
