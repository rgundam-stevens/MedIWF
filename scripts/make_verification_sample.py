"""Draw a stratified, flag-enriched random sample of generated items for the author's blind hand-verification (RQ4).

Design (v4, 2026-09-17, detector v1.2; supersedes v3 of 16 Sep (v1.1), whose frame silently lost 4 of the 12,000 items and
which was never labelled; v2 of 15 Sep (v1.0); and the plain random sample of 320 items):
  * strata are MUTUALLY EXCLUSIVE: every item is assigned to the first rule (in MAJOR + MINOR order) that flags it, or to
    "unflagged" if no rule does; the population size of each stratum is counted on the same partition, so that the
    stratum weights used by scripts/analyze_verification.py are exact (v2 counted overlapping populations);
  * for each major rule 50 flagged items, for each minor rule up to 30 (all of them when fewer exist), drawn at random
    across all 15 models and both conditions, plus 200 unflagged items stratified by model x condition;
  * items flagged only by a rule outside the sampled list ("other_flag") are all included, so every item of the corpus is in
    exactly one stratum and the frame is the whole corpus;
  * items are shuffled and the detector output is hidden, so the rater cannot tell which stratum an item came from.

Writes outputs/verification_sample_pass1.xlsx (item text + empty label columns; detector output hidden)
and outputs/verification_sample_key.csv (sample id, job id, stratum, detector flags; do not open while labelling).
Usage: python3 scripts/make_verification_sample.py full --major 50 --minor 30 --unflagged 200
"""
import json, sys, random, csv, pathlib, collections, argparse
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
root = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "src"))
from mediwf.parsing import usable_record
from mediwf.rules import CORE

MAJOR = ["longest_option_key", "clang_cue", "absolute_terms"]                       # common rules: precision from n=major
MINOR = ["nonparallel_options", "overlapping_options", "numeric_not_ordered", "vague_terms", "grammatical_cue", "combination_options"]   # rarer rules: up to n=minor each
ALL_RULES = CORE   # v1.2: every counted rule (true_false_stem and fill_in_blank were missing from the v3 list)
LABELS = ["negative_stem", "meta_option (all/none of the above)", "combination_options", "longest_option_key", "absolute_terms",
          "vague_terms", "clang_cue", "grammatical_cue", "nonparallel_options", "overlapping_options", "notes"]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run", nargs="?", default="full")
    ap.add_argument("--major", type=int, default=50); ap.add_argument("--minor", type=int, default=30); ap.add_argument("--unflagged", type=int, default=200)
    ap.add_argument("--seed", type=int, default=20260917)
    a = ap.parse_args()
    random.seed(a.seed)
    recs = {}
    for line in (root / "data" / "generated" / f"items_{a.run}.jsonl").read_text().splitlines():
        if not line.strip(): continue
        r = json.loads(line); item = usable_record(r)
        if item and r["job_id"] not in recs: recs[r["job_id"]] = item   # v1.2: same validator as detect.py, so the frame is the whole corpus
    flags = {r["job_id"]: r for r in csv.DictReader(open(root / "outputs" / f"flags_{a.run}.csv"))}
    missing = [j for j in flags if j not in recs]
    assert not missing, "flags without a usable record: %d" % len(missing)
    # partition: first flagging rule in MAJOR + MINOR order, else "other_flag" (flagged only by a rule outside the list) or "unflagged"
    def stratum_of(f):
        for r in MAJOR + MINOR:
            if f[r] == "1": return "flagged:" + r
        return "other_flag" if any(f[r] == "1" for r in ALL_RULES) else "unflagged"
    part = {j: stratum_of(f) for j, f in flags.items()}
    pop = collections.Counter(part.values())
    chosen = {}   # job_id -> stratum
    for rule, n in [(r, a.major) for r in MAJOR] + [(r, a.minor) for r in MINOR]:
        pool = [j for j, st in part.items() if st == "flagged:" + rule]
        for j in random.sample(pool, min(n, len(pool))): chosen[j] = "flagged:" + rule
    pool = [j for j, st in part.items() if st == "other_flag"]
    for j in random.sample(pool, min(a.minor, len(pool))): chosen[j] = "other_flag"   # v1.2: sampled (all, up to --minor)
    # unflagged stratum, stratified by model x condition
    clean = [j for j, st in part.items() if st == "unflagged"]
    cells = collections.defaultdict(list)
    for j in clean: cells[(flags[j]["model_label"], flags[j]["condition"])].append(j)
    per = max(1, a.unflagged // len(cells)); picked = []
    for k in sorted(cells): picked += random.sample(cells[k], min(per, len(cells[k])))
    for j in picked[:a.unflagged]: chosen[j] = "unflagged"
    sample = list(chosen); random.shuffle(sample)
    wb = Workbook(); ws = wb.active; ws.title = "pass1"
    hdr = ["sample_id", "stem", "A", "B", "C", "D", "E", "key"] + LABELS
    ws.append(hdr)
    for c in ws[1]: c.font = Font(bold=True, name="Arial"); c.fill = PatternFill("solid", fgColor="DDEBF7")
    for i, j in enumerate(sample, 1):
        p = recs[j]; o = p["options"]
        ws.append([i, p["stem"], o.get("A"), o.get("B"), o.get("C"), o.get("D"), o.get("E"), p["answer"]] + [""] * len(LABELS))
    for row in ws.iter_rows(min_row=2):
        for c in row: c.alignment = Alignment(wrap_text=True, vertical="top"); c.font = Font(name="Arial", size=10)
    for col, w in zip("ABCDEFGH", [9, 70, 22, 22, 22, 22, 22, 6]): ws.column_dimensions[col].width = w
    for k in range(len(LABELS)): ws.column_dimensions[chr(ord("I") + k)].width = 14
    ws.freeze_panes = "C2"
    wb.save(root / "outputs" / "verification_sample_pass1.xlsx")
    skip = ("job_id", "model_id", "model_label", "family", "tier", "specialty", "topic_index", "condition", "rep", "reasoning_mode", "target_position", "provider", "reasoning_tokens")
    with open(root / "outputs" / "verification_sample_key.csv", "w", newline="") as f:
        w = csv.writer(f)
        first = flags[sample[0]]
        w.writerow(["sample_id", "job_id", "model_label", "tier", "condition", "stratum", "stratum_population"] + [k for k in first if k not in skip])
        for i, j in enumerate(sample, 1):
            fl = flags[j]
            w.writerow([i, j, fl["model_label"], fl.get("tier", "base"), fl["condition"], chosen[j], pop[chosen[j]]] + [fl[k] for k in fl if k not in skip])
    cnt = collections.Counter(chosen.values())
    print(f"sampled {len(sample)} items -> outputs/verification_sample_pass1.xlsx ; key -> outputs/verification_sample_key.csv")
    for k in sorted(cnt): print(f"  {k:<32} n={cnt[k]:4d}   (population {pop[k]})")
    print(f"  frame: {sum(pop.values())} items in {len(pop)} mutually exclusive strata (sum of populations must equal the corpus size)")
    models = collections.Counter(flags[j]["model_label"] for j in sample)
    print("  per model:", dict(sorted(models.items())))

if __name__ == "__main__":
    main()
