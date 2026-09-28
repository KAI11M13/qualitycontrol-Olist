#!/usr/bin/env bash
# 容器入口：单元测试 → 全流程 → PPT / 讲稿 / Word 报告 → 术语检查
set -euo pipefail
cd /app
python3 -m pytest
python3 scripts/run_pipeline.py
(cd ppt && node build_deck.js && node build_deck_short.js && node build_talk.js)
(cd report && node build_report.js)
python3 -m pytest tests/test_terminology.py   # 术语检查：扫描重新生成的全部产出
echo "完成：dashboard/index.html、ppt/*.pptx、report/*.docx、docs/ 已按最新数据重新生成"
