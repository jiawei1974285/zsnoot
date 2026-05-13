# 知枢 · 数合云智

> 把"日常材料"自动整理成"结构化知识网络"的本地知识中枢。
>
> 像平时一样上传 Word / PDF / 图片 / 笔记，LLM 自动抽实体、建关系、补反向链接、画图谱。云端只做认证与调度，**用户语料始终在本机**。

[![Web V1.0](https://img.shields.io/badge/release-web--v1.0-blue)](https://github.com/jiawei1974285/zsnoot/releases/tag/web-v1.0)
[![Tests](https://img.shields.io/badge/tests-92%20pass%20%2B%2032%20E2E-green)]()
[![Architecture](https://img.shields.io/badge/arch-cloud%20%2B%20local-orange)]()

---

## 1. 它能干什么

围绕"个人 / 团队的知识管理"，按使用频率高低五块能力：

### 1.1 材料入库
- **多格式解析**：Word / PowerPoint / PDF / Markdown / TXT / Excel / 图片 OCR；缺解析库自动降级到 XML 兜底
- **LLM 自动抽取**：单次 LLM 调用产出多个分类页面（人物 / 案件 / 事件 / 证据 / 结论 …）+ `[[wiki-link]]` 双向链接
- **批次化 + 可回滚**：每次上传是一个批次，元数据完整保留；不满意一键回滚
- **二次解析**：对历史批次"再追一刀"——拿现有上下文做更深的抽取，新结果与原页面合并而不是覆盖
- **失败兜底**：解析失败的页面进 `status: 待精炼` 队列，不阻塞流程；后台或手动重试

### 1.2 对话查询（RAG）
- 自然语言问答，答案带可点击的来源引用
- 命中关键词后沿 `[[wiki-link]]` 边走 N 跳把强相关页拉进上下文（默认 1 跳）
- 问答结果自动沉淀为 `outputs/` 类型记忆页，下次同问可命中
- > 当前版本是手写的"中文 bigram 加权计数"检索；向量化是路线图项

### 1.3 知识浏览与编辑
- **卡片视图**：所有 wiki 页按目录分类，多维度排序（最后导入 / 更新 / 创建 / 标题），支持多选批量操作
- **新建笔记**：标题 + URL + 正文 + 标签；URL 一键提取网页正文，提交后走完整 LLM 抽取链路
- **关系图谱**：D3 力导向布局，4 种排布（force / type / community / radial），点节点聚焦一度邻居
- **源文档预览**：知识维护抽屉里直接调本机 file_parser 解析任意 raw 文件

### 1.4 知识库体检（A 整改后唯一权威）
- **4 类问题统一概览**：断链 / 孤立 / 过期 / 占位
- **健康度透明公式**：`100 − (断链×3 + 孤立×1 + 过期×0.5 + 占位×1.5) × 100 / 总页数`
- **修复动作**（按类）：
  - 断链：删链接 / 创建空白占位页 / **智能补齐**（LLM 根据上下文写草稿）
  - 孤立：自动补充关联（LLM enrich）/ 标记独立
  - 过期：标记已确认 / 标记独立
  - 占位：智能补全（LLM）/ 接受存档 / 删除
- **首页 KPI 直达**：健康度卡片可点；右侧栏每一行可点 → 直接弹出对应类别的修复对话框

### 1.5 系统能力
- **多 schema 模板**：5 套预置（警务办案 / 法律合规 / 财务营销 / 科研项目 / 通用知识库）+ **LLM 合成自定义 schema**（输目标 + 主要对象，agent 生成）
- **定时任务**：APScheduler；4 种白名单 kind（inbox 扫描 / 孤页索引刷新 / wiki 体检 / 自动补齐）
- **多用户**：邀请码注册；管理员控制台看所有用户心跳与计数
- **数据隔离**：每个用户独立目录 `~/.handynotes/<username>/{wiki,raw,data,config,.env}`，互不可见

---

## 2. 三种部署形态

| 形态 | 使用场景 | 启动 | 跨用户 |
|------|---------|------|--------|
| **单体（Monolith）** | 单人离线 / 演示 / 老部署回滚 | `scripts\start.bat` | ✗ |
| **本机分离（Local Split）** | 一台开发机起三进程方便联调 | `scripts\start_split.bat` | ✗ |
| **服务器（Server）** | 多人共享，云端做认证调度 | `deploy/install.sh` | ✓ |

三者**共用同一份代码**，由环境变量切换；任何形态都可零代码改动迁回上一形态。

### 2.1 架构（服务器形态）

```
┌──────────── 浏览器 (前端 SPA) ────────────┐
│   /api/cloud/*  ─►  云端 (Nginx :8090 ─► :5005)
│   /api/*        ─►  本机 agent (127.0.0.1:5004)
└────────────────────────────────────────────┘
         │                     │
   ┌─────▼──────┐       ┌──────▼─────────────┐
   │ 云端控制面 │       │ 本机 agent          │
   │ 用户/邀请码 │       │  ~/.handynotes/<u>/│
   │ Schema 模板│       │   wiki/ raw/ .env  │
   │ Schema 合成│       │  LLM API key       │
   │ 心跳 / 调度│       │  入库 / 体检 / 调度 │
   └───────────┘       └────────────────────┘
   PostgreSQL ❌（V1.0 用 JSON）   每个用户的电脑
```

**云端绝不接触用户语料**——这是产品价值的核心承诺。云端只持有用户名 / 哈希密码 / 邀请码 / Schema 模板 / 心跳计数。

---

## 3. 快速开始

### 3.1 单体演示（5 分钟）

```bash
git clone -b web-v1.0 https://github.com/jiawei1974285/zsnoot.git
cd zsnoot

pip install -r requirements.txt
cd frontend && npm install && cd ..

# Windows 一键
scripts\start.bat        # → http://localhost:5174

# 或手动
python app.py            # 后端 5004
cd frontend && npm run dev   # 前端 5174（vite proxy 转 5004）
```

首次进入：填管理员账号 → 选 `raw/` 目录 → 进入主界面。

### 3.2 服务器部署（生产）

详见 [`deploy/README.md`](deploy/README.md)。一键脚本：

```bash
sudo git clone -b web-v1.0 https://github.com/jiawei1974285/zsnoot.git /opt/mjq-handynotes
cd /opt/mjq-handynotes
sudo bash deploy/install.sh <服务器 IP 或域名>
```

脚本会：
1. 装 python3 / nodejs ≥ 22 / nginx
2. 建 system 账号 `mjq`，配 venv
3. 生成 `cloud.env`（含**随机 64 hex JWT 密钥**，输出到屏幕——记下）
4. 构建前端（baked `VITE_CLOUD_API=http://<IP>`）
5. 装 systemd 单元，nginx 站点；自检三个 endpoint

### 3.3 本机 agent 连服务器 —— 一键安装包（最常用，**推荐发给同事**）

> 服务器已部署后，给同事的方式：他们直接从浏览器下安装包。

**同事侧**（Windows）：

1. 找你要邀请码
2. 浏览器开 `http://<服务器 IP>:8090` → 切「注册」tab → 填邀请码 + 用户名 + 密码 → 选 schema 模板 → 注册
3. **同一页面下方点「下载本机客户端」** → 70 MB zip
4. 解压到任意位置（例如 `D:\zsnoot`）
5. 双击 `setup.bat`
   - 自动检测内嵌 Python（无需自己装 Python）
   - 读 `preset.ini`：云端地址 + JWT 密钥已预填好
   - 只问一件事：刚刚注册的用户名
   - 自动绑定本机 + 在桌面建「知枢」图标
6. 双击桌面「知枢」图标启动

**管理员侧**：

```powershell
# 在 Windows 上 build server-baked zip
.\installer\build_release.ps1 `
  -PresetCloudUrl http://<服务器 IP>:8090 `
  -PresetJwt <服务器 cloud.env 里那串 64 hex>

# 上传到服务器（覆盖 /opt/mjq-handynotes/public-downloads/ 下的旧 zip）
pscp -pw <密码> dist\zsnoot-agent-v1.0.0-bundled.zip `
  root@<服务器 IP>:/opt/mjq-handynotes/public-downloads/zsnoot-agent-v1.0.0.zip
```

服务器的 nginx 已配 `/downloads/` 公开此目录（见 `deploy/README.md`）。

### 3.4 本机 agent 连服务器 —— 手工方式（开发 / 调试用）

不打包，直接 git clone 跑：

```powershell
# Windows PowerShell（Mac / Linux 用 export）
$env:MJQ_CLOUD_URL    = "http://<服务器 IP>"
$env:MJQ_JWT_SECRET   = "<服务器 cloud.env 里那串 hex>"
$env:MJQ_LOCAL_CORS_ORIGINS = "http://<服务器 IP>"

python -m scripts.bind_user bind <自己的用户名>   # 与浏览器登录用名一致
python app.py                                       # 监听 127.0.0.1:5004
```

或者用现成脚本：`scripts\start_local_agent.bat`。

---

## 4. 第一次使用流程

### 4.1 管理员（admin）首次

> 服务器已部署完成、cloud 上还没有任何用户时

1. 浏览器开服务器地址 → 进入「初始化设置」
2. 填用户名 + 密码 + 单位 + 职务 + **选 schema 模板**（首次不可改，后续可在维护抽屉里自定义）
3. 注册成功 → **同页下方点「下载本机客户端」** → 70 MB zip
4. 解压、双击 `setup.bat` → 填用户名（与刚才注册一致）→ 双击 `start.bat`
5. 浏览器进主界面 → 弹「原始材料 raw 目录」对话框 → 选默认或自定义路径
6. 「系统配置」→ 填 LLM API key（**不会同步到云端**）→ 点测试连接
7. 「系统配置」→ 用户与邀请码 → 生成邀请码发给同事

### 4.2 成员（member）注册

1. 服务器地址 → 切到「注册」tab
2. 填邀请码 + 用户名 + 密码 + 单位 + 职务 + **选 schema 模板**
3. **同页下方点「下载本机客户端」** → 解压 → 双击 `setup.bat` → 填刚注册的用户名
4. 双击桌面「知枢」图标启动 agent
5. 浏览器进主界面 → 弹 raw 目录对话框 → 选默认 → 「系统配置」填 LLM key

### 4.3 日常用法

- **打开 agent**：双击桌面「知枢」图标（必须开着 agent 才能与本机数据交互）
- **打开 web**：浏览器到 `http://<服务器 IP>:8090`
- **拖文件入库**：左栏「上传材料」→ 拖 N 个文件 → 看进度 → 看产出的卡片
- **查问题**：左栏「对话查询」→ 自然语言问 → 答案带来源
- **看图谱**：左栏「关系图谱」→ 选排布方式 → 点节点看一度邻居
- **维护**：左栏「知识库体检」→ 看 4 张概览 → 点「处理」批量修
- **定时任务**：左栏底部「知识维护」→ 定时任务 tab → 建一个"每天 02:00 体检"

---

## 5. 配置与环境变量

### 5.1 用户级（在本机 `.env`，每用户独立）

| 字段 | 说明 |
|------|------|
| `LLM_API_KEY` | LLM 服务 API key（OpenAI 兼容协议） |
| `LLM_BASE_URL` | 例如 `https://api.deepseek.com/v1` |
| `LLM_MODEL` | 例如 `deepseek-chat` 或 `gpt-4o-mini` |
| `LLM_PROVIDER` | `openai` / `deepseek` 等（影响个别字段） |
| `VISION_MODEL_*` | 图片解析专用模型（可与 LLM 不同） |
| `OCR_MODEL_*` | OCR 专用模型 |

可视化在主界面"系统配置"修改。

### 5.2 进程级（环境变量，本机 agent 启动时）

| 变量 | 默认 | 说明 |
|------|------|------|
| `MJQ_CLOUD_URL` | `http://127.0.0.1:5005` | 云端 baseURL |
| `MJQ_JWT_SECRET` | 自动生成 | **必须与云端同**，跨进程验签的共享密钥 |
| `MJQ_LOCAL_CORS_ORIGINS` | dev 端口 | 哪些前端域名允许跨域调本机 |
| `MJQ_USER_HOME` | `~/.handynotes` | 用户数据根（测试用，生产别动） |
| `MJQ_AUTOBIND` | 不开 | 1=首个有效 JWT 自动绑定（开发友好） |
| `MJQ_AGENT_TOKEN` | 空 | 心跳后台线程用的长期 token（P5+ 工程债） |

### 5.3 云端（服务器 `/opt/mjq-handynotes/cloud.env`）

| 变量 | 说明 |
|------|------|
| `MJQ_CLOUD_HOST` / `PORT` | 监听地址（生产建议 `127.0.0.1:5005`，前面挂 Nginx） |
| `MJQ_JWT_SECRET` | **必须与本机 agent 同** |
| `MJQ_CLOUD_CORS_ORIGINS` | 前端来源白名单 |
| `MJQ_CLOUD_LLM_API_KEY` | Schema 合成 agent 的独立 LLM key（可选；不设走 mock） |
| `MJQ_CLOUD_LLM_BASE_URL` / `MODEL` | 同上 |

---

## 6. 数据存储与隐私

### 6.1 哪些放本机（每用户独立）

- `~/.handynotes/<u>/wiki/`        所有知识页（markdown）
- `~/.handynotes/<u>/raw/sources/` 上传归档的原文
- `~/.handynotes/<u>/data/`        批次元数据 / 活动日志 / scheduled_tasks / schema_binding
- `~/.handynotes/<u>/config/`      schema.yaml / config.yaml
- `~/.handynotes/<u>/.env`         **LLM API key 等敏感凭据**
- `~/.handynotes/<u>/embeddings/`  向量缓存（路线图）
- `~/.handynotes/<u>/mjq.log`      结构化日志

### 6.2 哪些放云端

- `cloud/data/users.json`         用户名 / **哈希密码** / role / unit / title / template_key
- `cloud/data/invite_codes.json`  邀请码（一次性）
- `cloud/data/heartbeats.json`    每用户最近一次心跳计数（无任何语料）
- `cloud/templates/*.yaml`        5 套 schema 模板（公共）
- `<install>/config/jwt.secret`   云本机共享的 JWT 签名密钥

### 6.3 LLM 调用路径

- 用户语料 → 用户**自己的本机 LLM key** → LLM 服务（点对点）
- Schema 合成（仅元数据）→ **云端独立 LLM key**（与用户分开计费）

---

## 7. API 概览

### 7.1 云端 (`/api/cloud/*`)

| 路径 | 方法 | 说明 |
|------|------|------|
| `/api/cloud/health` | GET | 健康 + 能力披露（前端连接灯用） |
| `/api/cloud/auth/{status,setup,login,register,refresh,logout,change-password}` | GET/POST | 鉴权流程 |
| `/api/cloud/admin/invites` | GET/POST/DELETE | 邀请码 CRUD（admin） |
| `/api/cloud/admin/users` | GET | 用户表 + 心跳（admin） |
| `/api/cloud/schema/templates` | GET | 5 套模板概览（公开） |
| `/api/cloud/schema/template/<key>` | GET | 模板完整内容 |
| `/api/cloud/schema/me` | GET | 当前用户 schema（custom > template） |
| `/api/cloud/schema/synthesize` | POST | LLM 合成 schema（goal+objects） |
| `/api/cloud/schema/apply-custom` | POST | 把合成结果存为用户 custom schema |
| `/api/cloud/agent/heartbeat` | POST | 本机 agent 心跳上报 |

### 7.2 本机 agent (`/api/*`)

| 分类 | 路径 | 方法 | 说明 |
|---|---|---|---|
| **健康** | `/api/health` | GET | 公开端点；前端连接灯 |
| **页面** | `/api/wiki/pages` | GET / POST | 列出 / 创建（POST 默认只读保护） |
|         | `/api/wiki/pages/<slug>` | GET / PUT / DELETE | 读 / 改 / 删 |
|         | `/api/wiki/categories` | GET | schema-aware 子目录列表 |
|         | `/api/wiki/index` / `log` | GET | 索引与活动日志 |
| **入库** | `/api/ingest/upload` | POST | 上传材料 |
|         | `/api/ingest/batches` | GET/DELETE | 批次列表 |
|         | `/api/ingest/batches/<id>/{rollback,reparse}` | POST | 回滚 / 二次解析 |
|         | `/api/ingest/{stale,retry-stale}` | GET/POST | 待精炼队列管理 |
| **检索** | `/api/search` | GET | 关键词加权检索 |
|         | `/api/chat` | POST | 对话查询（带源引用） |
| **图谱** | `/api/graph` / `/api/graph/merged` | GET | 全图 / 合并视图 |
| **体检** | `/api/lint` | GET | 4 类问题 + health_score |
|         | `/api/lint/fix` | POST | 按类别批量修复 |
| **维护** | `/api/orphans/scan` | GET | 孤立扫描（被 lint 复用） |
|         | `/api/orphans/dangling/auto-fill` | POST | 批量补占位页 |
|         | `/api/orphans/index/refresh` | POST | 写孤页区块到 index.md |
| **预览** | `/api/source/preview?path=&format=` | GET | 解析任意 raw 文件 |
|         | `/api/source/raw?path=` | GET | 流式二进制 |
| **调度** | `/api/schedule/tasks` | GET/POST/PUT/DELETE | 定时任务 CRUD |
|         | `/api/schedule/tasks/<id>/run-now` | POST | 立即触发 |
| **配置** | `/api/config` | GET/PUT | 读 / 写本机配置 |
|         | `/api/config/test-llm` | POST | 测 LLM 连通性 |
| **统计** | `/api/stats` | GET | 首页 dashboard 数据 |
|         | `/api/activity` | GET | 最近活动 |
|         | `/api/agent/status` | GET | 入库实时进度 |

详见 `app.py`（本机 60+ 路由）和 `cloud/main.py`（云端 17 路由）。

---

## 8. 目录结构

```
zsnoot/
├── app.py                       本机 agent 入口
├── auth.py                      用户/邀请码（共享给 cloud）
├── auto_ingest.py               入库流水线（schema-aware）
├── ingest_service.py            批次编排（并发）
├── ingest_batches.py            批次元数据
├── file_parser.py               多格式解析（懒加载依赖）
├── file_watcher.py              inbox 文件监听
├── graph.py                     图谱构建 + run_lint（唯一健康源）
├── wiki_links.py                [[wiki-link]] 双向链接
├── llm_client.py                用户 LLM 调用器（读用户 .env）
├── llm_tester.py                LLM 连通性
├── activity_log.py              活动日志（首页 KPI 数据源）
├── agent_status.py              入库实时进度
├── config_store.py              .env / config.yaml 读写
├── mjq_logging.py               结构化 logging
├── schema_runtime.py            (P2-A) 运行时 schema 解析
├── user_data.py                 (P2-B) install_dir vs user_data_dir
├── agent_bootstrap.py           (P2)   首登从云拉 schema
├── orphan_detector.py           (P3)   孤立 + 占位补齐工具
├── scheduler.py                 (P4)   APScheduler 单例
├── heartbeat.py                 (P5)   心跳上报
│
├── cloud/
│   ├── main.py                  云端 Flask
│   ├── jwt_utils.py             共享密钥 / 签发 / 验签
│   ├── auth_service.py 复用根 auth.py
│   ├── llm.py                   云端独立 LLM 调用
│   ├── schema_synth.py          LLM 合成 agent
│   ├── templates_service.py     模板加载
│   ├── templates_/*.yaml        5 套预置 schema
│   ├── heartbeat_store.py       心跳持久化
│   └── README.md                云端启动详解
│
├── deploy/
│   ├── install.sh               一键部署
│   ├── cloud.service            systemd 单元
│   ├── nginx.conf               Nginx 站点
│   ├── cloud.env.example        环境变量模板
│   └── README.md                部署指南（含 HTTPS 切换）
│
├── scripts/
│   ├── bind_user.py             本机绑定 CLI
│   ├── start.{bat,ps1}          单体一键
│   ├── start_split.{bat,ps1}    分离一键（本机起三进程：cloud+agent+frontend）
│   ├── start_local_agent.{bat,ps1}  仅启动本机 agent（连远端云）
│   ├── start_local_dev.{bat,ps1}    agent + frontend dev（最常用开发组合）
│   └── retry_stale.py           批量重试待精炼
│
├── installer/                   一键安装包构建（给同事发的成品）
│   ├── build_release.ps1        bundled / lite 双模式打包
│   ├── setup.{bat,ps1}          首次配置（自动读 preset.ini）
│   ├── start.{bat,ps1}          日常启动（读 config.ini）
│   ├── stop.{bat,ps1}           停止
│   └── README.txt               给最终用户看的中文说明
│
├── frontend/
│   ├── src/App.vue              主组件
│   ├── src/styles.css           全局样式
│   ├── src/apiClient.js         双 baseURL + JWT 客户端
│   ├── src/{graphLayouts,pageSorting,chatSources}.js
│   └── .env.example             VITE_CLOUD_API / VITE_LOCAL_API
│
├── tests/
│   ├── test_full_e2e.py         (P1-P5) 32 项断言
│   └── test_*.py                既有 92 用例
│
├── purpose.md                   产品定位
├── schema.md                    Wiki 数据规范（可读版）
└── README.md                    本文件
```

---

## 9. 测试

```bash
# 既有单元测试（92 用例）
python -m pytest tests/ --ignore=tests/test_full_e2e.py -q

# 全链路 E2E（32 断言；启动临时云端 + 本机 agent）
python tests/test_full_e2e.py
```

E2E 覆盖 P1-P5 所有架构契约：进程边界 / JWT 双向 / 5 模板注册 / 数据隔离 / Schema 合成 / 孤立扫描与补齐 / 文档预览 / 定时任务 / 心跳 / admin 视图。

---

## 10. 故障排查

| 现象 | 排查方向 |
|------|----------|
| 浏览器报 "无法连接后端" | 检查云端 `systemctl status mjq-cloud`；浏览器硬刷 `Ctrl+Shift+R` |
| 报 "Failed to fetch"（GET 通、POST/PUT 失败）| **Chrome PNA 拦了**：公网页面到 127.0.0.1 需要 `Access-Control-Allow-Private-Network`。已在 0.4 修复；老版本 agent 升级到 c662735+ 或重下 zip |
| 报 "Failed to fetch"（所有请求都失败）| 本机 agent 没启 / CORS 白名单缺当前域名 |
| 报 `agent_not_bound` (412) | 本机没绑：`python -m scripts.bind_user bind <name>` 后重启 agent；或重跑 `setup.bat` |
| 报 `wrong_user` (403) | JWT.sub 与本机绑定不一致；登录的用户名要与 `bind_user` 的相同 |
| setup.bat 报 `No module named 'scripts'` | 内嵌 Python 的 `python311._pth` 缺 `..` 那行。已在 505980f 修复；老 zip 手工编辑加入 `..` 或重下 |
| 上传后批次"待精炼"很多 | `python scripts/retry_stale.py --list` 看清单；`--all --limit 5` 试跑 |
| LLM 调用慢 / 失败 | 系统配置点"测试连接"；查 `~/.handynotes/<u>/data/llm_calls.jsonl` |
| schema 没切换 | 重启本机 agent（`PROJECT_DIR` 是模块级，需要重启） |
| 端口被占 | `scripts\stop.bat`（单体）/ `stop_split.bat`（分离）/ 安装包里的 `stop.bat` |
| nginx 502 但 cloud `active` | `journalctl -u mjq-cloud -n 50` 看 cloud 报错；通常是 cloud crash |
| 占位页满天飞 | 体检 → 占位页 tab → 智能补全或批量删除 |
| zip 下载链接打不开 | 看 `/opt/mjq-handynotes/public-downloads/` 文件是否在；nginx `/downloads/` 配置在；安全组放通 8090 |

日志位置：
- 本机 agent：`~/.handynotes/<u>/mjq.log` + `data/llm_calls.jsonl`
- 云端：`journalctl -u mjq-cloud -f`
- nginx：`/var/log/nginx/{access,error}.log`

---

## 11. 路线图

### 已完成（自 Web V1.0 发布起）

- [x] **一键安装包**：内嵌 Python 3.11 + server-baked preset.ini → 用户解压、双击、填一个用户名就能用（70 MB zip）
- [x] **服务器下载入口**：注册页直接挂"下载本机客户端"按钮（nginx `/downloads/`）
- [x] **Chrome PNA 兼容**：本机 agent 应答 `Access-Control-Allow-Private-Network`，公网页面到 127.0.0.1 不再被拦
- [x] **桌面快捷方式**：setup.bat 自动建桌面「知枢」图标
- [x] **健康检查统一**：体检页 4 类问题（断链/孤立/过期/占位）成唯一入口，KPI 可点

### 短期

- [ ] 占位页可视化：卡片视图加"待补充"徽章；列表过滤"只看占位"
- [ ] 修复带 preview：自动补齐前先让用户看 LLM 草稿，确认后再写盘
- [ ] 健康度公式可视化（可调权重）
- [ ] agent_key 长期令牌（替换 `MJQ_AGENT_TOKEN` 工程债）
- [ ] inbox_scan 真正触发入库（当前只数文件）
- [ ] admin 控制台铺前端（邀请码 / 模板 / 撤销用户）
- [ ] 真向量检索（embedding-based RAG）

### 中期

- [ ] PostgreSQL 替换云端 JSON 存储
- [ ] Markdown 实时编辑器（图片粘贴上传 / 实时预览）
- [ ] 移动端响应式
- [ ] 多用户协作的 diff/merge

### 长期

- [ ] 桌面端打包（Tauri / Electron 包本机 agent）
- [ ] 私有化部署一键工具（含 LLM 模型预下载）

---

## 12. 工程原则

代码遵循《工程控制论》范式（详见 `~/.claude/CLAUDE.md` 镜像）：

- **原则 1**：实践是检验唯一标准 —— 每个阶段都有 E2E 验证（92 + 32 通过）
- **原则 4**：区分技术革新 vs 革命 —— 云本机分离是革命，按重写而非改造规划
- **原则 5**：先讲清"系统"四要素（边界 / 组成 / 相互制约 / 目标功能）
- **原则 9**：反馈环最短 —— 单文件 schema、即时心跳、可点击 KPI
- **原则 12**：稳定性优先于性能 —— 失败兜底先于优化
- **原则 14**：关键路径必有兜底 —— 云挂了本机仍能跑；LLM 失败 mock 顶上

---

## 13. 鸣谢

- 产品 / 业务设计：数合云智
- 前端组件库：Element Plus
- 图可视化：D3.js
- 调度：APScheduler
- 灵感来源：Obsidian 的 [[wiki-link]] 知识网络范式

## 14. License

内部项目；外部使用请联系数合云智。
