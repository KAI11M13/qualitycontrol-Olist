"""Step 14：用标注样本评估标签识别规则：标签精确率与标签召回率。

之前的 140 条复核是"按规则结果分层抽样"，只能评估精确率（判为品质问题的准不准），评估不了召回率（漏了多少）。
标注样本从全部"签收订单、最后一次评价 1-3 星、有文字"的评价中随机抽 200 条，判定时不看规则结果，与规则结果对比得到：
  标签精确率 = 规则判为品质问题、且标注样本也判为品质问题的评价数 ÷ 规则判为品质问题的评价数
  标签召回率 = 规则判为品质问题、且标注样本也判为品质问题的评价数 ÷ 标注样本判为品质问题的评价数
并据此估算"真实"品质客诉率的区间，检验结论对打标误差是否敏感。
输出：outputs/qa/tag_gold_set.csv（含中文释义，供人工抽查）、outputs/qa/tag_gold_eval.json
"""
import json

import numpy as np
import pandas as pd

from common import OUT_DIR, query
from gold_labels import GOLD

SEED = 20260926
TYPES = [("F", "fake", "假货"), ("D", "defect", "质量缺陷"), ("M", "mismatch", "货不对板"),
         ("S", "missing", "少件漏发"), ("P", "package", "包装破损")]

pop = query("""
    SELECT q.order_id, r.review_score, CONCAT_WS(' | ', r.review_comment_title, r.review_comment_message) AS txt
    FROM dwd_qc_order q JOIN dwd_review r ON r.order_id = q.order_id
    WHERE q.in_scope = 1 AND q.is_delivered = 1 AND r.review_score <= 3 AND r.has_comment = 1""")
# 样本当初用 pop.sample(200, random_state=SEED) 抽出；标签按 order_id 保存，这里按 order_id 取回，不依赖查询的行顺序
s = pop[pop.order_id.isin(GOLD)].copy()
s["_pos"] = s.order_id.map({k: i for i, k in enumerate(GOLD)})
s = s.sort_values("_pos").drop(columns="_pos").reset_index(drop=True)
assert len(GOLD) == len(s) == 200, f"标注样本应为 200 条，实际在总体中找到 {len(s)} 条"
s["gold"] = s.order_id.map(lambda k: GOLD[k][0])
s["中文释义"] = s.order_id.map(lambda k: GOLD[k][1])

rule = query("""SELECT t.order_id, t.tag_fake, t.tag_defect, t.tag_mismatch, t.tag_missing, t.tag_package
                FROM dwd_review_tag t""")
s = s.merge(rule, on="order_id", how="left")
for code, key, _ in TYPES:
    s[f"g_{key}"] = s.gold.str.contains(code).astype(int)
s["g_any"] = (s.gold != "").astype(int)
s["r_any"] = (s[[f"tag_{k}" for _, k, _ in TYPES]].sum(axis=1) > 0).astype(int)


def prf(g, r):
    tp = int(((g == 1) & (r == 1)).sum())
    fp = int(((g == 0) & (r == 1)).sum())
    fn = int(((g == 1) & (r == 0)).sum())
    p = tp / (tp + fp) if tp + fp else np.nan
    rc = tp / (tp + fn) if tp + fn else np.nan
    f1 = 2 * p * rc / (p + rc) if p and rc else np.nan
    return {"support": int(g.sum()), "predicted": int(r.sum()), "tp": tp, "fp": fp, "fn": fn,
            "precision": p, "recall": rc, "f1": f1}


res = {"sample": 200, "population": int(len(pop)), "seed": SEED,
       "any": prf(s.g_any, s.r_any),
       "by_type": {name: prf(s[f"g_{k}"], s[f"tag_{k}"]) for _, k, name in TYPES}}

# 按下单年份看标签召回率是否稳定（稳定则两年对比不受漏标影响）
yr = query("SELECT order_id, LEFT(purchase_month, 4) y FROM dwd_qc_order")
s = s.merge(yr, on="order_id", how="left")
res["by_year"] = {y: prf(g.g_any, g.r_any) for y, g in s.groupby("y")}

# 真实品质客诉率估算：规则值 × 标签精确率 ÷ 标签召回率（两者都在样本上估计，这里给出点估计）
a = res["any"]
res["correction_factor"] = a["precision"] / a["recall"]
res["note"] = ("品质客诉率的真实值 ≈ 规则值 × 标签精确率 ÷ 标签召回率；只要这个比例在 2017 年和 2018 年之间稳定，"
               "两年对比与结构性结论就不受影响")

# 漏标与误标明细，便于迭代规则
s["判定"] = np.select([(s.g_any == 1) & (s.r_any == 1), (s.g_any == 0) & (s.r_any == 1), (s.g_any == 1) & (s.r_any == 0)],
                    ["命中", "误标", "漏标"], default="正确排除")
out = s[["order_id", "review_score", "txt", "中文释义", "gold", "tag_fake", "tag_defect", "tag_mismatch", "tag_missing",
         "tag_package", "判定"]].rename(columns={"txt": "评价原文（葡语）", "gold": "标注标签"})
(OUT_DIR / "qa").mkdir(exist_ok=True)
out.to_csv(OUT_DIR / "qa" / "tag_gold_set.csv", index=False, encoding="utf-8-sig")
res["misses"] = s[s["判定"] == "漏标"][["中文释义", "gold"]].values.tolist()
res["false_pos"] = s[s["判定"] == "误标"][["中文释义"]].values.ravel().tolist()


def clean(o):
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()}
    if isinstance(o, list):
        return [clean(v) for v in o]
    if isinstance(o, float):
        return None if np.isnan(o) else round(o, 4)
    return o


(OUT_DIR / "qa" / "tag_gold_eval.json").write_text(json.dumps(clean(res), ensure_ascii=False, indent=1), encoding="utf-8")
print(f"整体：标签精确率 {a['precision']:.1%}  标签召回率 {a['recall']:.1%}  F1 {a['f1']:.1%}  （标注样本中的品质问题 {a['support']} 条）")
for name, v in res["by_type"].items():
    print(f"  {name:<6} 支持 {v['support']:>3}  标签精确率 {v['precision'] if v['precision'] == v['precision'] else float('nan'):.0%}  标签召回率 {v['recall'] if v['recall'] == v['recall'] else float('nan'):.0%}")
print("漏标：", res["misses"])
print("误标：", res["false_pos"])
