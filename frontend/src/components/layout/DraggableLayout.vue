<template>
  <div class="draggable-layout" ref="layoutContainer">
    <!-- 网格背景 -->
    <div class="grid-background" v-if="showGrid"></div>

    <!-- 可拖拽的模块 -->
    <div
      v-for="module in modules"
      :key="module.id"
      :ref="el => setModuleRef(module.id, el)"
      class="draggable-module"
      :class="{
        'dragging': draggingModule === module.id,
        'resizing': resizingModule === module.id,
        'selected': selectedModule === module.id
      }"
      :style="getModuleStyle(module)"
      @mousedown="handleMouseDown($event, module.id)"
      @touchstart="handleTouchStart($event, module.id)"
    >
      <!-- 模块头部 -->
      <div class="module-header" @mousedown.stop="handleHeaderMouseDown($event, module.id)">
        <div class="module-title">
          <el-icon class="module-icon">
            <component :is="module.icon" />
          </el-icon>
          <span>{{ module.title }}</span>
        </div>
        <div class="module-controls">
          <el-button size="small" text @click="toggleModuleMinimize(module.id)">
            <el-icon><Minus v-if="!module.minimized" /><Plus v-else /></el-icon>
          </el-button>
          <el-button size="small" text @click="toggleModuleMaximize(module.id)">
            <el-icon><FullScreen v-if="!module.maximized" /><CloseBold v-else /></el-icon>
          </el-button>
        </div>
      </div>

      <!-- 模块内容 -->
      <div class="module-content" v-show="!module.minimized">
        <component :is="getModuleComponent(module.component)" v-bind="module.props" />
      </div>

      <!-- 调整大小的句柄 -->
      <div
        v-if="!module.minimized && !module.maximized"
        class="resize-handles"
      >
        <div class="resize-handle resize-n" @mousedown.stop="handleResizeStart($event, module.id, 'n')"></div>
        <div class="resize-handle resize-ne" @mousedown.stop="handleResizeStart($event, module.id, 'ne')"></div>
        <div class="resize-handle resize-e" @mousedown.stop="handleResizeStart($event, module.id, 'e')"></div>
        <div class="resize-handle resize-se" @mousedown.stop="handleResizeStart($event, module.id, 'se')"></div>
        <div class="resize-handle resize-s" @mousedown.stop="handleResizeStart($event, module.id, 's')"></div>
        <div class="resize-handle resize-sw" @mousedown.stop="handleResizeStart($event, module.id, 'sw')"></div>
        <div class="resize-handle resize-w" @mousedown.stop="handleResizeStart($event, module.id, 'w')"></div>
        <div class="resize-handle resize-nw" @mousedown.stop="handleResizeStart($event, module.id, 'nw')"></div>
      </div>
    </div>

    <!-- 拖拽辅助线 -->
    <div v-if="showSnapLines" class="snap-lines">
      <div
        v-for="line in snapLines"
        :key="line.id"
        class="snap-line"
        :class="line.type"
        :style="line.style"
      ></div>
    </div>

    <!-- 网格吸附指示器 -->
    <div v-if="showGridSnap && gridSnapPosition" class="grid-snap-indicator" :style="gridSnapPosition"></div>
  </div>
</template>

<script>
import { ref, reactive, computed, onMounted, onUnmounted, nextTick } from 'vue'
import {
  Minus,
  Plus,
  FullScreen,
  CloseBold,
  VideoCamera,
  DataAnalysis,
  Location,
  Setting
} from '@element-plus/icons-vue'

// 导入所有可能的模块组件
import Scene3D from '../RViz/Scene3D.vue'
import NodeTopicGraph from '../RQT/widgets/NodeTopicGraph.vue'
import Scene3DController from '../RViz/Scene3DController.vue'
import GpsPanel from '../panels/GpsPanel.vue'
import StatusPanel from '../panels/StatusPanel.vue'
import ChartPanel from '../panels/ChartPanel.vue'

export default {
  name: 'DraggableLayout',
  components: {
    Minus,
    Plus,
    FullScreen,
    CloseBold,
    VideoCamera,
    DataAnalysis,
    Location,
    Setting,
    Scene3D,
    NodeTopicGraph,
    Scene3DController,
    GpsPanel,
    StatusPanel,
    ChartPanel
  },
  props: {
    modules: {
      type: Array,
      default: () => []
    },
    gridSize: {
      type: Number,
      default: 20
    },
    snapThreshold: {
      type: Number,
      default: 10
    },
    enableGrid: {
      type: Boolean,
      default: true
    },
    enableSnap: {
      type: Boolean,
      default: true
    }
  },
  emits: ['module-update', 'layout-change'],
  setup(props, { emit }) {
    const layoutContainer = ref(null)
    const moduleRefs = ref({})

    // 状态
    const draggingModule = ref(null)
    const resizingModule = ref(null)
    const selectedModule = ref(null)
    const showGrid = ref(props.enableGrid)
    const showSnapLines = ref(false)
    const showGridSnap = ref(false)

    // 拖拽和调整大小的状态
    const dragState = reactive({
      startX: 0,
      startY: 0,
      startLeft: 0,
      startTop: 0,
      startWidth: 0,
      startHeight: 0,
      resizeDirection: null
    })

    // 吸附线
    const snapLines = ref([])
    const gridSnapPosition = ref(null)

    // 组件映射
    const componentMap = {
      'Scene3D': Scene3D,
      'NodeTopicGraph': NodeTopicGraph,
      'Scene3DController': Scene3DController,
      'GpsPanel': GpsPanel,
      'StatusPanel': StatusPanel,
      'ChartPanel': ChartPanel
    }

    // 获取模块组件
    const getModuleComponent = (componentName) => {
      return componentMap[componentName] || 'div'
    }

    // 设置模块引用
    const setModuleRef = (id, el) => {
      if (el) {
        moduleRefs.value[id] = el
      }
    }

    // 获取模块样式
    const getModuleStyle = (module) => {
      const style = {
        left: `${module.x}px`,
        top: `${module.y}px`,
        width: `${module.width}px`,
        height: `${module.height}px`,
        zIndex: module.zIndex || 1
      }

      if (module.maximized) {
        style.left = '0px'
        style.top = '0px'
        style.width = '100%'
        style.height = '100%'
        style.zIndex = 1000
      }

      return style
    }

    // 鼠标事件处理
    const handleMouseDown = (event, moduleId) => {
      if (event.target.closest('.module-header') || event.target.closest('.resize-handle')) {
        return
      }
      selectModule(moduleId)
    }

    const handleTouchStart = (event, moduleId) => {
      if (event.target.closest('.module-header') || event.target.closest('.resize-handle')) {
        return
      }
      selectModule(moduleId)
    }

    // 头部拖拽开始
    const handleHeaderMouseDown = (event, moduleId) => {
      event.preventDefault()
      startDrag(event, moduleId)
    }

    // 开始拖拽
    const startDrag = (event, moduleId) => {
      const module = props.modules.find(m => m.id === moduleId)
      if (!module || module.maximized) return

      draggingModule.value = moduleId
      selectedModule.value = moduleId

      const clientX = event.touches ? event.touches[0].clientX : event.clientX
      const clientY = event.touches ? event.touches[0].clientY : event.clientY

      dragState.startX = clientX
      dragState.startY = clientY
      dragState.startLeft = module.x
      dragState.startTop = module.y

      document.addEventListener('mousemove', handleDragMove)
      document.addEventListener('mouseup', handleDragEnd)
      document.addEventListener('touchmove', handleDragMove, { passive: false })
      document.addEventListener('touchend', handleDragEnd)

      document.body.style.userSelect = 'none'
      document.body.style.cursor = 'move'

      if (props.enableSnap) {
        showSnapLines.value = true
      }
      if (props.enableGrid) {
        showGridSnap.value = true
      }
    }

    // 拖拽移动
    const handleDragMove = (event) => {
      if (!draggingModule.value) return

      event.preventDefault()
      const clientX = event.touches ? event.touches[0].clientX : event.clientX
      const clientY = event.touches ? event.touches[0].clientY : event.clientY

      const deltaX = clientX - dragState.startX
      const deltaY = clientY - dragState.startY

      let newX = dragState.startLeft + deltaX
      let newY = dragState.startTop + deltaY

      // 边界限制
      const containerRect = layoutContainer.value.getBoundingClientRect()
      const module = props.modules.find(m => m.id === draggingModule.value)

      newX = Math.max(0, Math.min(newX, containerRect.width - module.width))
      newY = Math.max(0, Math.min(newY, containerRect.height - module.height))

      // 网格吸附
      if (props.enableGrid) {
        const snappedX = Math.round(newX / props.gridSize) * props.gridSize
        const snappedY = Math.round(newY / props.gridSize) * props.gridSize

        if (Math.abs(newX - snappedX) < props.snapThreshold && Math.abs(newY - snappedY) < props.snapThreshold) {
          newX = snappedX
          newY = snappedY
          gridSnapPosition.value = {
            left: `${newX}px`,
            top: `${newY}px`,
            width: `${module.width}px`,
            height: `${module.height}px`
          }
        } else {
          gridSnapPosition.value = null
        }
      }

      // 模块吸附
      if (props.enableSnap) {
        const snapResult = calculateSnap(newX, newY, module)
        newX = snapResult.x
        newY = snapResult.y
        snapLines.value = snapResult.lines
      }

      // 更新模块位置
      updateModulePosition(draggingModule.value, newX, newY)
    }

    // 拖拽结束
    const handleDragEnd = () => {
      draggingModule.value = null
      showSnapLines.value = false
      showGridSnap.value = false
      snapLines.value = []
      gridSnapPosition.value = null

      document.removeEventListener('mousemove', handleDragMove)
      document.removeEventListener('mouseup', handleDragEnd)
      document.removeEventListener('touchmove', handleDragMove)
      document.removeEventListener('touchend', handleDragEnd)

      document.body.style.userSelect = ''
      document.body.style.cursor = ''

      emit('layout-change', props.modules)
    }

    // 调整大小开始
    const handleResizeStart = (event, moduleId, direction) => {
      event.preventDefault()
      event.stopPropagation()

      const module = props.modules.find(m => m.id === moduleId)
      if (!module) return

      resizingModule.value = moduleId
      selectedModule.value = moduleId
      dragState.resizeDirection = direction

      const clientX = event.touches ? event.touches[0].clientX : event.clientX
      const clientY = event.touches ? event.touches[0].clientY : event.clientY

      dragState.startX = clientX
      dragState.startY = clientY
      dragState.startLeft = module.x
      dragState.startTop = module.y
      dragState.startWidth = module.width
      dragState.startHeight = module.height

      document.addEventListener('mousemove', handleResizeMove)
      document.addEventListener('mouseup', handleResizeEnd)
      document.addEventListener('touchmove', handleResizeMove, { passive: false })
      document.addEventListener('touchend', handleResizeEnd)

      document.body.style.userSelect = 'none'
      document.body.style.cursor = getResizeCursor(direction)
    }

    // 调整大小移动
    const handleResizeMove = (event) => {
      if (!resizingModule.value) return

      event.preventDefault()
      const clientX = event.touches ? event.touches[0].clientX : event.clientX
      const clientY = event.touches ? event.touches[0].clientY : event.clientY

      const deltaX = clientX - dragState.startX
      const deltaY = clientY - dragState.startY

      const direction = dragState.resizeDirection
      let newX = dragState.startLeft
      let newY = dragState.startTop
      let newWidth = dragState.startWidth
      let newHeight = dragState.startHeight

      // 根据调整方向计算新的位置和大小
      if (direction.includes('n')) {
        newY = dragState.startTop + deltaY
        newHeight = dragState.startHeight - deltaY
      }
      if (direction.includes('s')) {
        newHeight = dragState.startHeight + deltaY
      }
      if (direction.includes('w')) {
        newX = dragState.startLeft + deltaX
        newWidth = dragState.startWidth - deltaX
      }
      if (direction.includes('e')) {
        newWidth = dragState.startWidth + deltaX
      }

      // 最小尺寸限制
      const minWidth = 200
      const minHeight = 150

      if (newWidth < minWidth) {
        if (direction.includes('w')) {
          newX = dragState.startLeft + dragState.startWidth - minWidth
        }
        newWidth = minWidth
      }

      if (newHeight < minHeight) {
        if (direction.includes('n')) {
          newY = dragState.startTop + dragState.startHeight - minHeight
        }
        newHeight = minHeight
      }

      // 边界限制
      const containerRect = layoutContainer.value.getBoundingClientRect()
      newX = Math.max(0, Math.min(newX, containerRect.width - newWidth))
      newY = Math.max(0, Math.min(newY, containerRect.height - newHeight))

      // 网格吸附
      if (props.enableGrid) {
        newX = Math.round(newX / props.gridSize) * props.gridSize
        newY = Math.round(newY / props.gridSize) * props.gridSize
        newWidth = Math.round(newWidth / props.gridSize) * props.gridSize
        newHeight = Math.round(newHeight / props.gridSize) * props.gridSize
      }

      // 更新模块
      updateModuleRect(resizingModule.value, newX, newY, newWidth, newHeight)
    }

    // 调整大小结束
    const handleResizeEnd = () => {
      resizingModule.value = null
      dragState.resizeDirection = null

      document.removeEventListener('mousemove', handleResizeMove)
      document.removeEventListener('mouseup', handleResizeEnd)
      document.removeEventListener('touchmove', handleResizeMove)
      document.removeEventListener('touchend', handleResizeEnd)

      document.body.style.userSelect = ''
      document.body.style.cursor = ''

      emit('layout-change', props.modules)
    }

    // 获取调整大小的光标样式
    const getResizeCursor = (direction) => {
      const cursors = {
        n: 'n-resize',
        ne: 'ne-resize',
        e: 'e-resize',
        se: 'se-resize',
        s: 's-resize',
        sw: 'sw-resize',
        w: 'w-resize',
        nw: 'nw-resize'
      }
      return cursors[direction] || 'default'
    }

    // 计算吸附
    const calculateSnap = (x, y, module) => {
      const lines = []
      let snappedX = x
      let snappedY = y

      // 获取其他模块的边界
      const otherModules = props.modules.filter(m => m.id !== module.id && !m.minimized)
      const bounds = otherModules.map(m => ({
        left: m.x,
        right: m.x + m.width,
        top: m.y,
        bottom: m.y + m.height
      }))

      // 水平吸附
      for (const bound of bounds) {
        // 左边对齐
        if (Math.abs(x - bound.left) < props.snapThreshold) {
          snappedX = bound.left
          lines.push({
            id: `h-${bound.left}`,
            type: 'vertical',
            style: { left: `${bound.left}px`, top: '0', height: '100%' }
          })
        }
        // 右边对齐
        if (Math.abs(x + module.width - bound.right) < props.snapThreshold) {
          snappedX = bound.right - module.width
          lines.push({
            id: `h-${bound.right}`,
            type: 'vertical',
            style: { left: `${bound.right}px`, top: '0', height: '100%' }
          })
        }
      }

      // 垂直吸附
      for (const bound of bounds) {
        // 顶部对齐
        if (Math.abs(y - bound.top) < props.snapThreshold) {
          snappedY = bound.top
          lines.push({
            id: `v-${bound.top}`,
            type: 'horizontal',
            style: { top: `${bound.top}px`, left: '0', width: '100%' }
          })
        }
        // 底部对齐
        if (Math.abs(y + module.height - bound.bottom) < props.snapThreshold) {
          snappedY = bound.bottom - module.height
          lines.push({
            id: `v-${bound.bottom}`,
            type: 'horizontal',
            style: { top: `${bound.bottom}px`, left: '0', width: '100%' }
          })
        }
      }

      return { x: snappedX, y: snappedY, lines }
    }

    // 更新模块位置
    const updateModulePosition = (moduleId, x, y) => {
      const module = props.modules.find(m => m.id === moduleId)
      if (module) {
        module.x = x
        module.y = y
        emit('module-update', { id: moduleId, x, y })
      }
    }

    // 更新模块矩形
    const updateModuleRect = (moduleId, x, y, width, height) => {
      const module = props.modules.find(m => m.id === moduleId)
      if (module) {
        module.x = x
        module.y = y
        module.width = width
        module.height = height
        emit('module-update', { id: moduleId, x, y, width, height })
      }
    }

    // 选择模块
    const selectModule = (moduleId) => {
      selectedModule.value = moduleId
      // 提升选中模块的层级
      const module = props.modules.find(m => m.id === moduleId)
      if (module) {
        module.zIndex = Math.max(...props.modules.map(m => m.zIndex || 1)) + 1
      }
    }

    // 切换模块最小化
    const toggleModuleMinimize = (moduleId) => {
      const module = props.modules.find(m => m.id === moduleId)
      if (module) {
        module.minimized = !module.minimized
        emit('module-update', { id: moduleId, minimized: module.minimized })
      }
    }

    // 切换模块最大化
    const toggleModuleMaximize = (moduleId) => {
      const module = props.modules.find(m => m.id === moduleId)
      if (module) {
        module.maximized = !module.maximized
        if (module.maximized) {
          module.zIndex = 1000
        } else {
          module.zIndex = 1
        }
        emit('module-update', { id: moduleId, maximized: module.maximized })
      }
    }

    // 键盘事件处理
    const handleKeyDown = (event) => {
      if (selectedModule.value && event.key === 'Delete') {
        // 可以添加删除模块的逻辑
      }
    }

    // 点击空白区域取消选择
    const handleLayoutClick = (event) => {
      if (event.target === layoutContainer.value) {
        selectedModule.value = null
      }
    }

    onMounted(() => {
      document.addEventListener('keydown', handleKeyDown)
      layoutContainer.value.addEventListener('click', handleLayoutClick)
    })

    onUnmounted(() => {
      document.removeEventListener('keydown', handleKeyDown)
      if (layoutContainer.value) {
        layoutContainer.value.removeEventListener('click', handleLayoutClick)
      }
    })

    return {
      layoutContainer,
      moduleRefs,
      draggingModule,
      resizingModule,
      selectedModule,
      showGrid,
      showSnapLines,
      showGridSnap,
      snapLines,
      gridSnapPosition,
      setModuleRef,
      getModuleComponent,
      getModuleStyle,
      handleMouseDown,
      handleTouchStart,
      handleHeaderMouseDown,
      handleResizeStart,
      toggleModuleMinimize,
      toggleModuleMaximize
    }
  }
}
</script>

<style scoped>
.draggable-layout {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: transparent;
}

/* 网格背景 */
.grid-background {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  opacity: 0.1;
  background-image:
    linear-gradient(to right, rgba(255, 255, 255, 0.1) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(255, 255, 255, 0.1) 1px, transparent 1px);
  background-size: 20px 20px;
  pointer-events: none;
  z-index: 0;
}

/* 可拖拽模块 */
.draggable-module {
  position: absolute;
  background: rgba(15, 23, 42, 0.95);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  transition: all 0.2s ease;
  overflow: hidden;
  min-width: 200px;
  min-height: 150px;
}

.draggable-module:hover {
  border-color: rgba(59, 130, 246, 0.4);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
}

.draggable-module.selected {
  border-color: rgba(59, 130, 246, 0.6);
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
}

.draggable-module.dragging {
  transform: rotate(2deg);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.5);
  z-index: 1000;
}

.draggable-module.resizing {
  box-shadow: 0 8px 32px rgba(59, 130, 246, 0.4);
}

/* 模块头部 */
.module-header {
  height: 36px;
  background: rgba(15, 23, 42, 0.9);
  border-bottom: 1px solid rgba(148, 163, 184, 0.1);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px;
  cursor: move;
  user-select: none;
}

.module-title {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #e2e8f0;
  font-size: 14px;
  font-weight: 500;
}

.module-icon {
  font-size: 16px;
  color: #3b82f6;
}

.module-controls {
  display: flex;
  gap: 4px;
}

/* 模块内容 */
.module-content {
  height: calc(100% - 36px);
  padding: 8px;
  overflow: auto;
}

/* 调整大小句柄 */
.resize-handles {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.resize-handle {
  position: absolute;
  pointer-events: all;
  transition: all 0.2s ease;
}

/* 边缘调整句柄 */
.resize-n {
  top: -3px;
  left: 8px;
  right: 8px;
  height: 6px;
  cursor: n-resize;
}

.resize-s {
  bottom: -3px;
  left: 8px;
  right: 8px;
  height: 6px;
  cursor: s-resize;
}

.resize-w {
  left: -3px;
  top: 8px;
  bottom: 8px;
  width: 6px;
  cursor: w-resize;
}

.resize-e {
  right: -3px;
  top: 8px;
  bottom: 8px;
  width: 6px;
  cursor: e-resize;
}

/* 角落调整句柄 */
.resize-nw {
  top: -3px;
  left: -3px;
  width: 12px;
  height: 12px;
  cursor: nw-resize;
}

.resize-ne {
  top: -3px;
  right: -3px;
  width: 12px;
  height: 12px;
  cursor: ne-resize;
}

.resize-sw {
  bottom: -3px;
  left: -3px;
  width: 12px;
  height: 12px;
  cursor: sw-resize;
}

.resize-se {
  bottom: -3px;
  right: -3px;
  width: 12px;
  height: 12px;
  cursor: se-resize;
  background: linear-gradient(-45deg, transparent 0%, transparent 40%, rgba(59, 130, 246, 0.6) 60%);
}

.resize-handle:hover {
  background-color: rgba(59, 130, 246, 0.3);
}

/* 吸附线 */
.snap-lines {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 999;
}

.snap-line {
  position: absolute;
  background: rgba(59, 130, 246, 0.8);
  pointer-events: none;
}

.snap-line.vertical {
  width: 1px;
}

.snap-line.horizontal {
  height: 1px;
}

/* 网格吸附指示器 */
.grid-snap-indicator {
  position: absolute;
  border: 2px dashed rgba(59, 130, 246, 0.6);
  background: rgba(59, 130, 246, 0.1);
  pointer-events: none;
  z-index: 998;
  border-radius: 4px;
}

/* 滚动条样式 */
.module-content::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

.module-content::-webkit-scrollbar-track {
  background: rgba(148, 163, 184, 0.1);
  border-radius: 3px;
}

.module-content::-webkit-scrollbar-thumb {
  background: rgba(148, 163, 184, 0.4);
  border-radius: 3px;
  transition: background 0.3s;
}

.module-content::-webkit-scrollbar-thumb:hover {
  background: rgba(148, 163, 184, 0.6);
}
</style>