# 下载包清单

## 应包含

- `app.py`
- `auth.py`
- `activity_log.py`
- `agent_status.py`
- `auto_ingest.py`
- `config_store.py`
- `file_parser.py`
- `file_watcher.py`
- `graph.py`
- `ingest_batches.py`
- `ingest_service.py`
- `llm_client.py`
- `llm_tester.py`
- `mjq_logging.py`
- `note_intake.py`
- `wiki_links.py`
- `requirements.txt`
- `.env.example`
- `config/`
- `frontend/package.json`
- `frontend/package-lock.json` when present
- `frontend/src/`
- `frontend/public/`
- `frontend/vite.config.js`
- `templates/`
- `scripts/retry_stale.py`
- `desktop-release/`
- `README.md`
- `purpose.md`
- `schema.md`

## 同步说明

desktop-release 打包脚本直接复制根目录的 `app.py`、`agent_status.py`、`note_intake.py` 和 `frontend/src/`。因此首页近期动态、智能体状态样式和新建笔记入口以根目录版本为准，不维护第二套桌面端源码。

## 首次运行时生成

- `.env`
- `frontend/dist/`
- `frontend/node_modules/`
- `data/`
- `wiki/`
- `raw/`
- `mjq.log`
- `desktop-release/runtime/`

## 不应包含

- `.git/`
- `.env`
- `data/users.json`
- `data/invite_codes.json`
- `data/llm_calls.jsonl`
- `wiki/` 中的真实客户知识库数据
- `raw/` 中的真实客户原始材料
- `*.log`
- `*.pid`
- `__pycache__/`
- `.test-tmp/`
- `test-tmp/`
- `node_modules/`
- `frontend/dist/` unless publishing a prebuilt package
- `cloud-demo/`

## 推荐发布形态

第一版可以发布为 zip：

```text
mjq-handynotes-desktop-v0.1.0-windows.zip
```

可用以下命令生成：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File desktop-release\build-package.ps1 -Version 0.1.0
```

解压后目录结构：

```text
mjq-handynotes/
  app.py
  requirements.txt
  frontend/
  config/
  desktop-release/
    install.ps1
    start-desktop.bat
    stop-desktop.bat
```
