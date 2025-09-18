<template>
  <div class="grid-layout-system" ref="gridContainer">
    <!-- 网格背景指示器 -->
    <div class="grid-indicator" v-if="showGridIndicator">
      <div
        v-for="cell in gridCells"
        :key="`${cell.row}-${cell.col}`"
        class="grid-cell"
        :class="{ 'occupied': cell.occupied, 'suggested': cell.suggested }"
        :style="getCellStyle(cell)"
      ></div>
    </div>

    <!-- 自动布局建议 -->
    <div v-if="showLayoutSuggestions" class="layout-suggestions">
      <div class="suggestions-header">
        <h4>布局建议</h4>
        <el-button size="small" @click="showLayoutSuggestions = false">
          <el-icon><Close /></el-icon>
        </el-button>
      </div>
      <div class="suggestions-content">
        <div
          v-for="suggestion in layoutSuggestions"
          :key="suggestion.id"
          class="suggestion-item"
          @click="applySuggestion(suggestion)"
        >
          <div class="suggestion-preview">
            <div
              v-for="module in suggestion.layout"
              :key="module.id"
              class="suggestion-module"
              :style="getSuggestionModuleStyle(module, suggestion.containerSize)"
            ></div>
          </div>
          <div class="suggestion-info">
            <span>{{ suggestion.name }}</span>
            <small>{{ suggestion.description }}</small>
          </div>
        </div>
      </div>
    </div>

    <!-- 布局控制面板 -->
    <div class="layout-controls">
      <el-button-group size="small">
        <el-button @click="autoArrange" type="primary">
          <el-icon><Refresh /></el-icon>
          自动排列
        </el-button>
        <el-button @click="toggleGridSnap">
          <el-icon><Grid /></el-icon>
          {{ gridSnapEnabled ? '关闭' : '开启' }}网格
        </el-button>
        <el-button @click="optimizeLayout">
          <el-icon><MagicStick /></el-icon>
          优化布局
        </el-button>
        <el-button @click="showLayoutSuggestions = true">
          <el-icon><Lightbulb /></el-icon>
          布局建议
        </el-button>
      </el-button-group>

      <div class="layout-info">
        <span>网格: {{ gridRows }}×{{ gridCols }}</span>
        <span>利用率: {{ Math.round(spaceUtilization * 100) }}%</span>
      </div>
    </div>

    <!-- 拖拽模块 -->
    <DraggableLayout
      :modules="modules"
      :grid-size="gridSize"
      :snap-threshold="snapThreshold"
      :enable-grid="gridSnapEnabled"
      :enable-snap="true"
      @module-update="handleModuleUpdate"
      @layout-change="handleLayoutChange"
    />
  </div>
</template>

<script>
import { ref, reactive, computed, watch, onMounted, nextTick } from 'vue'
import {
  Close,
  Refresh,
  Grid,
  MagicStick,
  Lightbulb
} from '@element-plus/icons-vue'
import DraggableLayout from './DraggableLayout.vue'

export default {
  name: 'GridLayoutSystem',
  components: {
    Close,
    Refresh,
    Grid,
    MagicStick,
    Lightbulb,
    DraggableLayout
  },
  props: {
    modules: {
      type: Array,
      default: () => []
    },
    autoOptimize: {
      type: Boolean,
      default: true
    },
    gridSize: {
      type: Number,
      default: 20
    }
  },
  emits: ['modules-update', 'layout-optimized'],
  setup(props, { emit }) {
    const gridContainer = ref(null)

    // 网格配置
    const gridSnapEnabled = ref(true)
    const snapThreshold = ref(10)
    const showGridIndicator = ref(false)
    const showLayoutSuggestions = ref(false)

    // 网格状态
    const containerSize = reactive({ width: 0, height: 0 })
    const gridCols = computed(() => Math.floor(containerSize.width / props.gridSize))
    const gridRows = computed(() => Math.floor(containerSize.height / props.gridSize))

    // 网格单元格
    const gridCells = computed(() => {
      const cells = []
      for (let row = 0; row < gridRows.value; row++) {
        for (let col = 0; col < gridCols.value; col++) {
          const cell = {
            row,
            col,
            x: col * props.gridSize,
            y: row * props.gridSize,
            occupied: false,
            suggested: false
          }

          // 检查是否被模块占用
          for (const module of props.modules) {
            if (!module.minimized && isOverlapping(cell, module)) {
              cell.occupied = true
              break
            }
          }

          cells.push(cell)
        }
      }
      return cells
    })

    // 空间利用率
    const spaceUtilization = computed(() => {
      const totalCells = gridRows.value * gridCols.value
      if (totalCells === 0) return 0

      const occupiedCells = gridCells.value.filter(cell => cell.occupied).length
      return occupiedCells / totalCells
    })

    // 布局建议
    const layoutSuggestions = ref([
      {
        id: 'balanced',
        name: '平衡布局',
        description: '均匀分布所有模块',
        layout: []
      },
      {
        id: 'sidebar',
        name: '侧边栏布局',
        description: '主要内容居中，工具栏在侧边',
        layout: []
      },
      {
        id: 'dashboard',
        name: '仪表板布局',
        description: '适合数据展示的网格排列',
        layout: []
      },
      {
        id: 'focus',
        name: '焦点布局',
        description: '突出主要模块，辅助模块紧凑排列',
        layout: []
      }
    ])

    // 检查重叠
    const isOverlapping = (cell, module) => {
      const cellRight = cell.x + props.gridSize
      const cellBottom = cell.y + props.gridSize
      const moduleRight = module.x + module.width
      const moduleBottom = module.y + module.height

      return !(cell.x >= moduleRight ||
               cellRight <= module.x ||
               cell.y >= moduleBottom ||
               cellBottom <= module.y)
    }

    // 获取单元格样式
    const getCellStyle = (cell) => {
      return {
        left: `${cell.x}px`,
        top: `${cell.y}px`,
        width: `${props.gridSize}px`,
        height: `${props.gridSize}px`
      }
    }

    // 获取建议模块样式
    const getSuggestionModuleStyle = (module, containerSize) => {
      const scale = 0.2 // 缩放比例
      return {
        left: `${module.x * scale}px`,
        top: `${module.y * scale}px`,
        width: `${module.width * scale}px`,
        height: `${module.height * scale}px`
      }
    }

    // 自动排列
    const autoArrange = () => {
      const sortedModules = [...props.modules].sort((a, b) => {
        // 按照重要性和大小排序
        const aArea = a.width * a.height
        const bArea = b.width * b.height
        return bArea - aArea // 大的模块优先
      })

      let currentX = 0
      let currentY = 0
      let rowHeight = 0

      sortedModules.forEach(module => {
        // 检查是否需要换行
        if (currentX + module.width > containerSize.width) {
          currentX = 0
          currentY += rowHeight + props.gridSize
          rowHeight = 0
        }

        // 网格对齐
        if (gridSnapEnabled.value) {
          currentX = Math.round(currentX / props.gridSize) * props.gridSize
          currentY = Math.round(currentY / props.gridSize) * props.gridSize
        }

        // 更新模块位置
        module.x = currentX
        module.y = currentY
        module.maximized = false
        module.minimized = false

        currentX += module.width + props.gridSize
        rowHeight = Math.max(rowHeight, module.height)
      })

      emit('modules-update', props.modules)
      emit('layout-optimized', 'auto-arrange')
    }

    // 优化布局
    const optimizeLayout = () => {
      // 1. 找出空隙
      const gaps = findGaps()

      // 2. 尝试填充空隙
      fillGaps(gaps)

      // 3. 调整模块大小以更好利用空间
      optimizeModuleSizes()

      emit('modules-update', props.modules)
      emit('layout-optimized', 'optimize')
    }

    // 寻找空隙
    const findGaps = () => {
      const gaps = []
      const occupiedGrid = new Array(gridRows.value).fill(null).map(() => new Array(gridCols.value).fill(false))

      // 标记被占用的网格
      props.modules.forEach(module => {
        if (!module.minimized) {
          const startCol = Math.floor(module.x / props.gridSize)
          const endCol = Math.ceil((module.x + module.width) / props.gridSize)
          const startRow = Math.floor(module.y / props.gridSize)
          const endRow = Math.ceil((module.y + module.height) / props.gridSize)

          for (let row = startRow; row < endRow && row < gridRows.value; row++) {
            for (let col = startCol; col < endCol && col < gridCols.value; col++) {
              occupiedGrid[row][col] = true
            }
          }
        }
      })

      // 寻找连续的空白区域
      for (let row = 0; row < gridRows.value; row++) {
        for (let col = 0; col < gridCols.value; col++) {
          if (!occupiedGrid[row][col]) {
            const gap = findLargestGapFrom(occupiedGrid, row, col)
            if (gap.width > 0 && gap.height > 0) {
              gaps.push(gap)
              // 标记这个区域已经处理过
              for (let r = gap.row; r < gap.row + gap.height; r++) {
                for (let c = gap.col; c < gap.col + gap.width; c++) {
                  occupiedGrid[r][c] = true
                }
              }
            }
          }
        }
      }

      return gaps
    }

    // 从指定位置寻找最大的空隙
    const findLargestGapFrom = (occupiedGrid, startRow, startCol) => {
      let maxWidth = 0
      let maxHeight = 0

      // 寻找最大宽度
      for (let col = startCol; col < gridCols.value && !occupiedGrid[startRow][col]; col++) {
        maxWidth++
      }

      // 寻找最大高度（考虑宽度约束）
      for (let row = startRow; row < gridRows.value; row++) {
        let canExpand = true
        for (let col = startCol; col < startCol + maxWidth; col++) {
          if (occupiedGrid[row][col]) {
            canExpand = false
            break
          }
        }
        if (canExpand) {
          maxHeight++
        } else {
          break
        }
      }

      return {
        row: startRow,
        col: startCol,
        x: startCol * props.gridSize,
        y: startRow * props.gridSize,
        width: maxWidth,
        height: maxHeight,
        pixelWidth: maxWidth * props.gridSize,
        pixelHeight: maxHeight * props.gridSize
      }
    }

    // 填充空隙
    const fillGaps = (gaps) => {
      // 按面积排序，优先填充大的空隙
      gaps.sort((a, b) => (b.width * b.height) - (a.width * a.height))

      gaps.forEach(gap => {
        // 寻找可以扩展到这个空隙的相邻模块
        const adjacentModules = findAdjacentModules(gap)

        if (adjacentModules.length > 0) {
          // 选择最适合的模块进行扩展
          const bestModule = adjacentModules.reduce((best, current) => {
            const bestFit = calculateExpansionFit(best, gap)
            const currentFit = calculateExpansionFit(current, gap)
            return currentFit > bestFit ? current : best
          })

          expandModuleToGap(bestModule, gap)
        }
      })
    }

    // 寻找空隙相邻的模块
    const findAdjacentModules = (gap) => {
      const adjacent = []
      const tolerance = props.gridSize

      props.modules.forEach(module => {
        if (!module.minimized && !module.maximized) {
          const moduleRight = module.x + module.width
          const moduleBottom = module.y + module.height
          const gapRight = gap.x + gap.pixelWidth
          const gapBottom = gap.y + gap.pixelHeight

          // 检查是否相邻（水平或垂直）
          const isHorizontallyAdjacent =
            (Math.abs(moduleRight - gap.x) <= tolerance || Math.abs(module.x - gapRight) <= tolerance) &&
            !(module.y >= gapBottom || moduleBottom <= gap.y)

          const isVerticallyAdjacent =
            (Math.abs(moduleBottom - gap.y) <= tolerance || Math.abs(module.y - gapBottom) <= tolerance) &&
            !(module.x >= gapRight || moduleRight <= gap.x)

          if (isHorizontallyAdjacent || isVerticallyAdjacent) {
            adjacent.push({
              module,
              direction: isHorizontallyAdjacent ? 'horizontal' : 'vertical'
            })
          }
        }
      })

      return adjacent
    }

    // 计算扩展适合度
    const calculateExpansionFit = (adjacentInfo, gap) => {
      const { module, direction } = adjacentInfo
      let fit = 0

      if (direction === 'horizontal') {
        // 水平扩展的适合度
        fit = Math.min(module.height, gap.pixelHeight) / Math.max(module.height, gap.pixelHeight)
      } else {
        // 垂直扩展的适合度
        fit = Math.min(module.width, gap.pixelWidth) / Math.max(module.width, gap.pixelWidth)
      }

      return fit
    }

    // 将模块扩展到空隙
    const expandModuleToGap = (adjacentInfo, gap) => {
      const { module, direction } = adjacentInfo

      if (direction === 'horizontal') {
        // 水平扩展
        if (module.x + module.width <= gap.x) {
          // 向右扩展
          module.width = gap.x + gap.pixelWidth - module.x
        } else if (gap.x + gap.pixelWidth <= module.x) {
          // 向左扩展
          module.width = module.x + module.width - gap.x
          module.x = gap.x
        }
      } else {
        // 垂直扩展
        if (module.y + module.height <= gap.y) {
          // 向下扩展
          module.height = gap.y + gap.pixelHeight - module.y
        } else if (gap.y + gap.pixelHeight <= module.y) {
          // 向上扩展
          module.height = module.y + module.height - gap.y
          module.y = gap.y
        }
      }
    }

    // 优化模块大小
    const optimizeModuleSizes = () => {
      props.modules.forEach(module => {
        if (!module.minimized && !module.maximized) {
          // 将模块大小调整到网格边界
          const gridX = Math.round(module.x / props.gridSize) * props.gridSize
          const gridY = Math.round(module.y / props.gridSize) * props.gridSize
          const gridWidth = Math.ceil(module.width / props.gridSize) * props.gridSize
          const gridHeight = Math.ceil(module.height / props.gridSize) * props.gridSize

          module.x = gridX
          module.y = gridY
          module.width = Math.min(gridWidth, containerSize.width - gridX)
          module.height = Math.min(gridHeight, containerSize.height - gridY)
        }
      })
    }

    // 生成布局建议
    const generateLayoutSuggestions = () => {
      const moduleCount = props.modules.length
      const containerRatio = containerSize.width / containerSize.height

      // 平衡布局
      layoutSuggestions.value[0].layout = generateBalancedLayout()

      // 侧边栏布局
      layoutSuggestions.value[1].layout = generateSidebarLayout()

      // 仪表板布局
      layoutSuggestions.value[2].layout = generateDashboardLayout()

      // 焦点布局
      layoutSuggestions.value[3].layout = generateFocusLayout()
    }

    // 生成平衡布局
    const generateBalancedLayout = () => {
      const layout = []
      const cols = Math.ceil(Math.sqrt(props.modules.length))
      const rows = Math.ceil(props.modules.length / cols)
      const moduleWidth = Math.floor(containerSize.width / cols)
      const moduleHeight = Math.floor(containerSize.height / rows)

      props.modules.forEach((module, index) => {
        const row = Math.floor(index / cols)
        const col = index % cols

        layout.push({
          ...module,
          x: col * moduleWidth,
          y: row * moduleHeight,
          width: moduleWidth - 10,
          height: moduleHeight - 10,
          minimized: false,
          maximized: false
        })
      })

      return layout
    }

    // 生成侧边栏布局
    const generateSidebarLayout = () => {
      const layout = []
      const sidebarWidth = Math.floor(containerSize.width * 0.25)
      const mainWidth = containerSize.width - sidebarWidth - 10

      // 主要模块 (3D场景和拓扑图)
      const mainModules = props.modules.filter(m =>
        m.id.includes('scene') || m.id.includes('topology')
      )

      // 辅助模块
      const sidebarModules = props.modules.filter(m =>
        !m.id.includes('scene') && !m.id.includes('topology')
      )

      // 布置主要模块
      mainModules.forEach((module, index) => {
        layout.push({
          ...module,
          x: sidebarWidth + 10,
          y: index * (containerSize.height / mainModules.length),
          width: mainWidth,
          height: Math.floor(containerSize.height / mainModules.length) - 10,
          minimized: false,
          maximized: false
        })
      })

      // 布置侧边栏模块
      sidebarModules.forEach((module, index) => {
        layout.push({
          ...module,
          x: 0,
          y: index * (containerSize.height / sidebarModules.length),
          width: sidebarWidth,
          height: Math.floor(containerSize.height / sidebarModules.length) - 10,
          minimized: false,
          maximized: false
        })
      })

      return layout
    }

    // 生成仪表板布局
    const generateDashboardLayout = () => {
      const layout = []
      const cols = 3
      const rows = Math.ceil(props.modules.length / cols)
      const moduleWidth = Math.floor(containerSize.width / cols)
      const moduleHeight = Math.floor(containerSize.height / rows)

      props.modules.forEach((module, index) => {
        const row = Math.floor(index / cols)
        const col = index % cols

        // 某些模块占用更多空间
        let width = moduleWidth - 10
        let height = moduleHeight - 10

        if (module.id.includes('scene') || module.id.includes('topology')) {
          width = moduleWidth * 2 - 10
          height = moduleHeight * 2 - 10
        }

        layout.push({
          ...module,
          x: col * moduleWidth,
          y: row * moduleHeight,
          width,
          height,
          minimized: false,
          maximized: false
        })
      })

      return layout
    }

    // 生成焦点布局
    const generateFocusLayout = () => {
      const layout = []
      const focusModule = props.modules.find(m => m.id.includes('scene')) || props.modules[0]

      // 焦点模块占用大部分空间
      layout.push({
        ...focusModule,
        x: 0,
        y: 0,
        width: Math.floor(containerSize.width * 0.7),
        height: Math.floor(containerSize.height * 0.7),
        minimized: false,
        maximized: false
      })

      // 其他模块紧凑排列
      const otherModules = props.modules.filter(m => m.id !== focusModule.id)
      const sideWidth = containerSize.width - Math.floor(containerSize.width * 0.7) - 10
      const moduleHeight = Math.floor(containerSize.height / otherModules.length)

      otherModules.forEach((module, index) => {
        layout.push({
          ...module,
          x: Math.floor(containerSize.width * 0.7) + 10,
          y: index * moduleHeight,
          width: sideWidth,
          height: moduleHeight - 10,
          minimized: false,
          maximized: false
        })
      })

      return layout
    }

    // 应用布局建议
    const applySuggestion = (suggestion) => {
      suggestion.layout.forEach(suggestedModule => {
        const originalModule = props.modules.find(m => m.id === suggestedModule.id)
        if (originalModule) {
          Object.assign(originalModule, suggestedModule)
        }
      })

      emit('modules-update', props.modules)
      emit('layout-optimized', `suggestion-${suggestion.id}`)
      showLayoutSuggestions.value = false
    }

    // 切换网格吸附
    const toggleGridSnap = () => {
      gridSnapEnabled.value = !gridSnapEnabled.value
      showGridIndicator.value = gridSnapEnabled.value
    }

    // 事件处理
    const handleModuleUpdate = (moduleData) => {
      emit('modules-update', props.modules)
    }

    const handleLayoutChange = (modules) => {
      emit('modules-update', modules)

      // 如果启用了自动优化，延迟执行优化
      if (props.autoOptimize) {
        setTimeout(() => {
          optimizeLayout()
        }, 1000)
      }
    }

    // 更新容器大小
    const updateContainerSize = () => {
      if (gridContainer.value) {
        const rect = gridContainer.value.getBoundingClientRect()
        containerSize.width = rect.width
        containerSize.height = rect.height
      }
    }

    // 监听容器大小变化
    watch([() => containerSize.width, () => containerSize.height], () => {
      generateLayoutSuggestions()
    })

    onMounted(() => {
      updateContainerSize()
      generateLayoutSuggestions()

      // 监听窗口大小变化
      const resizeObserver = new ResizeObserver(() => {
        updateContainerSize()
      })
      resizeObserver.observe(gridContainer.value)

      // 清理
      return () => {
        resizeObserver.disconnect()
      }
    })

    return {
      gridContainer,
      gridSnapEnabled,
      snapThreshold,
      showGridIndicator,
      showLayoutSuggestions,
      gridCols,
      gridRows,
      gridCells,
      spaceUtilization,
      layoutSuggestions,
      getCellStyle,
      getSuggestionModuleStyle,
      autoArrange,
      toggleGridSnap,
      optimizeLayout,
      applySuggestion,
      handleModuleUpdate,
      handleLayoutChange
    }
  }
}
</script>

<style scoped>
.grid-layout-system {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
}

/* 网格指示器 */
.grid-indicator {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 1;
}

.grid-cell {
  position: absolute;
  border: 1px solid rgba(148, 163, 184, 0.1);
  transition: all 0.2s ease;
}

.grid-cell.occupied {
  background: rgba(59, 130, 246, 0.1);
  border-color: rgba(59, 130, 246, 0.3);
}

.grid-cell.suggested {
  background: rgba(34, 197, 94, 0.2);
  border-color: rgba(34, 197, 94, 0.5);
  animation: pulse-suggest 2s infinite;
}

@keyframes pulse-suggest {
  0%, 100% {
    opacity: 0.5;
  }
  50% {
    opacity: 1;
  }
}

/* 布局建议面板 */
.layout-suggestions {
  position: absolute;
  top: 20px;
  right: 20px;
  width: 300px;
  background: rgba(15, 23, 42, 0.95);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 8px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
  z-index: 1000;
  overflow: hidden;
}

.suggestions-header {
  height: 40px;
  background: rgba(15, 23, 42, 0.9);
  border-bottom: 1px solid rgba(148, 163, 184, 0.1);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 15px;
}

.suggestions-header h4 {
  margin: 0;
  color: #e2e8f0;
  font-size: 14px;
  font-weight: 500;
}

.suggestions-content {
  max-height: 400px;
  overflow-y: auto;
  padding: 10px;
}

.suggestion-item {
  display: flex;
  gap: 10px;
  padding: 10px;
  border: 1px solid rgba(148, 163, 184, 0.1);
  border-radius: 6px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.suggestion-item:hover {
  border-color: rgba(59, 130, 246, 0.4);
  background: rgba(59, 130, 246, 0.05);
}

.suggestion-preview {
  position: relative;
  width: 60px;
  height: 40px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 4px;
  overflow: hidden;
  flex-shrink: 0;
}

.suggestion-module {
  position: absolute;
  background: rgba(59, 130, 246, 0.6);
  border: 1px solid rgba(59, 130, 246, 0.8);
  border-radius: 2px;
}

.suggestion-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.suggestion-info span {
  color: #e2e8f0;
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 2px;
}

.suggestion-info small {
  color: #94a3b8;
  font-size: 11px;
}

/* 布局控制面板 */
.layout-controls {
  position: absolute;
  bottom: 20px;
  left: 20px;
  display: flex;
  align-items: center;
  gap: 15px;
  background: rgba(15, 23, 42, 0.95);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 8px;
  padding: 10px 15px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  z-index: 100;
}

.layout-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.layout-info span {
  color: #94a3b8;
  font-size: 11px;
}

/* 滚动条样式 */
.suggestions-content::-webkit-scrollbar {
  width: 6px;
}

.suggestions-content::-webkit-scrollbar-track {
  background: rgba(148, 163, 184, 0.1);
  border-radius: 3px;
}

.suggestions-content::-webkit-scrollbar-thumb {
  background: rgba(148, 163, 184, 0.4);
  border-radius: 3px;
  transition: background 0.3s;
}

.suggestions-content::-webkit-scrollbar-thumb:hover {
  background: rgba(148, 163, 184, 0.6);
}
</style>