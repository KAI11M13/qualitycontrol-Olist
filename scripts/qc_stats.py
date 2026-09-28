"""比率类指标的统计检验（13_advanced_analysis.py 使用，tests/test_qc_stats.py 覆盖）。"""
import numpy as np
from scipy import stats


def ztest(x1, n1, x2, n2):
    """两比例 z 检验（合并比例算标准误）。返回 (z, 双侧 p)，z > 0 表示第二组比例更高。"""
    p = (x1 + x2) / (n1 + n2)
    z = (x2 / n2 - x1 / n1) / np.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    return float(z), float(2 * (1 - stats.norm.cdf(abs(z))))


def wilson(x, n, z=1.96):
    """比例的 Wilson 置信区间；小样本、比例接近 0 时比正态近似可靠。n = 0 时返回 (nan, nan)。"""
    if n == 0:
        return (np.nan, np.nan)
    p = x / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h
