"""Summarize a generation run WITHOUT printing item text. Usage: python3 scripts/summarize_run.py pilot"""
import json, sys, pathlib, collections
root = pathlib.Path(__file__).resolve().parents[1]
run = sys.argv[1] if len(sys.argv) > 1 else "pilot"
p = root / "data" / "generated" / f"items_{run}.jsonl"
raw = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
# de-duplicate by job_id: keep the successful record if any, else the last attempt
best = {}
for r in raw:
    j = r["job_id"]
    if j not in best or (r.get("parsed") and not best[j].get("parsed")): best[j] = r
recs = list(best.values())
print(f"raw records={len(raw)} (including retried failures)")
by = collections.defaultdict(lambda: dict(n=0, ok=0, cost=0.0, ptok=0, ctok=0, lat=0.0, errs=collections.Counter(), nopt=collections.Counter(), keys=collections.Counter(), providers=collections.Counter(), stem_len=0))
for r in recs:
    b = by[r["model_id"]]; b["n"] += 1
    b["cost"] += float(r.get("cost_usd") or 0); b["ptok"] += int(r.get("prompt_tokens") or 0); b["ctok"] += int(r.get("completion_tokens") or 0)
    b["lat"] += float(r.get("latency_s") or 0); b["providers"][str(r.get("provider"))] += 1
    if r.get("parsed"):
        b["ok"] += 1; b["nopt"][r["parsed"]["n_options"]] += 1; b["keys"][r["parsed"]["answer"]] += 1; b["stem_len"] += len(r["parsed"]["stem"])
    else:
        b["errs"][r.get("parse_error") or r.get("error", "?")[:40]] += 1
print(f"run={run}  records={len(recs)}")
for mid, b in sorted(by.items()):
    per = b["cost"] / b["n"] if b["n"] else 0
    print(f"\n{mid}\n  n={b['n']} parsed_ok={b['ok']} cost=${b['cost']:.4f} (${per:.4f}/item) tokens in/out={b['ptok']}/{b['ctok']} mean_latency={b['lat']/max(b['n'],1):.1f}s")
    print(f"  providers={dict(b['providers'])} n_options={dict(b['nopt'])} key_positions={dict(b['keys'])} mean_stem_chars={b['stem_len']//max(b['ok'],1)}")
    if b["errs"]: print(f"  errors={dict(b['errs'])}")
