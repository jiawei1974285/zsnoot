// 知枢 · 数合云智 — 客户汇报 PPT
// 政务/公安风格：深蓝 + 暖金，简洁示意图，无 emoji
const pptxgen = require("pptxgenjs");
const path = require("path");

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9"; // 10 × 5.625
pres.author = "数合云智";
pres.title = "知枢 · 智能警务知识库";
pres.subject = "客户汇报";

// ── 调色板 ──────────────────────────────
const C = {
  navy:    "1E2761", // 主色：政务深蓝
  navyLt:  "2E3F7A",
  slate:   "4A5C7E",
  bg:      "FFFFFF",
  panel:   "F4F6FA",
  border:  "DDE3EC",
  text:    "1F2937",
  muted:   "6B7280",
  gold:    "B8924A", // 强调色：暖金
  green:   "2E7D5C",
  red:     "B0413E",
};
const F = "Microsoft YaHei";

// ── 通用部件 ────────────────────────────
function pageFooter(slide, pageNum) {
  // 左下角细标识
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 5.32, w: 0.16, h: 0.05, fill: { color: C.gold }, line: { color: C.gold }
  });
  slide.addText("知枢 · 数合云智", {
    x: 0.72, y: 5.22, w: 3, h: 0.25,
    fontSize: 9, fontFace: F, color: C.muted, margin: 0
  });
  slide.addText(String(pageNum), {
    x: 9.0, y: 5.22, w: 0.6, h: 0.25,
    fontSize: 9, fontFace: F, color: C.muted, align: "right", margin: 0
  });
}

function sectionTitle(slide, kicker, title) {
  // 顶部细金条
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 0.45, w: 0.32, h: 0.06, fill: { color: C.gold }, line: { color: C.gold }
  });
  // kicker（小标签）
  slide.addText(kicker, {
    x: 0.9, y: 0.36, w: 4, h: 0.28,
    fontSize: 11, fontFace: F, color: C.gold, bold: true, margin: 0,
    charSpacing: 2,
  });
  // 主标题
  slide.addText(title, {
    x: 0.5, y: 0.62, w: 9, h: 0.6,
    fontSize: 26, fontFace: F, color: C.navy, bold: true, margin: 0
  });
}

function makeShadow() {
  return { type: "outer", color: "000000", blur: 8, offset: 2, angle: 90, opacity: 0.08 };
}

// ════════════════════════════════════════
// Slide 1 — 封面
// ════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.navy };
  // 装饰：右下角大色块
  s.addShape(pres.shapes.RECTANGLE, {
    x: 7.5, y: 4.0, w: 2.5, h: 1.625, fill: { color: C.navyLt }, line: { color: C.navyLt }
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.85, w: 0.5, h: 0.08, fill: { color: C.gold }, line: { color: C.gold }
  });
  s.addText("智能警务知识库", {
    x: 0.5, y: 2.0, w: 9, h: 0.5,
    fontSize: 18, fontFace: F, color: "C9D2E5", margin: 0, charSpacing: 6
  });
  s.addText("知枢", {
    x: 0.5, y: 2.55, w: 9, h: 1.1,
    fontSize: 80, fontFace: F, color: "FFFFFF", bold: true, margin: 0
  });
  s.addText("LLM × Wiki  让基层笔记自动沉淀为可串可并的知识网络", {
    x: 0.5, y: 3.7, w: 9, h: 0.4,
    fontSize: 16, fontFace: F, color: "C9D2E5", margin: 0
  });
  s.addText("数合云智 · 客户汇报", {
    x: 0.5, y: 5.0, w: 5, h: 0.3,
    fontSize: 12, fontFace: F, color: "8896B0", margin: 0
  });
}

// ════════════════════════════════════════
// Slide 2 — 目录
// ════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.bg };
  sectionTitle(s, "CONTENTS", "汇报内容");

  const items = [
    ["01", "项目定位", "为什么做、给谁用"],
    ["02", "核心理念", "LLM+Wiki 与 RAG 的本质差异"],
    ["03", "主要功能", "七大模块逐一展示"],
    ["04", "业务场景", "案件 / 资金 / 笔录 三类典型应用"],
    ["05", "未来规划", "本地与云端协同的知识服务"],
  ];

  let y = 1.6;
  items.forEach(([num, title, desc]) => {
    s.addText(num, {
      x: 0.6, y: y, w: 0.9, h: 0.55,
      fontSize: 32, fontFace: F, color: C.gold, bold: true, margin: 0
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: 1.55, y: y + 0.08, w: 0.02, h: 0.45, fill: { color: C.border }, line: { color: C.border }
    });
    s.addText(title, {
      x: 1.75, y: y + 0.02, w: 3, h: 0.32,
      fontSize: 18, fontFace: F, color: C.navy, bold: true, margin: 0
    });
    s.addText(desc, {
      x: 1.75, y: y + 0.32, w: 7, h: 0.28,
      fontSize: 12, fontFace: F, color: C.muted, margin: 0
    });
    y += 0.7;
  });

  pageFooter(s, 2);
}

// ════════════════════════════════════════
// Slide 3 — 项目定位
// ════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.bg };
  sectionTitle(s, "01  项目定位", "轻量级 LLM+Wiki 本地知识库");

  // 大引语
  s.addText("打开即用，像写笔记一样积累知识", {
    x: 0.5, y: 1.5, w: 9, h: 0.6,
    fontSize: 24, fontFace: F, color: C.text, bold: true, margin: 0
  });
  s.addText("面向基层民警的日常工作场景设计，无需复杂部署、无需数据建模训练。", {
    x: 0.5, y: 2.1, w: 9, h: 0.4,
    fontSize: 14, fontFace: F, color: C.muted, margin: 0
  });

  // 三个特性卡
  const cards = [
    ["本地部署", "数据不出本机/不出内网；满足公安数据合规要求"],
    ["零配置上手", "Windows 一键启动；上传材料自动建库；不改变记录习惯"],
    ["越用越聪明", "LLM 把笔记编译成结构化 Wiki；每一次问答都沉淀回知识库"],
  ];
  let x = 0.5;
  cards.forEach(([title, desc]) => {
    s.addShape(pres.shapes.RECTANGLE, {
      x: x, y: 3.2, w: 3.0, h: 1.85,
      fill: { color: C.panel }, line: { color: C.border, width: 0.75 },
      shadow: makeShadow()
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: x, y: 3.2, w: 0.06, h: 1.85, fill: { color: C.gold }, line: { color: C.gold }
    });
    s.addText(title, {
      x: x + 0.25, y: 3.35, w: 2.7, h: 0.4,
      fontSize: 16, fontFace: F, color: C.navy, bold: true, margin: 0
    });
    s.addText(desc, {
      x: x + 0.25, y: 3.85, w: 2.7, h: 1.1,
      fontSize: 12, fontFace: F, color: C.text, margin: 0,
      paraSpaceAfter: 4
    });
    x += 3.17;
  });

  pageFooter(s, 3);
}

// ════════════════════════════════════════
// Slide 4 — 痛点
// ════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.bg };
  sectionTitle(s, "01  项目定位", "我们要解决的痛点");

  const pains = [
    ["散落", "笔记、案卷、巡查记录散落在笔记本、手机、微信群"],
    ["难检索", "想找过去某次记录，只能翻聊天记录或纸质本"],
    ["难关联", "同一人物、同一地点的案件无法自动串并"],
    ["难传承", "老民警的经验技战法停留在个人脑子里"],
  ];

  let x = 0.5, y = 1.55;
  pains.forEach(([title, desc], i) => {
    const col = i % 2;
    const row = Math.floor(i / 2);
    const cx = 0.5 + col * 4.6;
    const cy = 1.55 + row * 1.7;

    s.addShape(pres.shapes.RECTANGLE, {
      x: cx, y: cy, w: 4.4, h: 1.5,
      fill: { color: "FFFFFF" }, line: { color: C.border, width: 0.75 },
      shadow: makeShadow()
    });
    s.addText(title, {
      x: cx + 0.3, y: cy + 0.18, w: 1.5, h: 0.45,
      fontSize: 22, fontFace: F, color: C.navy, bold: true, margin: 0
    });
    s.addShape(pres.shapes.LINE, {
      x: cx + 0.3, y: cy + 0.7, w: 0.4, h: 0,
      line: { color: C.gold, width: 1.5 }
    });
    s.addText(desc, {
      x: cx + 0.3, y: cy + 0.78, w: 3.9, h: 0.65,
      fontSize: 13, fontFace: F, color: C.text, margin: 0
    });
  });

  pageFooter(s, 4);
}

// ════════════════════════════════════════
// Slide 5 — 什么是 LLM + Wiki（概念图）
// ════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.bg };
  sectionTitle(s, "02  核心理念", "什么是 LLM + Wiki");

  s.addText("把零散输入「编译」成结构化、互链接的知识，而不是临时检索片段", {
    x: 0.5, y: 1.45, w: 9, h: 0.4,
    fontSize: 14, fontFace: F, color: C.muted, margin: 0
  });

  // 流程：输入 → LLM 编译 → Wiki 知识网络 → 查询/分析
  const stepW = 2.0, stepH = 1.4, stepY = 2.1, gap = 0.32;
  const steps = [
    ["材料输入", "笔记 / 文档 / 图片 / 网页", C.slate],
    ["LLM 编译", "抽取实体 + 关系 + 摘要", C.navy],
    ["Wiki 知识网络", "结构化页面 + 双向链接", C.navy],
    ["查询 / 分析", "对话 + 图谱 + 体检", C.gold],
  ];

  let x = 0.5;
  steps.forEach(([t, d, color], i) => {
    s.addShape(pres.shapes.RECTANGLE, {
      x: x, y: stepY, w: stepW, h: stepH,
      fill: { color: i === 1 || i === 2 ? color : "FFFFFF" },
      line: { color: color, width: 1 },
      shadow: makeShadow()
    });
    const fg = (i === 1 || i === 2) ? "FFFFFF" : color;
    s.addText(t, {
      x: x + 0.1, y: stepY + 0.25, w: stepW - 0.2, h: 0.4,
      fontSize: 16, fontFace: F, color: fg, bold: true, align: "center", margin: 0
    });
    s.addText(d, {
      x: x + 0.1, y: stepY + 0.7, w: stepW - 0.2, h: 0.55,
      fontSize: 11, fontFace: F,
      color: (i === 1 || i === 2) ? "C9D2E5" : C.muted,
      align: "center", margin: 0
    });

    if (i < 3) {
      // 箭头
      s.addShape(pres.shapes.RIGHT_TRIANGLE, {
        x: x + stepW + 0.05, y: stepY + stepH/2 - 0.1, w: 0.22, h: 0.22,
        fill: { color: C.gold }, line: { color: C.gold }, rotate: 90
      });
    }
    x += stepW + gap;
  });

  // 底部要点
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 4.0, w: 9, h: 0.95,
    fill: { color: C.panel }, line: { color: C.border, width: 0.5 }
  });
  s.addText("关键差异", {
    x: 0.7, y: 4.1, w: 1.5, h: 0.32,
    fontSize: 12, fontFace: F, color: C.gold, bold: true, margin: 0, charSpacing: 2
  });
  s.addText("知识被 LLM 反复阅读、消化、互联，沉淀为持久结构。用得越久，知识网络越稠密、回答质量越高。", {
    x: 0.7, y: 4.4, w: 8.6, h: 0.5,
    fontSize: 13, fontFace: F, color: C.text, margin: 0
  });

  pageFooter(s, 5);
}

// ════════════════════════════════════════
// Slide 6 — LLM+Wiki vs RAG 对比表
// ════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.bg };
  sectionTitle(s, "02  核心理念", "LLM+Wiki  vs  传统 RAG");

  const headFill = { fill: { color: C.navy }, color: "FFFFFF", bold: true, fontFace: F, fontSize: 13, align: "center", valign: "middle" };
  const cellLeft  = { fill: { color: "FFFFFF" }, color: C.text, fontFace: F, fontSize: 12, valign: "middle" };
  const cellRight = { fill: { color: C.panel }, color: C.text, fontFace: F, fontSize: 12, valign: "middle" };
  const labelCell = { fill: { color: C.panel }, color: C.navy, bold: true, fontFace: F, fontSize: 12, align: "center", valign: "middle" };

  const tableData = [
    [
      { text: "对比维度", options: headFill },
      { text: "传统 RAG", options: { ...headFill, fill: { color: C.slate } } },
      { text: "LLM + Wiki（本项目）", options: headFill },
    ],
    [
      { text: "知识形态",   options: labelCell },
      { text: "原始文档片段，按需检索", options: cellLeft },
      { text: "结构化 Wiki 页 + 双向链接，持续编译", options: cellRight },
    ],
    [
      { text: "积累效应",   options: labelCell },
      { text: "用半年与第一天差不多", options: cellLeft },
      { text: "用得越久，知识网络越稠密", options: cellRight },
    ],
    [
      { text: "关联发现",   options: labelCell },
      { text: "依赖向量相似度，跨案件难发现", options: cellLeft },
      { text: "实体关系图谱，自动串并案", options: cellRight },
    ],
    [
      { text: "可解释性",   options: labelCell },
      { text: "答案来源是片段，难追溯", options: cellLeft },
      { text: "答案来源是 Wiki 页，可追溯", options: cellRight },
    ],
    [
      { text: "维护成本",   options: labelCell },
      { text: "每次查询重算，无沉淀", options: cellLeft },
      { text: "支持体检、纠错、人工干预", options: cellRight },
    ],
  ];

  s.addTable(tableData, {
    x: 0.5, y: 1.45, w: 9, h: 3.5,
    colW: [1.8, 3.4, 3.8],
    rowH: [0.45, 0.55, 0.55, 0.55, 0.55, 0.55],
    border: { type: "solid", pt: 0.5, color: C.border },
  });

  pageFooter(s, 6);
}

// ════════════════════════════════════════
// Slide 7 — 优劣势分析
// ════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.bg };
  sectionTitle(s, "02  核心理念", "优势与代价");

  // 左：优势
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.55, w: 4.4, h: 3.5,
    fill: { color: "FFFFFF" }, line: { color: C.border, width: 0.75 }, shadow: makeShadow()
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.55, w: 4.4, h: 0.45, fill: { color: C.green }, line: { color: C.green }
  });
  s.addText("优势", {
    x: 0.7, y: 1.6, w: 4, h: 0.36,
    fontSize: 14, fontFace: F, color: "FFFFFF", bold: true, margin: 0, charSpacing: 3
  });
  s.addText([
    { text: "知识可积累、可追溯，回答有据可依", options: { bullet: { code: "25A0" }, breakLine: true, color: C.text } },
    { text: "实体关系自动建立，串并案天然支持", options: { bullet: { code: "25A0" }, breakLine: true, color: C.text } },
    { text: "Wiki 兼容 Obsidian，离开系统也能读", options: { bullet: { code: "25A0" }, breakLine: true, color: C.text } },
    { text: "本地部署，数据安全可控", options: { bullet: { code: "25A0" }, breakLine: true, color: C.text } },
    { text: "对历史材料可重新解析、合并补充", options: { bullet: { code: "25A0" }, color: C.text } },
  ], {
    x: 0.75, y: 2.15, w: 4.0, h: 2.8,
    fontSize: 12.5, fontFace: F, paraSpaceAfter: 6
  });

  // 右：代价
  s.addShape(pres.shapes.RECTANGLE, {
    x: 5.1, y: 1.55, w: 4.4, h: 3.5,
    fill: { color: "FFFFFF" }, line: { color: C.border, width: 0.75 }, shadow: makeShadow()
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 5.1, y: 1.55, w: 4.4, h: 0.45, fill: { color: C.gold }, line: { color: C.gold }
  });
  s.addText("代价 / 限制", {
    x: 5.3, y: 1.6, w: 4, h: 0.36,
    fontSize: 14, fontFace: F, color: "FFFFFF", bold: true, margin: 0, charSpacing: 3
  });
  s.addText([
    { text: "首次入库需调用 LLM，比纯 RAG 慢", options: { bullet: { code: "25A0" }, breakLine: true, color: C.text } },
    { text: "依赖 LLM 调用预算，需配置 API 或本地模型", options: { bullet: { code: "25A0" }, breakLine: true, color: C.text } },
    { text: "Wiki 结构需与 schema 配合，初期需熟悉", options: { bullet: { code: "25A0" }, breakLine: true, color: C.text } },
    { text: "极短零散的输入价值不如成段材料明显", options: { bullet: { code: "25A0" }, color: C.text } },
  ], {
    x: 5.35, y: 2.15, w: 4.0, h: 2.8,
    fontSize: 12.5, fontFace: F, paraSpaceAfter: 6
  });

  pageFooter(s, 7);
}

// ════════════════════════════════════════
// Slide 8 — 产品全景（七大模块）
// ════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.bg };
  sectionTitle(s, "03  主要功能", "七大功能模块");

  const mods = [
    ["01", "文件快速导入", "拖入材料自动建库"],
    ["02", "新建笔记 / 网页", "一键提取网页正文"],
    ["03", "对话查询", "自然语言问答"],
    ["04", "Wiki 页面", "结构化知识卡片"],
    ["05", "关系图谱", "可视化串并案线索"],
    ["06", "知识库体检", "断链 / 孤立 / 过期"],
    ["07", "系统配置", "模型 / 目录 / 账号"],
  ];

  // 4列 2行布局，最后一格留给"持续迭代"
  const cw = 2.18, ch = 1.6, gx = 0.07, gy = 0.13;
  const startX = 0.5, startY = 1.55;
  for (let i = 0; i < mods.length; i++) {
    const [n, t, d] = mods[i];
    const col = i % 4;
    const row = Math.floor(i / 4);
    const x = startX + col * (cw + gx);
    const y = startY + row * (ch + gy);

    s.addShape(pres.shapes.RECTANGLE, {
      x, y, w: cw, h: ch,
      fill: { color: "FFFFFF" }, line: { color: C.border, width: 0.75 }, shadow: makeShadow()
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x, y, w: cw, h: 0.06, fill: { color: C.navy }, line: { color: C.navy }
    });
    s.addText(n, {
      x: x + 0.18, y: y + 0.18, w: 0.7, h: 0.3,
      fontSize: 11, fontFace: F, color: C.gold, bold: true, margin: 0, charSpacing: 2
    });
    s.addText(t, {
      x: x + 0.18, y: y + 0.5, w: cw - 0.36, h: 0.4,
      fontSize: 14.5, fontFace: F, color: C.navy, bold: true, margin: 0
    });
    s.addText(d, {
      x: x + 0.18, y: y + 0.95, w: cw - 0.36, h: 0.55,
      fontSize: 11, fontFace: F, color: C.muted, margin: 0
    });
  }

  // 最后一格补一个总结块
  const x = startX + 3 * (cw + gx);
  const y = startY + 1 * (ch + gy);
  s.addShape(pres.shapes.RECTANGLE, {
    x, y, w: cw, h: ch,
    fill: { color: C.navy }, line: { color: C.navy }
  });
  s.addText("整套链路", {
    x: x + 0.18, y: y + 0.3, w: cw - 0.36, h: 0.35,
    fontSize: 14, fontFace: F, color: "FFFFFF", bold: true, margin: 0
  });
  s.addText("从材料到 Wiki，从 Wiki 到关系图谱，再回到对话查询，构成可观测、可干预的知识闭环。", {
    x: x + 0.18, y: y + 0.7, w: cw - 0.36, h: 0.85,
    fontSize: 10.5, fontFace: F, color: "C9D2E5", margin: 0
  });

  pageFooter(s, 8);
}

// ── 模块详情通用模板 ─────────────────────
function moduleSlide(opts) {
  const s = pres.addSlide();
  s.background = { color: C.bg };
  sectionTitle(s, opts.kicker, opts.title);

  // 左侧主描述
  s.addText(opts.lead, {
    x: 0.5, y: 1.5, w: 5.4, h: 0.5,
    fontSize: 14, fontFace: F, color: C.text, bold: true, margin: 0
  });
  // 要点列表
  s.addText(
    opts.bullets.map((b, i) => ({
      text: b,
      options: {
        bullet: { code: "25A0" },
        breakLine: i < opts.bullets.length - 1,
        color: C.text,
      }
    })),
    {
      x: 0.5, y: 2.1, w: 5.4, h: 2.9,
      fontSize: 12.5, fontFace: F, paraSpaceAfter: 8
    }
  );

  // 右侧高亮卡
  s.addShape(pres.shapes.RECTANGLE, {
    x: 6.2, y: 1.5, w: 3.3, h: 3.5,
    fill: { color: C.panel }, line: { color: C.border, width: 0.75 }
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 6.2, y: 1.5, w: 0.06, h: 3.5, fill: { color: C.gold }, line: { color: C.gold }
  });
  s.addText(opts.highlightLabel, {
    x: 6.4, y: 1.65, w: 3, h: 0.3,
    fontSize: 11, fontFace: F, color: C.gold, bold: true, margin: 0, charSpacing: 2
  });
  s.addText(opts.highlightTitle, {
    x: 6.4, y: 1.95, w: 3, h: 0.45,
    fontSize: 17, fontFace: F, color: C.navy, bold: true, margin: 0
  });
  s.addText(opts.highlightBody, {
    x: 6.4, y: 2.5, w: 3, h: 2.4,
    fontSize: 12, fontFace: F, color: C.text, margin: 0, paraSpaceAfter: 6
  });

  pageFooter(s, opts.page);
  return s;
}

// ════════════════════════════════════════
// Slides 9-15 — 七大模块
// ════════════════════════════════════════
moduleSlide({
  kicker: "03  主要功能 · 模块一",
  title:  "文件快速导入",
  lead:   "拖入文件 → LLM 自动解析 → 结构化 Wiki 页面",
  bullets: [
    "支持 Word / PDF / PPT / Excel / 图片 / Markdown / 文本",
    "图片走视觉模型 OCR，无需本地装 Tesseract",
    "按批次入库，可回滚、可二次解析",
    "并发处理，多文件同时入库不阻塞",
    "SHA256 增量缓存：相同文件不重复消耗 LLM",
  ],
  highlightLabel: "EFFICIENCY",
  highlightTitle: "重复入库自动复用",
  highlightBody: "同一份材料被多次上传时，系统自动识别内容指纹，跳过 LLM 调用直接复用既有知识页，演示与日常使用都更稳。",
  page: 9,
});

moduleSlide({
  kicker: "03  主要功能 · 模块二",
  title:  "新建笔记 + 自动解析网页",
  lead:   "随手记一段文字、贴一个网页链接，知识就进了库",
  bullets: [
    "顶部固定笔记入口，无需切换页面",
    "支持标题、正文、URL、标签四类输入",
    "URL 一键提取网页正文（基于 Readability 算法）",
    "保存后进入 LLM 深度解析，抽取实体与关系",
    "新增内容自动与既有 Wiki 合并，建立双向链接",
  ],
  highlightLabel: "WORKFLOW",
  highlightTitle: "贴近巡逻笔记习惯",
  highlightBody: "民警一边走访一边记，回到办公室或在手机上贴个网页，系统自动接住——不改变记录习惯，知识自然沉淀。",
  page: 10,
});

moduleSlide({
  kicker: "03  主要功能 · 模块三",
  title:  "对话查询",
  lead:   "自然语言提问，基于本地知识库回答，可点击溯源",
  bullets: [
    "中文 bigram 分词检索，对警务术语友好",
    "图谱二跳扩展：命中页的关联实体一并入上下文",
    "字符预算可配，单次最多容纳约 10 万字 Wiki 内容",
    "回答附带可点击的 Wiki 来源链接，便于核对",
    "每次问答自动沉淀为 outputs 类知识页，形成复利",
  ],
  highlightLabel: "INSIGHT",
  highlightTitle: "串并案天然支持",
  highlightBody: "提问只命中 A 案的关键词，但 A 案与 B 案通过同一嫌疑人或地点连着——图谱二跳会把 B 案一起拉进上下文，自然形成串并案推理。",
  page: 11,
});

moduleSlide({
  kicker: "03  主要功能 · 模块四",
  title:  "知识 Wiki 页面",
  lead:   "案件 / 人物 / 地点 / 法规 / 技战法 等结构化卡片",
  bullets: [
    "每条知识 = 一份带 YAML frontmatter 的 Markdown 文件",
    "类目齐全：案件、人物、地点、法规、技战法、笔记、研判等",
    "卡片视图浏览，支持类目筛选、多维排序、批量删除",
    "页面间通过 [[wiki-link]] 双向链接，自动回填反向关联",
    "完全兼容 Obsidian，离线可读，git 友好",
  ],
  highlightLabel: "TRACEABILITY",
  highlightTitle: "知识可追溯、可审计",
  highlightBody: "每个 Wiki 页面记录来源材料路径、创建/更新时间、引用关系。出庭质证或上级审计时，可逐条回溯到原始材料。",
  page: 12,
});

moduleSlide({
  kicker: "03  主要功能 · 模块五",
  title:  "图谱关系展示",
  lead:   "把人物、地点、案件之间的关系可视化为知识网络",
  bullets: [
    "D3 力导向布局，支持四种排布方式",
    "单击节点：一度邻居高亮、其他节点淡化",
    "节点详情抽屉同步展开，无需跳页",
    "按线索簇自动分组，关键节点高亮",
    "支持节点合并视图，避免大库视觉混乱",
  ],
  highlightLabel: "ANALYSIS",
  highlightTitle: "线索簇直观可见",
  highlightBody: "同一团伙的多个嫌疑人、多个落脚点会聚集成簇。新的笔记一旦进库，新节点就连入对应簇，研判线索一目了然。",
  page: 13,
});

moduleSlide({
  kicker: "03  主要功能 · 模块六",
  title:  "知识库体检",
  lead:   "定期巡检知识库健康度，主动发现问题并一键修复",
  bullets: [
    "断链检测：发现 [[wiki-link]] 指向不存在的页面",
    "孤立页面：未被任何页面引用的知识点",
    "过期检测：长期未更新（默认 180 天）的页面",
    "按类别批量修复：删除链接 / 创建占位页 / 自动补充关联",
    "首页健康度评分，配合首页仪表盘看大盘",
  ],
  highlightLabel: "GOVERNANCE",
  highlightTitle: "知识库不是垃圾场",
  highlightBody: "随着材料增加，质量会自然下降。体检模块定期发现问题、给出修复建议，保证知识库始终可用、不腐烂。",
  page: 14,
});

moduleSlide({
  kicker: "03  主要功能 · 模块七",
  title:  "系统配置",
  lead:   "模型、目录、账号、并发参数集中可视化管理",
  bullets: [
    "文本 / 视觉 / OCR 三类模型独立配置",
    "支持 OpenAI / DashScope / DeepSeek / Ollama 等",
    "深度思考（thinking）开关，DeepSeek V4 等推理模型可一键启用",
    "知识库路径、并发数、自定义类目可配",
    "用户与邀请码管理，邀请同事加入工作台",
  ],
  highlightLabel: "FLEXIBILITY",
  highlightTitle: "云端 / 本地双模式",
  highlightBody: "公网环境用云端大模型，涉密环境切到本地 Ollama 模型；同一套界面同一套数据结构，按场景切换无感。",
  page: 15,
});

// ════════════════════════════════════════
// Slide 16 — 业务场景概览
// ════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.bg };
  sectionTitle(s, "04  业务场景", "三类典型应用");

  const scenes = [
    ["案件分析", "把零散接处警笔录、勘查记录编织成一张案情网", "嫌疑人共现 · 作案手法聚类 · 时间线还原"],
    ["资金流向分析", "将转账记录、银行流水文档结构化为人–账户图", "账户关系 · 资金路径 · 异常节点定位"],
    ["笔录分析", "把多份笔录的关键事实提取出来对比交叉", "口供一致性 · 时间矛盾 · 关键证人识别"],
  ];

  let y = 1.55;
  scenes.forEach(([title, desc, kpi]) => {
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y: y, w: 9, h: 1.05,
      fill: { color: "FFFFFF" }, line: { color: C.border, width: 0.75 }, shadow: makeShadow()
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y: y, w: 0.06, h: 1.05, fill: { color: C.navy }, line: { color: C.navy }
    });
    s.addText(title, {
      x: 0.75, y: y + 0.15, w: 2.5, h: 0.4,
      fontSize: 17, fontFace: F, color: C.navy, bold: true, margin: 0
    });
    s.addText(desc, {
      x: 0.75, y: y + 0.55, w: 5.5, h: 0.45,
      fontSize: 12, fontFace: F, color: C.text, margin: 0
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: 6.4, y: y + 0.18, w: 0.02, h: 0.7, fill: { color: C.border }, line: { color: C.border }
    });
    s.addText(kpi, {
      x: 6.55, y: y + 0.3, w: 2.85, h: 0.5,
      fontSize: 11.5, fontFace: F, color: C.gold, bold: true, margin: 0
    });
    y += 1.18;
  });

  pageFooter(s, 16);
}

// ════════════════════════════════════════
// Slide 17 — 业务场景：案件分析
// ════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.bg };
  sectionTitle(s, "04  业务场景 · 案例一", "案件分析");

  // 流程
  const steps = [
    ["材料入库", "接处警单、勘查笔录、嫌疑人笔录"],
    ["实体抽取", "案件 / 嫌疑人 / 地点 / 物证"],
    ["关系建图", "嫌疑人共现 · 同地点 · 同手法"],
    ["研判输出", "串并案推荐 · 团伙画像 · 缺口提醒"],
  ];

  s.addText("从离散笔录到完整案情图谱", {
    x: 0.5, y: 1.45, w: 9, h: 0.4,
    fontSize: 14, fontFace: F, color: C.muted, margin: 0
  });

  let x = 0.5;
  const w = 2.18, h = 2.0;
  steps.forEach(([t, d], i) => {
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: 2.05, w, h,
      fill: { color: i === 3 ? C.navy : "FFFFFF" },
      line: { color: i === 3 ? C.navy : C.border, width: 0.75 },
      shadow: makeShadow()
    });
    s.addText(`步骤 ${i + 1}`, {
      x: x + 0.15, y: 2.2, w: w - 0.3, h: 0.3,
      fontSize: 10, fontFace: F,
      color: i === 3 ? C.gold : C.gold, bold: true, margin: 0, charSpacing: 2
    });
    s.addText(t, {
      x: x + 0.15, y: 2.55, w: w - 0.3, h: 0.4,
      fontSize: 16, fontFace: F,
      color: i === 3 ? "FFFFFF" : C.navy, bold: true, margin: 0
    });
    s.addText(d, {
      x: x + 0.15, y: 3.0, w: w - 0.3, h: 0.95,
      fontSize: 11.5, fontFace: F,
      color: i === 3 ? "C9D2E5" : C.text, margin: 0
    });
    x += w + 0.12;
  });

  // 收益条
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 4.3, w: 9, h: 0.7,
    fill: { color: C.panel }, line: { color: C.border, width: 0.5 }
  });
  s.addText("典型收益", {
    x: 0.7, y: 4.42, w: 1.3, h: 0.32,
    fontSize: 12, fontFace: F, color: C.gold, bold: true, margin: 0, charSpacing: 2
  });
  s.addText("过去靠人工翻笔录关联，现在系统主动发现 → 串并案效率显著提升，新接案件自动比对历史。", {
    x: 2.0, y: 4.42, w: 7.4, h: 0.5,
    fontSize: 12, fontFace: F, color: C.text, margin: 0
  });

  pageFooter(s, 17);
}

// ════════════════════════════════════════
// Slide 18 — 业务场景：资金流向
// ════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.bg };
  sectionTitle(s, "04  业务场景 · 案例二", "资金流向分析");

  s.addText("把银行流水、转账记录、第三方支付凭证统一为账户–金额关系图", {
    x: 0.5, y: 1.45, w: 9, h: 0.4,
    fontSize: 14, fontFace: F, color: C.muted, margin: 0
  });

  // 左：输入
  const cards = [
    ["输入", "Excel 流水 · PDF 对账单 · 截图凭证 · 询问笔录中的账户描述", C.slate],
    ["处理", "LLM 抽取「人–账户–金额–时间」四元组，归一化为 Wiki 实体与关系", C.navy],
    ["输出", "账户关系图谱 · 资金路径可视化 · 大额异常节点高亮 · 关联人物自动出现", C.gold],
  ];
  let y = 2.0;
  cards.forEach(([title, body, color]) => {
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y, w: 9, h: 0.95,
      fill: { color: "FFFFFF" }, line: { color: C.border, width: 0.75 }, shadow: makeShadow()
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y, w: 1.4, h: 0.95, fill: { color }, line: { color }
    });
    s.addText(title, {
      x: 0.6, y: y + 0.3, w: 1.2, h: 0.35,
      fontSize: 16, fontFace: F, color: "FFFFFF", bold: true, align: "center", margin: 0
    });
    s.addText(body, {
      x: 2.05, y: y + 0.22, w: 7.3, h: 0.65,
      fontSize: 12.5, fontFace: F, color: C.text, valign: "middle", margin: 0
    });
    y += 1.05;
  });

  pageFooter(s, 18);
}

// ════════════════════════════════════════
// Slide 19 — 业务场景：笔录分析
// ════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.bg };
  sectionTitle(s, "04  业务场景 · 案例三", "笔录分析");

  s.addText("多份笔录交叉比对，自动发现一致点、矛盾点、关键证人", {
    x: 0.5, y: 1.45, w: 9, h: 0.4,
    fontSize: 14, fontFace: F, color: C.muted, margin: 0
  });

  // 左右两列
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 2.0, w: 4.4, h: 3.0,
    fill: { color: "FFFFFF" }, line: { color: C.border, width: 0.75 }, shadow: makeShadow()
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 2.0, w: 4.4, h: 0.45, fill: { color: C.navy }, line: { color: C.navy }
  });
  s.addText("能做什么", {
    x: 0.7, y: 2.05, w: 4, h: 0.36,
    fontSize: 14, fontFace: F, color: "FFFFFF", bold: true, margin: 0, charSpacing: 3
  });
  s.addText([
    { text: "提取每份笔录的关键事实（人、地、时、物、行为）", options: { bullet: { code: "25A0" }, breakLine: true, color: C.text } },
    { text: "跨笔录比对：哪些说法一致、哪些矛盾", options: { bullet: { code: "25A0" }, breakLine: true, color: C.text } },
    { text: "时间线还原与冲突标记", options: { bullet: { code: "25A0" }, breakLine: true, color: C.text } },
    { text: "识别同一事件被多人提及的关键证人", options: { bullet: { code: "25A0" }, color: C.text } },
  ], {
    x: 0.75, y: 2.6, w: 4.0, h: 2.3,
    fontSize: 12, fontFace: F, paraSpaceAfter: 7
  });

  s.addShape(pres.shapes.RECTANGLE, {
    x: 5.1, y: 2.0, w: 4.4, h: 3.0,
    fill: { color: "FFFFFF" }, line: { color: C.border, width: 0.75 }, shadow: makeShadow()
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 5.1, y: 2.0, w: 4.4, h: 0.45, fill: { color: C.gold }, line: { color: C.gold }
  });
  s.addText("典型流程", {
    x: 5.3, y: 2.05, w: 4, h: 0.36,
    fontSize: 14, fontFace: F, color: "FFFFFF", bold: true, margin: 0, charSpacing: 3
  });
  s.addText([
    { text: "上传同一案件的多份询问/讯问笔录", options: { bullet: { type: "number" }, breakLine: true, color: C.text } },
    { text: "系统自动建立人物页 + 事件页 + 笔录页", options: { bullet: { type: "number" }, breakLine: true, color: C.text } },
    { text: "对话框提问「比对 A 与 B 在 X 事件的描述」", options: { bullet: { type: "number" }, breakLine: true, color: C.text } },
    { text: "结果含 Wiki 来源链接，可逐句回溯笔录原文", options: { bullet: { type: "number" }, color: C.text } },
  ], {
    x: 5.35, y: 2.6, w: 4.0, h: 2.3,
    fontSize: 12, fontFace: F, paraSpaceAfter: 7
  });

  pageFooter(s, 19);
}

// ════════════════════════════════════════
// Slide 20 — 未来规划：本地+云端
// ════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.bg };
  sectionTitle(s, "05  未来规划", "本地 + 云端 统一知识服务");

  s.addText("本地保留隐私敏感数据，云端汇聚跨警种、跨警务区的共性知识", {
    x: 0.5, y: 1.45, w: 9, h: 0.4,
    fontSize: 14, fontFace: F, color: C.muted, margin: 0
  });

  // 左：本地
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 2.05, w: 4.0, h: 2.95,
    fill: { color: "FFFFFF" }, line: { color: C.navy, width: 1.2 }, shadow: makeShadow()
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 2.05, w: 4.0, h: 0.5, fill: { color: C.navy }, line: { color: C.navy }
  });
  s.addText("本地知识库", {
    x: 0.7, y: 2.12, w: 3.6, h: 0.4,
    fontSize: 16, fontFace: F, color: "FFFFFF", bold: true, margin: 0
  });
  s.addText([
    { text: "涉密案件、本地化经验、个人笔记", options: { bullet: { code: "25A0" }, breakLine: true, color: C.text } },
    { text: "数据不出本机/不出内网", options: { bullet: { code: "25A0" }, breakLine: true, color: C.text } },
    { text: "可选用本地 Ollama 推理", options: { bullet: { code: "25A0" }, breakLine: true, color: C.text } },
    { text: "与云端按需双向同步脱敏后内容", options: { bullet: { code: "25A0" }, color: C.text } },
  ], {
    x: 0.75, y: 2.7, w: 3.6, h: 2.2,
    fontSize: 12, fontFace: F, paraSpaceAfter: 8
  });

  // 中：连接
  s.addShape(pres.shapes.OVAL, {
    x: 4.7, y: 3.2, w: 0.6, h: 0.6,
    fill: { color: C.gold }, line: { color: C.gold }
  });
  s.addText("⇆", {
    x: 4.7, y: 3.18, w: 0.6, h: 0.65,
    fontSize: 24, fontFace: F, color: "FFFFFF", bold: true, align: "center", valign: "middle", margin: 0
  });
  s.addText("脱敏 / 鉴权 / 选择性同步", {
    x: 4.4, y: 3.85, w: 1.2, h: 0.3,
    fontSize: 9, fontFace: F, color: C.muted, align: "center", margin: 0
  });

  // 右：云端
  s.addShape(pres.shapes.RECTANGLE, {
    x: 5.5, y: 2.05, w: 4.0, h: 2.95,
    fill: { color: "FFFFFF" }, line: { color: C.gold, width: 1.2 }, shadow: makeShadow()
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 5.5, y: 2.05, w: 4.0, h: 0.5, fill: { color: C.gold }, line: { color: C.gold }
  });
  s.addText("云端统一知识服务", {
    x: 5.7, y: 2.12, w: 3.6, h: 0.4,
    fontSize: 16, fontFace: F, color: "FFFFFF", bold: true, margin: 0
  });
  s.addText([
    { text: "跨警种、跨辖区共性知识汇聚", options: { bullet: { code: "25A0" }, breakLine: true, color: C.text } },
    { text: "标准技战法、典型案例库", options: { bullet: { code: "25A0" }, breakLine: true, color: C.text } },
    { text: "全国/全省级模型与算力支撑", options: { bullet: { code: "25A0" }, breakLine: true, color: C.text } },
    { text: "向本地下发更新 + 共建", options: { bullet: { code: "25A0" }, color: C.text } },
  ], {
    x: 5.75, y: 2.7, w: 3.6, h: 2.2,
    fontSize: 12, fontFace: F, paraSpaceAfter: 8
  });

  pageFooter(s, 20);
}

// ════════════════════════════════════════
// Slide 21 — 结语
// ════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.navy };

  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.6, w: 0.5, h: 0.08, fill: { color: C.gold }, line: { color: C.gold }
  });
  s.addText("从笔记开始，让知识真正长出来", {
    x: 0.5, y: 1.8, w: 9, h: 0.7,
    fontSize: 32, fontFace: F, color: "FFFFFF", bold: true, margin: 0
  });
  s.addText("知枢 · 数合云智", {
    x: 0.5, y: 2.65, w: 9, h: 0.5,
    fontSize: 18, fontFace: F, color: "C9D2E5", margin: 0, charSpacing: 4
  });

  // 三个关键词
  const tags = ["本地部署", "开箱即用", "持续积累"];
  let x = 0.5;
  tags.forEach(t => {
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: 4.0, w: 2.0, h: 0.55,
      fill: { color: C.navyLt }, line: { color: C.gold, width: 1 }
    });
    s.addText(t, {
      x, y: 4.0, w: 2.0, h: 0.55,
      fontSize: 14, fontFace: F, color: "FFFFFF", bold: true, align: "center", valign: "middle", margin: 0
    });
    x += 2.15;
  });

  s.addText("感谢聆听  ·  欢迎交流", {
    x: 0.5, y: 5.0, w: 9, h: 0.4,
    fontSize: 14, fontFace: F, color: "8896B0", align: "right", margin: 0
  });
}

// ── 输出 ────────────────────────────────
const outPath = path.join(__dirname, "知枢汇报.pptx");
pres.writeFile({ fileName: outPath }).then(p => {
  console.log("生成完成: " + p);
});
