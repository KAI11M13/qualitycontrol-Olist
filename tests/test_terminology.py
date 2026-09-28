"""术语一致性检查：所有产出（文档、PPT、报告、看板、表格、脚本里的图表文字）都不得出现
docs/00_术语与口径.md 第 6 节列出的"不再使用的叫法"，也不出现面向具体公司或岗位的表述。

直接运行 `python tests/test_terminology.py` 可列出全部命中位置。
"""
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# (规则名, 正则, 应改为)
BANNED = [
    ("北极星", r"北极星", "核心指标"),
    ("护栏指标", r"护栏指标", "体验指标"),
    ("签收单", r"签收单|已签收订单", "签收订单"),
    ("客诉单", r"客诉单|品质投诉", "品质客诉订单"),
    ("假货投诉", r"假货投诉", "假货客诉率"),
    ("少件/漏发", r"少件\s*/\s*漏发", "少件漏发"),
    ("准时率", r"准时率", "准时签收率"),
    # "客诉率"前面必须是 品质 / 假货 / 质量缺陷 / 货不对板 / 少件漏发 / 包装破损 之一
    ("不带前缀的客诉率", r"(?<![质货陷板发损])客诉率", "品质客诉率 / 平滑品质客诉率 / 某标签客诉率"),
    ("平台均值", r"平台均值", "商家基准品质客诉率 / 品质客诉率"),
    # "客诉"必须带前缀（品质 / 某标签），"客诉记录"指外部的客服记录
    ("不带前缀的客诉", r"(?<![质发陷板货损])客诉(?!率|订单|记录)|(?<![质发陷板货损])客诉订单", "品质客诉订单 / 某标签客诉订单"),
    ("准确率", r"准确率", "标签精确率"),
    ("金标准", r"金标准|盲评", "标注样本"),
    ("一单一评", r"一单一评", "只取最后一次评价"),
    ("投诉", r"投诉", "客诉（品质客诉订单 / 品质客诉率 / 某标签客诉率）"),
    ("签收量", r"签收量", "签收订单数"),
    ("风险分层", r"风险分层|风险等级", "商家分层"),
    ("平台基准", r"平台基准|平台品质客诉率|平台客诉", "商家基准品质客诉率 / 品质客诉率"),
    ("发生率", r"发生率", "某标签客诉率"),
    ("UCL/LCL", r"(?<![A-Za-z])[UL]CL(?![A-Za-z])", "上控制限 / 下控制限"),
    # 面向具体公司或岗位的表述：唯品会只允许作为"穿戴类占比 75%"的数据出处出现
    ("JD", r"(?<![A-Za-z])JD(?![A-Za-z])", "删除"),
    ("公司名", r"唯品会(?!\s*2024\s*年财报)|(?i:vipshop|vip_qc)", "删除（仅保留数据出处：唯品会 2024 年财报）"),
    ("岗位表述", r"应聘|岗位职责|入职", "删除"),
]
PATTERNS = [(name, re.compile(p), fix) for name, p, fix in BANNED]

TEXT_SUFFIXES = {".md", ".tpl", ".py", ".js", ".html", ".sql", ".hql", ".yml", ".sh", ".csv", ".json"}
SKIP_DIRS = {"node_modules", "vendor", ".git", ".spark", "__pycache__", "data", "metastore_db", "spark-warehouse"}
SKIP_FILES = {Path("tests/test_terminology.py")}
GLOSSARY = Path("docs/00_术语与口径.md")


def _text_files():
    for p in sorted(ROOT.rglob("*")):
        rel = p.relative_to(ROOT)
        if not p.is_file() or rel in SKIP_FILES or any(part in SKIP_DIRS for part in rel.parts):
            continue
        if p.suffix in TEXT_SUFFIXES:
            yield rel


def _office_files():
    for pattern in ("ppt/*.pptx", "report/*.docx", "docs/*.xlsx", "outputs/*.xlsx"):
        yield from (p.relative_to(ROOT) for p in sorted(ROOT.glob(pattern)))


def _lines(rel):
    """返回 (位置, 文本) 列表。Office 文件按 XML 部件取出文字。"""
    path = ROOT / rel
    if path.suffix in {".pptx", ".docx", ".xlsx"}:
        out = []
        with zipfile.ZipFile(path) as z:
            for name in sorted(z.namelist()):
                if not name.endswith(".xml") or "theme" in name:
                    continue
                xml = z.read(name).decode("utf-8", "ignore")
                text = "".join(re.findall(r"<(?:a:t|w:t|t)(?:\s[^>]*)?>([^<]*)</(?:a:t|w:t|t)>", xml))
                text += " ".join(re.findall(r'\b(?:name|descr|title)="([^"]*)"', xml))
                if text:
                    out.append((name, text))
        return out
    text = path.read_text(encoding="utf-8", errors="ignore")
    if path.suffix == ".json":  # JSON 里的中文是 \uXXXX 转义
        try:
            text = json.dumps(json.loads(text), ensure_ascii=False, indent=0)
        except ValueError:
            pass
    lines = text.splitlines()
    if rel == GLOSSARY:  # 术语表第 6 节就是"不再使用的叫法"清单本身
        cut = next((i for i, ln in enumerate(lines) if ln.startswith("## 6.")), len(lines))
        lines = lines[:cut]
    return [(f"L{i + 1}", ln) for i, ln in enumerate(lines)]


def find_hits():
    hits = []
    for rel in list(_text_files()) + list(_office_files()):
        for loc, line in _lines(rel):
            for name, pat, fix in PATTERNS:
                for m in pat.finditer(line):
                    s = max(0, m.start() - 15)
                    hits.append((str(rel), loc, name, fix, line[s:m.end() + 15].strip()))
    return hits


def test_no_banned_terms():
    hits = find_hits()
    msg = "\n".join(f"{f}:{loc}  [{name} → {fix}]  …{ctx}…" for f, loc, name, fix, ctx in hits[:60])
    assert not hits, f"发现 {len(hits)} 处不再使用的叫法（前 60 处）：\n{msg}"


if __name__ == "__main__":
    from collections import Counter

    hits = find_hits()
    for f, loc, name, fix, ctx in hits:
        print(f"{f}:{loc}  [{name}]  …{ctx}…")
    print("\n按文件：", Counter(h[0] for h in hits).most_common())
    print("按规则：", Counter(h[2] for h in hits).most_common())
    print("合计", len(hits))
