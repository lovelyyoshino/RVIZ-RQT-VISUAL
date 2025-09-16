# 单一容器部署 Dockerfile
# 多阶段构建：前端 + 后端

# 阶段 1: 构建前端
FROM node:18-alpine AS frontend-build

WORKDIR /app/frontend

# 复制前端依赖文件
COPY frontend/package*.json ./
RUN npm ci --only=production

# 复制前端源码并构建
COPY frontend/ ./
RUN npm run build

# 阶段 2: 构建最终镜像 (Python + 静态文件)
FROM python:3.9-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    gnupg2 \
    lsb-release \
    && rm -rf /var/lib/apt/lists/*

# 安装 ROS2 Humble (简化版本，实际部署时需要完整 ROS2)
# 注意：这里仅作为示例，生产环境建议使用 ROS2 官方镜像作为基础镜像
RUN echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(lsb_release -cs) main" > /etc/apt/sources.list.d/ros2.list \
    && curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg \
    && apt-get update \
    && apt-get install -y python3-rosdep \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制并安装 Python 依赖
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端代码
COPY backend/ ./

# 复制前端构建产物到静态文件目录
COPY --from=frontend-build /app/frontend/dist ./static

# 设置环境变量
ENV PYTHONPATH=/app
ENV ROS_DOMAIN_ID=0
ENV ROSBRIDGE_PORT=9090
ENV WEB_PORT=8000
ENV WEB_HOST=0.0.0.0

# 暴露端口
EXPOSE 8000 9090

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
