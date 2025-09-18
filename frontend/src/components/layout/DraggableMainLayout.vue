<template>
  <div class="draggable-main-layout">
    <!-- 顶部工具栏 -->
    <div class="top-toolbar">
      <div class="toolbar-left">
        <el-text size="large" class="app-title">ROS2 实时可视化系统</el-text>
      </div>

      <div class="toolbar-center">
        <el-button-group size="small">
          <el-button @click="toggleLayoutMode" :type="isDraggableMode ? 'primary' : 'default'">
            <el-icon><Grid /></el-icon>
            {{ isDraggableMode ? '退出' : '进入' }}拖拽模式
          </el-button>
          <el-button @click="saveLayout" v-if="isDraggableMode">
            <el-icon><FolderOpened /></el-icon>
            保存布局
          </el-button>
          <el-button @click="loadLayout" v-if="isDraggableMode">
            <el-icon><Download /></el-icon>
            加载布局
          </el-button>
          <el-button @click="resetLayout" v-if="isDraggableMode">
            <el-icon><RefreshLeft /></el-icon>
            重置布局
          </el-button>
        </el-button-group>
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

    <!-- 主内容区 -->
    <div class="main-content">
      <!-- 拖拽模式 -->
      <template v-if="isDraggableMode">
        <GridLayoutSystem
          :modules="draggableModules"
          :auto-optimize="true"
          :grid-size="20"
          @modules-update="updateModules"
          @layout-optimized="onLayoutOptimized"
        />
      </template>

      <!-- 传统布局模式 -->
      <template v-else>
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
      </template>
    </div>

    <!-- 布局保存/加载对话框 -->
    <el-dialog
      v-model="showLayoutDialog"
      :title="layoutDialogMode === 'save' ? '保存布局' : '加载布局'"
      width="500px"
      :close-on-click-modal="false"
    >
      <div v-if="layoutDialogMode === 'save'">
        <el-form @submit.prevent="handleSaveLayout">
          <el-form-item label="布局名称">
            <el-input
              v-model="layoutName"
              placeholder="请输入布局名称"
              clearable
            />
          </el-form-item>
          <el-form-item label="描述">
            <el-input
              v-model="layoutDescription"
              type="textarea"
              placeholder="布局描述（可选）"
              :rows="3"
              clearable
            />
          </el-form-item>
        </el-form>
      </div>
      <div v-else>
        <div class="saved-layouts">
          <div
            v-for="layout in savedLayouts"
            :key="layout.id"
            class="layout-item"
            :class="{ 'selected': selectedLayoutId === layout.id }"
            @click="selectedLayoutId = layout.id"
          >
            <div class="layout-info">
              <h4>{{ layout.name }}</h4>
              <p>{{ layout.description || '无描述' }}</p>
              <small>保存时间: {{ formatDate(layout.timestamp) }}</small>
            </div>
            <div class="layout-preview">
              <div
                v-for="module in layout.modules"
                :key="module.id"
                class="preview-module"
                :style="getPreviewModuleStyle(module, layout)"
              ></div>
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="showLayoutDialog = false">取消</el-button>
          <el-button
            v-if="layoutDialogMode === 'save'"
            type="primary"
            @click="handleSaveLayout"
            :disabled="!layoutName.trim()"
          >
            保存
          </el-button>
          <el-button
            v-else
            type="primary"
            @click="handleLoadLayout"
            :disabled="!selectedLayoutId"
          >
            加载
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Aim,
  Grid,
  Coordinate,
  FullScreen,
  Expand,
  FolderOpened,
  Download,
  RefreshLeft
} from '@element-plus/icons-vue'

// 引入组件
import GridLayoutSystem from './GridLayoutSystem.vue'
import Scene3D from '../RViz/Scene3D.vue'
import GpsPanel from '../panels/GpsPanel.vue'
import NodeTopicGraph from '../RQT/widgets/NodeTopicGraph.vue'
import Scene3DController from '../RViz/Scene3DController.vue'
import ChartPanel from '../panels/ChartPanel.vue'
import StatusPanel from '../panels/StatusPanel.vue'

export default {
  name: 'DraggableMainLayout',
  components: {
    Aim,
    Grid,
    Coordinate,
    FullScreen,
    Expand,
    FolderOpened,
    Download,
    RefreshLeft,
    GridLayoutSystem,
    Scene3D,
    GpsPanel,
    NodeTopicGraph,
    Scene3DController,
    ChartPanel,
    StatusPanel
  },
  setup() {
    // 引用
    const scene3dRef = ref(null)
    const nodeTopicGraphRef = ref(null)

    // 模式控制
    const isDraggableMode = ref(false)

    // 传统布局状态
    const sceneWidth = ref(50)
    const isResizing = ref(false)
    const startX = ref(0)
    const startWidth = ref(0)
    const isTopologyFullscreen = ref(false)

    // 拖拽模块配置
    const draggableModules = ref([
      {
        id: 'scene3d',
        title: '3D 可视化',
        icon: 'VideoCamera',
        component: 'Scene3D',
        x: 20,
        y: 20,
        width: 800,
        height: 600,
        zIndex: 1,
        minimized: false,
        maximized: false,
        props: {}
      },
      {
        id: 'topology',
        title: 'ROS 通信拓扑图',
        icon: 'DataAnalysis',
        component: 'NodeTopicGraph',
        x: 840,
        y: 20,
        width: 500,
        height: 400,
        zIndex: 1,
        minimized: false,
        maximized: false,
        props: {}
      },
      {
        id: 'gps',
        title: 'GPS 位置信息',
        icon: 'Location',
        component: 'GpsPanel',
        x: 840,
        y: 440,
        width: 240,
        height: 180,
        zIndex: 1,
        minimized: false,
        maximized: false,
        props: { compact: false }
      },
      {
        id: 'controller',
        title: '3D 控制器',
        icon: 'Setting',
        component: 'Scene3DController',
        x: 1100,
        y: 440,
        width: 240,
        height: 180,
        zIndex: 1,
        minimized: false,
        maximized: false,
        props: { compact: false }
      },
      {
        id: 'status',
        title: '状态面板',
        icon: 'DataAnalysis',
        component: 'StatusPanel',
        x: 20,
        y: 640,
        width: 240,
        height: 180,
        zIndex: 1,
        minimized: false,
        maximized: false,
        props: { compact: false }
      },
      {
        id: 'chart',
        title: '数据图表',
        icon: 'DataAnalysis',
        component: 'ChartPanel',
        x: 280,
        y: 640,
        width: 240,
        height: 180,
        zIndex: 1,
        minimized: false,
        maximized: false,
        props: { compact: false }
      }
    ])

    // 布局保存/加载
    const showLayoutDialog = ref(false)
    const layoutDialogMode = ref('save') // 'save' | 'load'
    const layoutName = ref('')
    const layoutDescription = ref('')
    const selectedLayoutId = ref('')
    const savedLayouts = ref([])

    // 加载保存的布局
    const loadSavedLayouts = () => {
      const saved = localStorage.getItem('ros2-web-layouts')
      if (saved) {
        try {
          savedLayouts.value = JSON.parse(saved)
        } catch (e) {
          console.error('Failed to load saved layouts:', e)
          savedLayouts.value = []
        }
      }
    }

    // 切换布局模式
    const toggleLayoutMode = () => {
      isDraggableMode.value = !isDraggableMode.value

      if (isDraggableMode.value) {
        ElMessage.success('已进入拖拽模式，您可以自由拖动和调整每个模块')
      } else {
        ElMessage.info('已退出拖拽模式，恢复传统布局')
      }
    }

    // 保存布局
    const saveLayout = () => {
      layoutDialogMode.value = 'save'
      layoutName.value = ''
      layoutDescription.value = ''
      showLayoutDialog.value = true
    }

    // 加载布局
    const loadLayout = () => {
      loadSavedLayouts()
      layoutDialogMode.value = 'load'
      selectedLayoutId.value = ''
      showLayoutDialog.value = true
    }

    // 重置布局
    const resetLayout = async () => {
      try {
        await ElMessageBox.confirm(
          '确定要重置到默认布局吗？当前的布局设置将会丢失。',
          '重置布局',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )

        // 重置到默认位置
        draggableModules.value.forEach((module, index) => {
          const row = Math.floor(index / 3)
          const col = index % 3
          module.x = col * 320 + 20
          module.y = row * 240 + 20
          module.width = 300
          module.height = 220
          module.minimized = false
          module.maximized = false
          module.zIndex = 1
        })

        ElMessage.success('布局已重置为默认设置')
      } catch {
        // 用户取消
      }
    }

    // 处理保存布局
    const handleSaveLayout = () => {
      if (!layoutName.value.trim()) {
        ElMessage.error('请输入布局名称')
        return
      }

      const newLayout = {
        id: Date.now().toString(),
        name: layoutName.value.trim(),
        description: layoutDescription.value.trim(),
        timestamp: Date.now(),
        modules: JSON.parse(JSON.stringify(draggableModules.value))
      }

      savedLayouts.value.push(newLayout)
      localStorage.setItem('ros2-web-layouts', JSON.stringify(savedLayouts.value))

      showLayoutDialog.value = false
      ElMessage.success('布局保存成功')
    }

    // 处理加载布局
    const handleLoadLayout = () => {
      const layout = savedLayouts.value.find(l => l.id === selectedLayoutId.value)
      if (!layout) {
        ElMessage.error('未找到选中的布局')
        return
      }

      draggableModules.value.forEach(module => {
        const savedModule = layout.modules.find(m => m.id === module.id)
        if (savedModule) {
          Object.assign(module, savedModule)
        }
      })

      showLayoutDialog.value = false
      ElMessage.success(`布局 "${layout.name}" 加载成功`)
    }

    // 获取预览模块样式
    const getPreviewModuleStyle = (module, layout) => {
      const maxX = Math.max(...layout.modules.map(m => m.x + m.width))
      const maxY = Math.max(...layout.modules.map(m => m.y + m.height))
      const scale = 100 / Math.max(maxX, maxY)

      return {
        left: `${module.x * scale}px`,
        top: `${module.y * scale}px`,
        width: `${module.width * scale}px`,
        height: `${module.height * scale}px`
      }
    }

    // 格式化日期
    const formatDate = (timestamp) => {
      return new Date(timestamp).toLocaleString('zh-CN')
    }

    // 更新模块
    const updateModules = (modules) => {
      draggableModules.value = modules
    }

    // 布局优化回调
    const onLayoutOptimized = (type) => {
      ElMessage.success(`布局优化完成: ${type}`)
    }

    // 传统布局的分割器功能
    const startResize = (event) => {
      if (isDraggableMode.value) return

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
      if (!isResizing.value || isDraggableMode.value) return

      event.preventDefault()
      const currentX = event.type === 'mousemove' ? event.clientX : event.touches[0].clientX
      const deltaX = currentX - startX.value
      const containerWidth = window.innerWidth
      const deltaPercent = (deltaX / containerWidth) * 100

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

    // RQT事件处理
    const onTopicSubscribe = (topicName, messageType) => {
      console.log(`订阅主题: ${topicName}, 类型: ${messageType}`)

      if (scene3dRef.value && scene3dRef.value.subscribeToRosTopic) {
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

    const toggleTopologyFullscreen = () => {
      isTopologyFullscreen.value = !isTopologyFullscreen.value
      if (isTopologyFullscreen.value) {
        document.querySelector('.topology-main-panel')?.classList.add('fullscreen')
      } else {
        document.querySelector('.topology-main-panel')?.classList.remove('fullscreen')
      }
    }

    const expandPanel = (panelType) => {
      console.log(`展开面板: ${panelType}`)
      // 在拖拽模式下，找到对应的模块并最大化
      if (isDraggableMode.value) {
        const module = draggableModules.value.find(m => m.id === panelType)
        if (module) {
          module.maximized = !module.maximized
        }
      } else {
        ElMessage.info(`面板展开功能开发中: ${panelType}`)
      }
    }

    onMounted(() => {
      loadSavedLayouts()
    })

    return {
      // 引用
      scene3dRef,
      nodeTopicGraphRef,

      // 模式控制
      isDraggableMode,
      toggleLayoutMode,

      // 拖拽模块
      draggableModules,
      updateModules,
      onLayoutOptimized,

      // 传统布局
      sceneWidth,
      startResize,
      isTopologyFullscreen,
      toggleTopologyFullscreen,
      expandPanel,

      // 布局保存/加载
      showLayoutDialog,
      layoutDialogMode,
      layoutName,
      layoutDescription,
      selectedLayoutId,
      savedLayouts,
      saveLayout,
      loadLayout,
      resetLayout,
      handleSaveLayout,
      handleLoadLayout,
      getPreviewModuleStyle,
      formatDate,

      // 3D场景控制
      resetView,
      toggleGrid,
      toggleAxes,

      // 事件处理
      onTopicSubscribe,
      onTopicUnsubscribe,
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
/* 继承原始样式 */
.draggable-main-layout {
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

.toolbar-left,
.toolbar-center,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.toolbar-center {
  flex: 1;
  justify-content: center;
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
  position: relative;
}

/* 传统布局样式 - 复用原始样式 */
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

.resize-line {
  width: 2px;
  height: 40px;
  background: rgba(255, 255, 255, 0.6);
  border-radius: 1px;
  transition: all 0.2s;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.scene-panel,
.topology-main-panel {
  flex: 1;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(148, 163, 184, 0.1);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  position: relative;
}

.scene-header,
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

.scene-content,
.topology-content {
  height: calc(100% - 40px);
  position: relative;
  z-index: 2;
  min-height: 400px;
  overflow: auto;
}

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
  min-width: calc(4 * 220px + 3 * 10px);
}

.mini-panel {
  min-width: 200px;
  background: rgba(15, 23, 42, 0.8);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(148, 163, 184, 0.1);
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
  transition: all 0.3s ease;
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
  padding: 8px;
}

/* 布局对话框样式 */
.saved-layouts {
  max-height: 400px;
  overflow-y: auto;
}

.layout-item {
  display: flex;
  gap: 15px;
  padding: 15px;
  border: 1px solid rgba(148, 163, 184, 0.1);
  border-radius: 8px;
  margin-bottom: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.layout-item:hover {
  border-color: rgba(59, 130, 246, 0.4);
  background: rgba(59, 130, 246, 0.05);
}

.layout-item.selected {
  border-color: rgba(59, 130, 246, 0.6);
  background: rgba(59, 130, 246, 0.1);
}

.layout-info {
  flex: 1;
}

.layout-info h4 {
  margin: 0 0 5px 0;
  color: #e2e8f0;
  font-size: 16px;
}

.layout-info p {
  margin: 0 0 5px 0;
  color: #94a3b8;
  font-size: 14px;
}

.layout-info small {
  color: #64748b;
  font-size: 12px;
}

.layout-preview {
  width: 100px;
  height: 60px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 4px;
  position: relative;
  overflow: hidden;
  border: 1px solid rgba(148, 163, 184, 0.2);
}

.preview-module {
  position: absolute;
  background: rgba(59, 130, 246, 0.6);
  border: 1px solid rgba(59, 130, 246, 0.8);
  border-radius: 1px;
}

.dialog-footer {
  text-align: right;
}
</style>