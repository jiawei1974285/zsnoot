# 民警随手记 · 数合云智

> 面向基层民警的本地化智能知识库工作台 —— 像平时一样随手记,LLM 自动整理成结构化的 wiki,自动发现人物、地点、案件之间的关联。

## 项目简介

**核心问题**:基层民警日常会产生大量笔记、案件记录、巡查信息,但这些信息散落在笔记本、手机、微信群等各处,难以检索和关联,无法自动发现串并案线索,经验技巧也难以传承。

**解决方案**:
1. 民警按习惯随手记(语音、文字、图片、文档)
2. LLM 自动把笔记编译成结构化的 markdown wiki(案件 / 人物 / 地点 / 法规 / 技战法 / 笔记 / 研判)
3. 自动建立人物、地点、案件之间的双向链接,生成知识图谱
4. 支持对话式查询、串并案分析、知识体检与维护

详细产品定位见 `purpose.md`,wiki schema 定义见 `schema.md`。

---

## 主要功能

| 模块 | 能力 |
|---|---|
| **材料入库** | 拖入 Word / PDF / Markdown / Excel / 图片 / 文本,自动解析、抽取实体、生成 wiki 页面、建立 `[[wiki-link]]`、按批次可回滚，也可对历史批次再次解析并与既有知识合并 |
| **对话查询** | 基于本地知识库的 RAG 问答,带可点击的知识来源引用,问答结果自动沉淀为 outputs 类型记忆页 |
| **整理后的知识** | 卡片视图浏览所有 wiki 页面,支持按类别筛选、按最后导入/更新/创建/标题排序、分页大小自定义、多选批量删除、单击查看 |
| **新建笔记** | 在上传材料下方提级显示，可输入标题、正文和标签，自动抽取人物关系并写入 notes/persons 页面和关系图谱 |
| **关系图谱** | D3 力导向布局,支持 4 种排布(force / type / community / radial)。**单击节点**:① 一度邻居聚焦(其他淡化) ② 同时滑出该实体 wiki 详情抽屉。「重置视图」恢复全图 |
| **知识库体检** | 检测断链、孤立页面、过期内容(>30 天未更新)。**一键修复**:按类别弹窗,勾选条目 + 选动作(删除链接 / 创建占位页 / 自动补充关联 / 标记独立 / 触发更新) |
| **系统配置** | LLM 模型 / API key / 知识库路径 / 入库阈值 等可视化配置,支持模型连通性测试 |

---

## 技术栈

**后端** (`Python ≥ 3.10`)
- Flask 3 — Web 框架与 API；Werkzeug 提供密码哈希
- PyYAML — frontmatter 解析
- python-docx / python-pptx / PyMuPDF / pandas+openpyxl / Pillow — 多格式文档解析（懒加载）
- watchdog — 文件系统监听（可选自动入库）
- requests — LLM HTTP 调用
- 内置：`logging` + `RotatingFileHandler` 写 `mjq.log`，`data/llm_calls.jsonl` 持久化每次 LLM 调用耗时与异常详情

**前端** (`Node ≥ 18`)
- Vue 3.5 (Composition API)
- Element Plus 2.11 — UI 组件库
- D3 7 — 知识图谱可视化
- ECharts 6 + vue-echarts — 首页 dashboard 折线/饼图
- Vite 7 — 构建工具

**数据存储**
- 文件式 wiki：每条知识是一个带 frontmatter 的 `.md`，直接 git 友好
- 批次元数据：`data/ingest_batches.json`
- 用户/邀请码：`data/users.json` + `data/invite_codes.json`
- 活动日志：`data/activity_log.json`（用于首页统计） + `wiki/log.md`（人类可读审计）
- LLM 调用流水：`data/llm_calls.jsonl`（结构化，便于离线分析耗时与失败模式）

> **检索说明**：当前版本 `/api/chat` 走的是手写的「中文 bigram 分词 + 标题/正文/标签加权计数」检索，**未启用向量索引**。后续若要升级到 embedding-based RAG，会在 `embeddings/` 目录下落盘 numpy 向量。

---

## 快速开始

### 安装依赖

```bash
# 后端
pip install -r requirements.txt

# 前端
cd frontend
npm install
cd ..
```

### 运行(开发模式)

**一键启动（推荐，Windows）**

```cmd
:: 双击或在 PowerShell 执行
scripts\start.bat
```

会弹出两个新终端窗口，分别跑 Flask（5004）和 Vite dev（5174），首次会自动检查端口占用、依赖完整性。停止：双击 `scripts\stop.bat` 或关掉两个窗口。

**手动启动**

```bash
# 终端 A — 启动后端 (默认 http://localhost:5004)
python app.py

# 终端 B — 启动前端开发服务器 (热重载,http://localhost:5174,代理到 5004)
cd frontend
npm run dev
```

### 运行(生产模式 / 一键启动)

```bash
# 1. 构建前端 → frontend/dist/
cd frontend
npm run build
cd ..

# 2. 启动后端,Flask 直接服务 dist/ 静态资源
python app.py
# 浏览器打开 http://localhost:5004
```

### 配置

**敏感凭据走 `.env`**（不会被 git 跟踪）：

```bash
cp .env.example .env
# 编辑 .env 填入：LLM_API_KEY / LLM_BASE_URL / LLM_MODEL / LLM_PROVIDER
```

**非敏感设置走 `config/config.yaml`**：模型温度、知识库路径、ingest 并发参数（`single_call`、`max_workers`）、自定义类目等。

也可以启动后通过「系统配置」tab 在 Web 界面里改，改完点「测试连接」确认模型可达。

### 首次登录

第一次启动会进入「初始化」流程，引导你创建第一个**管理员账号**。后续要让同事使用：管理员在「系统配置」→「用户与邀请码」生成一次性邀请码，对方在登录页「注册」tab 输入邀请码 + 用户名/密码 + 单位 + 职务即可加入。

---

## 目录结构

```
mjq-handynotes/
├── app.py                      # Flask 主入口，所有 API 路由
├── auto_ingest.py              # 自动入库流水线（single_call + two_call 双模式）
├── ingest_service.py           # 入库批次编排（ThreadPoolExecutor 并发）
├── ingest_batches.py           # 批次元数据存储
├── file_parser.py              # 多格式文档解析（docx/pptx/pdf/xlsx/img）
├── file_watcher.py             # 文件夹监听（可选）
├── graph.py                    # 知识图谱构建 + 体检逻辑（run_lint）
├── wiki_links.py               # [[wiki-link]] 双向链接工具
├── llm_client.py               # LLM 调用（含结构化耗时与异常日志）
├── llm_tester.py               # LLM 连通性测试
├── auth.py                     # 用户 + 邀请码 + 角色（admin/member）
├── activity_log.py             # 活动日志，首页 KPI/趋势数据源
├── agent_status.py             # 入库进度状态（线程安全原子写）
├── config_store.py             # 配置读写
├── mjq_logging.py              # 集中 logging 配置（RotatingFileHandler）
├── config/config.yaml          # 非敏感配置
├── .env.example                # 敏感凭据样板（复制为 .env 后填）
├── requirements.txt            # Python 依赖
│
├── scripts/
│   ├── start.bat / start.ps1   # 一键启动前后端
│   ├── stop.bat  / stop.ps1    # 一键停止
│   └── retry_stale.py          # 批量重试入库失败的「待精炼」页面
│
├── wiki/                       # 知识库本体（markdown 文件，运行时生成，未入 git）
│   ├── cases/ persons/ locations/ laws/ techniques/ notes/
│   ├── organizations/ events/ evidence/ case_summaries/
│   ├── crime_patterns/ conclusions/ outputs/ summaries/
│   ├── templates/              # 实体页模板（入 git）
│   ├── index.md                # 全部页面索引
│   └── log.md                  # 时间倒序活动日志
│
├── raw/sources/<batch_id>/     # 上传的原始材料归档（运行时生成，未入 git）
├── data/                       # 批次/用户/邀请码/活动日志/LLM 调用流水（未入 git）
│
├── frontend/                   # Vue + Vite 前端
│   ├── public/                 # 静态资源（logo 等）
│   ├── src/App.vue             # 主组件（所有视图）
│   ├── src/styles.css          # 全局样式
│   ├── src/graphLayouts.js     # D3 图谱布局算法
│   ├── package.json
│   └── vite.config.js
│
├── tests/                      # Python 单元测试（治理、入库、图谱体检、文件解析等）
├── purpose.md                  # 产品目标
├── schema.md                   # wiki 数据结构规范
└── README.md                   # 本文件
```

---

## API 概览

所有接口前缀 `/api`，仅本地访问，鉴权用 Flask session cookie。详见 `app.py`。

| 分类 | 路径 | 方法 | 说明 |
|---|---|---|---|
| **鉴权** | `/api/auth/status` | GET | 当前登录态 + role |
| | `/api/auth/setup` | POST | 首次创建管理员账号（仅当 users.json 为空） |
| | `/api/auth/register` | POST | 凭邀请码注册成员 |
| | `/api/auth/login` / `logout` | POST | 登录 / 登出 |
| | `/api/auth/change-password` | POST | 修改密码 |
| **管理** | `/api/admin/invites` | GET / POST | admin：列出 / 生成邀请码 |
| | `/api/admin/invites/<code>` | DELETE | admin：撤销未用邀请码 |
| **页面** | `/api/wiki/pages` | GET / POST | 列出页面；POST 当前保持只读保护（支持 `?type=cases`） |
| | `/api/wiki/pages/<slug>` | GET / PUT / DELETE | 读 / 改 / 删单页（当前 PUT 只读保护，DELETE 可从知识卡片删除） |
| | `/api/wiki/categories` | GET | 列出 wiki 子类目 |
| | `/api/wiki/index` / `log` | GET | 读索引/日志 |
| **入库** | `/api/ingest/upload` | POST | 上传材料并触发并发入库 |
| | `/api/ingest/batches` | GET | 列出历史批次 |
| | `/api/ingest/batches/<id>` | GET | 单批次详情 |
| | `/api/ingest/batches/<id>/rollback` | POST | 回滚批次（删除产物） |
| | `/api/ingest/batches/<id>/reparse` | POST | 复用归档原文再次解析，带历史结果上下文做补充抽取，并合并新实体/关系 |
| | `/api/ingest/stale` | GET | 列出 status:待精炼 的 fallback 页面 |
| | `/api/ingest/retry-stale` | POST | 重跑指定 stale 页面（成功后删原页） |
| **检索** | `/api/search` | GET | 关键词加权检索 |
| | `/api/chat` | POST | 知识库 QA（自动沉淀为 outputs/） |
| **图谱** | `/api/graph` | GET | 全图（节点 + 边 + 社区） |
| | `/api/graph/merged` | GET | 合并相近节点（`?threshold=0.3`） |
| **体检** | `/api/lint` | GET | 检测断链/孤立/过期 |
| | `/api/lint/fix` | POST | 按类别批量修复 |
| **富化** | `/api/analyze/<slug>` | POST | LLM 重新抽取实体 |
| | `/api/enrich/<slug>` | POST | 自动补充 `[[wiki-link]]` |
| **统计** | `/api/stats` | GET | 首页 dashboard 数据（KPI + 趋势 + 最近问答） |
| | `/api/activity` | GET | 最近活动日志 |
| | `/api/agent/status` | GET | 入库实时进度推送 |
| **配置** | `/api/config` | GET / PUT | 读 / 写配置 |
| | `/api/config/test-llm` | POST | 测试 LLM 连通性 |
| **关联** | `/api/cases/<slug>/related` | GET | 串并案推荐 |
| | `/api/themes` / `/api/themes/<theme>` | GET | 主题视图 |

---

## Wiki 数据规范

每个页面是带 YAML frontmatter 的 markdown 文件:

```markdown
---
type: case | person | location | law | technique | note | summary | outputs
title: 人类可读标题
tags: []
related: []
created: YYYY-MM-DD
updated: YYYY-MM-DD
# 案件页额外:case_type / status / date_occurred
# 人物页额外:role / case_ref
# 地点页额外:address / case_refs
---

正文内容,使用 [[other-slug]] 建立双向链接。

## 反向关联

- [[backlink-slug]]
```

完整规范见 `schema.md`。

---

## 开发说明

### 跑测试

```bash
python -m unittest discover tests
```

涵盖:`config_store`、`wiki_links`、`wiki_categories`、`ingest_batches`、`file_parser`、`llm_tester`。

### 前端图谱布局算法测试

```bash
cd frontend
npm run test:graph
```

### 调整图谱视觉

- 画布尺寸:`App.vue` 中 `renderGraph()` 内 `width=1400 / height=900`,`styles.css` `.graph-svg height: 820px`
- 节点半径:`Math.max(5, Math.min(13, 5 + linkCount * 1.0))`
- 节点字号:`styles.css` `.graph-node text font-size: 9px`
- 一度淡化:`styles.css` `.graph-dimmed { opacity: 0.08; pointer-events: none }`

### 自定义 LLM 提示词

入库与抽取的 prompt 集中在 `auto_ingest.py`,体检建议在 `graph.py:generate_lint_suggestions`,对话 prompt 在 `app.py /api/chat` 内。

---

## 故障排查

| 现象 | 排查方向 |
|---|---|
| 启动后访问空白页 | 确认 `frontend/dist/` 存在；若无，先 `cd frontend && npm run build` |
| 浏览器看不到改动 | 浏览器硬刷新 `Ctrl+Shift+R` 清旧 bundle 缓存 |
| 上传后批次「待精炼」太多 | `python scripts/retry_stale.py --list` 看清单；`--all --limit 5` 试跑 |
| 「上传慢」不知道怎么回事 | 看 `data/llm_calls.jsonl` 最后几行：每行有 latency_ms 和具体异常 |
| LLM 调用报错 | 「系统配置」点「测试连接」；确认 .env 里 LLM_* 字段；查 `mjq.log` |
| `.pptx`/Excel/PDF 入库失败 | 检查对应解析库是否装好（`pip install -r requirements.txt`） |
| 文件监听不生效 | 确认 `watchdog` 已装，且 `config.yaml` 中 watcher 段配置对 |
| 端口被占启动失败 | `scripts/stop.bat` 一键停，或手工 `taskkill /F /PID <pid>` |

`mjq.log` 是结构化应用日志（含 LLM 调用耗时与异常 traceback），`data/llm_calls.jsonl` 是每次 LLM 调用的结构化记录。

---

## 路线图（待办）

- [ ] 删除页面时联动清理反向链接（目前仅删 `.md`，体检会发现残留断链）
- [ ] 真正的向量检索（embedding-based RAG，替换当前的 token 加权计数）
- [ ] 知识图谱大改（按业务视角分层、关键节点高亮、社区演化）
- [ ] Markdown 编辑器升级（实时预览 / 图片粘贴上传）
- [ ] 移动端响应式优化
- [ ] 多警员协作：差异同步、冲突合并
- [ ] LLM 调用加 tenacity 重试（看 `llm_calls.jsonl` 评估必要性）
- [ ] 忘记密码（基于注册时填的邮箱发临时码）

---

## 鸣谢

- 产品 / 业务设计:数合云智
- 前端组件库:Element Plus
- 图可视化:D3.js
- 灵感来源:Obsidian 的 [[wiki-link]] 知识网络范式
