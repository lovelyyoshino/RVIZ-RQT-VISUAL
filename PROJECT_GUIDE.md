# ROS2 Web Visualization 项目指南

## 🎯 项目概述

这是一个基于 **Vue.js + FastAPI** 的 ROS2 Web 可视化平台，专注于 RViz 基础功能，支持本地开发和 Docker 单一容器部署。

### 核心特性

- ✅ **Web 端 RViz** - 3D 场景渲染与交互
- ✅ **ROS2 集成** - 完整的 ROS2 消息支持  
- ✅ **实时通信** - WebSocket 连接管理
- ✅ **插件系统** - 可扩展的可视化插件
- ✅ **单一容器** - 简化的 Docker 部署
- ✅ **响应式设计** - 现代化 UI 界面

### 技术栈

- **后端**: Python + FastAPI + ROS2 + rclpy
- **前端**: Vue.js 3 + JavaScript + Three.js + Element Plus
- **通信**: WebSocket (Rosbridge 协议)
- **部署**: 单一 Docker 容器 或 本地开发

## 🚀 快速开始

### 方式一：一键启动（推荐）

```bash
# 本地开发模式
./start.sh local

# Docker 容器模式  
./start.sh docker
```

### 方式二：手动启动

#### 本地开发

```bash
# 后端启动
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 前端启动 (新终端)
cd frontend  
npm install
npm run dev
```

#### Docker 部署

```bash
# 构建并运行
docker build -t ros-web-viz .
docker run -d -p 8000:8000 -p 9090:9090 ros-web-viz

# 或使用 docker-compose
docker-compose up -d
```

### 访问地址

- 🌐 **前端界面**: http://localhost:3000
- 🔧 **后端 API**: http://localhost:8000  
- 📚 **API 文档**: http://localhost:8000/docs
- 🔌 **WebSocket**: ws://localhost:9090

## 📁 项目结构

```
ros-web-viz/
├── backend/                    # Python FastAPI 后端
│   ├── app/
│   │   ├── main.py            # 应用入口
│   │   ├── core/              # 核心配置
│   │   ├── api/v1/            # API 路由
│   │   ├── models/            # 数据模型
│   │   ├── services/          # 业务逻辑
│   │   └── utils/             # 工具函数
│   └── requirements.txt       # Python 依赖
├── frontend/                   # Vue.js 前端
│   ├── src/
│   │   ├── main.js           # 应用入口
│   │   ├── App.vue           # 根组件
│   │   ├── router/           # 路由配置
│   │   ├── composables/      # Vue Composables
│   │   ├── components/       # Vue 组件
│   │   │   ├── common/       # 通用组件
│   │   │   ├── RViz/         # RViz 可视化
│   │   │   └── RQT/          # RQT 工具
│   │   └── services/         # 服务层
│   ├── package.json          # 前端依赖
│   └── vite.config.js        # 构建配置
├── Dockerfile                 # 单一容器构建
├── docker-compose.yml         # 多服务编排(可选)
├── start.sh                   # 一键启动脚本
└── .env                       # 环境变量配置
```

## 🔧 核心功能

### 1. RViz 可视化

**支持的消息类型**:
- `sensor_msgs/msg/PointCloud2` - 点云数据
- `sensor_msgs/msg/LaserScan` - 激光雷达数据  
- `visualization_msgs/msg/Marker` - 3D 标记
- `visualization_msgs/msg/MarkerArray` - 标记数组
- `nav_msgs/msg/Path` - 路径数据
- `geometry_msgs/msg/Twist` - 速度命令

**可视化功能**:
- 🎮 相机控制 (轨道、缩放、平移)
- 🎨 场景配置 (背景、网格、坐标轴)
- 📊 性能监控 (FPS、对象数、顶点数)
- 🔧 渲染设置 (阴影、抗锯齿、点大小)

### 2. 插件系统

**内置插件**:
- **点云渲染器** - 高性能点云显示
- **激光雷达渲染器** - 2D/3D 激光雷达数据
- **标记渲染器** - 几何标记与文本
- **路径渲染器** - 路径轨迹显示

**插件特性**:
- ✅ 动态启用/禁用
- ✅ 实时配置调整
- ✅ 多消息类型支持
- ✅ 可扩展架构

### 3. 实时通信

**WebSocket 功能**:
- 🔄 主题订阅/取消订阅
- 📤 消息发布
- 📋 主题/节点列表获取
- 🔗 自动重连机制

## 🛠️ 开发指南

### 添加新的可视化插件

1. **创建插件组件**
```vue
<!-- frontend/src/components/RViz/renderers/MyRenderer.vue -->
<template>
  <div><!-- 插件配置 UI --></div>
</template>

<script>
export default {
  name: 'MyRenderer',
  // 插件实现逻辑
}
</script>
```

2. **注册插件**
```javascript
// 在 VisualizationPlugins.vue 中添加
const newPlugin = {
  id: 'my_renderer',
  name: '我的渲染器',
  description: '自定义渲染器描述',
  supportedMessageTypes: ['custom_msgs/msg/MyMessage'],
  // ...
}
```

3. **实现渲染逻辑**
```javascript
// 在 Scene3D.vue 的 updateVisualization 方法中
case 'custom_msgs/msg/MyMessage':
  updateMyVisualization(topic, message)
  break
```

### 添加新的 API 端点

1. **定义数据模型**
```python
# backend/app/models/custom.py
from pydantic import BaseModel

class CustomData(BaseModel):
    field1: str
    field2: int
```

2. **创建 API 路由**
```python  
# backend/app/api/v1/custom.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/custom")
async def get_custom_data():
    return {"message": "Custom endpoint"}
```

3. **注册路由**
```python
# backend/app/main.py
from .api.v1 import custom

app.include_router(custom.router, prefix="/api/v1", tags=["Custom"])
```

## 🐳 部署说明

### 本地开发环境

**系统要求**:
- Python 3.9+
- Node.js 18+
- ROS2 Humble (可选)

**启动步骤**:
1. 克隆项目: `git clone <repo>`
2. 运行启动脚本: `./start.sh local`
3. 访问 http://localhost:3000

### Docker 生产部署

**镜像特性**:
- 📦 多阶段构建 (前端 + 后端)
- 🏗️ 单一容器运行
- 🔍 健康检查支持
- 📊 性能优化

**部署命令**:
```bash
# 快速部署
./start.sh docker

# 手动部署
docker build -t ros-web-viz .
docker run -d \
  --name ros-web-viz \
  -p 8000:8000 \
  -p 9090:9090 \
  -e ROS_DOMAIN_ID=0 \
  ros-web-viz
```

## 🔧 配置选项

### 环境变量

```bash
# ROS2 配置
ROS_DOMAIN_ID=0                 # ROS2 域 ID
ROS_DISCOVERY_SERVER=           # 发现服务器

# 服务配置  
WEB_HOST=0.0.0.0               # Web 服务主机
WEB_PORT=8000                  # Web 服务端口
ROSBRIDGE_PORT=9090            # Rosbridge 端口

# 性能配置
MAX_CONNECTIONS=100            # 最大连接数
MESSAGE_BUFFER_SIZE=10000      # 消息缓冲区大小
```

### 前端配置

```javascript
// vite.config.js
export default defineConfig({
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true
      }
    }
  }
})
```

## 🧪 测试

```bash
# 后端测试
cd backend
pytest tests/ -v

# 前端测试  
cd frontend
npm test

# 集成测试
docker-compose -f docker-compose.test.yml up
```

## 📝 API 文档

启动服务后访问: http://localhost:8000/docs

**主要端点**:
- `GET /api/v1/topics` - 获取主题列表
- `POST /api/v1/topics/{topic}/subscribe` - 订阅主题
- `GET /api/v1/nodes` - 获取节点列表
- `GET /api/v1/status` - 系统状态
- `WebSocket /ws` - 实时通信

## 🎯 下一步开发

### 计划功能
- [ ] RQT 工具面板完善
- [ ] 配置管理界面  
- [ ] 数据录制和回放
- [ ] 用户认证系统
- [ ] 移动端适配

### 性能优化
- [ ] 点云 LOD 渲染
- [ ] WebGL 实例化渲染
- [ ] 消息压缩传输
- [ ] 多线程处理

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支: `git checkout -b feature/new-feature`
3. 提交更改: `git commit -m 'Add new feature'`
4. 推送分支: `git push origin feature/new-feature`
5. 创建 Pull Request

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

---

**🎉 项目现已完成基础架构，可直接运行体验！**

**问题反馈**: 如遇问题请创建 Issue 或查看启动日志
