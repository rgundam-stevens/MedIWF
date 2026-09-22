"""Tier-B LLM judge for content-level item-writing flaws (resumable). Runs in Terminal (needs OpenRouter).

  python3 scripts/judge.py --judge openai/gpt-5.4-mini --corpus full                 # all 6,400 MedIWF items
  python3 scripts/judge.py --judge openai/gpt-5.4-mini --corpus full --subsample 1600 # stratified subsample
  python3 scripts/judge.py --judge openai/gpt-5.4-mini --validate                     # BenchMarker exam block (human labels)

Output: data/generated/judge_<judgeslug>_<target>.jsonl ; one line per item with pass/fail per rule.
"""
import argparse, json, ast, hashlib, pathlib, random, re, sys, time, datetime, collections
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from mediwf.env import load_env, require
from mediwf.openrouter import OpenRouterClient

root = load_env()
PROMPT = (root / "config" / "prompts" / "judge.txt").read_text()
SYSTEM = "You are a meticulous, conservative reviewer of examination items. Answer only in JSON."
RULES = ["single_best_answer", "plausible_distractors", "no_extraneous_info", "focused_stem", "problem_in_stem",
         "clear_language", "no_absolute_terms", "no_vague_terms", "no_logical_cues"]
OUT = root / "data" / "generated"

def fmt(item):
    opts = "\n".join(f"{k}. {v}" for k, v in sorted(item["options"].items()))
    return PROMPT.format(stem=item["stem"], options=opts, answer=item["answer"])

def parse(text):
    if not text: return None
    m = re.search(r"\{.*\}", text, re.S)
    for cand in ([text, m.group(0)] if m else [text]):
        try:
            d = json.loads(cand)
            if isinstance(d, dict) and all(r in d for r in RULES):
                return {r: (str(d[r]).strip().lower() == "fail") for r in RULES} | {"notes": str(d.get("notes", ""))[:300]}
        except Exception:
            continue
    return None

def corpus_items(run, subsample, seed=20260914):
    recs = {}
    for line in (OUT / f"items_{run}.jsonl").read_text().splitlines():
        r = json.loads(line)
        if r.get("parsed") and r["job_id"] not in recs: recs[r["job_id"]] = r
    items = [dict(uid=r["job_id"], model_label=r["model_label"], condition=r["condition"], specialty=r["specialty"], item=r["parsed"]) for r in recs.values()]
    if subsample:
        random.seed(seed); cells = collections.defaultdict(list)
        for it in items: cells[(it["model_label"], it["condition"])].append(it)
        per = subsample // len(cells); items = []
        for k in sorted(cells): items += random.sample(cells[k], min(per, len(cells[k])))
    return items

def validation_items():
    rows = [json.loads(l) for l in (root / "data" / "external" / "benchmarker" / "writing_flaws_judge.jsonl").read_text().splitlines()]
    seen = {}
    for r in rows:
        if not (isinstance(r["label"], int) or str(r["dataset"]).startswith("human_")): continue
        ch = r["choices"] if isinstance(r["choices"], list) else ast.literal_eval(r["choices"])
        key = hashlib.sha1((r["question"] + str(ch)).encode()).hexdigest()[:12]
        if key not in seen:
            seen[key] = dict(uid=key, dataset=r["dataset"], item={"stem": r["question"], "options": {chr(65 + i): c for i, c in enumerate(ch)}, "answer": r["answer"]})
    return list(seen.values())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judge", required=True); ap.add_argument("--corpus"); ap.add_argument("--subsample", type=int, default=0)
    ap.add_argument("--validate", action="store_true"); ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    if a.validate: items, target = validation_items(), "benchmarker"
    elif a.corpus: items, target = corpus_items(a.corpus, a.subsample), (a.corpus + (f"_sub{a.subsample}" if a.subsample else ""))
    else: ap.error("--corpus RUN or --validate")
    slug = re.sub(r"[^a-z0-9]+", "-", a.judge.lower())
    out = OUT / f"judge_{slug}_{target}.jsonl"
    done = set()
    if out.exists():
        for line in out.read_text().splitlines():
            try:
                rec = json.loads(line)
                if rec.get("judgment"): done.add(rec["uid"])
            except Exception: pass
    todo = [it for it in items if it["uid"] not in done]
    print(f"judge={a.judge} target={target}: {len(items)} items, {len(done)} done, {len(todo)} to run")
    client = OpenRouterClient(require("OPENROUTER_API_KEY"))
    def work(it):
        res = client.chat(a.judge, SYSTEM, fmt(it["item"]), temperature=0.0, seed=7, max_tokens=800)
        rec = {k: v for k, v in it.items() if k != "item"}
        rec.update(judge=a.judge, requested_at=datetime.datetime.utcnow().isoformat() + "Z")
        rec.update({k: res.get(k) for k in ("ok", "error", "provider", "model_returned", "prompt_tokens", "completion_tokens", "cost_usd", "reasoning_tokens")})
        rec["judgment"] = parse(res.get("content")) if res.get("ok") else None
        rec["raw"] = (res.get("content") or "")[:1500] if not rec["judgment"] else None
        return rec
    cost = 0.0; ok = 0; t0 = time.time()
    with out.open("a") as f, ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = [ex.submit(work, it) for it in todo]
        for i, fut in enumerate(as_completed(futs), 1):
            rec = fut.result(); f.write(json.dumps(rec, ensure_ascii=False) + "\n"); f.flush()
            cost += float(rec.get("cost_usd") or 0); ok += bool(rec.get("judgment"))
            if i % 50 == 0 or i == len(todo): print(f"  {i}/{len(todo)} | parsed ok={ok} | cost ${cost:.3f} | {time.time()-t0:.0f}s")
    print("finished ->", out)

if __name__ == "__main__":
    main()
