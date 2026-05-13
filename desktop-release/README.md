# 民警随手记桌面版一键部署包 A 版

这个目录是桌面版下载包的第一版方案。A 版不重写现有系统，而是把当前 Flask 后端和 Vue 前端包装成 Windows 本地一键部署、一键启动的形态。

## 用户体验目标

用户下载解压后只做两件事：

1. 首次运行 `install.ps1`，完成依赖安装、前端构建和基础目录初始化。
2. 后续双击 `start-desktop.bat` 启动系统，浏览器自动打开 `http://localhost:5004`。

停止系统时双击 `stop-desktop.bat`。

## A 版边界

- 运行在用户本机，不依赖公网服务器。
- 后端仍然是 `python app.py`。
- 前端使用 `frontend/dist`，由 Flask 静态服务承载。
- 数据仍然保存在本地 `wiki/`、`data/`、`raw/` 等目录。
- 商业授权先采用离线签名许可证设计，后续可以扩展在线激活。

## 文件说明

| 文件 | 用途 |
|---|---|
| `install.ps1` | 首次安装和构建 |
| `start-desktop.ps1` | 启动本地后端并打开浏览器 |
| `start-desktop.bat` | 双击入口，调用启动脚本 |
| `stop-desktop.ps1` | 停止本地后端 |
| `stop-desktop.bat` | 双击入口，调用停止脚本 |
| `PACKAGE_MANIFEST.md` | 下载包应包含和排除的文件 |
| `LICENSE_MODEL.md` | 商业授权模式和许可证管理设计 |
| `RELEASE_CHECKLIST.md` | 发包前和干净机器验证清单 |
| `build-package.ps1` | 生成 zip 下载包的发布脚本 |
| `license/example-license.json` | 示例许可证结构 |

## 发布前检查

- 在干净 Windows 机器上运行 `install.ps1`。
- 确认 `frontend/dist` 已生成。
- 双击 `start-desktop.bat` 后浏览器能打开登录/初始化页面。
- 上传或新建一条笔记后，确认图谱能展示关系。
- 确认 `.env` 未打包真实密钥，`data/`、`wiki/`、`raw/` 未混入客户数据。

## 后续工程任务

- 增加 `license_manager.py`，实现许可证解析、签名校验、过期校验和机器绑定校验。
- 增加 `/api/license/status`，供前端显示授权状态。
- 增加管理员上传许可证文件的 UI。
- 增加 Windows 快捷方式或安装器封装，降低用户看到脚本的概率。
