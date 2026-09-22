"""MedIWF generation pipeline (resumable). Response parsing/validation lives in src/mediwf/parsing.py.
Run in Terminal from the MedIWF folder:
  python3 scripts/generate.py --pilot            # small pilot: measures cost/parse rate per model
  python3 scripts/generate.py --full             # full grid from the protocol
  python3 scripts/generate.py --full --models openai/xxx qwen/yyy   # subset of models
Output: data/generated/items_<run>.jsonl  (one JSON line per item, raw output + parsed fields + provenance)
Safe to re-run: finished jobs are skipped.
"""
import argparse, json, hashlib, pathlib, random, re, sys, time, datetime, os, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from mediwf.env import load_env, require
from mediwf.openrouter import OpenRouterClient

root = load_env()
CFG = root / "config"
OUT = root / "data" / "generated"; OUT.mkdir(parents=True, exist_ok=True)

def read(p): return (CFG / p).read_text()
SYSTEM = read("prompts/system.txt").strip()
PROMPTS = {"plain": read("prompts/plain.txt"), "guided": read("prompts/guided.txt"), "guided_position": read("prompts/guided_position.txt"),
           # Amendment 2 (2026-09-16), template-control arm: the plain prompt with the example answer letter in the required JSON
           # template replaced by "..." (plain_neutral) or by a balanced rotating letter A-E (plain_rotated); see docs/protocol_amendment_2.md
           "plain_neutral": read("prompts/plain_neutral.txt"), "plain_rotated": read("prompts/plain_rotated.txt"),
           # Amendment 3 (2026-09-16): guided prompt with the neutral template; paraphrased guideline wording (guided2, same template as guided)
           "guided_neutral": read("prompts/guided_neutral.txt"), "guided2": read("prompts/guided2.txt")}
SPECIALTIES = json.loads(read("specialties.json"))
MODELS = json.loads(read("models.json"))["models"]

def pretty(s): return s.replace("_", " ")

def build_jobs(pilot, models, reps, topics_per_specialty, specialties=None, conditions=("plain", "guided"), reasoning="off", tag=None, temperature=0.7):
    jobs = []
    specs = specialties or list(SPECIALTIES)
    for m in models:
        for sp in specs:
            topics = SPECIALTIES[sp][:topics_per_specialty]
            for ti, topic in enumerate(topics):
                for cond in conditions:
                    for rep in range(reps):
                        key = f"{m['id']}|{sp}|{ti}|{cond}|{rep}" + ("" if reasoning == "off" else f"|reasoning={reasoning}") + (f"|tag={tag}" if tag else "")
                        jid = hashlib.sha1(key.encode()).hexdigest()[:12]
                        # balanced cyclic assignment of the requested key position for the guided_position condition:
                        # (global topic index + model index + rep) mod 5 -> every model gets exactly 40 items per position
                        # over the 200 topics (5 per specialty), and every topic receives each position 3 times over 15 models
                        target = None
                        if cond in ("guided_position", "plain_rotated"):
                            gti = list(SPECIALTIES).index(sp) * 25 + ti
                            mi = [x["id"] for x in MODELS].index(m["id"])
                            target = "ABCDE"[(gti + mi + rep) % 5]
                        jobs.append(dict(job_id=jid, model_id=m["id"], model_label=m["label"], family=m.get("family"), tier=m.get("tier", "base"),
                                         reasoning_toggle=m.get("reasoning_toggle"),
                                         provider_order=m.get("provider_order"), specialty=sp, topic_index=ti, topic=topic,
                                         condition=cond, rep=rep, seed=1000 + rep, reasoning_mode=reasoning, target_position=target, temperature=temperature))
    return jobs

from mediwf.parsing import parse_item, usable_record, EXPECTED_OPTIONS   # validator shared with scripts/detect.py

def run_job(client, job):
    prompt = PROMPTS[job["condition"]].format(specialty=pretty(job["specialty"]), topic=job["topic"], target=job.get("target_position") or "")
    reasoning_on = job.get("reasoning_mode") == "on"
    # a job that is being regenerated after a failed attempt gets a fresh seed (providers that honour seeds would
    # otherwise reproduce the same malformed output); retry_index and seed_used are recorded
    seed = job["seed"] + 1000 * int(job.get("retry_index") or 0)
    # completion budget: 4000 tokens for direct answers; 16000 when hidden reasoning is on or cannot be switched off
    # (a truncated attempt is billed but discarded, so starting high avoids paying twice; the cap itself is rarely reached)
    max_tokens = 16000 if (reasoning_on or job.get("reasoning_toggle") == "not_supported") else 4000
    res = client.chat(job["model_id"], SYSTEM, prompt, temperature=float(job.get("temperature", 0.7)), seed=seed,
                      provider_order=job["provider_order"], disable_reasoning=not reasoning_on, max_tokens=max_tokens)
    rec = dict(job)
    rec["requested_at"] = datetime.datetime.utcnow().isoformat() + "Z"
    rec["prompt_text"] = prompt
    rec.update(res)
    if res.get("ok"):
        parsed, err, repair = parse_item(res["content"])
        rec["parsed"] = parsed; rec["parse_error"] = err; rec["parse_repair"] = repair
    else:
        rec["parsed"] = None; rec["parse_error"] = "request_failed"; rec["parse_repair"] = None
    return rec

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", action="store_true")
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--models", nargs="*", help="subset of model ids")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--run", default=None, help="run name (default pilot/full)")
    ap.add_argument("--conditions", nargs="*", default=["plain", "guided"], help="prompt conditions: plain guided guided_position")
    ap.add_argument("--reasoning", choices=["off", "on"], default="off", help="request hidden reasoning (models that support it)")
    ap.add_argument("--reps", type=int, default=None, help="repetitions per cell for --full (default 2)")
    ap.add_argument("--stall-minutes", type=float, default=15, help="exit with code 3 if no item completes for this long (0 = off)")
    ap.add_argument("--stability", action="store_true", help="A4 stability re-run: first 2 topics of every specialty x plain/guided x all models, 1 rep, same seed as rep 0 (run name 'stability')")
    ap.add_argument("--template-control", action="store_true", help="Amendment 2 template-control arm: first 5 topics of every specialty x plain_neutral/plain_rotated x all models, 1 rep (run name 'template')")
    ap.add_argument("--temperature", type=float, default=None, help="Amendment 3 sensitivity arm: sampling temperature (default 0.7 as in the main corpus); a non-default value tags the jobs so they never collide with main-corpus jobs")
    ap.add_argument("--topics", type=int, default=None, help="topics per specialty for --full (default 25)")
    a = ap.parse_args()
    if not (a.pilot or a.full or a.stability or a.template_control): ap.error("choose --pilot, --full, --stability or --template-control")
    models = [m for m in MODELS if m["id"] != "TO-BE-FILLED"]
    if a.models: models = [m for m in models if m["id"] in a.models]
    if not models: raise SystemExit("No models configured. Fill config/models.json first.")
    if a.stability:
        jobs = build_jobs(False, models, reps=1, topics_per_specialty=2, conditions=["plain", "guided"], reasoning=a.reasoning, tag="stability")
        run = a.run or "stability"
    elif a.template_control:
        jobs = build_jobs(False, models, reps=1, topics_per_specialty=5, conditions=["plain_neutral", "plain_rotated"], reasoning=a.reasoning)
        run = a.run or "template"
    elif a.pilot:
        jobs = build_jobs(True, models, reps=1, topics_per_specialty=2, specialties=["internal_medicine", "pediatrics"], conditions=a.conditions, reasoning=a.reasoning)
        run = a.run or "pilot"
    else:
        temp = 0.7 if a.temperature is None else a.temperature
        jobs = build_jobs(False, models, reps=(a.reps or 2), topics_per_specialty=(a.topics or 25), conditions=a.conditions, reasoning=a.reasoning,
                          tag=(None if a.temperature is None or a.temperature == 0.7 else "temp%g" % a.temperature), temperature=temp)
        run = a.run or "full"
    out = OUT / f"items_{run}.jsonl"
    done = set()   # only jobs with a successfully parsed item count as done; failures are retried
    attempts = {}  # job_id -> list of stored attempts (for the re-parse pass and the retry seed)
    if out.exists():
        for line in out.read_text().splitlines():
            try:
                rec = json.loads(line)
                attempts.setdefault(rec["job_id"], []).append(rec)
                # a stored record counts as done only if its raw response passes the CURRENT validator
                # (records accepted by an older, looser parser are regenerated; see mediwf/parsing.py)
                if rec.get("parsed") and usable_record(rec): done.add(rec["job_id"])
            except Exception: pass
    # re-parse pass: a stored response that failed to parse under an older parser but parses now is accepted as-is
    # (no new API call; the record is appended with reparsed=True and keeps its original cost and tokens)
    reparsed = []
    for j in jobs:
        if j["job_id"] in done: continue
        for old in reversed(attempts.get(j["job_id"], [])):
            if not old.get("ok") or not old.get("content"): continue
            parsed, err, repair = parse_item(old["content"])
            if parsed:
                rec = dict(old); rec.update(parsed=parsed, parse_error=None, parse_repair=repair, reparsed=True,
                                            reparsed_at=datetime.datetime.utcnow().isoformat() + "Z")
                reparsed.append(rec); done.add(j["job_id"]); break
    if reparsed:
        with out.open("a") as f:
            for rec in reparsed: f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"re-parse pass: {len(reparsed)} previously failed responses recovered with the current parser (no API calls)")
    todo = []
    for j in jobs:
        if j["job_id"] in done: continue
        j = dict(j); j["retry_index"] = len(attempts.get(j["job_id"], [])); todo.append(j)
    n_done = sum(1 for j in jobs if j["job_id"] in done)
    print(f"run={run}: {len(jobs)} jobs total, {n_done} already done, {len(todo)} to run, models={len(models)}")
    client = OpenRouterClient(require("OPENROUTER_API_KEY"))
    random.shuffle(todo)
    n_ok = n_fail = 0; cost = 0.0; t0 = time.time()
    last_progress = [time.time()]
    if a.stall_minutes and todo:
        def watchdog():
            while True:
                time.sleep(30)
                if time.time() - last_progress[0] > a.stall_minutes * 60:
                    print(f"\n[watchdog] no item completed for {a.stall_minutes:.0f} min; exiting with code 3 so the wrapper can restart", flush=True)
                    os._exit(3)
        threading.Thread(target=watchdog, daemon=True).start()
    # main pass, then up to two automatic retry passes for jobs whose response could not be parsed
    # (each retry uses a fresh seed via retry_index; a job that still fails is left for the next launch)
    for pass_no in range(3):
        if not todo: break
        if pass_no: print(f"retry pass {pass_no}: {len(todo)} job(s) whose response could not be parsed")
        succeeded = set()
        with out.open("a") as f, ThreadPoolExecutor(max_workers=a.workers) as ex:
            futs = {ex.submit(run_job, client, j): j for j in todo}
            for i, fut in enumerate(as_completed(futs), 1):
                rec = fut.result()
                last_progress[0] = time.time()
                f.write(json.dumps(rec, ensure_ascii=False) + "\n"); f.flush()
                if rec.get("ok") and rec.get("parsed"): n_ok += 1; succeeded.add(rec["job_id"])
                else: n_fail += 1
                cost += float(rec.get("cost_usd") or 0)
                if i % 10 == 0 or i == len(todo):
                    print(f"  {i}/{len(todo)} done | parsed ok={n_ok} fail={n_fail} | cost so far ${cost:.4f} | {time.time()-t0:.0f}s")
        todo = [dict(j, retry_index=int(j.get("retry_index") or 0) + 1) for j in todo if j["job_id"] not in succeeded]
    if todo: print(f"{len(todo)} job(s) still without a usable item; launch the same command again to retry them")
    print(f"finished. output: {out}")

if __name__ == "__main__":
    main()
