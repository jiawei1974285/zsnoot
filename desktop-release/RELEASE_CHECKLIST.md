# A 版发布检查清单

## 发包前

- 确认 `.env` 不包含在下载包里。
- 确认 `data/`、`wiki/`、`raw/` 中没有客户真实数据。
- 确认 `frontend/package-lock.json` 存在时一起打包，便于复现依赖。
- 运行 `desktop-release\install.ps1 -DryRun`。
- 运行 `desktop-release\start-desktop.ps1 -DryRun`。
- 运行 `desktop-release\stop-desktop.ps1 -DryRun`。
- 运行 `desktop-release\build-package.ps1 -DryRun`。

## 生成下载包

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File desktop-release\build-package.ps1 -Version 0.1.0
```

输出：

```text
release-output\mjq-handynotes-desktop-v0.1.0-windows.zip
```

## 干净机器验证

1. 解压 zip。
2. 运行 `desktop-release\install.ps1`。
3. 双击 `desktop-release\start-desktop.bat`。
4. 浏览器打开后完成首个管理员初始化。
5. 配置 LLM。
6. 新建或上传一条测试笔记。
7. 确认知识页、关系抽取和图谱都能看到结果。
8. 双击 `desktop-release\stop-desktop.bat`，确认 5004 端口释放。

## 授权验证

- 无许可证：系统进入未授权/试用状态，不能误删数据。
- 有效许可证：商业功能可用。
- 过期许可证：进入只读或受限模式。
- 机器不匹配：阻止商业功能。
- 篡改许可证：签名失败，记录日志。

