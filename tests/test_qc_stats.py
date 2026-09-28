"""统计检验函数的单元测试（与教科书数值对照）。"""
import math

import pytest

from qc_stats import wilson, ztest


def test_wilson_matches_reference_values():
    lo, hi = wilson(10, 100)                 # 常见参考值：10/100 的 95% Wilson 区间 ≈ [5.52%, 17.44%]
    assert lo == pytest.approx(0.0552, abs=1e-4)
    assert hi == pytest.approx(0.1744, abs=1e-4)


def test_wilson_handles_zero_successes_and_empty_groups():
    lo, hi = wilson(0, 20)
    assert lo == pytest.approx(0.0, abs=1e-12) and 0 < hi < 0.2   # 不会像正态近似那样给出 [0, 0]
    assert all(math.isnan(v) for v in wilson(0, 0))


def test_wilson_interval_contains_point_estimate_and_narrows_with_n():
    for x, n in [(3, 30), (30, 300), (300, 3000)]:
        lo, hi = wilson(x, n)
        assert lo < x / n < hi
    assert (wilson(300, 3000)[1] - wilson(300, 3000)[0]) < (wilson(3, 30)[1] - wilson(3, 30)[0])


def test_ztest_reference_and_symmetry():
    z, p = ztest(100, 1000, 130, 1000)       # 10% vs 13%：合并比例 11.5%，SE = √(0.115×0.885×2/1000) ≈ 0.01427，z ≈ 2.103
    assert z == pytest.approx(0.03 / (0.115 * 0.885 * 2 / 1000) ** 0.5)
    assert z == pytest.approx(2.103, abs=1e-3)
    assert p == pytest.approx(0.0355, abs=1e-3)
    z2, p2 = ztest(130, 1000, 100, 1000)
    assert z2 == pytest.approx(-z) and p2 == pytest.approx(p)


def test_ztest_equal_rates_is_not_significant():
    z, p = ztest(50, 1000, 50, 1000)
    assert z == 0 and p == pytest.approx(1.0)
