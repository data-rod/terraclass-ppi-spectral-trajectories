"""Generate spectral profiles, distributions and STL figures from seed-13 results."""
from pathlib import Path
import argparse
import json

import numpy as np
import pandas as pd
from scipy.stats import gaussian_kde
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgba
from matplotlib.lines import Line2D
from matplotlib.ticker import FixedLocator, FuncFormatter, MaxNLocator
from sklearn.metrics import confusion_matrix, precision_recall_curve


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--data", type=Path, help="Diretório com as tabelas e os componentes do suplemento")
parser.add_argument("--output", type=Path, help="Pasta para os gráficos regenerados")
parser.add_argument("--dpi", type=int, help="Resolução dos PNGs em dpi; usa a configuração visual quando omitida")
args = parser.parse_args()

PACKAGE = Path(__file__).resolve().parents[1]
VISUAL = json.loads((PACKAGE / "config_visual.json").read_text(encoding="utf-8"))
PRINT_DPI = args.dpi or VISUAL["print_dpi"]
WORK = args.data.resolve() if args.data else PACKAGE / "dados"
FLAT = (WORK / "representatives-13.parquet").exists()
OUT = args.output.resolve() if args.output else PACKAGE / "figuras"
OUT.mkdir(parents=True, exist_ok=True)


def input_path(relative: str) -> Path:
    name = Path(relative).name
    if FLAT and name == "components-13.parquet":
        name = "componentes_270_ajustes.parquet"
    return WORK / name if FLAT else WORK / relative


def pt_formatter(decimals: int = 2) -> FuncFormatter:
    def _fmt(val: float, _pos: int) -> str:
        if abs(val) < 1e-12:
            val = 0.0
        return f"{val:.{decimals}f}".replace(".", ",")
    return FuncFormatter(_fmt)


CLASSES = [(c["code"], c["name"]) for c in VISUAL["classes"]]
# Paleta qualitativa Dark2 do ColorBrewer (Harrower e Brewer, 2003)
COLORS = [c["color"] for c in VISUAL["classes"]]
MARKERS = [c["marker"] for c in VISUAL["classes"]]
BANDS = ["B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B11", "B12"]
BAND_NM = [490, 560, 665, 705, 740, 783, 842, 865, 1610, 2190]
BAND_LABELS = [f"{b}\n({nm})" for b, nm in zip(BANDS, BAND_NM)]

plt.rcParams.update({
    "font.family": "Times New Roman",
    "mathtext.fontset": "stix",
    "font.size": 9,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.linewidth": 0.55,
    "pdf.fonttype": 42,
    "svg.fonttype": "path",
})

reps = pd.read_parquet(input_path("results/representatives-13.parquet"))
train = pd.read_csv(input_path("model/training.csv"))
metrics = pd.read_csv(input_path("results/metrics-13.csv"))
components = pd.read_parquet(input_path("results/components-13.parquet"))
assert len(reps) == 519 and reps.analysis_id.nunique() == 1


def save(fig: plt.Figure, name: str) -> None:
    for ext in ["png", "pdf", "svg"]:
        fig.savefig(OUT / f"{name}.{ext}", dpi=PRINT_DPI, bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figura 3: Perfis espectrais medianos (a) e deslocamentos sucessivos (b)
# ---------------------------------------------------------------------------
def plot_profiles(ax: plt.Axes) -> None:
    x = np.arange(len(BANDS))
    for (c, name), col, marker in zip(CLASSES, COLORS, MARKERS):
        v = reps.loc[reps.classe == c, BANDS]
        ax.fill_between(x, v.quantile(0.25), v.quantile(0.75), color=col, alpha=0.14, lw=0)
        ax.plot(
            x, v.median(), color=col, marker=marker, ms=3.8, lw=1.15,
            mec="white", mew=0.35, label=name, zorder=4
        )

    neg = train.loc[train.label == "incompatible", BANDS]
    ax.fill_between(x, neg.quantile(0.25), neg.quantile(0.75), color="#777777", alpha=0.10, lw=0)
    ax.plot(x, neg.median(), color="#555555", ls="--", lw=0.9, label="Não compatíveis rotulados", zorder=3)

    # Separadores e chaves de dominios espectrais alinhados a Figura 5
    for divider in (2.5, 5.5, 7.5):
        ax.axvline(divider, color="#cccccc", ls=":", lw=0.65, zorder=0)

    domains = [(0, 2, "VIS"), (3, 5, "RE"), (6, 7, "NIR"), (8, 9, "SWIR")]
    trans = ax.get_xaxis_transform()
    for start, end, dlabel in domains:
        ax.plot([start - 0.35, end + 0.35], [1.015, 1.015], color="#555555", lw=0.8, transform=trans, clip_on=False)
        ax.text((start + end) / 2, 1.035, dlabel, transform=trans, ha="center", va="bottom",
                fontsize=7.5, fontweight="bold", color="#333333")

    y_max = float(max(reps[BANDS].quantile(0.75).max(), neg.quantile(0.75).max()))
    ax.set(
        xticks=x,
        xticklabels=BAND_LABELS,
        xlim=(-0.45, 9.45),
        ylim=(0.0, np.ceil(y_max * 10) / 10),
        xlabel="Banda espectral (comprimento de onda central, nm)",
        ylabel="Reflectância",
    )
    ax.set_title("(a)", loc="left", fontweight="bold", fontsize=9.5, pad=18)
    ax.tick_params(axis="x", labelsize=7.2)
    ax.yaxis.set_major_formatter(pt_formatter(1))
    ax.legend(fontsize=7.3, frameon=False, loc="upper left", handlelength=2.2)
    ax.grid(axis="y", alpha=0.25, lw=0.35)


def plot_distances(ax: plt.Axes) -> None:
    d = pd.read_csv(input_path("results/distances-13.csv"))
    vals = [d.loc[d.classe == c, "distance_km"].to_numpy() for c, _ in CLASSES]
    box = ax.boxplot(
        vals,
        positions=[1, 2, 3],
        widths=0.40,
        showfliers=False,
        patch_artist=True,
        medianprops={"color": "#111111", "linewidth": 1.2},
        whiskerprops={"color": "#444444", "linewidth": 0.85},
        capprops={"color": "#444444", "linewidth": 0.85},
    )
    rng = np.random.default_rng(13)
    for i, (v, col, marker, patch) in enumerate(zip(vals, COLORS, MARKERS, box["boxes"]), 1):
        patch.set_facecolor(to_rgba(col, 0.22))
        patch.set_edgecolor(col)
        patch.set_linewidth(0.95)
        ax.scatter(
            i + rng.uniform(-0.14, 0.14, len(v)), v,
            s=8, color=col, marker=marker, alpha=0.36, edgecolors="none", zorder=2
        )
        med = float(np.median(v))
        ax.text(
            i + 0.23, med, f"{med:.2f}".replace(".", ","),
            va="center", ha="left", fontsize=7.2, color="#222222",
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.7, "pad": 0.6}
        )

    ax.set(
        xticks=[1, 2, 3],
        xticklabels=[n for _, n in CLASSES],
        xlim=(0.55, 3.65),
        ylabel="Deslocamento sucessivo (km)",
    )
    ax.set_title("(b)", loc="left", fontweight="bold", fontsize=9.5, pad=18)
    ax.grid(axis="y", alpha=0.25, lw=0.35)


fig, axes = plt.subplots(1, 2, figsize=(8.5, 3.25), gridspec_kw={"width_ratios": [1.42, 1.0]}, layout="constrained")
plot_profiles(axes[0])
plot_distances(axes[1])
save(fig, "figura_3_espectros_deslocamentos")


# ---------------------------------------------------------------------------
# Figura 4: Distribuições de reflectância por banda (mesma largura de banda KDE)
# ---------------------------------------------------------------------------
vis_hi = float(np.ceil(reps[["B02", "B03", "B04"]].max().max() * 25) / 25)
nir_lo = float(max(0.0, np.floor(reps[["B07", "B08", "B8A"]].min().min() * 20) / 20))
nir_hi = float(np.ceil(reps[["B07", "B08", "B8A"]].max().max() * 20) / 20)

fig, axes = plt.subplots(2, 5, figsize=(8.5, 3.9), layout="constrained")
summary = []
for ax, band in zip(axes.flat, BANDS):
    pool = reps[band].to_numpy()
    h = max(float(np.std(pool, ddof=1) * len(pool) ** (-0.2)), 1e-6)
    for i, ((c, name), col) in enumerate(zip(CLASSES, COLORS), 1):
        v = reps.loc[reps.classe == c, band].to_numpy()
        q0, q1, med, q3, q4 = np.quantile(v, [0.0, 0.25, 0.5, 0.75, 1.0])
        kde = gaussian_kde(v, bw_method=h / np.std(v, ddof=1))
        grid = np.linspace(q0, q4, 160)
        den = kde(grid)
        width = 0.37 * den / den.max()
        ax.fill_betweenx(
            grid, i - width, i + width,
            facecolor=to_rgba(col, 0.24), edgecolor=to_rgba(col, 0.80), lw=0.6
        )
        ax.plot([i, i], [q0, q4], color=col, lw=0.7)
        ax.plot([i, i], [q1, q3], color=col, lw=3.2, solid_capstyle="butt")
        ax.scatter([i], [med], s=13, c="white", edgecolors="#222222", linewidths=0.65, zorder=4)
        ax.plot([i - 0.075, i + 0.075], [q0, q0], color=col, lw=0.65)
        ax.plot([i - 0.075, i + 0.075], [q4, q4], color=col, lw=0.65)
        summary.append(dict(
            classe=c, band=band, n=len(v),
            minimum=q0, q25=q1, median=med, q75=q3, maximum=q4, kde_bandwidth=h
        ))

    ax.set(title=band, xticks=[1, 2, 3], xticklabels=[n for _, n in CLASSES], xlim=(0.45, 3.55))
    if band in {"B02", "B03", "B04"}:
        ax.set_ylim(0.0, vis_hi)
    elif band in {"B07", "B08", "B8A"}:
        ax.set_ylim(nir_lo, nir_hi)
    ax.tick_params(labelsize=7.0)
    ax.yaxis.set_major_locator(MaxNLocator(4))
    ax.yaxis.set_major_formatter(pt_formatter(2))
    ax.grid(axis="y", lw=0.3, alpha=0.25)

axes[0, 0].set_ylabel("Reflectância")
axes[1, 0].set_ylabel("Reflectância")
save(fig, "figura_4_distribuicoes_reflectancia")
pd.DataFrame(summary).to_csv(OUT / "distribuicoes_reflectancia.csv", index=False)


# ---------------------------------------------------------------------------
# Figura S2 (Suplemento): Decomposição completa na janela 7
# ---------------------------------------------------------------------------
f = components[components.window == 7].copy()
f["date"] = pd.to_datetime(f.date)
lo = float(np.floor(f[["trend", "seasonal", "residual"]].min().min() * 10) / 10)
hi = float(np.ceil(f[["trend", "seasonal", "residual"]].max().max() * 10) / 10)

fig, axes = plt.subplots(9, 10, figsize=(11, 11.4), sharex=True, sharey=True)
fig.subplots_adjust(left=0.116, right=0.995, bottom=0.045, top=0.943, hspace=0.26, wspace=0.13)
row_height = (0.880 - 2 * 0.045 - 6 * 0.020) / 9
for ci in range(3):
    block_top = 0.925 - ci * (3 * row_height + 2 * 0.020 + 0.045)
    for ki in range(3):
        top = block_top - ki * (row_height + 0.020)
        for ax in axes[ci * 3 + ki]:
            pos = ax.get_position()
            ax.set_position([pos.x0, top - row_height, pos.width, row_height])

domain_positions = [(0, 3, "VIS", "#53606b"), (3, 6, "Red edge", "#ab503b"), (6, 8, "NIR", "#297b54"), (8, 10, "SWIR", "#775590")]
for start, end, name, col in domain_positions:
    x0 = axes[0, start].get_position().x0
    x1 = axes[0, end - 1].get_position().x1
    fig.text((x0 + x1) / 2, 0.984, name, ha="center", color=col, fontweight="bold", fontsize=11)
    fig.add_artist(Line2D([x0, x1], [0.972, 0.972], transform=fig.transFigure, c=col, lw=1.4))

for ci, (c, name) in enumerate(CLASSES):
    for ki, (field, label) in enumerate([("trend", "Tendência"), ("seasonal", "Sazonal"), ("residual", "Resíduo")]):
        row = ci * 3 + ki
        for bi, band in enumerate(BANDS):
            ax = axes[row, bi]
            s = f[(f.classe == c) & (f.band == band)].sort_values("date")
            ax.plot(s.date, s[field], lw=0.7, c=COLORS[ci])
            ax.axhline(0, c="#999999", lw=0.35)
            ax.grid(axis="y", lw=0.3, alpha=0.25)
            ax.set_ylim(lo, hi)
            ax.set_yticks([-0.5, 0.0, 0.5])
            ax.set_yticklabels(["-0,5", "0", "0,5"])
            ax.tick_params(length=1.6, pad=1, labelsize=9.5)
            ax.set_xlim(pd.Timestamp("2017-01-01"), pd.Timestamp("2024-12-18"))
            ax.set_xticks([pd.Timestamp("2017-01-01"), pd.Timestamp("2024-12-18")], labels=["2017", "2024"])
            if ci == 2 and ki == 2:
                tick_labels = ax.get_xticklabels()
                tick_labels[0].set_ha("left")
                tick_labels[-1].set_ha("right")
            if ki == 0:
                if ci == 0:
                    ax.set_title(band, fontsize=11, fontweight="bold", pad=17)
                ax.axvspan(s.date.iloc[0], s.date.iloc[21], color="#e5e5e5", lw=0, zorder=-1)
                ax.axvspan(s.date.iloc[-22], s.date.iloc[-1], color="#e5e5e5", lw=0, zorder=-1)
            if ki == 1:
                ax.set_facecolor("#f5f8fc")
            if ki in (0, 1):
                m = metrics[(metrics.classe == c) & (metrics.band == band) & (metrics.window == 7)].iloc[0]
                sym, val = ("T", m.FT) if ki == 0 else ("S", m.FS)
                ax.text(0.99, 1.015, f"$F_{sym}$ = {val:.4f}".replace(".", ","), transform=ax.transAxes, ha="right", va="bottom", fontsize=9.5)
            if bi == 0:
                ax.set_ylabel(label, fontsize=10, color="black", labelpad=3)
    top = axes[ci * 3, 0].get_position().y1
    bottom = axes[ci * 3 + 2, 0].get_position().y0
    fig.text(0.038, (top + bottom) / 2, name, rotation=90, va="center", ha="center", fontsize=12, fontweight="bold", color=COLORS[ci])
    if ci < 2:
        mid = axes[ci * 3 + 2, 0].get_position().y0 - 0.005
        fig.add_artist(Line2D([0.055, 0.995], [mid, mid], transform=fig.transFigure, c="#aaaaaa", lw=0.7))

fig.text(0.54, 0.009, "Tempo", ha="center", fontsize=10)
fig.text(0.002, 0.5, "Reflectância e componentes", rotation=90, va="center", fontsize=10)
fig.canvas.draw()
renderer = fig.canvas.get_renderer()
for ci in range(3):
    for bi in range(10):
        ax = axes[ci * 3, bi]
        title_box = ax.title.get_window_extent(renderer)
        metric_box = ax.texts[0].get_window_extent(renderer)
        assert ci > 0 or not title_box.overlaps(metric_box), "Colisão entre banda e F_T"
        if ci:
            previous_box = axes[ci * 3 - 1, bi].get_window_extent(renderer)
            assert metric_box.y1 < previous_box.y0, "F_T invade classe anterior"
        else:
            assert title_box.y1 < 0.972 * fig.bbox.height, "Cabeçalho invade domínio"
global_box = fig.texts[-1].get_window_extent(renderer)
for text in fig.texts:
    if text.get_text() in {"VNFP", "VNFS", "SIL"}:
        assert not global_box.overlaps(text.get_window_extent(renderer)), "Colisão nos rótulos laterais"
save(fig, "figura_S2_decomposicao_completa")


# ---------------------------------------------------------------------------
# Figura S1 (Suplemento): Avaliação do classificador e disponibilidade mensal
# ---------------------------------------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.4), layout="constrained")
pred = pd.read_csv(input_path("model/outer_predictions.csv"))
ax = axes[0]
for fold, g in pred.groupby("outer_fold"):
    precision, recall, _ = precision_recall_curve(g.observed, g.probability)
    ax.plot(recall, precision, lw=0.9, label=f"Partição {fold}")
ax.axhline(pred.observed.mean(), color="#333333", ls=":", lw=0.8)
ax.set(xlabel="Sensibilidade", ylabel="Precisão positiva", xlim=(0, 1.01), ylim=(0, 1.01))
ax.set_title("(a)", loc="left", fontweight="bold", fontsize=9.5)
ax.xaxis.set_major_formatter(pt_formatter(1))
ax.yaxis.set_major_formatter(pt_formatter(1))
ax.legend(fontsize=7.2, loc="center left", frameon=False)
inset = ax.inset_axes([0.42, 0.05, 0.55, 0.30])
inset.axis("off")
cm = confusion_matrix(pred.observed, pred.predicted)
table = inset.table(cellText=cm, rowLabels=["NC", "C"], colLabels=["Pred. NC", "Pred. C"], loc="center", cellLoc="center")
table.auto_set_font_size(False)
table.set_fontsize(8)

cov = pd.read_csv(input_path("results/coverage-13.csv"))
cov["month"] = pd.to_datetime(cov.date).dt.month
counts = json.loads(input_path("spatial.json").read_text())["pixels"]
cov["valid_fraction"] = 100.0 * cov.n_valid / cov.classe.astype(str).map(counts)
ax = axes[1]
for (c, n), col, mark in zip(CLASSES, COLORS, MARKERS):
    a = cov[cov.classe == c].groupby("month").valid_fraction.median()
    ax.plot(a.index, a, color=col, marker=mark, ms=3.3, lw=1.0, mec="white", mew=0.3, label=n)
a = cov[cov.classe == 1].assign(available=lambda d: d.state == "selected").groupby("month").available.mean() * 100.0
ax.plot(a.index, a, color="#222222", ls="--", lw=0.85, label="Datas com representante")
ax.set(xlabel="Mês", ylabel="Percentual (%)", xticks=range(1, 13), ylim=(-2, 104))
ax.set_title("(b)", loc="left", fontweight="bold", fontsize=9.5)
ax.grid(axis="y", lw=0.3, alpha=0.25)
ax.legend(fontsize=7.2, loc="lower right", frameon=False)
save(fig, "figura_S1_classificacao_disponibilidade")


# ---------------------------------------------------------------------------
# Figura 5: Sensibilidade de F_S e F_T às nove janelas sazonais por domínio
# ---------------------------------------------------------------------------
dom = metrics.groupby(["domain", "window", "classe"])[["FS", "FT"]].median().reset_index()
fig, axes = plt.subplots(2, 4, figsize=(8.4, 4.05), sharex=True, sharey="row", layout="constrained")
y_labels = {"FS": r"Mediana de $F_S$", "FT": r"Mediana de $F_T$"}

for row, metric in enumerate(["FS", "FT"]):
    lo_value, hi_value = float(dom[metric].min()), float(dom[metric].max())
    pad = max((hi_value - lo_value) * 0.07, 0.003)
    for col_idx, (ax, domain) in enumerate(zip(axes[row], ["VIS", "RE", "NIR", "SWIR"])):
        for (c, name), color, marker in zip(CLASSES, COLORS, MARKERS):
            g = dom[(dom.classe == c) & (dom.domain == domain)].sort_values("window")
            ax.plot(
                g.window, g[metric], color=color, marker=marker,
                ms=3.4, lw=1.0, mec="white", mew=0.35, label=name
            )
        ax.set(
            title=domain if row == 0 else None,
            ylim=(max(0.0, lo_value - pad) if metric == "FT" else lo_value - pad, hi_value + pad),
            xlim=(5.5, 36.5),
            xticks=[7, 15, 21, 25, 31, 35],
        )
        if row == 0:
            ax.title.set_fontweight("bold")
        ax.xaxis.set_minor_locator(FixedLocator([9, 11, 13]))
        ax.tick_params(axis="x", which="major", labelsize=7.5)
        ax.tick_params(axis="x", which="minor", length=2.2)
        ax.tick_params(axis="y", labelsize=7.8)
        ax.yaxis.set_major_locator(MaxNLocator(4))
        ax.yaxis.set_major_formatter(pt_formatter(2))
        ax.grid(axis="y", lw=0.32, alpha=0.30)
    axes[row, 0].set_ylabel(y_labels[metric])

fig.supxlabel("Janela sazonal", fontsize=9)
handles = [
    Line2D([], [], color=c, marker=m, ms=4.5, mec="white", mew=0.35, lw=1.1, label=n)
    for (_, n), c, m in zip(CLASSES, COLORS, MARKERS)
]
fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, -0.065), ncol=3, fontsize=8.0, frameon=False)
save(fig, "figura_5_sensibilidade")

(OUT / "proveniencia.json").write_text(
    json.dumps({
        "analysis_id": reps.analysis_id.iloc[0],
        "seed": 13,
        "n_representatives": len(reps),
        "violin_n_per_class": 173,
        "complete_STL_panels": 90,
        "global_component_limits": [lo, hi],
    }, indent=2),
    encoding="utf8",
)
print("Figures 3-5, S1 and S2 regenerated; 30 distributions; 90 supplementary STL panels.")
