"""Hive 版与 MySQL 版结果对账函数的单元测试（scripts/16_hive_sql.py）。"""
import importlib

import pandas as pd

hive = importlib.import_module("16_hive_sql")


def frame(rows):
    return pd.DataFrame(rows, columns=["month", "qc_cnt", "qc_rate"])


def test_same_rows_in_different_order_reconcile():
    a = frame([["2018-01", 10, 0.05], ["2018-02", 12, 0.06]])
    b = frame([["2018-02", 12, 0.06], ["2018-01", 10, 0.05]])
    ok, note = hive.reconcile(a, b, tol=0)
    assert ok, note


def test_numeric_difference_within_tolerance_passes_and_beyond_fails():
    a = frame([["2018-01", 10, 0.0500]])
    assert hive.reconcile(a, frame([["2018-01", 10, 0.0501]]), tol=1e-4)[0]
    assert not hive.reconcile(a, frame([["2018-01", 10, 0.0503]]), tol=1e-4)[0]


def test_row_count_and_column_mismatch_fail():
    a = frame([["2018-01", 10, 0.05]])
    assert not hive.reconcile(a, frame([["2018-01", 10, 0.05], ["2018-02", 1, 0.01]]), tol=0)[0]
    assert not hive.reconcile(a, a.rename(columns={"qc_rate": "rate"}), tol=0)[0]


def test_dates_and_strings_compare_as_text():
    a = pd.DataFrame({"d": ["2018-06-05"], "n": [3]})
    b = pd.DataFrame({"d": [pd.Timestamp("2018-06-05").date()], "n": [3]})
    assert hive.reconcile(a, b, tol=0)[0]


def test_statement_splitter_handles_trailing_comments():
    sts = hive.statements("USE x;\nSELECT 1; -- 注释\n-- 整行注释\nSELECT 2;\n")
    assert sts == ["USE x", "SELECT 1", "SELECT 2"]
