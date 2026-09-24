"""The paper's figure files from the flag files: 600 dpi TIFF (and PDF), 164 mm wide, sentence-case labels, numerals.
Fig. 1: prevalence of any structural flaw by model (plain vs guided) and per-flaw pooled prevalence, with the NBME reference.
Fig. 2: answer-key position by model x condition, with the NBME reference (percent labels rounded half up, as in Table 2).
Usage: python3 scripts/make_figures_paper.py outputs/flags_full.csv outputs/nbme_aggregate_for_figures.json <outdir>
"""
import sys, csv, math, collections, pathlib, json
from decimal import Decimal, ROUND_HALF_UP
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import rcParams

rcParams["font.family"] = "DejaVu Sans"; rcParams["font.size"] = 7
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#8a8985", "#e6e5e1"
BLUE, ORANGE = "#2a78d6", "#eb6834"
RAMP = ["#2a78d6", "#6a9fe0", "#a3c1ea", "#c9d8ee", "#9a9995"]
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from mediwf.rules import CORE

WIDTH_IN = 164 / 25.4          # 82 or 164 mm wide
DPI = 600

def pct_half_up(k, n):
    return int((Decimal(100 * k) / Decimal(n)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

def wilson(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0.0, c - h), min(1.0, c + h)

def style(ax):
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    for s in ("left", "bottom"): ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2, length=0)
    ax.grid(axis="x", color=GRID, linewidth=0.5); ax.set_axisbelow(True)

def tiers(rows):
    return {r["model_label"]: r.get("tier", "base") for r in rows}

def bold_flagship(ax, labels, tier_of):
    for lab, tick in zip(labels, ax.get_yticklabels()):
        name = lab.split("  ·  ")[0]
        if tier_of.get(name) == "flagship": tick.set_fontweight("bold")

def save(fig, out, stem):
    fig.savefig(out / f"{stem}.tif", dpi=DPI, facecolor="white", pil_kwargs={"compression": "tiff_lzw"})
    from PIL import Image
    im = Image.open(out / f"{stem}.tif")
    if im.mode != "RGB":
        bg = Image.new("RGB", im.size, (255, 255, 255)); bg.paste(im.convert("RGBA"), mask=im.convert("RGBA").split()[3]); im = bg
        im.save(out / f"{stem}.tif", compression="tiff_lzw", dpi=(DPI, DPI))
    fig.savefig(out / f"{stem}.pdf")
    fig.savefig(out / f"{stem}_preview.png", dpi=150)
    plt.close(fig)

def fig_key_position(rows, nbme, out):
    tier_of = tiers(rows)
    def share_a(m):
        rs = [r for r in rows if r["model_label"] == m and r["condition"] == "plain"]
        return sum(1 for r in rs if r["key"] == "A") / max(1, len(rs))
    models = sorted(tier_of, key=lambda m: -share_a(m))
    fig, ax = plt.subplots(figsize=(WIDTH_IN, 0.205 * (2 * len(models) + 2) + 0.9))
    labels, ys = [], []
    y = 0
    for m in models:
        for c in ("plain", "guided"):
            rs = [r for r in rows if r["model_label"] == m and r["condition"] == c]
            n = len(rs); cnt = collections.Counter(r["key"] for r in rs)
            left = 0
            for j, L in enumerate("ABCDE"):
                w = 100 * cnt.get(L, 0) / n
                ax.barh(y, w, left=left, color=RAMP[j], edgecolor="white", linewidth=0.8, height=0.72)
                left += w
            ax.text(101, y, "%d%%" % pct_half_up(cnt.get("A", 0), n), va="center", ha="left", fontsize=6.5, color=INK)
            labels.append("%s  ·  %s" % (m, c)); ys.append(y)
            y += 1 if c == "plain" else 1.6
    cnt = collections.Counter(nbme["key_counts"]); n = sum(cnt.values())
    left = 0
    for j, L in enumerate("ABCDE"):
        w = 100 * cnt[L] / n
        ax.barh(y, w, left=left, color=RAMP[j], edgecolor="white", linewidth=0.8, height=0.72); left += w
    ax.text(101, y, "%d%%" % pct_half_up(cnt["A"], n), va="center", ha="left", fontsize=6.5, color=INK)
    labels.append("NBME retired USMLE items, 5 options (n=%d)" % n); ys.append(y)
    ax.set_yticks(ys); ax.set_yticklabels(labels, fontsize=6.5, color=INK); ax.invert_yaxis()
    bold_flagship(ax, labels, tier_of)
    ax.set_xlim(0, 100); ax.set_xlabel("Share of items (%)", color=INK2, fontsize=7)
    ax.set_xticks([0, 25, 50, 75, 100])
    style(ax)
    handles = [plt.Rectangle((0, 0), 1, 1, color=RAMP[j]) for j in range(5)]
    ax.legend(handles, ["Key at A", "B", "C", "D", "E"], loc="lower center", bbox_to_anchor=(0.5, 1.005), ncol=5, frameon=False, fontsize=7)
    ax.text(101, ys[0] - 1.0, "Key at A", fontsize=6.5, color=INK2, ha="left", va="center")
    fig.tight_layout()
    save(fig, out, "MedIWF_Fig2_key_position")

def fig_flaw_prevalence(rows, nbme, out):
    tier_of = tiers(rows)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(WIDTH_IN, 0.24 * len(tier_of) + 1.2), gridspec_kw={"width_ratios": [1.15, 1]})
    stats = {}
    for m in tier_of:
        for c in ("plain", "guided"):
            rs = [r for r in rows if r["model_label"] == m and r["condition"] == c]
            k = sum(1 for r in rs if any(int(r[f]) for f in CORE)); stats[(m, c)] = wilson(k, len(rs))
    order = sorted(tier_of, key=lambda m: -stats[(m, "plain")][0])
    for i, m in enumerate(order):
        p, plo, phi = stats[(m, "plain")]; g, glo, ghi = stats[(m, "guided")]
        ax1.plot([100 * g, 100 * p], [i, i], color=GRID, linewidth=1.6, zorder=1)
        ax1.errorbar(100 * p, i, xerr=[[100 * (p - plo)], [100 * (phi - p)]], fmt="o", color=ORANGE, ms=4, elinewidth=0.7, capsize=0, zorder=3)
        ax1.errorbar(100 * g, i, xerr=[[100 * (g - glo)], [100 * (ghi - g)]], fmt="o", color=BLUE, ms=4, elinewidth=0.7, capsize=0, zorder=3)
    nb = 100 * nbme["any_core"] / nbme["n"]
    ax1.axvline(nb, color=INK2, linestyle=(0, (3, 3)), linewidth=0.8)
    ax1.text(nb + 0.6, -0.75, "NBME items %.1f%%" % nb, fontsize=6.5, color=INK2, va="center", ha="left")
    ax1.set_ylim(len(order) - 0.4, -1.1)
    ax1.set_yticks(range(len(order))); ax1.set_yticklabels(order, fontsize=6.5, color=INK)
    bold_flagship(ax1, order, tier_of)
    ax1.set_xlim(0, 45); ax1.set_xlabel("Items with at least 1 of the 14 structural flaws (%)", color=INK2, fontsize=7)
    style(ax1)
    ax1.plot([], [], "o", color=ORANGE, label="Plain prompt"); ax1.plot([], [], "o", color=BLUE, label="Guided prompt")
    ax1.legend(loc="lower right", frameon=False, fontsize=6.5)
    ax1.set_title("(A) By generator model (95% CI; bold, flagship tier)", loc="left", fontsize=7.5, color=INK)
    flaws = [("longest_option_key", "Longest option is the key"), ("clang_cue", "Stem–key word repetition"), ("absolute_terms", "Absolute terms in options"),
             ("nonparallel_options", "Non-parallel options"), ("overlapping_options", "Overlapping options"), ("vague_terms", "Vague frequency terms"),
             ("numeric_not_ordered", "Numeric options not ordered"), ("grammatical_cue", "Grammatical cue")]
    n_plain = sum(1 for r in rows if r["condition"] == "plain"); n_guided = sum(1 for r in rows if r["condition"] == "guided")
    for i, (f, lab) in enumerate(flaws):
        p = 100 * sum(int(r[f]) for r in rows if r["condition"] == "plain") / n_plain
        g = 100 * sum(int(r[f]) for r in rows if r["condition"] == "guided") / n_guided
        nbv = 100 * nbme["flaw_counts"].get(f, 0) / nbme["n"]
        ax2.plot([g, p], [i, i], color=GRID, linewidth=1.6, zorder=1)
        ax2.plot(p, i, "o", color=ORANGE, ms=4, zorder=3); ax2.plot(g, i, "o", color=BLUE, ms=4, zorder=3)
        ax2.plot(nbv, i, marker="|", color=INK2, ms=9, mew=1.2, linestyle="none", zorder=2)
    ax2.set_yticks(range(len(flaws))); ax2.set_yticklabels([l for _, l in flaws], fontsize=6.5, color=INK); ax2.invert_yaxis()
    ax2.set_xlim(0, 14); ax2.set_xlabel("Prevalence, pooled over %d models (%%)" % len(tier_of), color=INK2, fontsize=7)
    style(ax2)
    ax2.plot([], [], marker="|", color=INK2, ms=8, mew=1.2, linestyle="none", label="NBME reference")
    ax2.plot([], [], "o", color=ORANGE, label="Plain (n=%s)" % format(n_plain, ",")); ax2.plot([], [], "o", color=BLUE, label="Guided (n=%s)" % format(n_guided, ","))
    ax2.legend(loc="lower right", frameon=False, fontsize=6.5)
    ax2.set_title("(B) By flaw", loc="left", fontsize=7.5, color=INK)
    fig.tight_layout()
    save(fig, out, "MedIWF_Fig1_flaw_prevalence")

if __name__ == "__main__":
    rows = [r for r in csv.DictReader(open(sys.argv[1])) if r["condition"] in ("plain", "guided") and r.get("reasoning_mode", "off") == "off" and r.get("run", "full") == "full"]
    nbme = json.load(open(sys.argv[2]))
    out = pathlib.Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
    fig_flaw_prevalence(rows, nbme, out); fig_key_position(rows, nbme, out); print("figures written to", out)
