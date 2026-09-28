"""图表统一样式（与 08_analysis.py 保持一致）。"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

from common import FIG_DIR

# 配色：白底 + 玫红（#E1006C，主色）+ 95 度黑（#161418）；与 PPT（ppt/deck_kit.js）、看板一致
INK, INK2, MUTED, GRID, AXIS, SURFACE = "#161418", "#4a454d", "#8a848d", "#ece8ec", "#cdc7cf", "#ffffff"
PINK, PINK2, PINK_DARK, DARK = "#e1006c", "#f08cb8", "#8c0044", "#161418"   # 主色、浅玫红、深玫红、强调黑
AMBER = "#e8a317"
GRAY = "#cdc7cf"
WARN, CRIT = AMBER, PINK          # 状态色：需关注 = 琥珀，高风险 = 玫红（与 PPT、看板相同）
PCT = PercentFormatter(1.0, decimals=0)
PCT1 = PercentFormatter(1.0, decimals=1)
# 数据标签的写法与 docs/00_术语与口径.md 第 5 节一致
QC = lambda v: f"{v * 100:.2f}%"          # 品质客诉率与结果指标（假货客诉率除外）
SHARE = lambda v: f"{v * 100:.1f}%"       # 其他比率与占比
FAKE = lambda v: f"{v * 1e4:.1f} 单/万单"  # 假货客诉率


def month_labels(months):
    """'2017-01' → 每年第一个月写成 '01\\n2017'，其余只写月份。"""
    out, prev = [], None
    for m in months:
        y, mm = m[:4], m[5:7]
        out.append(f"{mm}\n{y}" if y != prev else mm)
        prev = y
    return out

plt.rcParams.update({
    "font.family": "Noto Sans CJK SC", "font.size": 11,
    "axes.edgecolor": AXIS, "axes.linewidth": 0.8, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
    "xtick.color": MUTED, "ytick.color": MUTED, "xtick.labelcolor": INK2, "ytick.labelcolor": INK2,
    "axes.labelcolor": INK2, "text.color": INK, "axes.titlesize": 11, "axes.titleweight": "bold",
    "axes.titlelocation": "left", "axes.titlecolor": INK,
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "legend.frameon": False, "legend.fontsize": 10,
})


def save(fig, name):
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_DIR / f"{name}.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  图 → outputs/figures/{name}.png")
