"""一键重跑：ODS 入库 → DWD → 标签识别 → 订单宽表 → DWS → ADS → 数据质量校验
            → 专题分析 → 指标字典 → 看板导出 → SQL 题库实跑 → 笔试模拟卷 → Hive 版对账
            → 进阶分析（控制图 / 检验 / 回测 / 情景 / 抽检） → 标注样本评估 → Excel 月报模板 → PPT/报告数据。"""
import importlib
import time

from common import SQL_DIR, run_sql_file

STEPS = [
    ("ODS 入库", lambda: importlib.import_module("01_load_ods").main()),
    ("DWD 明细层", lambda: run_sql_file(SQL_DIR / "02_dwd.sql")),
    ("评价文字标签识别", lambda: importlib.import_module("03_tag_reviews").main()),
    ("DWD 订单宽表", lambda: run_sql_file(SQL_DIR / "04_dwd_qc_wide.sql")),
    ("DWS 汇总层", lambda: run_sql_file(SQL_DIR / "05_dws.sql")),
    ("ADS 应用层", lambda: run_sql_file(SQL_DIR / "06_ads.sql")),
    ("数据质量校验", lambda: importlib.import_module("07_data_quality_check").main()),
    ("专题分析出图", lambda: importlib.import_module("08_analysis")),
    ("指标字典", lambda: _run_main("09_metric_dictionary")),
    ("看板数据导出", lambda: importlib.import_module("10_export_dashboard").main()),
    ("SQL 面试题库实跑", lambda: importlib.import_module("11_build_interview").main()),
    ("SQL 笔试模拟卷实跑", lambda: _run_main("17_mock_exam")),
    ("Hive / Spark SQL 版与 MySQL 对账（需要 Java 17+ 与 pyspark，未安装 pyspark 时跳过）", lambda: _run_main("16_hive_sql")),
    ("进阶分析：控制图 / 显著性 / 回测 / 情景 / 差异化抽检", lambda: _run_main("13_advanced_analysis")),
    ("标注样本评估（标签精确率 + 标签召回率）", lambda: _run_main("14_tag_gold_eval")),
    ("Excel 商家品质月报模板（需要 LibreOffice）", lambda: _run_main("15_excel_template")),
    ("PPT / 报告数据导出", lambda: _run_main("12_deck_data")),
]
# PPT 与 Word 报告由 Node 生成：cd ppt && npm install && node build_deck.js；cd report && npm install && node build_report.js


def _run_main(mod):
    import runpy
    runpy.run_module(mod, run_name="__main__")

if __name__ == "__main__":
    t0 = time.time()
    for i, (name, fn) in enumerate(STEPS, 1):
        print(f"\n===== [{i}/{len(STEPS)}] {name} =====")
        fn()
    print(f"\n全部完成，用时 {time.time() - t0:.0f}s")
