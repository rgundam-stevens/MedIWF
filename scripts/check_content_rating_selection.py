"""Verify the released physician-rating item selection (outputs/content_rating_selection.json) against the corpus
(added 17 Sep 2026; the selection was drawn on 15 Sep 2026 and the drawing code was not kept, so its properties are
checked here instead: 100 main-set items, 3-4 per model x condition, half plain and half guided, every job id in the
main corpus, and no overlap between the main set and the 20 calibration items).
Usage: python3 scripts/check_content_rating_selection.py
"""
import json, csv, pathlib, collections
root = pathlib.Path(__file__).resolve().parents[1]
sel = json.load(open(root / "outputs/content_rating_selection.json"))
flags = {r["job_id"]: r for r in csv.DictReader(open(root / "outputs/flags_full.csv"))}
main = sel["main"] if isinstance(sel, dict) and "main" in sel else sel
ids = [x["job_id"] if isinstance(x, dict) else x for x in main]
cells = collections.Counter((flags[j]["model_label"], flags[j]["condition"]) for j in ids if j in flags)
print("main set: %d items; %d in the main corpus; cells: %d; per-cell counts: %s; plain/guided: %d/%d" % (
    len(ids), sum(j in flags for j in ids), len(cells), dict(collections.Counter(cells.values())),
    sum(flags[j]["condition"] == "plain" for j in ids if j in flags), sum(flags[j]["condition"] == "guided" for j in ids if j in flags)))
cal = {r["job_id"] for r in csv.DictReader(open(root / "outputs/content_rating/calibration_key_DO_NOT_SEND.csv")) if r.get("job_id")}
print("calibration items: %d; overlap with main set: %d" % (len(cal), len(cal & set(ids))))
