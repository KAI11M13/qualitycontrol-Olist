"""标签识别规则回归测试：用标注样本（outputs/qa/tag_gold_set.csv，200 条，含中文释义）检查标签精确率和标签召回率不下降。

注意：这 200 条同时是规则 v1.1 的开发集，迭代规则后需要另抽测试集评估（见 scripts/14_tag_gold_eval.py）。
"""
import csv
from pathlib import Path

import pytest

from complaint_rules import QUALITY_TAGS, tag_text

GOLD = Path(__file__).resolve().parents[1] / "outputs" / "qa" / "tag_gold_set.csv"


@pytest.fixture(scope="module")
def gold_rows():
    with GOLD.open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 200
    return rows


def test_rules_reproduce_the_warehouse_tags(gold_rows):
    """规则代码与数仓里的打标结果一致（没有人改了规则却没重跑流程）。"""
    diff = [r["order_id"] for r in gold_rows
            if [tag_text(r["评价原文（葡语）"])[k] for k in QUALITY_TAGS] != [int(r[f"tag_{k}"]) for k in QUALITY_TAGS]]
    assert diff == []


def test_precision_and_recall_do_not_regress(gold_rows):
    tp = fp = fn = 0
    for r in gold_rows:
        gold = r["标注标签"] != ""
        pred = any(tag_text(r["评价原文（葡语）"])[k] for k in QUALITY_TAGS)
        tp += gold and pred
        fp += (not gold) and pred
        fn += gold and not pred
    precision, recall = tp / (tp + fp), tp / (tp + fn)
    assert precision >= 0.95, f"标签精确率下降到 {precision:.1%}"
    assert recall >= 0.74, f"标签召回率下降到 {recall:.1%}"
