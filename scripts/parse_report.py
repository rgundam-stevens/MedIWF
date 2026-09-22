"""Output-format compliance report for a generation run (no item text printed). For every model and condition it
re-derives, from the stored raw responses, (a) the first-attempt strict-JSON parse rate, (b) the share recovered by the
documented repair rules, (c) the number of jobs that needed a regeneration, plus cost, tokens and hidden-reasoning use.
Usage: python3 scripts/parse_report.py full [outputs/parse_report_full.txt]
"""
import json, sys, pathlib, collections, io
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
root = pathlib.Path(__file__).resolve().parents[1]
from mediwf import parsing as g   # _validate / parse_item now live in src/mediwf/parsing.py (shared with detect.py)

def strict_ok(text):
    """Does the raw response parse as JSON with all required fields, with no repair at all?"""
    try:
        d = json.loads(text)
    except Exception:
        return False
    item, err = g._validate(d if not isinstance(d, dict) else dict(d))
    if not item: return False
    # _validate tolerates answer nested in options (a missing brace); count that as needing repair
    opts = d.get("options") if isinstance(d, dict) else None
    return not (isinstance(opts, dict) and ("answer" in opts or "rationale" in opts))

def main(run, out_path=None):
    buf = io.StringIO()
    def P(*a):
        print(*a); print(*a, file=buf)
    p = root / "data" / "generated" / f"items_{run}.jsonl"
    attempts = collections.defaultdict(list)
    for line in p.read_text().splitlines():
        if line.strip():
            r = json.loads(line); attempts[r["job_id"]].append(r)
    rows = collections.defaultdict(lambda: dict(jobs=0, first_ok=0, first_strict=0, repaired=0, regen=0, final_ok=0, cost=0.0, ctok=0, rtok=0, n_reason=0, repairs=collections.Counter(), errors=collections.Counter()))
    for jid, recs in attempts.items():
        real = [r for r in recs if not r.get("reparsed")]          # API attempts, in order
        first = real[0]
        key = (first["model_label"], first["condition"], first.get("reasoning_mode", "off"))
        b = rows[key]; b["jobs"] += 1
        b["cost"] += sum(float(r.get("cost_usd") or 0) for r in real)
        b["ctok"] += sum(int(r.get("completion_tokens") or 0) for r in real)
        b["rtok"] += sum(int(r.get("reasoning_tokens") or 0) for r in real); b["n_reason"] += sum(1 for r in real if (r.get("reasoning_tokens") or 0) > 0)
        c = first.get("content") or ""
        if first.get("ok") and strict_ok(c): b["first_strict"] += 1
        item, err, how = g.parse_item(c) if first.get("ok") else (None, first.get("error", "request_failed")[:40], None)
        if item:
            b["first_ok"] += 1
            if how != "none": b["repaired"] += 1; b["repairs"][how] += 1
        else:
            b["errors"][err or "?"] += 1
        if len(real) > 1: b["regen"] += 1
        if any(r.get("parsed") for r in recs): b["final_ok"] += 1
    P("run=%s: %d jobs" % (run, len(attempts)))
    P("%-20s %-16s %-4s %5s | first-attempt: strict-JSON  usable(after repair)  repaired | regenerated | final usable | cost $  | reasoning share, mean tokens" % ("model", "condition", "rsn", "jobs"))
    tot = collections.Counter()
    for key in sorted(rows):
        b = rows[key]; n = b["jobs"]
        P("%-20s %-16s %-4s %5d |             %5.1f%%        %5.1f%%           %4d   |     %4d    |    %5.1f%%    | %7.2f | %4.0f%%  %6.0f" % (
            key[0], key[1], key[2], n, 100 * b["first_strict"] / n, 100 * b["first_ok"] / n, b["repaired"], b["regen"], 100 * b["final_ok"] / n, b["cost"],
            100 * b["n_reason"] / n, b["rtok"] / max(1, b["n_reason"])))
        for k in ("jobs", "first_strict", "first_ok", "repaired", "regen", "final_ok"): tot[k] += b[k]
        tot["cost"] += b["cost"]
    n = tot["jobs"]
    P("%-20s %-16s %-4s %5d |             %5.1f%%        %5.1f%%           %4d   |     %4d    |    %5.1f%%    | %7.2f" % (
        "ALL", "", "", n, 100 * tot["first_strict"] / n, 100 * tot["first_ok"] / n, tot["repaired"], tot["regen"], 100 * tot["final_ok"] / n, tot["cost"]))
    P("\nrepairs applied on first attempts, by model:")
    for key in sorted(rows):
        if rows[key]["repairs"]: P("  %-20s %-16s %s" % (key[0], key[1], dict(rows[key]["repairs"])))
    P("\nfirst-attempt failures by model:")
    for key in sorted(rows):
        if rows[key]["errors"]: P("  %-20s %-16s %s" % (key[0], key[1], dict(rows[key]["errors"])))
    if out_path:
        pathlib.Path(out_path).write_text(buf.getvalue()); print("\nwritten ->", out_path)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
