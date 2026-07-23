# ============================================
# 智行规划师 Docker 镜像
#
# 构建: docker build -t travel-planner .
# 运行: docker run -p 8501:8501 \
#          -e OPENAI_API_KEY=sk-xxx \
#          -e OPENAI_BASE_URL=https://api.deepseek.com \
#          -e OPENAI_MODEL=deepseek-v4-flash \
#          travel-planner
# ============================================

FROM python:3.12-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY . .

# 创建输出目录
RUN mkdir -p output

# Streamlit 端口
EXPOSE 8501

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# 启动
CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--browser.serverAddress=0.0.0.0"]
