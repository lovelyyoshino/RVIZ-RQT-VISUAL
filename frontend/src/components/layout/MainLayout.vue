<template>
  <div class="main-layout">
    <!-- 顶部工具栏 -->
    <div class="top-toolbar">
      <div class="toolbar-left">
        <el-text size="large" class="app-title">ROS2 实时可视化系统</el-text>
      </div>
      
      <div class="toolbar-right">
        <el-button-group size="small">
          <el-button @click="resetView">
            <el-icon><Aim /></el-icon>
            重置视角
          </el-button>
          <el-button @click="toggleGrid">
            <el-icon><Grid /></el-icon>
            网格
          </el-button>
          <el-button @click="toggleAxes">
            <el-icon><Coordinate /></el-icon>
            坐标轴
          </el-button>
        </el-button-group>
      </div>
    </div>
    
    <!-- 主内容区 - 双栏并列布局 -->
    <div class="main-content">
      <!-- 左侧 3D 场景区域 -->
      <div class="scene-section" :style="{ width: `${sceneWidth}%` }">
        <div class="scene-panel">
          <div class="scene-header">
            <h3>3D 可视化</h3>
            <div class="scene-controls">
              <el-button-group size="small">
                <el-button @click="resetView">重置视角</el-button>
                <el-button @click="toggleGrid">网格</el-button>
                <el-button @click="toggleAxes">坐标轴</el-button>
              </el-button-group>
            </div>
          </div>
          <div class="scene-content">
            <Scene3D ref="scene3dRef" />
          </div>
        </div>
      </div>
      
      <!-- 可拖拽的分割器 -->
      <div 
        class="resize-handle" 
        @mousedown="startResize"
        @touchstart="startResize"
      >
        <div class="resize-line"></div>
      </div>
      
      <!-- 右侧 ROS 拓扑图区域 -->
      <div class="topology-section" :style="{ width: `${100 - sceneWidth}%` }">
        <div class="topology-main-panel">
          <div class="topology-header">
            <h3>ROS 通信拓扑图</h3>
            <div class="topology-controls">
              <el-button-group size="small">
                <el-button @click="toggleTopologyFullscreen">
                  <el-icon><FullScreen /></el-icon>
                  全屏
                </el-button>
              </el-button-group>
            </div>
          </div>
          <div class="topology-content">
            <NodeTopicGraph
              ref="nodeTopicGraphRef"
              @topic-subscribe="onTopicSubscribe"
              @topic-unsubscribe="onTopicUnsubscribe"
              @topic-visualize="onTopicVisualize"
            />
          </div>
        </div>
        
        <!-- 下方控制面板区 -->
        <div class="control-panels-area">
          <div class="control-panels-container">
            <!-- GPS/位置信息面板 -->
            <div class="mini-panel gps-mini-panel">
              <div class="mini-panel-header">
                <h5>位置信息</h5>
                <el-button size="small" text @click="expandPanel('gps')">
                  <el-icon><Expand /></el-icon>
                </el-button>
              </div>
              <div class="mini-panel-content">
                <GpsPanel :compact="true" />
              </div>
            </div>
            
            <!-- 3D控制器面板 -->
            <div class="mini-panel controller-mini-panel">
              <div class="mini-panel-header">
                <h5>3D控制</h5>
                <el-button size="small" text @click="expandPanel('controller')">
                  <el-icon><Expand /></el-icon>
                </el-button>
              </div>
              <div class="mini-panel-content">
                <Scene3DController
                  :compact="true"
                  @laser-type-change="onLaserTypeChange"
                  @laser2d-change="onLaser2DChange"
                  @pointcloud-change="onPointCloudChange"
                  @map-topic-change="onMapTopicChange"
                  @map-file-change="onMapFileChange"
                  @map-files-change="onMapFilesChange"
                  @odom-topic-change="onOdomTopicChange"
                  @settings-update="onSettingsUpdate"
                  @camera-reset="onCameraReset"
                  @view-preset="onViewPreset"
                  @navigation-tool-change="onNavigationToolChange"
                />
              </div>
            </div>
            
            <!-- 状态指示面板 -->
            <div class="mini-panel status-mini-panel">
              <div class="mini-panel-header">
                <h5>状态</h5>
                <el-button size="small" text @click="expandPanel('status')">
                  <el-icon><Expand /></el-icon>
                </el-button>
              </div>
              <div class="mini-panel-content">
                <StatusPanel :compact="true" />
              </div>
            </div>
            
            <!-- 数据图表面板 -->
            <div class="mini-panel chart-mini-panel">
              <div class="mini-panel-header">
                <h5>数据图表</h5>
                <el-button size="small" text @click="expandPanel('chart')">
                  <el-icon><Expand /></el-icon>
                </el-button>
              </div>
              <div class="mini-panel-content">
                <ChartPanel :compact="true" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted } from 'vue'
import { 
  Aim,
  Grid,
  Coordinate,
  Setting,
  FullScreen,
  Expand
} from '@element-plus/icons-vue'

// 引入面板组件
import Scene3D from '../RViz/Scene3D.vue'
import GpsPanel from '../panels/GpsPanel.vue'
import NodeTopicGraph from '../RQT/widgets/NodeTopicGraph.vue'
import Scene3DController from '../RViz/Scene3DController.vue'
import ChartPanel from '../panels/ChartPanel.vue'
import StatusPanel from '../panels/StatusPanel.vue'

export default {
  name: 'MainLayout',
  components: {
    Aim,
    Grid, 
    Coordinate,
    Setting,
    FullScreen,
    Expand,
    Scene3D,
    GpsPanel,
    NodeTopicGraph,
    Scene3DController,
    ChartPanel,
    StatusPanel
  },
  setup() {
    const scene3dRef = ref(null)
    const nodeTopicGraphRef = ref(null)
    
    // 布局控制状态
    const sceneWidth = ref(50) // 3D场景和拓扑图各占50%宽度
    const isResizing = ref(false)
    const startX = ref(0)
    const startWidth = ref(0)
    const isTopologyFullscreen = ref(false)
    
    // 分割器拖拽功能
    const startResize = (event) => {
      isResizing.value = true
      startX.value = event.type === 'mousedown' ? event.clientX : event.touches[0].clientX
      startWidth.value = sceneWidth.value
      
      document.addEventListener('mousemove', handleResize)
      document.addEventListener('mouseup', stopResize)
      document.addEventListener('touchmove', handleResize, { passive: false })
      document.addEventListener('touchend', stopResize)
      
      document.body.style.userSelect = 'none'
      document.body.style.cursor = 'col-resize'
    }
    
    const handleResize = (event) => {
      if (!isResizing.value) return
      
      event.preventDefault()
      const currentX = event.type === 'mousemove' ? event.clientX : event.touches[0].clientX
      const deltaX = currentX - startX.value
      const containerWidth = window.innerWidth
      const deltaPercent = (deltaX / containerWidth) * 100
      
      // 限制分割范围在30%-80%之间
      const newWidth = Math.max(30, Math.min(80, startWidth.value + deltaPercent))
      sceneWidth.value = newWidth
    }
    
    const stopResize = () => {
      isResizing.value = false
      
      document.removeEventListener('mousemove', handleResize)
      document.removeEventListener('mouseup', stopResize)
      document.removeEventListener('touchmove', handleResize)
      document.removeEventListener('touchend', stopResize)
      
      document.body.style.userSelect = ''
      document.body.style.cursor = ''
    }
    
    // 3D场景控制方法
    
    const resetView = () => {
      if (scene3dRef.value) {
        scene3dRef.value.resetCamera()
      }
    }
    
    const toggleGrid = () => {
      if (scene3dRef.value) {
        scene3dRef.value.setGridVisible(!scene3dRef.value.showGrid)
      }
    }
    
    const toggleAxes = () => {
      if (scene3dRef.value) {
        scene3dRef.value.setAxesVisible(!scene3dRef.value.showAxes)
      }
    }
    
    // RQT树事件处理 - 直接与3D场景集成
    const onTopicSubscribe = (topicName, messageType) => {
      console.log(`订阅主题: ${topicName}, 类型: ${messageType}`)
      
      if (scene3dRef.value && scene3dRef.value.subscribeToRosTopic) {
        // 直接让3D场景组件处理ROS主题订阅
        scene3dRef.value.subscribeToRosTopic(topicName, messageType)
        ElMessage.success(`已订阅可视化主题: ${topicName}`)
      } else {
        console.warn('3D场景未就绪或不支持该消息类型')
      }
    }
    
    const onTopicUnsubscribe = (topicName) => {
      console.log(`取消订阅主题: ${topicName}`)
      if (scene3dRef.value && scene3dRef.value.unsubscribeFromRosTopic) {
        scene3dRef.value.unsubscribeFromRosTopic(topicName)
        ElMessage.info(`已取消订阅主题: ${topicName}`)
      }
    }
    
    const onNodeSelected = (nodeData) => {
      console.log('选中节点:', nodeData)
      // 可以在这里处理节点选择的逻辑
    }

    // Node-Topic图事件处理
    const onTopicVisualize = (topicName, messageType) => {
      console.log(`可视化主题: ${topicName}, 类型: ${messageType}`)
      onTopicSubscribe(topicName, messageType)
    }

    // 3D控制器事件处理
    const onLaserTypeChange = (laserType) => {
      console.log(`激光类型切换: ${laserType}`)
      if (scene3dRef.value && scene3dRef.value.setLaserType) {
        scene3dRef.value.setLaserType(laserType)
      }
    }

    const onLaser2DChange = (topicName) => {
      console.log(`2D激光主题切换: ${topicName}`)
      onTopicSubscribe(topicName, 'sensor_msgs/msg/LaserScan')
    }

    const onPointCloudChange = (topicName) => {
      console.log(`点云主题切换: ${topicName}`)
      onTopicSubscribe(topicName, 'sensor_msgs/msg/PointCloud2')
    }

    const onMapTopicChange = (topicName) => {
      console.log(`地图主题切换: ${topicName}`)
      onTopicSubscribe(topicName, 'nav_msgs/msg/OccupancyGrid')
    }

    const onMapFileChange = (file) => {
      console.log(`地图文件选择: ${file.name}`)
      if (scene3dRef.value && scene3dRef.value.loadMapFile) {
        scene3dRef.value.loadMapFile(file)
      } else {
        ElMessage.warning('3D场景未就绪，无法加载地图文件')
      }
    }

    const onMapFilesChange = ({ yamlFile, pgmFile }) => {
      console.log(`地图文件对选择: ${yamlFile.name} + ${pgmFile.name}`)
      if (scene3dRef.value && scene3dRef.value.loadMapFiles) {
        scene3dRef.value.loadMapFiles(yamlFile, pgmFile)
      } else {
        ElMessage.warning('3D场景未就绪，无法加载地图文件')
      }
    }

    const onOdomTopicChange = (topicName) => {
      console.log(`里程计主题切换: ${topicName}`)
      onTopicSubscribe(topicName, 'nav_msgs/msg/Odometry')
    }

    const onSettingsUpdate = (settings) => {
      console.log('设置更新:', settings)
      if (scene3dRef.value && scene3dRef.value.updateSettings) {
        scene3dRef.value.updateSettings(settings)
      }
    }

    const onCameraReset = () => {
      console.log('重置相机')
      resetView()
    }

    const onViewPreset = (preset) => {
      console.log(`视角预设: ${preset}`)
      if (scene3dRef.value && scene3dRef.value.setViewPreset) {
        scene3dRef.value.setViewPreset(preset)
      }
    }

    const onNavigationToolChange = (tool) => {
      console.log('导航工具切换:', tool)
      if (scene3dRef.value && scene3dRef.value.setNavigationTool) {
        scene3dRef.value.setNavigationTool(tool)
      }
    }

    // 新增的布局控制方法
    const toggleTopologyFullscreen = () => {
      isTopologyFullscreen.value = !isTopologyFullscreen.value
      if (isTopologyFullscreen.value) {
        // 全屏拓扑图
        document.querySelector('.topology-main-panel').classList.add('fullscreen')
      } else {
        document.querySelector('.topology-main-panel').classList.remove('fullscreen')
      }
    }

    const expandPanel = (panelType) => {
      console.log(`展开面板: ${panelType}`)
      // TODO: 实现面板展开逻辑
      ElMessage.info(`面板展开功能开发中: ${panelType}`)
    }
    
    return {
      // DOM引用
      scene3dRef,
      nodeTopicGraphRef,
      
      // 布局控制
      sceneWidth,
      startResize,
      isTopologyFullscreen,
      toggleTopologyFullscreen,
      expandPanel,
      
      // 3D场景控制
      resetView,
      toggleGrid,
      toggleAxes,
      
      // 事件处理
      onTopicSubscribe,
      onTopicUnsubscribe,
      onNodeSelected,
      onTopicVisualize,
      onLaserTypeChange,
      onLaser2DChange,
      onPointCloudChange,
      onMapTopicChange,
      onMapFileChange,
      onMapFilesChange,
      onOdomTopicChange,
      onSettingsUpdate,
      onCameraReset,
      onViewPreset,
      onNavigationToolChange
    }
  }
}
</script>

<style scoped>
.main-layout {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: transparent;
}

.top-toolbar {
  height: 50px;
  background: rgba(15, 23, 42, 0.8);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(148, 163, 184, 0.1);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
}

.toolbar-left {
  display: flex;
  align-items: center;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.app-title {
  font-weight: 600;
  background: linear-gradient(90deg, #ffffff, #94a3b8);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.main-content {
  flex: 1;
  display: flex;
  min-height: calc(100vh - 50px);
  height: auto;
}

.scene-section {
  display: flex;
  flex-direction: column;
  min-width: 300px;
  padding: 10px;
  transition: width 0.1s ease-out;
}

.topology-section {
  display: flex;
  flex-direction: column;
  min-width: 400px;
  padding: 10px;
  transition: width 0.1s ease-out;
  min-height: calc(100vh - 50px);
  height: auto;
  overflow-y: auto;
  overflow-x: hidden;
}

/* 分割器样式 */
.resize-handle {
  width: 8px;
  background: linear-gradient(180deg, rgba(148, 163, 184, 0.3), rgba(148, 163, 184, 0.6));
  cursor: col-resize;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  transition: background-color 0.2s;
  user-select: none;
  border-left: 1px solid rgba(148, 163, 184, 0.2);
  border-right: 1px solid rgba(148, 163, 184, 0.2);
}

.resize-handle:hover {
  background: linear-gradient(180deg, rgba(59, 130, 246, 0.3), rgba(59, 130, 246, 0.6));
}

.resize-handle:active {
  background: linear-gradient(180deg, rgba(59, 130, 246, 0.5), rgba(59, 130, 246, 0.8));
}

.resize-line {
  width: 2px;
  height: 40px;
  background: rgba(255, 255, 255, 0.6);
  border-radius: 1px;
  transition: all 0.2s;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.resize-handle:hover .resize-line {
  background: rgba(59, 130, 246, 0.8);
  height: 60px;
  box-shadow: 0 4px 8px rgba(59, 130, 246, 0.3);
}

.scene-panel {
  flex: 1;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(148, 163, 184, 0.1);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  position: relative;
}

.scene-panel::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, rgba(0, 212, 255, 0.02) 0%, rgba(0, 153, 204, 0.02) 100%);
  pointer-events: none;
  z-index: 1;
}

.scene-header {
  height: 40px;
  background: rgba(15, 23, 42, 0.9);
  backdrop-filter: blur(10px);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 15px;
  color: #e2e8f0;
  border-bottom: 1px solid rgba(148, 163, 184, 0.1);
  position: relative;
  z-index: 2;
}

.scene-header h3 {
  font-size: 14px;
  font-weight: 500;
}

.scene-content {
  height: calc(100% - 40px);
  position: relative;
  z-index: 2;
  min-height: 400px;
}

/* 拓扑图主面板样式 */
.topology-main-panel {
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(148, 163, 184, 0.1);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  position: relative;
  flex: 1;
  min-height: 400px;
  margin-bottom: 10px;
  display: flex;
  flex-direction: column;
}

.topology-main-panel::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, rgba(0, 212, 255, 0.02) 0%, rgba(0, 153, 204, 0.02) 100%);
  pointer-events: none;
  z-index: 1;
}

.topology-main-panel.fullscreen {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: 9999;
  border-radius: 0;
  margin: 0;
}

.topology-header {
  height: 40px;
  background: rgba(15, 23, 42, 0.9);
  backdrop-filter: blur(10px);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 15px;
  color: #e2e8f0;
  border-bottom: 1px solid rgba(148, 163, 184, 0.1);
  position: relative;
  z-index: 2;
}

.topology-header h3 {
  font-size: 14px;
  font-weight: 500;
}

.topology-content {
  flex: 1;
  position: relative;
  z-index: 2;
  min-height: 0;
  overflow: auto;
}

/* 控制面板区域 */
.control-panels-area {
  min-height: 160px;
  height: auto;
  overflow-x: auto;
  overflow-y: visible;
  flex-shrink: 0;
  max-height: 200px;
}

.control-panels-container {
  display: flex;
  gap: 10px;
  height: 100%;
  padding: 5px;
  min-width: calc(4 * 220px + 3 * 10px); /* 确保需要水平滚动 */
}

/* 迷你面板样式 */
.mini-panel {
  min-width: 200px;
  background: rgba(15, 23, 42, 0.8);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(148, 163, 184, 0.1);
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
  transition: all 0.3s ease;
  position: relative;
}

.mini-panel::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, rgba(0, 212, 255, 0.03) 0%, transparent 50%);
  pointer-events: none;
  z-index: 1;
}

.mini-panel:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
  border-color: rgba(0, 212, 255, 0.3);
}

.mini-panel-header {
  height: 28px;
  background: rgba(15, 23, 42, 0.9);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(148, 163, 184, 0.1);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 10px;
  position: relative;
  z-index: 2;
}

.mini-panel-header h5 {
  font-size: 12px;
  font-weight: 500;
  color: #e2e8f0;
  margin: 0;
}

.mini-panel-content {
  height: calc(100% - 28px);
  overflow: hidden;
  position: relative;
  z-index: 2;
  padding: 8px;
}

/* 特定迷你面板样式 */
.gps-mini-panel {
  min-width: 180px;
}

.controller-mini-panel {
  min-width: 220px;
}

.status-mini-panel {
  min-width: 160px;
}

.chart-mini-panel {
  min-width: 200px;
}

/* 滚动条样式优化 - 确保可见 */
.topology-section {
  scrollbar-width: thin;
  scrollbar-color: rgba(59, 130, 246, 0.6) rgba(148, 163, 184, 0.2);
}

.topology-section::-webkit-scrollbar {
  width: 14px;
}

.topology-section::-webkit-scrollbar-track {
  background: rgba(148, 163, 184, 0.2);
  border-radius: 7px;
  margin: 4px;
}

.topology-section::-webkit-scrollbar-thumb {
  background: rgba(59, 130, 246, 0.6);
  border-radius: 7px;
  transition: background 0.3s;
  border: 2px solid transparent;
  background-clip: content-box;
  min-height: 30px;
}

.topology-section::-webkit-scrollbar-thumb:hover {
  background: rgba(59, 130, 246, 0.8);
  background-clip: content-box;
}

.topology-section::-webkit-scrollbar-thumb:active {
  background: rgba(59, 130, 246, 1.0);
  background-clip: content-box;
}

.control-panels-area {
  scrollbar-width: thin;
  scrollbar-color: rgba(148, 163, 184, 0.3) rgba(148, 163, 184, 0.1);
}

.control-panels-area::-webkit-scrollbar {
  height: 8px;
  width: 8px;
}

.control-panels-area::-webkit-scrollbar-track {
  background: rgba(148, 163, 184, 0.1);
  border-radius: 4px;
  margin: 2px;
}

.control-panels-area::-webkit-scrollbar-thumb {
  background: rgba(148, 163, 184, 0.4);
  border-radius: 4px;
  transition: background 0.3s;
}

.control-panels-area::-webkit-scrollbar-thumb:hover {
  background: rgba(148, 163, 184, 0.6);
}

/* 确保控制面板区域可以滚动 */
.control-panels-area {
  overflow-y: auto;
  overflow-x: auto;
}
</style>
