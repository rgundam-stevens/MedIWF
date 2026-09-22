"""Paper figures from the flag files (no item text needed). Handles the 15-model corpus (flagship-tier models in bold).
Figure 1: answer-key position by model x condition, with NBME reference.
Figure 2: prevalence of any validated Tier-A flaw by model (plain vs guided) and per-flaw pooled prevalence.
Usage: python3 scripts/make_figures.py outputs/flags_full.csv outputs/flags_nbme.csv outputs/figures
   or: python3 scripts/make_figures.py outputs/flags_full.csv outputs/nbme_aggregate_for_figures.json outputs/figures
The NBME item-level file is not released (data-use agreement); when it is present the script writes the aggregate
counts the figures need to outputs/nbme_aggregate_for_figures.json, and that JSON reproduces the figures without it.
v1.2 audit fix: the NBME reference in both figures is the 525 five-option items (the comparable set), not all 667.
"""
import sys, csv, math, collections, pathlib, json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import rcParams

rcParams["font.family"] = "DejaVu Sans"; rcParams["font.size"] = 9
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#8a8985", "#e6e5e1"
BLUE, ORANGE = "#2a78d6", "#eb6834"
RAMP = ["#2a78d6", "#7aabe6", "#b3cdf0", "#d9e6f7", "#f0f4fb"]   # A (dark) -> E (light), one hue
import sys as _sys, pathlib as _pl; _sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1] / "src"))
from mediwf.rules import CORE

def wilson(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0.0, c - h), min(1.0, c + h)

def style(ax):
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    for s in ("left", "bottom"): ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2, length=0)
    ax.grid(axis="x", color=GRID, linewidth=0.6); ax.set_axisbelow(True)

def tiers(rows):
    return {r["model_label"]: r.get("tier", "base") for r in rows}

def bold_flagship(ax, labels, tier_of):
    for lab, tick in zip(labels, ax.get_yticklabels()):
        name = lab.split("  ·  ")[0]
        if tier_of.get(name) == "flagship": tick.set_fontweight("bold")

def fig1(rows, nbme, out):
    tier_of = tiers(rows)
    models = sorted(tier_of, key=lambda m: -sum(1 for r in rows if r["model_label"] == m and r["condition"] == "plain" and r["key"] == "A")
                    / max(1, sum(1 for r in rows if r["model_label"] == m and r["condition"] == "plain")))
    fig, ax = plt.subplots(figsize=(7.2, 0.28 * (2 * len(models) + 2) + 1.3), dpi=300)
    labels, ys = [], []
    y = 0
    for m in models:
        for c in ("plain", "guided"):
            rs = [r for r in rows if r["model_label"] == m and r["condition"] == c]
            n = len(rs); cnt = collections.Counter(r["key"] for r in rs)
            left = 0
            for j, L in enumerate("ABCDE"):
                w = 100 * cnt.get(L, 0) / n
                ax.barh(y, w, left=left, color=RAMP[j], edgecolor="white", linewidth=1.2, height=0.72)
                left += w
            ax.text(101, y, "%.0f%%" % (100 * cnt.get("A", 0) / n), va="center", ha="left", fontsize=8, color=INK)
            labels.append("%s  ·  %s" % (m, c)); ys.append(y)
            y += 1 if c == "plain" else 1.6
    cnt = collections.Counter(nbme["key_counts"]); n = sum(cnt.values())
    left = 0
    for j, L in enumerate("ABCDE"):
        w = 100 * cnt[L] / n
        ax.barh(y, w, left=left, color=RAMP[j], edgecolor="white", linewidth=1.2, height=0.72); left += w
    ax.text(101, y, "%.0f%%" % (100 * cnt["A"] / n), va="center", ha="left", fontsize=8, color=INK)
    labels.append("NBME retired USMLE items, five options (n=%d)" % n); ys.append(y)
    ax.set_yticks(ys); ax.set_yticklabels(labels, fontsize=7.5, color=INK); ax.invert_yaxis()
    bold_flagship(ax, labels, tier_of)
    ax.set_xlim(0, 100); ax.set_xlabel("Share of items (%)", color=INK2)
    ax.set_xticks([0, 25, 50, 75, 100])
    style(ax); ax.grid(axis="x", color=GRID, linewidth=0.6)
    handles = [plt.Rectangle((0, 0), 1, 1, color=RAMP[j]) for j in range(5)]
    ax.legend(handles, ["Key at A", "B", "C", "D", "E"], loc="lower center", bbox_to_anchor=(0.5, 1.005), ncol=5, frameon=False, fontsize=8)
    ax.text(101, ys[0] - 1.0, "key at A", fontsize=7.5, color=INK2, ha="left", va="center")
    fig.text(0.01, 0.004, "Position of the correct answer among five options, by generator model (bold = flagship tier) and prompt condition;\n"
             "n≈400 items per bar; models ordered by share of keys at A under the plain prompt.", fontsize=6.5, color=MUTED)
    fig.tight_layout(rect=(0, 0.025, 1, 1))
    fig.savefig(out / "fig1_key_position.png"); fig.savefig(out / "fig1_key_position.svg"); plt.close(fig)

def fig2(rows, nbme, out):
    tier_of = tiers(rows)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.6, 0.32 * len(tier_of) + 1.6), dpi=300, gridspec_kw={"width_ratios": [1.15, 1]})
    stats = {}
    for m in tier_of:
        for c in ("plain", "guided"):
            rs = [r for r in rows if r["model_label"] == m and r["condition"] == c]
            k = sum(1 for r in rs if any(int(r[f]) for f in CORE)); stats[(m, c)] = wilson(k, len(rs))
    order = sorted(tier_of, key=lambda m: -stats[(m, "plain")][0])
    for i, m in enumerate(order):
        p, plo, phi = stats[(m, "plain")]; g, glo, ghi = stats[(m, "guided")]
        ax1.plot([100 * g, 100 * p], [i, i], color=GRID, linewidth=2, zorder=1)
        ax1.errorbar(100 * p, i, xerr=[[100 * (p - plo)], [100 * (phi - p)]], fmt="o", color=ORANGE, ms=5.5, elinewidth=0.8, capsize=0, zorder=3)
        ax1.errorbar(100 * g, i, xerr=[[100 * (g - glo)], [100 * (ghi - g)]], fmt="o", color=BLUE, ms=5.5, elinewidth=0.8, capsize=0, zorder=3)
    nb = 100 * nbme["any_core"] / nbme["n"]
    ax1.axvline(nb, color=INK2, linestyle=(0, (3, 3)), linewidth=1)
    ax1.text(nb + 0.6, -0.75, "NBME items %.0f%%" % nb, fontsize=7.5, color=INK2, va="center", ha="left")
    ax1.set_ylim(len(order) - 0.4, -1.1)
    ax1.set_yticks(range(len(order))); ax1.set_yticklabels(order, fontsize=7.5, color=INK)
    bold_flagship(ax1, order, tier_of)
    ax1.set_xlim(0, 45); ax1.set_xlabel("Items with ≥1 of the 14 structural flaws (%)", color=INK2)
    style(ax1)
    ax1.plot([], [], "o", color=ORANGE, label="Plain prompt"); ax1.plot([], [], "o", color=BLUE, label="Guidelines in prompt")
    ax1.legend(loc="lower right", frameon=False, fontsize=8)
    ax1.set_title("A. By generator model (95% CI; bold = flagship tier)", loc="left", fontsize=9, color=INK)
    flaws = [("longest_option_key", "Longest option is the key"), ("clang_cue", "Stem–key word repetition"), ("absolute_terms", "Absolute terms in options"),
             ("grammatical_cue", "Grammatical cue"), ("nonparallel_options", "Non-parallel options"), ("overlapping_options", "Overlapping options"),
             ("combination_options", "Combination options"), ("negative_stem", "Negative lead-in")]
    n_plain = sum(1 for r in rows if r["condition"] == "plain"); n_guided = sum(1 for r in rows if r["condition"] == "guided")
    for i, (f, lab) in enumerate(flaws):
        p = 100 * sum(int(r[f]) for r in rows if r["condition"] == "plain") / n_plain
        g = 100 * sum(int(r[f]) for r in rows if r["condition"] == "guided") / n_guided
        nbv = 100 * nbme["flaw_counts"].get(f, 0) / nbme["n"]
        ax2.plot([g, p], [i, i], color=GRID, linewidth=2, zorder=1)
        ax2.plot(p, i, "o", color=ORANGE, ms=5.5, zorder=3); ax2.plot(g, i, "o", color=BLUE, ms=5.5, zorder=3)
        ax2.plot(nbv, i, marker="|", color=INK2, ms=11, mew=1.4, linestyle="none", zorder=2)
    ax2.set_yticks(range(len(flaws))); ax2.set_yticklabels([l for _, l in flaws], fontsize=7.5, color=INK); ax2.invert_yaxis()
    ax2.set_xlim(0, 14); ax2.set_xlabel("Prevalence, pooled over %d models (%%)" % len(tier_of), color=INK2)
    style(ax2)
    ax2.plot([], [], marker="|", color=INK2, ms=10, mew=1.4, linestyle="none", label="NBME reference")
    ax2.plot([], [], "o", color=ORANGE, label="Plain (n=%s)" % format(n_plain, ",")); ax2.plot([], [], "o", color=BLUE, label="Guided (n=%s)" % format(n_guided, ","))
    ax2.legend(loc="lower right", frameon=False, fontsize=8)
    ax2.set_title("B. By flaw", loc="left", fontsize=9, color=INK)
    fig.tight_layout()
    fig.savefig(out / "fig2_flaw_prevalence.png"); fig.savefig(out / "fig2_flaw_prevalence.svg"); plt.close(fig)

if __name__ == "__main__":
    rows = [r for r in csv.DictReader(open(sys.argv[1])) if r["condition"] in ("plain", "guided") and r.get("reasoning_mode", "off") == "off"]
    src = pathlib.Path(sys.argv[2])
    if src.suffix == ".json":
        nbme = json.load(open(src))
    else:   # item-level NBME flags available: aggregate the five-option items and save the aggregate for the release
        items = [r for r in csv.DictReader(open(src)) if r["n_options"] == "5"]
        nbme = {"n": len(items), "definition": "five-option retired USMLE items; any_core = any of the 14 core rules (mediwf.rules.CORE)",
                "detector_version": items[0].get("detector_version", ""),
                "key_counts": dict(collections.Counter(r["key"] for r in items if r["key"] in "ABCDE")),
                "any_core": sum(1 for r in items if any(int(r[f]) for f in CORE)),
                "flaw_counts": {f: sum(int(r[f]) for r in items) for f in CORE + ["option_length_outlier", "options_not_alphabetical", "numeric_units_inconsistent"]}}
        json.dump(nbme, open(src.parent / "nbme_aggregate_for_figures.json", "w"), indent=1)
    out = pathlib.Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
    fig1(rows, nbme, out); fig2(rows, nbme, out); print("figures written to", out)
