# 电商品控数据分析项目：差评率在下降，品质客诉率在上升

用 Olist 巴西电商平台公开的真实订单数据，搭建以**品质客诉率**为核心指标的品控分析，包括四个模块：指标体系、经营看板、专题分析、SQL 取数。

> **品质客诉率** = 品质客诉订单数 ÷ 签收订单数（分子、分母按同一下单月归属）；品质客诉订单 = 签收订单中，最后一次评价为 1-3 星、且评价文字命中至少一个品质问题标签（假货、质量缺陷、货不对板、少件漏发、包装破损）的订单。全部术语、定义和数字格式见 [docs/00_术语与口径.md](docs/00_术语与口径.md)：一个概念只有一个名称，一个名称只有一个定义。

![看板总览](docs/images/dashboard_overview_top.png)

## 核心结论

- **结论**：差评率在下降，品质客诉率在上升，而且是持续偏移。品质客诉率从 2017 年的 4.31% 升到 2018 年 1-8 月的 5.00%（两比例 z 检验 z = 5.05，p < 0.0001），控制图上 2017-10 至 2018-08 连续 11 个月高于中心线；差评率随准时签收率变化：下单月 2018-03 准时签收率 81.0%、差评率 22.8%，2018-08 为 93.8% 和 10.9%。
- **原因**：上升来自组内效应（+0.74pp），结构效应只有 −0.01pp；差评品质原因占比从 2017Q1 的 21.9% 升到 2018Q3 的 35.2%。
- **问题**：多件订单占签收订单 10.0%，贡献 33.6% 的品质客诉订单；10 家高风险商家贡献 12.5% 的商家品质客诉订单，回测中下一个 6 个月仍是商家基准品质客诉率的 2.2 倍；假货集中在电脑配件（66.2 单/万单）和钟表礼品（53.0 单/万单）。
- **举措**：多件订单出库复核、高风险商家和需关注商家整改、一级类目 3C数码、钟表与潮流好物的正品与商品描述专项，中性情景下把品质客诉率从 5.00% 降到 3.82%（悲观 4.32%，乐观 3.34%）。
- **可信度**：18 项数据校验全部通过；标注样本 200 条，标签精确率 97.4%、标签召回率 74.5%，2017 年与 2018 年标签召回率相近，上升趋势不会被高估。

## 交付物

| 模块 | 交付物 | 位置 |
|---|---|---|
| 术语与口径 | 核心概念拆解、四层指标、全部术语定义、数字格式、不再使用的叫法；自动检查所有产出 | [00_术语与口径.md](docs/00_术语与口径.md) · [tests/test_terminology.py](tests/test_terminology.py) |
| ① 指标体系 | 31 个指标（核心指标、结果指标、体验指标、过程指标四层）、六条口径规则、口径变更记录；基准值由口径 SQL 实际运行得到 | [指标体系说明](docs/02_指标体系.md) · [指标字典.xlsx](docs/品控指标字典.xlsx) |
| ② 经营看板 | 3 页交互看板（经营总览 / 商家分层 / 指标口径）：第一屏有控制图和预警清单；Power BI、Tableau、SmartBI 搭建指南；Tableau Public 逐步搭建清单 | [dashboard/index.html](dashboard/index.html)（本地双击打开）· [搭建指南](docs/04_BI看板设计与搭建指南.md) · [Tableau Public 清单](docs/07_Tableau_Public搭建清单.md) · [BI 导入数据](dashboard/bi_data/) |
| Excel 报表 | 商家品质月报模板：改参数页的月份和阈值，SUMIFS / INDEX-MATCH 公式自动重算商家分层，附数据透视表和条件格式；商家分层结果与数仓逐一核对 | [商家品质月报模板.xlsx](docs/商家品质月报模板.xlsx) |
| ③ 专题分析 | 分析报告（Word + Markdown）、25 页完整版 PPT（21 页正文 + 4 页附录）与 6 页精简版；控制图、显著性检验、商家分层回测、三组情景、差异化抽检、品类结构重加权 | [报告.docx](report/品控专题分析报告.docx) · [报告.md](docs/03_专题分析报告.md) · [完整版 PPT](ppt/Olist品控数据分析项目.pptx) · [分析明细](outputs/advanced_tables.xlsx) |
| 外部参考 | 市场监管总局抽查结果、穿戴类 GMV 占比（来自公告、新闻转载与财报报道，附出处） | [data/external/](data/external/) |
| 工程化 | 单元测试（标签规则、标注样本回归、统计检验、Hive 对账、术语检查）；GitHub Actions 每次推送在干净环境里从原始数据重跑全流程；Docker 一键复现 | [tests/](tests/) · [CI 配置](.github/workflows/ci.yml) · [Dockerfile](Dockerfile) |

## 方法概览

```
Olist 原始 CSV（8 张表，行数与官方一致）
   │  scripts/01_load_ods.py
   ▼
ODS 原始数据层 ──► DWD 明细层（只取最后一次评价、时间倒挂标记、主品类 / 主商家归属）
                 │  scripts/03_tag_reviews.py：葡语评价文字 → 8 个标签（标签精确率 97.4%、标签召回率 74.5%）
                 ▼
             dwd_qc_order 订单宽表（每个订单一行，所有指标都从这里计算）
                 ▼
             DWS 商家 × 月 / 品类 × 月（只存订单数）──► ADS 月度核心指标 / 商家品质分与商家分层 / 品类排行 / 看板数据集
                 │  scripts/07_data_quality_check.py：18 项数据校验，全部通过才输出结果
                 ▼
   专题分析（08）· 指标字典（09）· 看板（10）· SQL 题库（11）· 笔试模拟卷（17）· Hive 版对账（16）
   进阶分析（13）· 标注样本评估（14）· Excel 月报模板（15）· PPT / 报告 / 讲稿（12 + Node）
```

## 复现

**方式一：Docker（推荐，本机只需要装 Docker）**

```bash
docker compose up --build     # 启动 MySQL 8.0 → 单元测试 → 全流程 17 步 → 生成 PPT / 报告 / 讲稿，结果写回本目录
```

**方式二：本机运行**

需要 MySQL 8.0、Python 3.10+、Node 18+；生成 Excel 模板的数据透视表需要 LibreOffice（`soffice`）；Hive 版对账需要 Java 17+ 和 `pip install -r requirements-hive.txt`（没装 pyspark 时这一步自动跳过）。

```bash
pip install -r requirements.txt

# MySQL 连接参数通过环境变量设置（默认 localhost:3306，账号 analyst/analyst）
export MYSQL_USER=... MYSQL_PASSWORD=...

python scripts/run_pipeline.py          # 入库 → 数仓 → 标签 → 校验 → 分析 → 字典 → 看板 → 题库 → 笔试卷 → Hive 对账 → 进阶分析 → 标注样本评估 → Excel 模板

cd ppt && npm install && node build_deck.js && node build_deck_short.js && node build_talk.js   # PPT（完整版 + 精简版）与讲稿
cd ../report && npm install && node build_report.js  # Word 报告
cd .. && pytest                         # 单元测试（含术语检查：扫描上面生成的全部产出）
```

原始数据已随仓库提供（`data/raw/*.csv.gz`）；需要重新下载时运行 `python scripts/00_download_data.py`，脚本会校验行数与官方一致。

## 目录结构

```
data/raw/          原始数据（gzip）          data/dim/        品类中文维表（人工整理）
data/external/     外部参考（附出处）
sql/               数仓分层 SQL              sql/interview/   面试库建表与 19 道题答案
sql/hive/          Hive 分区表与 5 道题      sql/exam/        笔试模拟卷答案
scripts/           Python 全流程（00-17）    dashboard/       HTML 看板、BI 导入数据
tests/             单元测试                  docker/          MySQL 初始化脚本
docs/              术语、各模块说明与指标字典  outputs/         分析结果、图表、数据校验报告
ppt/               PPT、讲稿与生成脚本        report/          Word 报告与生成脚本
```

## 关于标注样本，需要说明的一点

标注样本（200 条随机样本）和规则迭代期的 140 条分层样本，逐条判定都是借助大模型（Claude）阅读葡语原文完成的，不是人工逐条标注。每条样本都附了中文释义和判定结果（见 `outputs/qa/`），可以直接人工抽查。判定结果据实使用，不在任何材料里称作"人工复核"。

## 数据来源与声明
- 外部参考数据（`data/external/`）取自公告、新闻转载和财报报道，数字引用前应核对原文。
- 本项目是个人作品，不代表 Olist 或任何公司的观点。
