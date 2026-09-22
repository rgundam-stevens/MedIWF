"""Run the Tier-A detector over a corpus and write one row per item with flaw flags (no item text in the output).

Usage:
  python3 scripts/detect.py generated full          # -> outputs/flags_full.csv   (MedIWF corpus)
  python3 scripts/detect.py nbme                    # -> outputs/flags_nbme.csv   (NBME items; flags only, never text)
"""
import csv, json, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from mediwf.detector import Detector, VERSION as DETECTOR_VERSION
from mediwf.parsing import usable_record

root = pathlib.Path(__file__).resolve().parents[1]
OUT = root / "outputs"; OUT.mkdir(exist_ok=True)
det = Detector()
FLAWS = det.FLAWS

def write(rows, path):
    if not rows:
        print("no rows"); return
    cols = list(rows[0].keys())
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
    print(f"wrote {len(rows)} rows -> {path}")

def run_generated(run):
    p = root / "data" / "generated" / f"items_{run}.jsonl"
    best = {}; seen = set(); invalid = {}
    for line in p.read_text().splitlines():
        if not line.strip(): continue
        r = json.loads(line); seen.add(r["job_id"])
        if r["job_id"] in best: continue
        item = usable_record(r)            # raw response re-parsed with the current validator (mediwf/parsing.py)
        if item: best[r["job_id"]] = dict(r, parsed=item)
        elif r.get("parsed"): invalid[r["job_id"]] = r.get("model_label")
    missing = {j: m for j, m in invalid.items() if j not in best}
    if missing:
        print("WARNING: %d job(s) have no response that passes the current validator and are excluded; regenerate them with the "
              "same generate.py command: %s" % (len(missing), missing))
    rows = []
    for r in best.values():
        res = det.detect(r["parsed"])
        row = {"job_id": r["job_id"], "model_id": r["model_id"], "model_label": r["model_label"], "family": r.get("family"),
               "tier": r.get("tier", "base"), "specialty": r["specialty"], "topic_index": r["topic_index"], "condition": r["condition"], "rep": r["rep"],
               "reasoning_mode": r.get("reasoning_mode", "off"), "target_position": r.get("target_position") or "",
               "provider": r.get("provider"), "reasoning_tokens": r.get("reasoning_tokens") or 0, "temperature": r.get("temperature", 0.7)}
        row.update({k: int(bool(res["flaws"][k])) for k in FLAWS})
        row.update({"n_flaws": res["features"]["n_flaws"], "n_options": res["features"]["n_options"], "key": res["features"]["key"],
                    "stem_words": res["features"]["stem_words"], "key_chars": res["features"]["key_chars"],
                    "mean_distractor_chars": res["features"]["mean_distractor_chars"], "detector_version": DETECTOR_VERSION})
        rows.append(row)
    write(rows, OUT / f"flags_{run}.csv")

def _cell_text(v):
    """Excel cell -> option text. Numbers keep their value; a datetime is Excel's misreading of a range such as '1-2'
    and is written back in that form (one cell in the BEA 2024 file)."""
    import datetime, math
    if v is None or (isinstance(v, float) and math.isnan(v)): return ""
    if isinstance(v, datetime.datetime): return "%d-%d" % (v.month, v.day)
    if isinstance(v, float) and v.is_integer(): return str(int(v))
    return str(v).strip()

def run_nbme():
    import pandas as pd
    d = root / "data" / "nbme"
    train = pd.read_excel(d / "train_final.xlsx")
    test = pd.read_excel(d / "test_final.xlsx").merge(pd.read_excel(d / "gold_final.xlsx"), on="ItemNum")
    train["split"] = "train"; test["split"] = "test"
    df = pd.concat([train, test], ignore_index=True)
    rows = []
    for _, r in df.iterrows():
        # option cells may be numeric (eight items have purely numeric options, which Excel stores as numbers); keep them as text
        opts = {L: _cell_text(r.get(f"Answer__{L}")) for L in "ABCDEFGHIJ" if _cell_text(r.get(f"Answer__{L}"))}
        res = det.detect({"stem": r["ItemStem_Text"], "options": opts, "answer": r["Answer_Key"]})
        row = {"ItemNum": int(r["ItemNum"]), "split": r["split"], "EXAM": r["EXAM"], "ItemType": r["ItemType"],
               "Difficulty": float(r["Difficulty"]), "Response_Time": float(r["Response_Time"])}
        row.update({k: int(bool(res["flaws"][k])) for k in FLAWS})
        row.update({"n_flaws": res["features"]["n_flaws"], "n_options": res["features"]["n_options"], "key": res["features"]["key"],
                    "stem_words": res["features"]["stem_words"], "key_chars": res["features"]["key_chars"],
                    "mean_distractor_chars": res["features"]["mean_distractor_chars"], "detector_version": DETECTOR_VERSION})
        rows.append(row)
    write(rows, OUT / "flags_nbme.csv")

if __name__ == "__main__":
    if sys.argv[1] == "generated": run_generated(sys.argv[2])
    elif sys.argv[1] == "nbme": run_nbme()
    else: raise SystemExit(__doc__)
