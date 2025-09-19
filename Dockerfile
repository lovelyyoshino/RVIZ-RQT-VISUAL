# 单一容器部署 Dockerfile
# 多阶段构建：前端 + 后端

# 阶段 1: 构建前端
FROM node:18-alpine AS frontend-build

WORKDIR /app/frontend

# 配置npm使用国内镜像源加速
RUN npm config set registry https://registry.npmmirror.com

# 复制前端依赖文件
COPY frontend/package*.json ./
RUN npm ci --only=production

# 复制前端源码并构建
COPY frontend/ ./
RUN npm run build

# 阶段 2: 使用 ROS2 Humble + Ubuntu 22.04 作为基础镜像
FROM ros:humble-perception-jammy

# 配置apt镜像源加速（使用清华大学镜像）
RUN echo "deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ jammy main restricted universe multiverse" > /etc/apt/sources.list \
    && echo "deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ jammy-updates main restricted universe multiverse" >> /etc/apt/sources.list \
    && echo "deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ jammy-security main restricted universe multiverse" >> /etc/apt/sources.list

# 安装必要的系统包
RUN apt-get update && apt-get install -y \
    curl \
    nginx \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 配置pip使用国内镜像源加速
RUN pip3 config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple \
    && pip3 config set global.trusted-host pypi.tuna.tsinghua.edu.cn

# 复制并安装 Python 依赖
COPY backend/requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

# 复制后端代码
COPY backend/ ./

# 复制前端构建产物到Nginx静态文件目录
COPY --from=frontend-build /app/frontend/dist /var/www/html

# 配置 Nginx 作为前端服务器
RUN echo 'server { \
    listen 3000; \
    server_name localhost; \
    root /var/www/html; \
    index index.html; \
    \
    # 前端路由支持 \
    location / { \
        try_files $uri $uri/ /index.html; \
    } \
    \
    # API 代理到后端 \
    location /api/ { \
        proxy_pass http://localhost:8000/; \
        proxy_set_header Host $host; \
        proxy_set_header X-Real-IP $remote_addr; \
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; \
        proxy_set_header X-Forwarded-Proto $scheme; \
    } \
    \
    # WebSocket 代理 \
    location /ws { \
        proxy_pass http://localhost:8000/ws; \
        proxy_http_version 1.1; \
        proxy_set_header Upgrade $http_upgrade; \
        proxy_set_header Connection "upgrade"; \
        proxy_set_header Host $host; \
        proxy_set_header X-Real-IP $remote_addr; \
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; \
        proxy_set_header X-Forwarded-Proto $scheme; \
    } \
}' > /etc/nginx/sites-available/default

# 创建启动脚本
RUN echo '#!/bin/bash' > /app/start.sh && \
    echo 'source /opt/ros/humble/setup.bash' >> /app/start.sh && \
    echo 'cd /app && python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &' >> /app/start.sh && \
    echo 'nginx -g "daemon off;" &' >> /app/start.sh && \
    echo 'sleep 5' >> /app/start.sh && \
    echo 'wait' >> /app/start.sh && \
    chmod +x /app/start.sh

# 设置环境变量
ENV PYTHONPATH=/app
ENV ROS_DOMAIN_ID=0
ENV ROSBRIDGE_PORT=9090
ENV WEB_PORT=8000
ENV WEB_HOST=0.0.0.0
# 强制使用 Fast DDS + UDPv4，禁用共享内存，避免容器/宿主机间SHM问题
ENV RMW_IMPLEMENTATION=rmw_fastrtps_cpp
ENV FASTDDS_BUILTIN_TRANSPORTS=UDPv4
ENV ROS_LOCALHOST_ONLY=0

# 暴露端口
EXPOSE 3000 8000 9090

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:3000 || exit 1

# 启动命令
CMD ["/app/start.sh"]
