#!/usr/bin/env bash
# 一键部署脚本：把 mjq-handynotes 的云端控制面 + 前端 SPA 装到 Linux 服务器
# 测试过的环境：Ubuntu 22.04 / Debian 12 / CentOS Stream 9
#
# 用法（在服务器上以 root 或 sudo 跑）：
#   curl https://github.com/jiawei1974285/zsnoot/raw/web-v1.0/deploy/install.sh | bash -s -- <SERVER_IP_OR_DOMAIN>
# 或者：
#   git clone -b web-v1.0 https://github.com/jiawei1974285/zsnoot.git /opt/mjq-handynotes
#   cd /opt/mjq-handynotes && sudo bash deploy/install.sh <SERVER_IP_OR_DOMAIN>

set -euo pipefail

SERVER_HOST="${1:?usage: $0 <server-ip-or-domain>}"
INSTALL_DIR="/opt/mjq-handynotes"
SERVICE_USER="mjq"

if [[ $EUID -ne 0 ]]; then
   echo "请用 sudo 或 root 运行" >&2
   exit 1
fi

echo "==> 部署目标：$SERVER_HOST  →  $INSTALL_DIR"

# ─── 1. 系统依赖 ───────────────────────────────────
echo "==> 安装系统依赖..."
if command -v apt-get &>/dev/null; then
    apt-get update -y
    apt-get install -y python3 python3-venv python3-pip nginx git nodejs npm curl
elif command -v dnf &>/dev/null; then
    dnf install -y python3 python3-pip nginx git nodejs npm curl
else
    echo "未识别的包管理器，请手动装 python3/nginx/nodejs" >&2; exit 1
fi

# ─── 2. 服务账号 ───────────────────────────────────
if ! id -u "$SERVICE_USER" &>/dev/null; then
    useradd --system --home-dir "$INSTALL_DIR" --shell /usr/sbin/nologin "$SERVICE_USER"
    echo "==> 创建系统账号 $SERVICE_USER"
fi

# ─── 3. 代码就位 ───────────────────────────────────
if [[ ! -d "$INSTALL_DIR/.git" ]]; then
    echo "==> $INSTALL_DIR 还没有代码，请先 git clone"
    echo "    sudo git clone -b web-v1.0 https://github.com/jiawei1974285/zsnoot.git $INSTALL_DIR"
    exit 1
fi
cd "$INSTALL_DIR"

# ─── 4. Python venv + 依赖 ─────────────────────────
if [[ ! -d "$INSTALL_DIR/.venv" ]]; then
    echo "==> 创建 Python venv"
    python3 -m venv .venv
fi
"$INSTALL_DIR/.venv/bin/pip" install --upgrade pip wheel
"$INSTALL_DIR/.venv/bin/pip" install -r requirements.txt

# ─── 5. cloud.env ──────────────────────────────────
if [[ ! -f "$INSTALL_DIR/cloud.env" ]]; then
    JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    cat > "$INSTALL_DIR/cloud.env" <<EOF
MJQ_CLOUD_HOST=127.0.0.1
MJQ_CLOUD_PORT=5005
MJQ_JWT_SECRET=$JWT_SECRET
MJQ_CLOUD_CORS_ORIGINS=http://$SERVER_HOST,http://localhost:5174
MJQ_CLOUD_DEBUG=false
EOF
    chmod 600 "$INSTALL_DIR/cloud.env"
    chown root:"$SERVICE_USER" "$INSTALL_DIR/cloud.env"
    echo "==> 已生成 $INSTALL_DIR/cloud.env（含随机 JWT 密钥）"
    echo "    ★ 把这里的 MJQ_JWT_SECRET 同步给本机 agent，否则 JWT 无法跨进程互认"
    grep MJQ_JWT_SECRET "$INSTALL_DIR/cloud.env"
fi

# ─── 6. 前端构建 ───────────────────────────────────
echo "==> 构建前端..."
cd "$INSTALL_DIR/frontend"
npm install --no-audit --no-fund

# 构建时 baked 进 dist 的环境变量
cat > .env.production <<EOF
VITE_CLOUD_API=http://$SERVER_HOST
VITE_LOCAL_API=http://127.0.0.1:5004
EOF
npm run build
cd "$INSTALL_DIR"

# ─── 7. 目录权限 ───────────────────────────────────
mkdir -p cloud/data config
chown -R "$SERVICE_USER:$SERVICE_USER" cloud/data config
chmod -R u+rwX,g+rX,o-rwx cloud/data config

# Nginx 要能读静态文件
chmod -R o+rX frontend/dist

# ─── 8. systemd ────────────────────────────────────
cp deploy/cloud.service /etc/systemd/system/mjq-cloud.service
systemctl daemon-reload
systemctl enable --now mjq-cloud
sleep 2
systemctl status mjq-cloud --no-pager -l | head -15 || true

# ─── 9. Nginx ──────────────────────────────────────
NGINX_SITE="/etc/nginx/sites-available/mjq-cloud"
if [[ -d /etc/nginx/sites-available ]]; then
    cp deploy/nginx.conf "$NGINX_SITE"
    ln -sf "$NGINX_SITE" /etc/nginx/sites-enabled/mjq-cloud
    # 关掉默认站点防止抢 listen 80 default_server
    rm -f /etc/nginx/sites-enabled/default
else
    cp deploy/nginx.conf /etc/nginx/conf.d/mjq-cloud.conf
fi
nginx -t
systemctl reload nginx

# ─── 10. 自检 ──────────────────────────────────────
echo "==> 部署完成，自检："
sleep 1
echo "  cloud /api/cloud/health（直连 :5005）："
curl -s http://127.0.0.1:5005/api/cloud/health | head -c 200; echo
echo "  Nginx 反代（公网）："
curl -s -m 5 "http://$SERVER_HOST/api/cloud/health" | head -c 200; echo
echo "  前端首页："
curl -sI -m 5 "http://$SERVER_HOST/" | head -1

cat <<EOF

═════════════════════════════════════════════════════
  部署完成 ✓
  浏览器打开： http://$SERVER_HOST
  日志查看：    sudo journalctl -u mjq-cloud -f
  重启服务：    sudo systemctl restart mjq-cloud

  下一步：把 cloud.env 里的 MJQ_JWT_SECRET 同步给每个本机 agent
  本机 agent 启动时设：
    export MJQ_JWT_SECRET=...（与服务器同一份）
    export MJQ_CLOUD_URL=http://$SERVER_HOST
═════════════════════════════════════════════════════
EOF
