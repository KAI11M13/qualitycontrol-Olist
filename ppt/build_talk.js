// 生成面试讲稿：node ppt/build_talk.js → docs/10_面试讲稿.md（内容来自 talk_track.js，数字来自 outputs/deck_data.json）
const path = require("path");
const fs = require("fs");
const { talkTrack, spoken } = require("./talk_track");

const ROOT = path.resolve(__dirname, "..");
const D = JSON.parse(fs.readFileSync(path.join(ROOT, "outputs", "deck_data.json"), "utf8"));
const { core, sections, numbers } = talkTrack(D);
const ORDER = ["一", "二", "三", "四", "五", "六"];
const chars = t => t.replace(/[\s，。；：、（）"「」\-—→×÷=<>]/g, "").length;
const total = sections.reduce((a, s) => a + chars(spoken(s)), 0);
const short = sections.reduce((a, s) => a + chars(s.conclusion), 0);
const mins = c => Math.round(c / 270 * 10) / 10;   // 按每分钟 270 字估算

const L = [
  "# 10 面试讲稿",
  "",
  "> - 术语与数字格式以 [00_术语与口径.md](00_术语与口径.md) 为准：一个概念只有一个名称，一个名称只有一个定义。",
  "> - 每一部分的结构相同：**关键术语 → 结论 → 依据 → 动作**。先用一个术语概括这部分，再说结论，再给数字，最后说要做什么。",
  "> - 所有数字由 `ppt/talk_track.js` 从数据生成，与 PPT、报告完全一致；每个数字的定义见文末\"数字说明\"。",
  "> - 精简版 PPT 每一页的备注就是对应部分的讲稿（第几页见各部分标题）。",
  `> - 两个版本：1 分钟版只讲六部分的结论（约 ${short} 字，${mins(short)} 分钟）；5 分钟版讲全部内容（约 ${total} 字，${mins(total)} 分钟），配合精简版 PPT。`,
  "",
  "## 核心概念",
  "",
  `**${core.term}**：${core.def}。`,
  "",
  "```",
  core.formula,
  "```",
  "",
  "逐层拆解见 [00_术语与口径.md 第 2 节](00_术语与口径.md#2-核心概念拆解逐层拆到不能再拆的词元)。",
  "",
  "## 1 分钟版（只讲每部分的结论）",
  "",
  ...sections.map((s, i) => `${i + 1}. **${s.name}**：${s.conclusion}`),
  "",
  "## 5 分钟版",
  "",
];
sections.forEach((s, i) => {
  L.push(`### ${ORDER[i]}、${s.name}（精简版 PPT 第 ${s.slide} 页）`, "",
    `**关键术语**：${s.term[0]}——${s.term[1]}。`, "",
    `**结论**：${s.conclusion}`, "",
    "**依据**：", "", ...s.evidence.map(e => `- ${e}`), "",
    `**动作**：${s.action}`, "");
});
L.push("## 数字说明", "", "讲稿中出现的每个数字，按出现顺序列出；同一个数字属于同一指标时只列一次。", "",
  "| 数字 | 指标 | 定义与范围 |", "|---|---|---|",
  ...numbers.map(x => `| ${x.text} | ${x.metric} | ${x.def} |`), "");
fs.writeFileSync(path.join(ROOT, "docs", "10_面试讲稿.md"), L.join("\n"), "utf8");
console.log(`写入 docs/10_面试讲稿.md（${sections.length} 部分，${numbers.length} 个数字，正文约 ${total} 字）`);
