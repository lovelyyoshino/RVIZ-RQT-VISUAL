#!/bin/bash

# ROS2 Web Visualization 启动脚本

echo "🚀 启动 ROS2 Web 可视化系统"
echo "================================"

# 检查是否安装了必要的依赖
check_dependencies() {
    echo "📋 检查依赖..."
    
    if ! command -v docker &> /dev/null; then
        echo "❌ Docker 未安装，请先安装 Docker"
        exit 1
    fi
    
    if ! command -v node &> /dev/null && [ "$1" != "docker" ]; then
        echo "❌ Node.js 未安装，请先安装 Node.js 18+ 或使用 Docker 模式"
        exit 1
    fi
    
    if ! command -v python3 &> /dev/null && [ "$1" != "docker" ]; then
        echo "❌ Python3 未安装，请先安装 Python 3.9+ 或使用 Docker 模式"
        exit 1
    fi
    
    echo "✅ 依赖检查完成"
}

# 本地开发模式启动
start_local() {
    echo "🔧 本地开发模式启动"
    
    # 启动后端
    echo "🐍 启动后端服务..."
    cd backend
    
    if [ ! -d "venv" ]; then
        echo "📦 创建虚拟环境..."
        python3 -m venv venv
    fi
    
    source venv/bin/activate
    pip install -r requirements.txt
    
    echo "🚀 启动 FastAPI 服务 (端口 8000)..."
    python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
    BACKEND_PID=$!
    
    cd ..
    
    # 启动前端
    echo "🌐 启动前端服务..."
    cd frontend
    
    if [ ! -d "node_modules" ]; then
        echo "📦 安装前端依赖..."
        npm install
    fi
    
    echo "🚀 启动 Vue.js 开发服务器 (端口 3000)..."
    npm run dev &
    FRONTEND_PID=$!
    
    cd ..
    
    echo ""
    echo "✅ 系统启动完成！"
    echo "🌐 前端地址: http://localhost:3000"
    echo "🔧 后端 API: http://localhost:8000"
    echo "📚 API 文档: http://localhost:8000/docs"
    echo ""
    echo "按 Ctrl+C 停止服务"
    
    # 等待中断信号
    trap 'echo "🛑 停止服务..."; kill $BACKEND_PID $FRONTEND_PID; exit 0' INT
    wait
}

# Docker 模式启动
start_docker() {
    echo "🐳 Docker 模式启动"
    
    if [ -f "docker-compose.yml" ]; then
        echo "🚀 使用 docker-compose 启动..."
        docker-compose up -d
        
        echo ""
        echo "✅ 系统启动完成！"
        echo "🌐 访问地址: http://localhost:3000"
        echo "🔧 后端 API: http://localhost:8000" 
        echo "📚 API 文档: http://localhost:8000/docs"
        echo ""
        echo "查看日志: docker-compose logs -f"
        echo "停止服务: docker-compose down"
    else
        echo "🔨 构建单一容器镜像..."
        docker build -t ros-web-viz .
        
        echo "🚀 启动容器..."
        docker run -d \
            --name ros-web-viz \
            -p 3000:3000 \
            -p 8000:8000 \
            -p 9090:9090 \
            --env-file .env \
            --network host \
            --pid host \
            -v /var/run/docker.sock:/var/run/docker.sock \
            -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
            -e DISPLAY=$DISPLAY \
            -e QT_X11_NO_MITSHM=1 \
            ros-web-viz
        
        echo ""
        echo "✅ 系统启动完成！"
        echo "🌐 访问地址: http://localhost:3000"
        echo "🔧 后端 API: http://localhost:8000"
        echo "📚 API 文档: http://localhost:8000/docs"
        echo ""
        echo "查看日志: docker logs -f ros-web-viz"
        echo "停止服务: docker stop ros-web-viz && docker rm ros-web-viz"
    fi
}

# 显示帮助信息
show_help() {
    echo "用法: $0 [local|docker]"
    echo ""
    echo "启动模式:"
    echo "  local   - 本地开发模式 (需要 Node.js 和 Python)"
    echo "  docker  - Docker 容器模式"
    echo ""
    echo "示例:"
    echo "  $0 local   # 本地开发启动"
    echo "  $0 docker  # Docker 启动"
    echo "  $0         # 默认本地开发启动"
}

# 主逻辑
case "${1:-local}" in
    "local")
        check_dependencies local
        start_local
        ;;
    "docker")
        check_dependencies docker
        start_docker
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        echo "❌ 未知启动模式: $1"
        show_help
        exit 1
        ;;
esac
