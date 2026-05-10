# 服务器部署指南（mjq-cloud Web V1.0）

把云端控制面（5005）+ 前端 SPA 部署到一台 Linux 服务器；本机 agent
仍然在每个用户自己的 Windows/Mac 上跑。

## 架构示意

```
                            ┌─────────────────────────────────┐
                            │       服务器 (Linux + IP)        │
                            │                                 │
   浏览器 ──http──►          │   Nginx :80                     │
                            │     ├─ /            → frontend/dist
                            │     └─ /api/cloud/* → 127.0.0.1:5005
                            │                                 │
                            │   systemd: mjq-cloud (5005)      │
                            │     ↓                            │
                            │   cloud/data/users.json …       │
                            └─────────────────────────────────┘
                                          │
                                          │ JWT
                                          ▼
                            ┌─────────────────────────────────┐
                            │  用户自己电脑上跑：python app.py    │
                            │  ~/.handynotes/<user>/{wiki,raw}│
                            └─────────────────────────────────┘
```

## 一键安装

```bash
# 服务器上（root 或 sudo）
sudo git clone -b web-v1.0 https://github.com/jiawei1974285/zsnoot.git /opt/mjq-handynotes
cd /opt/mjq-handynotes
sudo bash deploy/install.sh <服务器公网 IP>
```

脚本完成后会输出 `MJQ_JWT_SECRET`——**这个值要复制下来**，发给每个本机 agent 用户。

## 验收

```bash
# 1. cloud 进程
sudo systemctl status mjq-cloud
# 2. cloud 直连
curl http://127.0.0.1:5005/api/cloud/health
# 3. 经 Nginx
curl http://<IP>/api/cloud/health
# 4. 前端
curl -I http://<IP>/
```

浏览器打开 `http://<服务器 IP>`，应看到登录/初始化页面。

## 本机 agent 怎么连这台服务器

每个用户在自己电脑上：

```powershell
# Windows
$env:MJQ_CLOUD_URL    = "http://<服务器 IP>"
$env:MJQ_JWT_SECRET   = "服务器 cloud.env 里那一串 64 位 hex"
$env:MJQ_LOCAL_CORS_ORIGINS = "http://<服务器 IP>"

# 绑定本机到云端用户名（与浏览器里要登录的用户名一致）
python -m scripts.bind_user bind alice

# 启动本机 agent
python app.py
```

之后 alice 在浏览器（连服务器 IP）上登录，所有数据落到她自己电脑的
`C:\Users\alice\.handynotes\alice\`，云端只见到用户名、心跳、计数。

## 常见问题

**Q：浏览器报 mixed content / "无法访问 127.0.0.1"**
HTTP 页面访问 HTTP localhost 是浏览器允许的，不会报 mixed content。
但如果以后切 HTTPS，浏览器对 https 页面访问 http://localhost 仍允许（localhost 例外），
访问 http://127.0.0.1 也允许，所以 token 流程仍能跑。但请优先用 `localhost` 字面量。

**Q：服务器打开页面但 API 401 / 412**
- 401：cloud 没启动 → `sudo systemctl status mjq-cloud`
- 412：本机 agent 未绑定 → 在用户电脑上 `python -m scripts.bind_user bind <name>` 后重启 agent

**Q：CORS error**
`cloud.env` 里 `MJQ_CLOUD_CORS_ORIGINS` 必须包含浏览器看到的 Origin
（`http://<IP>` 不带尾巴的 / ）。改完 `sudo systemctl restart mjq-cloud`。

**Q：日志在哪**
- cloud：`sudo journalctl -u mjq-cloud -f`
- nginx：`/var/log/nginx/access.log` 与 `error.log`
- 用户语料相关日志：在每个用户自己机器的 `~/.handynotes/<user>/mjq.log`

**Q：升级 / 拉新版**
```bash
cd /opt/mjq-handynotes
sudo -u root git fetch && sudo -u root git checkout <new-tag>
sudo -u root .venv/bin/pip install -r requirements.txt
sudo -u root bash -c 'cd frontend && npm install && npm run build'
sudo systemctl restart mjq-cloud
sudo systemctl reload nginx
```

## 加 HTTPS（买完域名后）

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
# certbot 会自动改 deploy/nginx.conf 加 ssl_certificate 段；
# 同时把 cloud.env 里 MJQ_CLOUD_CORS_ORIGINS 改成 https://your-domain.com
sudo systemctl restart mjq-cloud
```

通知用户更新本机 agent：
```powershell
$env:MJQ_CLOUD_URL = "https://your-domain.com"
```

## 文件清单

| 文件 | 用途 |
|------|------|
| `deploy/install.sh` | 一键部署脚本 |
| `deploy/cloud.service` | systemd 单元 |
| `deploy/cloud.env.example` | 环境变量模板（含密钥） |
| `deploy/nginx.conf` | Nginx 站点配置 |
| `deploy/README.md` | 本文档 |
