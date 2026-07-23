# 🚀 部署指南 — 让所有人都能访问你的旅行规划师

三种方案按难度排序：Streamlit Cloud（免费/最简单）→ HuggingFace（免费/全球加速）→ 自部署（最灵活）。

---

## 方案一：Streamlit Community Cloud ⭐ 推荐入门

**免费 | 5 分钟上线 | 自动 HTTPS**

### 1. 推送到 GitHub

```bash
# 在项目根目录
git init
git add -A
git commit -m "feat: 智行规划师 v1.0"

# 创建 GitHub 仓库后推送
git remote add origin https://github.com/你的用户名/travel-planner.git
git branch -M main
git push -u origin main
```

### 2. 连接 Streamlit Cloud

1. 打开 [share.streamlit.io](https://share.streamlit.io)
2. 用 GitHub 账号登录
3. 点击 **New app** → 选择仓库 `travel-planner`
4. **Main file path**: `app.py`（已经在根目录）
5. 点击 **Advanced settings** → **Secrets**，填入：

```toml
OPENAI_API_KEY = "sk-你的key"
OPENAI_BASE_URL = "https://api.deepseek.com"
OPENAI_MODEL = "deepseek-v4-flash"
MAP_API_KEY = "高德地图key（可选）"
```

6. 点击 **Deploy!** 🎉

**URL 格式**: `https://你的用户名-travel-planner.streamlit.app`

> ⚠️ 国内访问可能较慢，建议用方案二或三。

---

## 方案二：HuggingFace Spaces ⭐ 推荐国内

**免费 | 5 分钟上线 | 国内访问较快 | 自带 HTTPS**

### 1. 推送到 GitHub（同上）

### 2. 创建 Space

1. 打开 [huggingface.co/new-space](https://huggingface.co/new-space)
2. **Space name**: `travel-planner`
3. **SDK**: `Streamlit`
4. **Visibility**: `Public`
5. 创建后，在 **Settings → Secrets** 中添加：

```
OPENAI_API_KEY = sk-你的key
OPENAI_BASE_URL = https://api.deepseek.com
OPENAI_MODEL = deepseek-v4-flash
```

6. 克隆 Space 仓库并推送代码：

```bash
git clone https://huggingface.co/spaces/你的用户名/travel-planner
cp -r 旅游规划/* travel-planner/
cd travel-planner
git add -A && git commit -m "deploy" && git push
```

**URL 格式**: `https://huggingface.co/spaces/你的用户名/travel-planner`

---

## 方案三：自部署（阿里云 / 腾讯云）

**完全控制 | 自定义域名 | 国内最优速度**

### 1. 购买服务器

| 平台 | 推荐机型 | 参考价格 |
|------|---------|---------|
| 阿里云 ECS | 2核4G，CentOS 7.9 | ~68元/月 |
| 腾讯云轻量 | 2核4G，Ubuntu 22.04 | ~58元/月 |

### 2. 安装 Docker（服务器上）

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

### 3. 部署

```bash
# 上传项目到服务器
scp -r . root@你的服务器IP:/opt/travel-planner/

# SSH 进入服务器
ssh root@你的服务器IP

# 构建并运行
cd /opt/travel-planner
docker build -t travel-planner .
docker run -d \
  --name travel-planner \
  --restart always \
  -p 8501:8501 \
  -e OPENAI_API_KEY=sk-你的key \
  -e OPENAI_BASE_URL=https://api.deepseek.com \
  -e OPENAI_MODEL=deepseek-v4-flash \
  -e MAP_API_KEY=你的高德key \
  travel-planner
```

### 4. 配置 Nginx + 域名 + HTTPS

```bash
# 安装 Nginx
apt install -y nginx certbot python3-certbot-nginx

# 配置反向代理 (替换 your-domain.com)
cat > /etc/nginx/sites-available/travel-planner << 'EOF'
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }
}
EOF

ln -s /etc/nginx/sites-available/travel-planner /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

# 免费 SSL 证书
certbot --nginx -d your-domain.com
```

---

## 配置对比

| 项目 | 本地 | Streamlit Cloud | HuggingFace | 自部署 |
|------|------|----------------|-------------|--------|
| API Key | `.env` 文件 | Dashboard Secrets | Settings Secrets | 环境变量 `-e` |
| 入口文件 | `frontend/app.py` | `app.py` | `app.py` | `app.py` |
| URL | localhost | `.streamlit.app` | `hf.co/spaces/` | 自定义域名 |
| HTTPS | ❌ | ✅ 自动 | ✅ 自动 | ✅ certbot |
| 费用 | 免费 | 免费 | 免费 | ~60元/月 |
| 国内速度 | ⚡ | 🐢 | 🚀 | ⚡ |
