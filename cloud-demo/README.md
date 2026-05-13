# 知枢云端体验 Demo

这是面向外部用户试用的云端体验版。它和正式本地部署版的定位不同：

- 体验版：用户上传的材料会暂存在云端服务器，仅用于试用功能。
- 正式版：推荐部署在用户本地电脑或内网服务器，源文件、raw 归档和 wiki 产物都保存在本地。

## 体验版限制

- 默认开启 `DEMO_MODE=true`。
- 默认关闭公开初始化：`DEMO_ALLOW_SETUP=false`，避免陌生用户抢占管理员账号。
- 默认最多注册 `DEMO_MAX_USERS=20` 个用户。
- 每个用户最多上传 `DEMO_MAX_UPLOAD_FILES_PER_USER=20` 个文件。
- 每个用户使用独立工作区：`runtime/users/<username>/`，不同用户之间的 raw、wiki、data 相互隔离。

## 目录说明

```text
cloud-demo/
├── app.py                 # 云端 demo 后端入口
├── auth.py                # 账号、邀请码、角色
├── ingest_service.py      # 上传解析与 wiki 生成
├── frontend/              # 云端 demo 前端
├── config/                # 非敏感默认配置
├── runtime/               # 运行时数据，部署时自动生成，不提交
└── tests/test_cloud_demo.py
```

## 环境变量

```bash
DEMO_MODE=true
DEMO_ALLOW_SETUP=false
DEMO_MAX_USERS=20
DEMO_MAX_UPLOAD_FILES_PER_USER=20
DEMO_RUNTIME_DIR=./runtime

LLM_API_KEY=...
LLM_BASE_URL=...
LLM_MODEL=...
LLM_PROVIDER=openai
```

初始化管理员时可临时设置：

```bash
DEMO_ALLOW_SETUP=true
```

创建好管理员后，再改回 `false` 并重启服务。

## 本地启动

```bash
pip install -r requirements.txt
cd frontend
npm install
npm run build
cd ..
python app.py
```

访问 `http://127.0.0.1:5004/`。

## 数据清理

删除体验数据：

```bash
rm -rf runtime
```

Windows PowerShell：

```powershell
Remove-Item -Recurse -Force .\runtime
```

## 安全提示

体验版会把用户上传文件写入云端服务器，请在页面和用户说明中明确告知。正式交付或处理敏感材料时，应使用本地部署版。
