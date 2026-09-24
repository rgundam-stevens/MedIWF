"""Build the paper's data files (csv/xlsx only) from the study's data and outputs.

Run on the analysis machine from the repository root:
    python3 scripts/build_paper_data.py paper_data
Nothing from the NBME item-level files is written; only the released aggregate counts (nbme_aggregate_for_figures.json).
CSV files are written as UTF-8 with a byte-order mark so that spreadsheet programs read the item text correctly.
"""
import csv, json, sys, shutil, ast, hashlib, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mediwf.parsing import usable_record
from mediwf.rules import CORE, FEATURES, VALIDATED, SENSITIVITY

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "paper_data"
OUT.mkdir(parents=True, exist_ok=True)
GEN = ROOT / "data/generated"
FLAGS = ROOT / "outputs"
RUNS = ["full", "full_reasoning", "position", "template", "wording", "stability"]
ENC = "utf-8-sig"


def tier_of():
    cfg = json.load(open(ROOT / "config/models.json"))
    items = cfg["models"] if isinstance(cfg, dict) and "models" in cfg else cfg
    if isinstance(items, dict):
        items = list(items.values())
    return {m["id"]: m.get("tier", "") for m in items}


TIER = tier_of()
ITEM_COLS = ["run", "job_id", "model_id", "model_label", "tier", "specialty", "topic_index", "topic", "condition", "rep", "seed", "seed_used",
             "reasoning_mode", "target_position", "temperature", "requested_at", "generation_id", "retry_index", "reparsed", "parse_repair",
             "provider", "model_returned", "finish_reason", "prompt_tokens", "completion_tokens", "reasoning_tokens", "cost_usd", "latency_s",
             "ok", "parse_error", "analysed", "stem", "option_A", "option_B", "option_C", "option_D", "option_E", "answer", "rationale", "n_options"]


def dataset1_items():
    """One CSV per run, one row per generation attempt. analysed = True marks the attempt the detector used (the first attempt per job
    whose response passes the current validator, as in scripts/detect.py); the analysed rows are exactly the rows of Dataset 2."""
    manifest = []
    for run in RUNS:
        src = GEN / f"items_{run}.jsonl"
        dst = OUT / f"MedIWF_Dataset1_items_{run}.csv"
        flagged = set()
        with open(FLAGS / f"flags_{run}.csv", newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                flagged.add(r["job_id"])
        n = 0; chosen = set(); n_analysed = 0
        with open(src, encoding="utf-8") as fh, open(dst, "w", newline="", encoding=ENC) as out:
            w = csv.DictWriter(out, fieldnames=ITEM_COLS, extrasaction="ignore")
            w.writeheader()
            for line in fh:
                if not line.strip():
                    continue
                r = json.loads(line)
                item = usable_record(r) if (r["job_id"] in flagged and r["job_id"] not in chosen) else None
                analysed = item is not None
                p = item if analysed else (r.get("parsed") or {})          # analysed rows: the text the detector analysed
                opts = p.get("options") or {}
                row = {k: r.get(k, "") for k in ITEM_COLS}
                row["run"] = run
                row["tier"] = TIER.get(r.get("model_id", ""), "")
                row["stem"] = p.get("stem", "")
                for L in "ABCDE":
                    row[f"option_{L}"] = opts.get(L, "")
                row["answer"] = p.get("answer", "")
                row["rationale"] = p.get("rationale", "")
                row["n_options"] = p.get("n_options", "")
                if analysed:
                    chosen.add(r["job_id"]); n_analysed += 1
                row["analysed"] = analysed
                for k in ("reparsed", "retry_index", "parse_repair", "seed_used", "generation_id"):
                    if k not in r:
                        row[k] = ""
                w.writerow(row); n += 1
        assert chosen == flagged, (run, len(chosen), len(flagged))
        manifest.append((dst.name, n, f"{n_analysed} analysed"))
    return manifest


def dataset2_flags():
    dst = OUT / "MedIWF_Dataset2_detector_flags.csv"
    n = 0
    with open(dst, "w", newline="", encoding=ENC) as out:
        w = None
        for run in RUNS:
            with open(FLAGS / f"flags_{run}.csv", newline="", encoding="utf-8") as fh:
                rd = csv.DictReader(fh)
                for r in rd:
                    r = {"run": run, **r}
                    r["n_flaws"] = sum(int(r[c]) for c in CORE)
                    r["any_flaw_14"] = int(r["n_flaws"] > 0)
                    r["any_flaw_11"] = int(any(int(r[c]) for c in SENSITIVITY))
                    r["any_flaw_10"] = int(any(int(r[c]) for c in VALIDATED))
                    r["topic_id"] = f"{r['specialty']}:{r['topic_index']}"
                    if w is None:
                        cols = list(r.keys())
                        for c in ("any_flaw_14", "any_flaw_11", "any_flaw_10", "topic_id"):
                            cols.remove(c)
                        i = cols.index("n_flaws") + 1
                        cols[i:i] = ["any_flaw_14", "any_flaw_11", "any_flaw_10", "topic_id"]
                        w = csv.DictWriter(out, fieldnames=cols); w.writeheader()
                    w.writerow(r); n += 1
    return [(dst.name, n, "")]


PROV_JUST = re.compile(r"^\(added from the rater's chat reply, ([^)]*)\)\s*")
PROV_ANS = re.compile(r"^(.*?)\s*\(corrected by chat reply ([^;]*); sheet said ([^)]*)\)\s*$")


def dataset3_ratings():
    out = []
    dst = OUT / "MedIWF_Dataset3_physician_ratings.csv"
    cols = ["item_id", "keyed_answer", "q1", "q2", "q3", "q4", "q5", "justification", "note", "rater", "ingested_utc",
            "q1_raw", "q2_raw", "q3_raw", "q4_raw", "q5_raw"]
    n = 0
    with open(dst, "w", newline="", encoding=ENC) as o:
        w = csv.DictWriter(o, fieldnames=cols); w.writeheader()
        for rater in ("R1", "R2"):
            with open(FLAGS / "content_rating/ratings" / f"main_{rater}.csv", newline="", encoding="utf-8") as fh:
                for r in csv.DictReader(fh):
                    row = {k: r.get(k, "") for k in cols}
                    row["ingested_utc"] = r.get("submitted_utc", "")
                    notes = []
                    m = PROV_JUST.match(row["justification"])
                    if m:
                        row["justification"] = row["justification"][m.end():]
                        notes.append(f"justification taken from the rater's chat reply ({m.group(1)})")
                    for q in ("q1_raw", "q2_raw", "q3_raw", "q4_raw", "q5_raw"):
                        m = PROV_ANS.match(row[q])
                        if m:
                            row[q] = m.group(1)
                            notes.append(f"{q[:2]} corrected from the rater's chat reply ({m.group(2)}); the sheet said {m.group(3)}")
                    row["note"] = "; ".join(notes)
                    w.writerow(row); n += 1
    out.append((dst.name, n, "minutes column not included"))
    key_dst = OUT / "MedIWF_Dataset3_item_key.csv"
    with open(FLAGS / "content_rating/main_key_DO_NOT_SEND.csv", newline="", encoding="utf-8") as fh, open(key_dst, "w", newline="", encoding=ENC) as o:
        rd = csv.DictReader(fh); w = csv.DictWriter(o, fieldnames=rd.fieldnames); w.writeheader(); k = 0
        for r in rd:
            w.writerow(r); k += 1
    out.append((key_dst.name, k, ""))
    shutil.copy(FLAGS / "content_rating/main_set_100.xlsx", OUT / "MedIWF_Dataset3_rated_items.xlsx")
    out.append(("MedIWF_Dataset3_rated_items.xlsx", 100, ""))
    return out


def dataset4_handcheck():
    out = []
    shutil.copy(FLAGS / "verification_sample_pass1_merged.xlsx", OUT / "MedIWF_Dataset4_handcheck_labels.xlsx")
    out.append(("MedIWF_Dataset4_handcheck_labels.xlsx", 439, ""))
    dst = OUT / "MedIWF_Dataset4_handcheck_detector_flags.csv"
    with open(FLAGS / "verification_sample_key.csv", newline="", encoding="utf-8") as fh, open(dst, "w", newline="", encoding=ENC) as o:
        rd = csv.DictReader(fh); w = csv.DictWriter(o, fieldnames=rd.fieldnames); w.writeheader(); k = 0
        for r in rd:
            w.writerow(r); k += 1
    out.append((dst.name, k, ""))
    return out


def dataset5_judges():
    """One row per judge x item x rule. Repeated calls for the same file, item and rule keep the last verdict, as validate_judge.py does;
    the 12-item reasoning-budget pilot file is not included."""
    dst = OUT / "MedIWF_Dataset5_llm_judge_verdicts.csv"
    cols = ["file", "judge", "item_set", "reasoning_requested", "uid", "dataset", "requested_at", "rule", "verdict_fail", "confidence", "explanation",
            "cost_usd", "prompt_tokens", "completion_tokens", "reasoning_tokens"]
    rows = {}; raw = 0; files = 0
    for src in sorted(GEN.glob("judgeR_*.jsonl")):
        name = src.stem
        if "budget" in name:
            continue
        files += 1
        item_set = "physician100" if "physician100" in name else "benchmarker"
        reasoning = "yes" if "reasoning" in name else "no"
        with open(src, encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                r = json.loads(line)
                judg = r.get("judgment") or {}
                det = r.get("details") or {}
                if isinstance(judg, str):
                    judg = ast.literal_eval(judg)
                if isinstance(det, str):
                    det = ast.literal_eval(det)
                for rule, verdict in judg.items():
                    d = det.get(rule, {}) if isinstance(det, dict) else {}
                    raw += 1
                    rows[(name, r.get("uid", ""), rule)] = {
                        "file": name, "judge": r.get("judge", ""), "item_set": item_set, "reasoning_requested": reasoning,
                        "uid": r.get("uid", ""), "dataset": r.get("dataset", ""), "requested_at": r.get("requested_at", ""),
                        "rule": rule, "verdict_fail": verdict, "confidence": d.get("confidence", "") if isinstance(d, dict) else "",
                        "explanation": str(d.get("explanation", "")).replace("\x00", " ") if isinstance(d, dict) else "",
                        "cost_usd": r.get("cost_usd", ""), "prompt_tokens": r.get("prompt_tokens", ""),
                        "completion_tokens": r.get("completion_tokens", ""), "reasoning_tokens": r.get("reasoning_tokens", "")}
    with open(dst, "w", newline="", encoding=ENC) as o:
        w = csv.DictWriter(o, fieldnames=cols); w.writeheader()
        for row in rows.values():
            w.writerow(row)
    return [(dst.name, len(rows), f"{raw} verdict rows read from {files} files; {raw - len(rows)} repeated calls dropped")]


def dataset6_nbme():
    agg = json.load(open(FLAGS / "nbme_aggregate_for_figures.json"))
    dst = OUT / "MedIWF_Dataset6_nbme_aggregate.csv"
    with open(dst, "w", newline="", encoding=ENC) as o:
        w = csv.writer(o); w.writerow(["quantity", "name", "value"])
        w.writerow(["n_items_five_option", "", agg["n"]])
        w.writerow(["detector_version", "", agg.get("detector_version", "")])
        w.writerow(["items_with_any_of_14_flaws", "", agg["any_core"]])
        for k in sorted(agg["key_counts"]):
            w.writerow(["key_position_count", k, agg["key_counts"][k]])
        for k in CORE:
            w.writerow(["flaw_count", k, agg["flaw_counts"][k]])
        for k in FEATURES:
            if k in agg["flaw_counts"]:
                w.writerow(["feature_count", k, agg["flaw_counts"][k]])
    return [(dst.name, sum(1 for _ in open(dst, encoding=ENC)) - 1, "")]


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


if __name__ == "__main__":
    manifest = []
    for fn in (dataset1_items, dataset2_flags, dataset3_ratings, dataset4_handcheck, dataset5_judges, dataset6_nbme):
        manifest += fn()
    with open(OUT / "MANIFEST.txt", "w", encoding="utf-8") as m:
        m.write("file\trows\tsize\tmd5\tnote\n")
        for name, n, note in manifest:
            size = (OUT / name).stat().st_size
            line = f"{name}\t{n} rows\t{size/1e6:.1f} MB\t{md5(OUT / name)}\t{note}"
            m.write(line + "\n"); print(line)
