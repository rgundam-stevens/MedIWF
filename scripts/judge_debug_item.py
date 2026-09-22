"""Diagnose and fill one item whose judge verdicts keep failing (empty or truncated responses).
Runs the missing rules for the item, prints finish_reason / token counts / the first characters of the content, retries once
with a larger completion budget if the content is empty or truncated, and appends a merged record to the judge file when a
verdict is obtained. Usage: python3 scripts/judge_debug_item.py --judge anthropic/claude-fable-5.1 --physician --uid MAIN-047
"""
import sys, json, argparse, pathlib, datetime, re
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import judge_perrule as jp
from mediwf.openrouter import OpenRouterClient
from mediwf.env import require

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--judge", required=True); ap.add_argument("--uid", required=True)
    ap.add_argument("--physician", action="store_true"); ap.add_argument("--validate", action="store_true")
    ap.add_argument("--rules", nargs="*", default=["single_best_answer", "plausible_distractors", "no_extraneous_info", "focused_stem"])
    a = ap.parse_args()
    items, target = (jp.physician_items(), "physician100") if a.physician else (jp.validation_items(), "benchmarker")
    it = next(i for i in items if i["uid"] == a.uid)
    slug = re.sub(r"[^a-z0-9]+", "-", a.judge.lower()); out = jp.OUT / f"judgeR_{slug}_{target}.jsonl"
    prev = {}; details = {}
    for line in out.read_text().splitlines():
        try: rec = json.loads(line)
        except Exception: continue
        if rec.get("uid") == a.uid and rec.get("judgment"): prev = dict(rec["judgment"]); details = dict(rec.get("details") or {})
    todo = [r for r in a.rules if r not in prev]
    print("item", a.uid, "| already have:", sorted(prev), "| to run:", todo)
    client = OpenRouterClient(require("OPENROUTER_API_KEY")); cost = 0.0; ptok = ctok = 0; errors = {}
    for rule in todo:
        for attempt, mt in enumerate((600, 4000)):
            res = client.chat(a.judge, jp.SYSTEM, jp.render(rule, it["item"]), temperature=0.0, seed=7, max_tokens=mt)
            cost += float(res.get("cost_usd") or 0); ptok += int(res.get("prompt_tokens") or 0); ctok += int(res.get("completion_tokens") or 0)
            content = res.get("content") or ""
            print("  %s attempt %d (max_tokens %d): ok=%s finish=%s completion_tokens=%s reasoning_tokens=%s provider=%s content[:160]=%r error=%r" % (
                rule, attempt + 1, mt, res.get("ok"), res.get("finish_reason"), res.get("completion_tokens"), res.get("reasoning_tokens"), res.get("provider"), content[:160], (res.get("error") or "")[:160]))
            pr = jp.parse_result(content) if res.get("ok") else None
            if pr is not None:
                prev[rule] = pr["fail"]; details[rule] = {"confidence": pr["confidence"], "explanation": pr["explanation"]}; break
        else:
            errors[rule] = (res.get("error") or content[:200])
    if any(r in prev for r in todo):
        rec = {"uid": a.uid, "dataset": it.get("dataset"), "judge": a.judge, "mode": "perrule", "requested_at": datetime.datetime.utcnow().isoformat() + "Z",
               "judgment": prev, "details": details, "errors": errors, "cost_usd": cost, "prompt_tokens": ptok, "completion_tokens": ctok, "note": "filled by judge_debug_item.py"}
        with out.open("a") as f: f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print("appended merged record; verdicts now:", sorted(prev), "| this run cost $%.3f" % cost)
    else:
        print("no verdict obtained; nothing written; cost $%.3f" % cost)

if __name__ == "__main__":
    main()
