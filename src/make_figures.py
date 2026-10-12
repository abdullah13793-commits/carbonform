"""Report figures from the Python engine.  python src/make_figures.py -> reports/figures/*.png"""
import sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from carbon import engine as E

DB = E.load_db()
FIG = ROOT / "reports/figures"; FIG.mkdir(parents=True, exist_ok=True)
SURF, INK, INK2, MUTED, GRID = "#121514", "#f2f4ef", "#b9c0b8", "#7d867e", "#2a302d"
P = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#9085e9"]
GOOD, BAD = "#0ca30c", "#e5484d"
plt.rcParams.update({"font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 10, "text.color": INK, "axes.facecolor": SURF,
                     "figure.facecolor": SURF, "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": MUTED,
                     "ytick.color": MUTED, "savefig.facecolor": SURF, "savefig.dpi": 200, "axes.titleweight": "semibold"})
LAB = dict(concrete="In-situ concrete", precast="Precast concrete", timber="CLT timber", steel="Steel frame",
           brick="Brick", wood="Larch", fibrecement="Fibre cement", render="Render")


def matrix():
    S, F = ["concrete", "precast", "steel", "timber"], ["brick", "render", "fibrecement", "wood"]
    M = np.array([[E.evaluate({"structure": s, "facade": f}, DB)["total"] for f in F] for s in S])
    cmap = LinearSegmentedColormap.from_list("r", ["#0f5d2f", "#2e7d3a", "#6a7a3a", "#a35a2a", "#c2402c"])
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    im = ax.imshow(M, cmap=cmap, norm=TwoSlopeNorm(vcenter=5.5, vmin=M.min() - 0.2, vmax=max(7.6, M.max())))
    for i in range(len(S)):
        for j in range(len(F)):
            ax.text(j, i, f"{M[i, j]:.2f}", ha="center", va="center", color="white", fontsize=12, fontweight="semibold")
    ax.set_xticks(range(len(F)), [LAB[f] for f in F]); ax.set_yticks(range(len(S)), [LAB[s] for s in S])
    ax.set_title("Whole-life carbon, kg CO₂e/m²/yr · 5-storey bar, mineral wool, wood-alu windows", loc="left", fontsize=10.5)
    for s in ax.spines.values(): s.set_visible(False)
    cb = fig.colorbar(im, ax=ax, fraction=.04, pad=.02); cb.outline.set_visible(False); cb.set_label("BR18 2025 limit = 7.5", color=INK2)
    fig.savefig(FIG / "matrix.png", bbox_inches="tight"); plt.close(fig)
    return M


ARCH = [("Concrete + brick", {}), ("Precast + render", {"structure": "precast", "facade": "render", "insulation": "eps"}),
        ("Steel + curtain wall", {"structure": "steel", "facade": "fibrecement", "windows": "curtain"}),
        ("CLT + larch", {"structure": "timber", "facade": "wood", "insulation": "woodfibre", "windows": "wood"}),
        ("Renovate 1970s", {"mode": "renovate", "facade": "wood", "insulation": "cellulose", "windows": "wood"}),
        ("Keep 1970s", {"mode": "keep"})]


def archetypes():
    keys, lab = ["A1A3", "B4", "B6", "C3C4"], ["Production A1–A3", "Replacements B4", "Operation B6", "End of life C3–C4"]
    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    y = np.arange(len(ARCH))
    for i, (name, d) in enumerate(ARCH):
        r = E.evaluate(d, DB)["perM2Yr"]
        pos, neg = 0.0, 0.0
        for k, c in zip(keys, P):
            v = r[k]
            if v >= 0:
                ax.barh(i, v - 0.04, left=pos, color=c, height=0.5); pos += v
            else:
                ax.barh(i, v, left=neg, color=c, height=0.5, alpha=.55); neg += v
        tot = sum(r[k] for k in keys)
        ax.text(pos + 0.12, i, f"{tot:.2f}", va="center", color=INK, fontsize=10, fontweight="semibold")
    ax.axvline(7.5, color=INK2, lw=1); ax.text(7.45, -0.45, "BR18 2025 limit 7.5", color=INK2, fontsize=9, ha="right")
    ax.axvline(0, color=GRID, lw=1)
    ax.set_yticks(y, [a[0] for a in ARCH]); ax.invert_yaxis(); ax.set_xlabel("kg CO₂e per m² per year (50 years)")
    ax.grid(axis="x", color=GRID, lw=.5); ax.set_axisbelow(True)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in P[:4]]
    ax.legend(handles, lab, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.16), fontsize=8.5, labelcolor=INK2, ncol=4)
    ax.set_title("Where the carbon goes: four new-build archetypes and the existing block", loc="left", fontsize=10.5)
    fig.savefig(FIG / "archetypes.png", bbox_inches="tight"); plt.close(fig)


def scenarios():
    fig, ax = plt.subplots(figsize=(8.6, 4.2))
    d = {"facade": "wood", "insulation": "cellulose", "windows": "wood", "structure": "timber"}
    keep = E.evaluate({**d, "mode": "keep"}, DB)["timeline"]
    reno = E.evaluate({**d, "mode": "renovate"}, DB)["timeline"]
    new = E.evaluate({**d, "mode": "new"}, DB)
    demo = E.evaluate({**d, "mode": "keep"}, DB)["modules"]["C3C4"]
    newt = [v + demo for v in new["timeline"]]
    newc = E.evaluate({"mode": "new"}, DB)["timeline"]; newc = [v + demo for v in newc]
    yrs = np.arange(E.PERIOD + 1) + E.START_YEAR
    for series, lab, c in [(keep, "Keep 1970s block (maintenance only)", MUTED), (reno, "Deep renovation (timber/cellulose)", "#b7f36a"),
                           (newt, "Demolish + new CLT block", P[0]), (newc, "Demolish + new concrete block", P[1])]:
        ax.plot(yrs, np.array(series) / 1000, color=c, lw=2, solid_capstyle="round")
        ax.plot(yrs[-1], series[-1] / 1000, "o", ms=6, color=c, mec=SURF, mew=2)
        ax.text(yrs[-1] + 0.8, series[-1] / 1000, f"{series[-1] / 1000:,.0f} t  {lab}", va="center", fontsize=8.5, color=INK2)
    be = next((i for i in range(1, len(reno)) if reno[i] <= keep[i]), None)
    if be:
        ax.axvline(E.START_YEAR + be, color="#b7f36a", alpha=.5, lw=1)
        ax.text(E.START_YEAR + be + 0.6, ax.get_ylim()[1] * 0.92, f"renovation below keep from {E.START_YEAR + be}", fontsize=8.5, color=INK)
    ax.set_xlim(E.START_YEAR, E.START_YEAR + 50); ax.set_ylabel("Cumulative t CO₂e")
    ax.grid(color=GRID, lw=.5); ax.set_axisbelow(True)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    ax.set_title("Same site, four futures: cumulative emissions 2026–2076", loc="left", fontsize=10.5)
    fig.savefig(FIG / "scenarios.png", bbox_inches="tight"); plt.close(fig)


def sensitivity():
    base = E.evaluate({}, DB)["total"]
    tests = [("Structure → CLT", {"structure": "timber"}), ("Structure → precast", {"structure": "precast"}),
             ("Facade → larch", {"facade": "wood"}), ("Insulation → wood fibre", {"insulation": "woodfibre"}),
             ("Windows → timber", {"windows": "wood"}), ("Windows → curtain wall", {"windows": "curtain"}),
             ("Heating → heat pump", {"heating": "heatpump"}), ("Roof → green", {"roof": "green"}),
             ("PV on 60 % of roof", {"pv": 0.6}), ("No balconies", {"balconies": False}),
             ("Window ratio 30 → 50 %", {"wwr": 0.5}), ("5 → 9 storeys", {"floors": 9})]
    vals = sorted([(lab, E.evaluate(d, DB)["total"] - base) for lab, d in tests], key=lambda x: x[1])
    fig, ax = plt.subplots(figsize=(8.0, 4.6))
    for i, (lab, v) in enumerate(vals):
        ax.barh(i, v, color=GOOD if v < 0 else BAD, height=.55)
        ax.text(v + (0.03 if v >= 0 else -0.03), i, f"{v:+.2f}", va="center", ha="left" if v >= 0 else "right", fontsize=9, color=INK)
    ax.set_yticks(range(len(vals)), [v[0] for v in vals]); ax.axvline(0, color=INK2, lw=1)
    ax.set_xlabel(f"Change in kg CO₂e/m²/yr from the concrete/brick base case ({base:.2f})")
    ax.grid(axis="x", color=GRID, lw=.5); ax.set_axisbelow(True)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    ax.set_title("One change at a time: what moves the result", loc="left", fontsize=10.5)
    fig.savefig(FIG / "sensitivity.png", bbox_inches="tight"); plt.close(fig)


if __name__ == "__main__":
    M = matrix(); archetypes(); scenarios(); sensitivity()
    print("figures ->", FIG); print(np.round(M, 2))
