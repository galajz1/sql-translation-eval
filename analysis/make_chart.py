"""Chart for WRITEUP.md: silent-wrong rate on trap translations by condition.

Numbers are from the Nov 13 2026 run (results/*.jsonl, 33 trap translations
per cell: 11 traps x 3 samples). Re-run score.py and update DATA if you rerun.
"""
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

CONDITIONS = [
    ("direct", "No reasoning"),
    ("direct_hint", "No reasoning\n+ hint"),
    ("reason_plain", "Written\nreasoning"),
    ("reason", "Written reasoning\n+ hint"),
    ("native", "Built-in\nthinking"),
]
# silent-wrong counts out of 33
DATA = {
    "Haiku 5.5": [12, 15, 3, 1, 0],
    "Sonnet 5.5": [2, 1, 0, 0, 0],
}
COLORS = {"Haiku 5.5": "#2a78d6", "Sonnet 5.5": "#eb6834"}  # validated: default slots 1-2
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e1"
N = 33

fig, ax = plt.subplots(figsize=(9, 4.8), dpi=200)
fig.patch.set_facecolor(SURFACE)
ax.set_facecolor(SURFACE)

bar_w, gap = 0.36, 0.04
for i, (model, counts) in enumerate(DATA.items()):
    offset = (i - 0.5) * (bar_w + gap)
    for x, c in enumerate(counts):
        pct = 100 * c / N
        h = max(pct, 0.0)
        if h > 0:
            ax.add_patch(FancyBboxPatch(
                (x + offset - bar_w / 2, 0), bar_w, h,
                boxstyle="round,pad=0,rounding_size=0.06", mutation_aspect=12,
                facecolor=COLORS[model], edgecolor=SURFACE, linewidth=1.5))
        label = f"{pct:.0f}%" if c else "0"
        ax.text(x + offset, h + 1.2, label, ha="center", va="bottom",
                fontsize=8.5, color=INK2 if c == 0 else INK)

ax.set_xlim(-0.6, len(CONDITIONS) - 0.4)
ax.set_ylim(0, 52)
ax.set_xticks(range(len(CONDITIONS)))
ax.set_xticklabels([c[1] for c in CONDITIONS], fontsize=9, color=INK)
ax.set_yticks([0, 10, 20, 30, 40, 50])
ax.set_yticklabels([f"{t}%" for t in [0, 10, 20, 30, 40, 50]], fontsize=8.5, color=INK2)
ax.yaxis.grid(True, color=GRID, linewidth=0.8)
ax.set_axisbelow(True)
for side in ("top", "right", "left"):
    ax.spines[side].set_visible(False)
ax.spines["bottom"].set_color(GRID)
ax.tick_params(length=0)

ax.set_title("Silently wrong SQL translations, by how the model was asked",
             loc="left", fontsize=12, color=INK, pad=22, fontweight="bold")
ax.text(0, 1.03, "Share of 33 trap translations per bar (11 Oracle traps x 3 samples) that ran "
        "on Athena/Trino but returned different results",
        transform=ax.transAxes, fontsize=8.5, color=INK2)

handles = [plt.Rectangle((0, 0), 1, 1, color=COLORS[m]) for m in DATA]
ax.legend(handles, list(DATA), loc="upper right", frameon=False, fontsize=9,
          labelcolor=INK)

fig.tight_layout()
out = Path(__file__).resolve().parent.parent / "silent_errors_by_condition.png"
fig.savefig(out, facecolor=SURFACE)
print(out)
