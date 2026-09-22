"""Does each model's own one-sentence rationale point at the keyed option? (Moved into the repository 17 Sep 2026; the
manuscript's '95-100% agreement in every cell' had rested on a scratch script.)

Two crude, text-only checks per item, on the raw generation records (data/generated/items_<run>.jsonl):
  lexical  - content-word overlap between the rationale and each option; a MISMATCH when the option with the highest
             overlap is not the key and beats the key by >= 2 words (ties and near-ties are not mismatches)
  letter   - the rationale names an option letter ("option B", "(B)", "choice B", "answer is B") that is not the key
Reported per model x condition and per key letter (A vs B-E), for every run given. Item text is never printed.
Usage: python3 scripts/rationale_key_check.py full position template wording full_reasoning [-o outputs/analysis_rationale_v1.txt]
"""
import sys, re, json, pathlib, io, collections
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from mediwf.parsing import usable_record
root = pathlib.Path(__file__).resolve().parents[1]
STOP = set("a an the and or of to in on at for with by from as is are was were be been this that these those it its he she his her they them their which what who most likely following best next step management appropriate diagnosis initial patient patients treatment therapy would should could than then after before during over under between into within without about above below more less other some any each such same only very also because due given has have had not no option options answer correct incorrect choice".split())
LETTER = re.compile(r"\b(?:option|choice|answer(?: is)?|alternative)\s*[:(]?\s*([A-E])\b|\(([A-E])\)", re.I)


def words(s): return {w for w in re.findall(r"[a-z][a-z\-']{3,}", (s or "").lower()) if w not in STOP}


def main(runs, out_path=None):
    buf = io.StringIO()
    def P(*a):
        print(*a); print(*a, file=buf)
    for run in runs:
        path = root / "data" / "generated" / ("items_%s.jsonl" % run)
        first = {}
        for line in path.read_text().splitlines():
            if not line.strip(): continue
            r = json.loads(line)
            item = usable_record(r)
            if item and r["job_id"] not in first: first[r["job_id"]] = (r, item)
        stats = collections.defaultdict(collections.Counter)
        for r, p in first.values():
            key = str(p["answer"]).strip().upper()[:1]; rat = p.get("rationale", "") or ""
            cell = (r.get("model_label", r.get("model")), r.get("condition"), "reasoning:" + str(r.get("reasoning_mode", "off")) if run == "full_reasoning" else "")
            st = stats[cell]; st["n"] += 1; st["keyA"] += int(key == "A")
            rw = words(rat)
            if len(rw) >= 3:
                ov = {L: len(words(o) & rw) for L, o in p["options"].items()}
                best = max(ov, key=ov.get)
                if best != key and ov[best] - ov.get(key, 0) >= 2:
                    st["lex_mismatch"] += 1; st["lex_mismatch_keyA"] += int(key == "A")
                st["lex_checked"] += 1
            named = {m.group(1) or m.group(2) for m in LETTER.finditer(rat)}
            named = {x.upper() for x in named if x}
            if named:
                st["letter_named"] += 1
                if key not in named: st["letter_mismatch"] += 1
        P("== run: %s (%d usable items)" % (run, sum(s["n"] for s in stats.values())))
        P("%-20s %-8s %-14s %5s | lexical check: n, mismatch %% (key A / key B-E) | letter check: named n, mismatch" % ("model", "cond", "", "n"))
        tot = collections.Counter()
        for cell in sorted(stats):
            s = stats[cell]; tot.update(s)
            lexA = s["lex_mismatch_keyA"]; lexO = s["lex_mismatch"] - lexA
            nA = s["keyA"]; nO = s["n"] - nA
            P("%-20s %-8s %-14s %5d | %5d  %4.1f%%  (%4.1f%% / %4.1f%%)                | %5d  %d" % (
                cell[0], cell[1], cell[2], s["n"], s["lex_checked"], 100 * s["lex_mismatch"] / max(1, s["lex_checked"]),
                100 * lexA / max(1, nA), 100 * lexO / max(1, nO), s["letter_named"], s["letter_mismatch"]))
        P("  ALL: lexical mismatch %.2f%% of %d checked (max cell %.1f%%); letter-named %d, letter mismatch %d (%.2f%%)" % (
            100 * tot["lex_mismatch"] / max(1, tot["lex_checked"]), tot["lex_checked"],
            max(100 * s["lex_mismatch"] / max(1, s["lex_checked"]) for s in stats.values()), tot["letter_named"], tot["letter_mismatch"], 100 * tot["letter_mismatch"] / max(1, tot["letter_named"])))
        P("")
    if out_path:
        pathlib.Path(out_path).write_text(buf.getvalue()); print("written ->", out_path)


if __name__ == "__main__":
    args = sys.argv[1:]; out = None
    if "-o" in args:
        i = args.index("-o"); out = args[i + 1]; args = args[:i] + args[i + 2:]
    main(args, out)
