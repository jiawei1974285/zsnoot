# mjq-cloud（P1）

云端控制面，与本机 agent 配合实现「前端在云、数据在本机」的分离部署。

## 范围

P1（已完成）
- 用户认证（首位 admin、邀请码注册、登录、改密）
- 邀请码 CRUD（admin only）
- 颁发短期 JWT（access 30 min / refresh 30 day），HS256 共享密钥

P2-A（已完成）
- 5 套 schema 模板：警务/法律/财务营销/科研/通用
- 注册时选模板 + 本机首次有效 JWT 自动拉模板写 `config/schema.yaml`
- `wiki_links` / `auto_ingest` / `app.py` 全部从 schema_runtime 读运行时配置

P2-B（已完成）
- **本机 agent 必须绑定到一个 cloud 用户后才能接受 JWT**
- 用户数据目录隔离：`~/.handynotes/<cloud_username>/{wiki,raw,data,config,embeddings,.env}`
- 代码目录与数据目录分离：jwt.secret / frontend/dist / cloud/templates 留在 install dir
- JWT 中间件硬闸门：未绑定 → 412；绑定到 X 但收到 Y 的 token → 403

**P1 不做**（按计划文件 `1-2-whimsical-waffle.md` 第 P2/P3 阶段）：

- Schema 模板分发与合成
- 心跳 / admin 控制台
- PostgreSQL —— P1 仍用 JSON 文件，路径 `cloud/data/{users.json,invite_codes.json}`

## 启动

### 单体模式（默认，零配置）

不启动云端。`python app.py` 跑老路。前端 `vite.config.js` 的 proxy 指向 `127.0.0.1:5004`，与改造前完全一致。

### 分离模式（P2-B 起）

启动顺序：

1. 本机先绑定到某个云端用户（这是 JWT 校验的安全闸门）：

   ```bash
   python -m scripts.bind_user status         # 查看
   python -m scripts.bind_user bind alice     # 绑定
   python -m scripts.bind_user unbind         # 解除
   ```

   绑定后：所有数据落在 `~/.handynotes/alice/`；其他 cloud 用户的 JWT 一律 403 拒收。
   开发场景设 `MJQ_AUTOBIND=1` 可让首个有效 JWT 自动绑定（绑后需重启 agent）。

2. 三进程同时跑：

```bash
# 终端 1：本机 agent
export MJQ_LOCAL_CORS_ORIGINS="http://localhost:5174"
python app.py

# 终端 2：云端控制面
export MJQ_CLOUD_PORT=5005
export MJQ_CLOUD_CORS_ORIGINS="http://localhost:5174"
python -m cloud.main

# 终端 3：前端 dev
cd frontend
cp .env.example .env.local
# 编辑 .env.local：
#   VITE_CLOUD_API=http://127.0.0.1:5005
#   VITE_LOCAL_API=http://127.0.0.1:5004
npm run dev
```

浏览器打开 `http://localhost:5174`：

1. 没有用户 → setup 页面 → 创建首位 admin（请求发到 cloud:5005）
2. 拿到 access + refresh token，存浏览器 localStorage
3. 之后所有 `/api/cloud/*` 请求带 `Authorization: Bearer <access>` 发到云端
4. 所有 `/api/*` 数据请求带同一 Bearer token 发到本机 agent:5004
5. 本机 agent 验签后用 `g.user` 串起原有路由

## 环境变量

| 变量 | 默认 | 说明 |
|------|------|------|
| `MJQ_CLOUD_HOST` | `0.0.0.0` | 云端绑定地址 |
| `MJQ_CLOUD_PORT` | `5005` | 云端端口 |
| `MJQ_CLOUD_DEBUG` | `false` | Flask debug 模式 |
| `MJQ_CLOUD_CORS_ORIGINS` | dev 端口列表 | 逗号分隔的前端来源白名单 |
| `MJQ_JWT_SECRET` | 自动生成 | JWT 共享密钥；不设则读 `config/jwt.secret`（首次自动生成） |

**关键**：`MJQ_JWT_SECRET` 在云端和本机 agent 必须相同。生产部署：

```bash
# 一次性生成
python -c "import secrets; print(secrets.token_hex(32))"
# 拿到的字符串同时设置到云端和本机的环境变量里
```

不设环境变量时，两边都会读项目根的 `config/jwt.secret`——单机演示场景够用。

## 数据隔离

- `cloud/data/users.json` —— 云端用户表（与本机 `data/users.json` 是两套，**互不同步**）
- `cloud/data/invite_codes.json` —— 云端邀请码

**本机 `data/users.json` 在 P1 仍存在**，仅用于单体模式回滚。分离模式下这文件不被读取（JWT 中间件直接从 token claim 取用户名/角色）。P2 多租户阶段会废弃本机的 users.json。

## 已知 P1 局限

1. token 存浏览器 localStorage —— XSS 风险高于 httpOnly cookie；P2 改 cookie
2. 没有 token 黑名单 —— 登出靠客户端丢 token，被泄露的 token 30 min 内仍有效
3. 单机器、单 schema —— 多租户的 wiki 隔离要等 P2
