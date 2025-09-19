<template>
  <div class="chart-panel">
    <!-- 主工具栏 -->
    <div class="chart-controls">
      <div class="controls-left">
        <el-button size="small" @click="showTopicSelector = !showTopicSelector" :type="showTopicSelector ? 'primary' : 'default'">
          <el-icon><Plus /></el-icon>
          添加数据源
        </el-button>
        <el-button size="small" @click="debugRosConnection" type="info">
          <el-icon><Refresh /></el-icon>
          调试连接
        </el-button>

        <el-button-group size="small">
          <el-button @click="pauseChart" :type="isPaused ? 'primary' : 'default'">
            <el-icon>
              <VideoPause v-if="!isPaused" />
              <VideoPlay v-else />
            </el-icon>
            {{ isPaused ? '继续' : '暂停' }}
          </el-button>
          <el-button @click="clearChart">
            <el-icon><Delete /></el-icon>
            清除
          </el-button>
        </el-button-group>
      </div>

      <div class="controls-center">
        <span class="time-range-label">时间范围:</span>
        <el-select v-model="timeWindow" size="small" style="width: 100px" @change="onTimeWindowChange">
          <el-option label="10秒" :value="10" />
          <el-option label="30秒" :value="30" />
          <el-option label="1分钟" :value="60" />
          <el-option label="5分钟" :value="300" />
          <el-option label="10分钟" :value="600" />
        </el-select>
      </div>

      <div class="controls-right">
        <el-button size="small" @click="showLegendPanel = !showLegendPanel" :type="showLegendPanel ? 'primary' : 'default'">
          <el-icon><List /></el-icon>
          图例
        </el-button>
        <el-button size="small" @click="resetZoom">
          <el-icon><Refresh /></el-icon>
          重置缩放
        </el-button>
        <el-button size="small" @click="toggleFullscreen" style="margin-left: 8px;">
          <el-icon><FullScreen /></el-icon>
          {{ isFullscreen ? '退出全屏' : '全屏' }}
        </el-button>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="chart-main" :class="{ 'with-sidebar': showTopicSelector || showLegendPanel }">

      <!-- 左侧主题选择面板 -->
      <div v-if="showTopicSelector" class="topic-selector-panel">
        <div class="panel-header">
          <h4>选择数据源</h4>
          <div class="panel-header-actions">
            <el-button size="small" @click="loadTopics" type="primary">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
            <el-button size="small" text @click="showTopicSelector = false">
              <el-icon><Close /></el-icon>
            </el-button>
          </div>
        </div>
        <div class="panel-content">
          <div class="topic-search">
            <el-input
              v-model="topicSearchText"
              size="small"
              placeholder="搜索主题..."
              clearable
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
          </div>
          <div v-if="filteredAvailableTopics.length === 0" class="empty-state">
            <div class="empty-icon">📡</div>
            <p>未找到可用的topic</p>
            <p class="empty-hint">请确保：</p>
            <ul class="empty-checklist">
              <li>ROS系统正在运行</li>
              <li>有节点在发布数据</li>
              <li>网络连接正常</li>
            </ul>
            <el-button @click="debugRosConnection" type="primary" size="small">
              <el-icon><Refresh /></el-icon>
              诊断连接
            </el-button>
          </div>
          <div v-else class="topic-tree">
            <div class="topic-stats">
              <span class="stats-item">总计: {{ availableTopics.length }}</span>
              <span class="stats-item active">活跃: {{ availableTopics.filter(t => t.isActive).length }}</span>
            </div>
            <div v-for="topic in filteredAvailableTopics" :key="topic.value" class="topic-item" :class="{ 'inactive': !topic.isActive }">
              <div class="topic-name" @click="expandTopic(topic)">
                <el-icon class="expand-icon" :class="{ 'expanded': expandedTopics.includes(topic.value) }">
                  <ArrowRight />
                </el-icon>
                <div class="topic-info">
                  <div class="topic-main">
                    <span class="topic-label">{{ topic.label }}</span>
                    <el-tag :type="topic.isActive ? 'success' : 'info'" size="small" class="status-tag">
                      {{ topic.status }}
                    </el-tag>
                  </div>
                  <div class="topic-details">
                    <span class="topic-path">{{ topic.fullName }}</span>
                    <span class="topic-type">{{ topic.messageType }}</span>
                  </div>
                </div>
              </div>
              <div v-if="expandedTopics.includes(topic.value)" class="topic-fields">
                <div
                  v-for="field in getTopicFields(topic)"
                  :key="`${topic.value}.${field.path}`"
                  class="field-item"
                  :class="{
                    'selected': isFieldSelected(topic.value, field.path),
                    'disabled': !isFieldPlottable(field.type) && !field.isParsing,
                    'plottable': isFieldPlottable(field.type),
                    'non-plottable': !isFieldPlottable(field.type) && !field.isParsing,
                    'parsing': field.isParsing
                  }"
                  @click="isFieldPlottable(field.type) ? addDataSeries(topic.value, field, topic.messageType) : null"
                  :title="field.isParsing ? '正在解析消息结构...' : (isFieldPlottable(field.type) ? `点击添加 ${field.name} 到图表` : `${getFieldTypeInfo(field.type).description} - 不支持绘制`)"
                >
                  <div class="field-main">
                    <span class="field-icon">
                      <span v-if="field.isParsing" class="parsing-spinner">⟳</span>
                      <span v-else>{{ getFieldTypeInfo(field.type).icon }}</span>
                    </span>
                    <span class="field-name">{{ field.name }}</span>
                    <span v-if="!field.isParsing" class="field-type" :class="getFieldTypeInfo(field.type).category">{{ field.type }}</span>
                    <span v-else class="field-type parsing">解析中...</span>
                  </div>
                  <div class="field-actions">
                    <span v-if="field.isParsing" class="field-status parsing">⟳</span>
                    <span v-else-if="isFieldSelected(topic.value, field.path)" class="field-status selected">✓</span>
                    <span v-else-if="!isFieldPlottable(field.type)" class="field-status disabled">🚫</span>
                    <span v-else class="field-status available">+</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 图表容器 -->
      <div class="chart-container" ref="chartContainer">
        <svg class="chart-svg" :width="chartSize.width" :height="chartSize.height" v-if="chartReady"
             @mousedown="startPan" @mousemove="handlePan" @mouseup="endPan" @mouseleave="endPan"
             @wheel="handleZoom">
          <!-- 网格线 -->
          <g class="grid">
            <defs>
              <pattern :id="`chartGrid-${isFullscreen ? 'fullscreen' : 'normal'}`" 
                       :width="gridSpacing.x" 
                       :height="gridSpacing.y" 
                       patternUnits="userSpaceOnUse">
                <path :d="`M ${gridSpacing.x} 0 L 0 0 0 ${gridSpacing.y}`" 
                      fill="none" 
                      stroke="#f0f0f0" 
                      stroke-width="1"/>
              </pattern>
            </defs>
            <rect 
              :x="currentMargin.left" 
              :y="currentMargin.top" 
              :width="chartSize.width - currentMargin.left - currentMargin.right" 
              :height="chartSize.height - currentMargin.top - currentMargin.bottom" 
              :fill="`url(#chartGrid-${isFullscreen ? 'fullscreen' : 'normal'})`" 
            />
          </g>

        <!-- Y轴 -->
        <g class="y-axis">
          <line
            :x1="currentMargin.left"
            :y1="currentMargin.top"
            :x2="currentMargin.left"
            :y2="chartSize.height - currentMargin.bottom"
            stroke="#333"
            stroke-width="2"
          />
          <g v-for="(tick, index) in yTicks" :key="`y-${index}`">
            <line
              :x1="currentMargin.left - 5"
              :y1="tick.y"
              :x2="currentMargin.left"
              :y2="tick.y"
              stroke="#333"
              stroke-width="1"
            />
            <text
              :x="currentMargin.left - 8"
              :y="tick.y + 4"
              text-anchor="end"
              class="axis-label"
            >
              {{ tick.value.toFixed(1) }}
            </text>
          </g>
        </g>

        <!-- X轴 -->
        <g class="x-axis">
          <line
            :x1="currentMargin.left"
            :y1="chartSize.height - currentMargin.bottom"
            :x2="chartSize.width - currentMargin.right"
            :y2="chartSize.height - currentMargin.bottom"
            stroke="#333"
            stroke-width="2"
          />
          <g v-for="(tick, index) in xTicks" :key="`x-${index}`">
            <line
              :x1="tick.x"
              :y1="chartSize.height - currentMargin.bottom"
              :x2="tick.x"
              :y2="chartSize.height - currentMargin.bottom + 5"
              stroke="#333"
              stroke-width="1"
            />
            <text
              :x="tick.x"
              :y="chartSize.height - currentMargin.bottom + 15"
              text-anchor="middle"
              class="axis-label"
            >
              {{ tick.label }}
            </text>
          </g>
        </g>

          <!-- 数据线 -->
          <g class="data-lines">
            <path
              v-for="(series, index) in visibleDataSeries"
              :key="`series-${series.id}`"
              :d="getLinePath(series.data)"
              :stroke="series.color"
              stroke-width="2"
              fill="none"
              class="data-line"
              :style="{ opacity: series.visible ? 0.8 : 0 }"
            />
          </g>

          <!-- 数据点 -->
          <g class="data-points">
            <g v-for="(series, seriesIndex) in visibleDataSeries" :key="`points-${series.id}`">
              <circle
                v-for="(point, pointIndex) in getVisibleDataPoints(series.data)"
                :key="`point-${series.id}-${pointIndex}`"
                :cx="getX(point.time)"
                :cy="getY(point.value, series.yAxisIndex)"
                r="4"
                :fill="series.color"
                :stroke="'white'"
                :stroke-width="2"
                class="data-point-end"
                :style="{ opacity: series.visible ? 1 : 0 }"
                @mouseenter="showTooltip($event, point, series)"
                @mouseleave="hideTooltip"
              />
            </g>
          </g>

          <!-- 简化的内嵌图例 -->
          <g class="legend" v-if="!showLegendPanel && visibleDataSeries.length > 0">
            <g v-for="(series, index) in visibleDataSeries.slice(0, 3)" :key="`legend-${series.id}`">
              <rect
                :x="currentMargin.left + index * 80"
                :y="5"
                width="12"
                height="12"
                :fill="series.color"
              />
              <text
                :x="currentMargin.left + index * 80 + 16"
                :y="15"
                class="legend-text"
              >
                {{ series.name.length > 8 ? series.name.substring(0, 8) + '...' : series.name }}
              </text>
            </g>
            <text v-if="visibleDataSeries.length > 3" :x="currentMargin.left + 3 * 80" :y="15" class="legend-text">
              +{{ visibleDataSeries.length - 3 }}更多
            </text>
          </g>

          <!-- 当前值显示 -->
          <g class="current-values" v-if="visibleDataSeries.length > 0">
            <rect
              :x="chartSize.width - currentMargin.right - 100"
              :y="currentMargin.top"
              width="95"
              :height="Math.min(60 + visibleDataSeries.length * 15, 150)"
              fill="rgba(255, 255, 255, 0.9)"
              stroke="#ddd"
              rx="4"
            />
            <text
              :x="chartSize.width - currentMargin.right - 95"
              :y="currentMargin.top + 15"
              class="current-value-title"
            >
              当前值
            </text>
            <g v-for="(series, index) in visibleDataSeries.slice(0, 8)" :key="`current-${series.id}`">
              <text
                :x="chartSize.width - currentMargin.right - 95"
                :y="currentMargin.top + 30 + index * 15"
                :fill="series.color"
                class="current-value-text"
              >
                {{ series.name.length > 6 ? series.name.substring(0, 6) + '...' : series.name }}: {{ getCurrentValue(series) }}
              </text>
            </g>
          </g>
        </svg>

        <div v-if="!chartReady" class="chart-loading">
          <div class="loading-spinner"></div>
          <span>初始化图表...</span>
        </div>
      </div>

      <!-- 右侧图例面板 -->
      <div v-if="showLegendPanel" class="legend-panel">
        <div class="panel-header">
          <h4>图例管理</h4>
          <el-button size="small" text @click="showLegendPanel = false">
            <el-icon><Close /></el-icon>
          </el-button>
        </div>
        <div class="panel-content">
          <div class="legend-list">
            <div
              v-for="(series, index) in dataSeries"
              :key="series.id"
              class="legend-item"
              :class="{ 'disabled': !series.visible }"
            >
              <div class="legend-item-main">
                <div class="color-indicator" :style="{ backgroundColor: series.color }"></div>
                <span class="series-name" :title="series.fullName">{{ series.name }}</span>
                <div class="legend-controls">
                  <el-button size="small" text @click="toggleSeriesVisibility(series.id)">
                    <el-icon>
                      <View v-if="series.visible" />
                      <Hide v-else />
                    </el-icon>
                  </el-button>
                  <el-button size="small" text @click="removeDataSeries(series.id)">
                    <el-icon><Close /></el-icon>
                  </el-button>
                </div>
              </div>
              <div class="legend-item-details">
                <span class="topic-info">{{ series.topic }}</span>
                <span class="field-info">{{ series.fieldPath }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { VideoPause, VideoPlay, Delete, Plus, Close, Search, ArrowRight, List, Refresh, View, Hide } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useRosbridge } from '../../composables/useRosbridge'

export default {
  name: 'ChartPanel',
  components: {
    VideoPause,
    VideoPlay,
    Delete,
    Plus,
    Close,
    Search,
    ArrowRight,
    List,
    Refresh,
    View,
    Hide
  },
  setup() {
    const rosbridge = useRosbridge()
    const chartContainer = ref(null)
    const chartReady = ref(false)

    // 图表配置
    const margin = ref({ top: 30, right: 90, bottom: 40, left: 60 })
    const chartSize = ref({ width: 300, height: 200 })
    const timeWindow = ref(30) // 30秒时间窗口
    
    // 全屏时的边距配置 - 最小化边距以最大化利用屏幕空间
    const fullscreenMargin = { top: 10, right: 10, bottom: 10, left: 10 }
    
    // 计算当前应该使用的边距
    const currentMargin = computed(() => {
      return isFullscreen.value ? fullscreenMargin : margin.value
    })
    
    // 计算栅格间距，使其与坐标轴刻度匹配
    const gridSpacing = computed(() => {
      const currentMargins = currentMargin.value
      const chartWidth = chartSize.value.width - currentMargins.left - currentMargins.right
      const chartHeight = chartSize.value.height - currentMargins.top - currentMargins.bottom
      
      if (isFullscreen.value) {
        // 全屏时使用更密集的栅格，充分利用屏幕空间
        const xSpacing = Math.max(15, Math.floor(chartWidth / 30)) // 至少15px间距，最多30个格子
        const ySpacing = Math.max(15, Math.floor(chartHeight / 25)) // 至少15px间距，最多25个格子
        return { x: xSpacing, y: ySpacing }
      } else {
        // 正常模式使用适中的栅格密度
        const xSpacing = Math.max(20, Math.floor(chartWidth / 20)) // 至少20px间距，最多20个格子
        const ySpacing = Math.max(20, Math.floor(chartHeight / 15)) // 至少20px间距，最多15个格子
        return { x: xSpacing, y: ySpacing }
      }
    })
    
    // 根据时间窗口获取固定的最大数据点数
    const getMaxDataPoints = () => {
      if (timeWindow.value <= 10) {
        return 100 // 10秒窗口：100个点
      } else if (timeWindow.value <= 30) {
        return 300 // 30秒窗口：300个点
      } else if (timeWindow.value <= 60) {
        return 600 // 1分钟窗口：600个点
      } else if (timeWindow.value <= 300) {
        return 3000 // 5分钟窗口：3000个点
      } else {
        return 6000 // 10分钟窗口：6000个点
      }
    }

    // 控制状态
    const isPaused = ref(false)
    const showTopicSelector = ref(false)
    const showLegendPanel = ref(false)
    const isFullscreen = ref(false)
    
    // 频率检测和采样管理
    const topicFrequencies = ref(new Map()) // 存储每个topic的实际频率
    const lastUpdateTime = ref(new Map()) // 存储每个topic的最后更新时间
    const samplingCounters = ref(new Map()) // 存储每个topic的采样计数器

    // 主题选择相关
    const topicSearchText = ref('')
    const expandedTopics = ref([])

    // 缩放和平移状态
    const zoomLevel = ref(1)
    const panOffset = ref({ x: 0, y: 0 })
    const isPanning = ref(false)
    const panStart = ref({ x: 0, y: 0 })

    // 数据系列管理
    let seriesIdCounter = 0

    // 可用主题列表 - 动态从ROS获取
    const availableTopics = ref([])

    // 数据系列
    const dataSeries = ref([])

    // 预定义颜色
    const predefinedColors = [
      '#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#909399',
      '#00d4ff', '#00ff88', '#ffaa00', '#ff4757', '#74b9ff',
      '#fd79a8', '#a29bfe', '#6c5ce7', '#00b894', '#00cec9'
    ]
    let colorIndex = 0

    // 计算属性
    const visibleDataSeries = computed(() => {
      return dataSeries.value.filter(series => series.visible)
    })

    const filteredAvailableTopics = computed(() => {
      if (!topicSearchText.value) return availableTopics.value

      const searchText = topicSearchText.value.toLowerCase()
      return availableTopics.value.filter(topic =>
        topic.label.toLowerCase().includes(searchText) ||
        topic.value.toLowerCase().includes(searchText) ||
        (topic.fullName && topic.fullName.toLowerCase().includes(searchText)) ||
        topic.messageType.toLowerCase().includes(searchText)
      )
    })

    // 计算Y轴刻度
    const yTicks = computed(() => {
      if (visibleDataSeries.value.length === 0) return []

      const allValues = visibleDataSeries.value.flatMap(series =>
        series.data.map(point => point.value)
      )

      if (allValues.length === 0) return []

      const minVal = Math.min(...allValues)
      const maxVal = Math.max(...allValues)
      const range = maxVal - minVal || 1
      const padding = range * 0.1

      const yMin = minVal - padding
      const yMax = maxVal + padding

      const currentMargins = currentMargin.value
      const chartHeight = chartSize.value.height - currentMargins.top - currentMargins.bottom
      
      // 根据栅格间距计算合适的刻度数量
      const gridY = gridSpacing.value.y
      const tickCount = Math.max(5, Math.floor(chartHeight / gridY))
      const ticks = []

      for (let i = 0; i <= tickCount; i++) {
        const value = yMin + (yMax - yMin) * (i / tickCount)
        const y = currentMargins.top + chartHeight * (1 - i / tickCount)
        ticks.push({ value, y })
      }

      return ticks
    })

    // 计算X轴刻度
    const xTicks = computed(() => {
      const now = Date.now()
      const ticks = []
      const timeWindowMs = timeWindow.value * 1000
      const currentMargins = currentMargin.value
      const chartWidth = chartSize.value.width - currentMargins.left - currentMargins.right
      
      // 根据栅格间距计算合适的刻度数量
      const gridX = gridSpacing.value.x
      const tickCount = Math.max(6, Math.floor(chartWidth / gridX))

      for (let i = 0; i < tickCount; i++) {
        const time = now - timeWindowMs * (1 - i / (tickCount - 1))
        const x = currentMargins.left + chartWidth * (i / (tickCount - 1))
        const label = new Date(time).toLocaleTimeString().slice(0, 8)
        ticks.push({ x, label, time })
      }

      console.log(`[ChartPanel] X轴刻度计算: 图表宽度=${chartSize.value.width}, 可用宽度=${chartWidth}, 刻度数量=${tickCount}`)
      console.log(`[ChartPanel] X轴刻度位置:`, ticks.map(t => `${t.label}:${t.x.toFixed(1)}`))

      return ticks
    })

    // 坐标转换
    const getX = (timestamp) => {
      const now = Date.now()
      const timeWindowMs = timeWindow.value * 1000
      const startTime = now - timeWindowMs
      const currentMargins = currentMargin.value
      const chartWidth = chartSize.value.width - currentMargins.left - currentMargins.right
      const ratio = Math.max(0, Math.min(1, (timestamp - startTime) / timeWindowMs))
      return currentMargins.left + chartWidth * ratio
    }

    const getY = (value, yAxisIndex = 0) => {
      if (yTicks.value.length < 2) return chartSize.value.height / 2

      const minY = yTicks.value[0].value
      const maxY = yTicks.value[yTicks.value.length - 1].value
      const ratio = (value - minY) / (maxY - minY) || 0
      const currentMargins = currentMargin.value
      return currentMargins.top + (chartSize.value.height - currentMargins.top - currentMargins.bottom) * (1 - ratio)
    }

    // 生成线条路径
    const getLinePath = (data) => {
      if (data.length < 2) return ''

      const now = Date.now()
      const timeWindowMs = timeWindow.value * 1000
      const startTime = now - timeWindowMs
      
      // 过滤时间窗口内的数据
      const validData = data.filter(point => point.time >= startTime && point.time <= now)

      if (validData.length < 2) return ''

      // 如果数据点太多，进行采样以提高渲染性能
      let dataToRender = validData
      if (validData.length > 1000) {
        // 均匀采样，保持线条的连续性
        const step = Math.ceil(validData.length / 1000)
        dataToRender = []
        for (let i = 0; i < validData.length; i += step) {
          dataToRender.push(validData[i])
        }
        // 确保包含最后一个点
        if (dataToRender[dataToRender.length - 1] !== validData[validData.length - 1]) {
          dataToRender.push(validData[validData.length - 1])
        }
      }

      let path = `M ${getX(dataToRender[0].time)} ${getY(dataToRender[0].value)}`

      for (let i = 1; i < dataToRender.length; i++) {
        path += ` L ${getX(dataToRender[i].time)} ${getY(dataToRender[i].value)}`
      }

      return path
    }

    // 获取当前值
    const getCurrentValue = (series) => {
      if (series.data.length === 0) return 'N/A'
      const latestPoint = series.data[series.data.length - 1]
      return latestPoint.value.toFixed(2)
    }

    // 获取时间窗口内可见的数据点（只返回末端点用于高亮）
    const getVisibleDataPoints = (data) => {
      if (data.length === 0) return []
      
      const now = Date.now()
      const timeWindowMs = timeWindow.value * 1000
      const startTime = now - timeWindowMs
      
      // 过滤时间窗口内的数据
      const validData = data.filter(point => point.time >= startTime && point.time <= now)
      
      // 只返回最后一个点用于末端高亮
      return validData.length > 0 ? [validData[validData.length - 1]] : []
    }

    // 控制方法
    const pauseChart = () => {
      isPaused.value = !isPaused.value
    }

    const clearChart = () => {
      dataSeries.value.forEach(series => {
        series.data = []
      })
    }

    const onTimeWindowChange = (newWindow) => {
      console.log(`[ChartPanel] 时间窗口变化: ${timeWindow.value}s -> ${newWindow}s`)
      timeWindow.value = newWindow
      
      // 重置所有采样计数器，适应新的时间窗口
      samplingCounters.value.clear()
      
      // 清理数据以适应新的限制
      cleanupDataSeries()
      
      console.log(`[ChartPanel] 时间窗口已切换到: ${newWindow}秒，最大数据点数: ${getMaxDataPoints()}`)
    }

    const resetZoom = () => {
      zoomLevel.value = 1
      panOffset.value = { x: 0, y: 0 }
    }

    // 切换全屏状态
    const toggleFullscreen = async () => {
      try {
        if (!isFullscreen.value) {
          // 进入全屏
          if (chartContainer.value.requestFullscreen) {
            await chartContainer.value.requestFullscreen()
          } else if (chartContainer.value.webkitRequestFullscreen) {
            await chartContainer.value.webkitRequestFullscreen()
          } else if (chartContainer.value.mozRequestFullScreen) {
            await chartContainer.value.mozRequestFullScreen()
          } else if (chartContainer.value.msRequestFullscreen) {
            await chartContainer.value.msRequestFullscreen()
          }
          
          // 进入全屏后立即更新尺寸和样式
          setTimeout(() => {
            chartSize.value = {
              width: window.innerWidth,
              height: window.innerHeight
            }
            
            // 强制应用全屏样式
            if (chartContainer.value) {
              chartContainer.value.style.width = '100vw'
              chartContainer.value.style.height = '100vh'
              chartContainer.value.style.margin = '0'
              chartContainer.value.style.borderRadius = '0'
              chartContainer.value.style.position = 'fixed'
              chartContainer.value.style.top = '0'
              chartContainer.value.style.left = '0'
              chartContainer.value.style.zIndex = '9999'
            }
            
            console.log(`[ChartPanel] 进入全屏 - 设置尺寸: ${chartSize.value.width}x${chartSize.value.height}`)
            console.log(`[ChartPanel] 全屏栅格间距: x=${gridSpacing.value.x}, y=${gridSpacing.value.y}`)
            console.log(`[ChartPanel] 全屏边距:`, currentMargin.value)
          }, 50)
        } else {
          // 退出全屏
          if (document.exitFullscreen) {
            await document.exitFullscreen()
          } else if (document.webkitExitFullscreen) {
            await document.webkitExitFullscreen()
          } else if (document.mozCancelFullScreen) {
            await document.mozCancelFullScreen()
          } else if (document.msExitFullscreen) {
            await document.msExitFullscreen()
          }
          
          // 退出全屏后重新计算尺寸和清理样式
          setTimeout(() => {
            // 清理全屏样式
            if (chartContainer.value) {
              chartContainer.value.style.width = ''
              chartContainer.value.style.height = ''
              chartContainer.value.style.margin = ''
              chartContainer.value.style.borderRadius = ''
              chartContainer.value.style.position = ''
              chartContainer.value.style.top = ''
              chartContainer.value.style.left = ''
              chartContainer.value.style.zIndex = ''
            }
            updateChartSize()
          }, 50)
        }
      } catch (error) {
        console.error('全屏切换失败:', error)
      }
    }

    // 缩放和平移功能
    const handleZoom = (event) => {
      event.preventDefault()
      const delta = event.deltaY > 0 ? 0.9 : 1.1
      zoomLevel.value = Math.max(0.1, Math.min(10, zoomLevel.value * delta))
    }

    const startPan = (event) => {
      isPanning.value = true
      panStart.value = { x: event.clientX, y: event.clientY }
    }

    const handlePan = (event) => {
      if (!isPanning.value) return
      const deltaX = event.clientX - panStart.value.x
      const deltaY = event.clientY - panStart.value.y
      panOffset.value = { x: deltaX, y: deltaY }
    }

    const endPan = () => {
      isPanning.value = false
    }

    // 主题管理
    const subscriptions = new Map() // topic -> subscription
    const parsedTopicFields = ref(new Map()) // topic -> fields[] 存储解析后的字段

    // 动态解析消息结构，寻找可绘制的数值字段
    const parseMessageStructure = (message, prefix = '', maxDepth = 3, currentDepth = 0) => {
      const fields = []
      
      if (currentDepth >= maxDepth) return fields
      
      if (message && typeof message === 'object') {
        for (const [key, value] of Object.entries(message)) {
          const fieldPath = prefix ? `${prefix}.${key}` : key
          const fieldName = key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, ' ')
          
          if (typeof value === 'number') {
            // 数值类型字段
            let type = 'float64'
            if (Number.isInteger(value)) {
              type = value >= 0 ? 'uint32' : 'int32'
            } else {
              type = 'float64'
            }
            fields.push({
              name: fieldName,
              path: fieldPath,
              type: type
            })
          } else if (typeof value === 'boolean') {
            // 布尔类型字段
            fields.push({
              name: fieldName,
              path: fieldPath,
              type: 'bool'
            })
          } else if (Array.isArray(value) && value.length > 0) {
            // 数组类型字段
            if (typeof value[0] === 'number') {
              // 数值数组，提供统计信息
              fields.push({
                name: `${fieldName} (Min)`,
                path: `${fieldPath}_computed_min`,
                type: 'computed'
              })
              fields.push({
                name: `${fieldName} (Max)`,
                path: `${fieldPath}_computed_max`,
                type: 'computed'
              })
              fields.push({
                name: `${fieldName} (Avg)`,
                path: `${fieldPath}_computed_avg`,
                type: 'computed'
              })
            }
          } else if (value && typeof value === 'object' && currentDepth < maxDepth - 1) {
            // 递归解析嵌套对象
            const nestedFields = parseMessageStructure(value, fieldPath, maxDepth, currentDepth + 1)
            fields.push(...nestedFields)
          }
        }
      }
      
      return fields
    }

    // 获取主题字段
    const getTopicFields = (topic) => {
      // 首先检查是否有解析后的字段
      if (parsedTopicFields.value.has(topic.value)) {
        return parsedTopicFields.value.get(topic.value)
      }

      const fields = []

      switch (topic.messageType) {
        case 'nav_msgs/msg/Odometry':
          fields.push(
            { name: 'Linear X', path: 'twist.twist.linear.x', type: 'float64' },
            { name: 'Linear Y', path: 'twist.twist.linear.y', type: 'float64' },
            { name: 'Linear Z', path: 'twist.twist.linear.z', type: 'float64' },
            { name: 'Angular X', path: 'twist.twist.angular.x', type: 'float64' },
            { name: 'Angular Y', path: 'twist.twist.angular.y', type: 'float64' },
            { name: 'Angular Z', path: 'twist.twist.angular.z', type: 'float64' },
            { name: 'Position X', path: 'pose.pose.position.x', type: 'float64' },
            { name: 'Position Y', path: 'pose.pose.position.y', type: 'float64' },
            { name: 'Position Z', path: 'pose.pose.position.z', type: 'float64' }
          )
          break
        case 'geometry_msgs/msg/Twist':
          fields.push(
            { name: 'Linear X', path: 'linear.x', type: 'float64' },
            { name: 'Linear Y', path: 'linear.y', type: 'float64' },
            { name: 'Linear Z', path: 'linear.z', type: 'float64' },
            { name: 'Angular X', path: 'angular.x', type: 'float64' },
            { name: 'Angular Y', path: 'angular.y', type: 'float64' },
            { name: 'Angular Z', path: 'angular.z', type: 'float64' }
          )
          break
        case 'sensor_msgs/msg/Imu':
          fields.push(
            { name: 'Accel X', path: 'linear_acceleration.x', type: 'float64' },
            { name: 'Accel Y', path: 'linear_acceleration.y', type: 'float64' },
            { name: 'Accel Z', path: 'linear_acceleration.z', type: 'float64' },
            { name: 'Gyro X', path: 'angular_velocity.x', type: 'float64' },
            { name: 'Gyro Y', path: 'angular_velocity.y', type: 'float64' },
            { name: 'Gyro Z', path: 'angular_velocity.z', type: 'float64' }
          )
          break
        case 'sensor_msgs/msg/BatteryState':
          fields.push(
            { name: 'Voltage', path: 'voltage', type: 'float32' },
            { name: 'Current', path: 'current', type: 'float32' },
            { name: 'Percentage', path: 'percentage', type: 'float32' },
            { name: 'Temperature', path: 'temperature', type: 'float32' }
          )
          break
        case 'sensor_msgs/msg/Temperature':
          fields.push(
            { name: 'Temperature', path: 'temperature', type: 'float64' },
            { name: 'Variance', path: 'variance', type: 'float64' }
          )
          break
        case 'sensor_msgs/msg/LaserScan':
          fields.push(
            { name: 'Min Range', path: '_computed_min_range', type: 'computed' },
            { name: 'Max Range', path: '_computed_max_range', type: 'computed' },
            { name: 'Avg Range', path: '_computed_avg_range', type: 'computed' }
          )
          break
        case 'sensor_msgs/msg/PointCloud2':
          fields.push(
            { name: 'Point Count', path: 'width', type: 'uint32' },
            { name: 'Height', path: 'height', type: 'uint32' },
            { name: 'Is Dense', path: 'is_dense', type: 'bool' },
            { name: 'Point Step', path: 'point_step', type: 'uint32' },
            { name: 'Row Step', path: 'row_step', type: 'uint32' },
            { name: 'Data Length', path: 'data', type: 'computed' }
          )
          break
        case 'sensor_msgs/msg/PointCloud':
          fields.push(
            { name: 'Point Count', path: 'points', type: 'computed' },
            { name: 'Channel Count', path: 'channels', type: 'computed' }
          )
          break
        case 'nav_msgs/msg/Path':
          fields.push(
            { name: 'Path Length', path: 'poses', type: 'computed' },
            { name: 'Header Seq', path: 'header.seq', type: 'uint32' },
            { name: 'Header Stamp', path: 'header.stamp.sec', type: 'uint32' }
          )
          break
        case 'nav_msgs/msg/OccupancyGrid':
          fields.push(
            { name: 'Width', path: 'info.width', type: 'uint32' },
            { name: 'Height', path: 'info.height', type: 'uint32' },
            { name: 'Resolution', path: 'info.resolution', type: 'float64' },
            { name: 'Origin X', path: 'info.origin.position.x', type: 'float64' },
            { name: 'Origin Y', path: 'info.origin.position.y', type: 'float64' },
            { name: 'Origin Z', path: 'info.origin.position.z', type: 'float64' }
          )
          break
        case 'geometry_msgs/msg/Pose':
          fields.push(
            { name: 'Position X', path: 'position.x', type: 'float64' },
            { name: 'Position Y', path: 'position.y', type: 'float64' },
            { name: 'Position Z', path: 'position.z', type: 'float64' },
            { name: 'Orientation X', path: 'orientation.x', type: 'float64' },
            { name: 'Orientation Y', path: 'orientation.y', type: 'float64' },
            { name: 'Orientation Z', path: 'orientation.z', type: 'float64' },
            { name: 'Orientation W', path: 'orientation.w', type: 'float64' }
          )
          break
        case 'geometry_msgs/msg/PoseStamped':
          fields.push(
            { name: 'Position X', path: 'pose.position.x', type: 'float64' },
            { name: 'Position Y', path: 'pose.position.y', type: 'float64' },
            { name: 'Position Z', path: 'pose.position.z', type: 'float64' },
            { name: 'Orientation X', path: 'pose.orientation.x', type: 'float64' },
            { name: 'Orientation Y', path: 'pose.orientation.y', type: 'float64' },
            { name: 'Orientation Z', path: 'pose.orientation.z', type: 'float64' },
            { name: 'Orientation W', path: 'pose.orientation.w', type: 'float64' },
            { name: 'Header Seq', path: 'header.seq', type: 'uint32' }
          )
          break
        case 'geometry_msgs/msg/Vector3':
          fields.push(
            { name: 'X', path: 'x', type: 'float64' },
            { name: 'Y', path: 'y', type: 'float64' },
            { name: 'Z', path: 'z', type: 'float64' }
          )
          break
        case 'geometry_msgs/msg/Quaternion':
          fields.push(
            { name: 'X', path: 'x', type: 'float64' },
            { name: 'Y', path: 'y', type: 'float64' },
            { name: 'Z', path: 'z', type: 'float64' },
            { name: 'W', path: 'w', type: 'float64' }
          )
          break
        case 'geometry_msgs/msg/Transform':
          fields.push(
            { name: 'Translation X', path: 'translation.x', type: 'float64' },
            { name: 'Translation Y', path: 'translation.y', type: 'float64' },
            { name: 'Translation Z', path: 'translation.z', type: 'float64' },
            { name: 'Rotation X', path: 'rotation.x', type: 'float64' },
            { name: 'Rotation Y', path: 'rotation.y', type: 'float64' },
            { name: 'Rotation Z', path: 'rotation.z', type: 'float64' },
            { name: 'Rotation W', path: 'rotation.w', type: 'float64' }
          )
          break
        case 'geometry_msgs/msg/TransformStamped':
          fields.push(
            { name: 'Translation X', path: 'transform.translation.x', type: 'float64' },
            { name: 'Translation Y', path: 'transform.translation.y', type: 'float64' },
            { name: 'Translation Z', path: 'transform.translation.z', type: 'float64' },
            { name: 'Rotation X', path: 'transform.rotation.x', type: 'float64' },
            { name: 'Rotation Y', path: 'transform.rotation.y', type: 'float64' },
            { name: 'Rotation Z', path: 'transform.rotation.z', type: 'float64' },
            { name: 'Rotation W', path: 'transform.rotation.w', type: 'float64' },
            { name: 'Header Seq', path: 'header.seq', type: 'uint32' }
          )
          break
        case 'geometry_msgs/msg/Point':
          fields.push(
            { name: 'X', path: 'x', type: 'float64' },
            { name: 'Y', path: 'y', type: 'float64' },
            { name: 'Z', path: 'z', type: 'float64' }
          )
          break
        case 'geometry_msgs/msg/PointStamped':
          fields.push(
            { name: 'X', path: 'point.x', type: 'float64' },
            { name: 'Y', path: 'point.y', type: 'float64' },
            { name: 'Z', path: 'point.z', type: 'float64' },
            { name: 'Header Seq', path: 'header.seq', type: 'uint32' }
          )
          break
        case 'geometry_msgs/msg/Wrench':
          fields.push(
            { name: 'Force X', path: 'force.x', type: 'float64' },
            { name: 'Force Y', path: 'force.y', type: 'float64' },
            { name: 'Force Z', path: 'force.z', type: 'float64' },
            { name: 'Torque X', path: 'torque.x', type: 'float64' },
            { name: 'Torque Y', path: 'torque.y', type: 'float64' },
            { name: 'Torque Z', path: 'torque.z', type: 'float64' }
          )
          break
        case 'geometry_msgs/msg/WrenchStamped':
          fields.push(
            { name: 'Force X', path: 'wrench.force.x', type: 'float64' },
            { name: 'Force Y', path: 'wrench.force.y', type: 'float64' },
            { name: 'Force Z', path: 'wrench.force.z', type: 'float64' },
            { name: 'Torque X', path: 'wrench.torque.x', type: 'float64' },
            { name: 'Torque Y', path: 'wrench.torque.y', type: 'float64' },
            { name: 'Torque Z', path: 'wrench.torque.z', type: 'float64' },
            { name: 'Header Seq', path: 'header.seq', type: 'uint32' }
          )
          break
        case 'geometry_msgs/msg/TwistStamped':
          fields.push(
            { name: 'Linear X', path: 'twist.linear.x', type: 'float64' },
            { name: 'Linear Y', path: 'twist.linear.y', type: 'float64' },
            { name: 'Linear Z', path: 'twist.linear.z', type: 'float64' },
            { name: 'Angular X', path: 'twist.angular.x', type: 'float64' },
            { name: 'Angular Y', path: 'twist.angular.y', type: 'float64' },
            { name: 'Angular Z', path: 'twist.angular.z', type: 'float64' },
            { name: 'Header Seq', path: 'header.seq', type: 'uint32' }
          )
          break
        case 'geometry_msgs/msg/Accel':
          fields.push(
            { name: 'Linear X', path: 'linear.x', type: 'float64' },
            { name: 'Linear Y', path: 'linear.y', type: 'float64' },
            { name: 'Linear Z', path: 'linear.z', type: 'float64' },
            { name: 'Angular X', path: 'angular.x', type: 'float64' },
            { name: 'Angular Y', path: 'angular.y', type: 'float64' },
            { name: 'Angular Z', path: 'angular.z', type: 'float64' }
          )
          break
        case 'geometry_msgs/msg/AccelStamped':
          fields.push(
            { name: 'Linear X', path: 'accel.linear.x', type: 'float64' },
            { name: 'Linear Y', path: 'accel.linear.y', type: 'float64' },
            { name: 'Linear Z', path: 'accel.linear.z', type: 'float64' },
            { name: 'Angular X', path: 'accel.angular.x', type: 'float64' },
            { name: 'Angular Y', path: 'accel.angular.y', type: 'float64' },
            { name: 'Angular Z', path: 'accel.angular.z', type: 'float64' },
            { name: 'Header Seq', path: 'header.seq', type: 'uint32' }
          )
          break
        case 'sensor_msgs/msg/JointState':
          fields.push(
            { name: 'Joint Count', path: 'name', type: 'computed' },
            { name: 'Position Count', path: 'position', type: 'computed' },
            { name: 'Velocity Count', path: 'velocity', type: 'computed' },
            { name: 'Effort Count', path: 'effort', type: 'computed' }
          )
          break
        case 'sensor_msgs/msg/MagneticField':
          fields.push(
            { name: 'Magnetic X', path: 'magnetic_field.x', type: 'float64' },
            { name: 'Magnetic Y', path: 'magnetic_field.y', type: 'float64' },
            { name: 'Magnetic Z', path: 'magnetic_field.z', type: 'float64' }
          )
          break
        case 'sensor_msgs/msg/FluidPressure':
          fields.push(
            { name: 'Pressure', path: 'fluid_pressure', type: 'float64' },
            { name: 'Variance', path: 'variance', type: 'float64' }
          )
          break
        case 'sensor_msgs/msg/Illuminance':
          fields.push(
            { name: 'Illuminance', path: 'illuminance', type: 'float64' },
            { name: 'Variance', path: 'variance', type: 'float64' }
          )
          break
        case 'sensor_msgs/msg/Range':
          fields.push(
            { name: 'Range', path: 'range', type: 'float32' },
            { name: 'Min Range', path: 'min_range', type: 'float32' },
            { name: 'Max Range', path: 'max_range', type: 'float32' }
          )
          break
        case 'sensor_msgs/msg/RelativeHumidity':
          fields.push(
            { name: 'Humidity', path: 'relative_humidity', type: 'float64' },
            { name: 'Variance', path: 'variance', type: 'float64' }
          )
          break
        case 'sensor_msgs/msg/TimeReference':
          fields.push(
            { name: 'Time Ref Sec', path: 'time_ref.sec', type: 'uint32' },
            { name: 'Time Ref Nsec', path: 'time_ref.nanosec', type: 'uint32' },
            { name: 'Source', path: 'source', type: 'string' }
          )
          break
        case 'sensor_msgs/msg/NavSatFix':
          fields.push(
            { name: 'Latitude', path: 'latitude', type: 'float64' },
            { name: 'Longitude', path: 'longitude', type: 'float64' },
            { name: 'Altitude', path: 'altitude', type: 'float64' },
            { name: 'Status', path: 'status.status', type: 'int8' },
            { name: 'Service', path: 'status.service', type: 'uint16' }
          )
          break
        case 'sensor_msgs/msg/Joy':
          fields.push(
            { name: 'Button Count', path: 'buttons', type: 'computed' },
            { name: 'Axis Count', path: 'axes', type: 'computed' }
          )
          break
        case 'std_msgs/msg/Float64':
          fields.push(
            { name: 'Data', path: 'data', type: 'float64' }
          )
          break
        case 'std_msgs/msg/Float32':
          fields.push(
            { name: 'Data', path: 'data', type: 'float32' }
          )
          break
        case 'std_msgs/msg/Int32':
          fields.push(
            { name: 'Data', path: 'data', type: 'int32' }
          )
          break
        case 'std_msgs/msg/Int64':
          fields.push(
            { name: 'Data', path: 'data', type: 'int64' }
          )
          break
        case 'std_msgs/msg/UInt32':
          fields.push(
            { name: 'Data', path: 'data', type: 'uint32' }
          )
          break
        case 'std_msgs/msg/UInt64':
          fields.push(
            { name: 'Data', path: 'data', type: 'uint64' }
          )
          break
        case 'std_msgs/msg/Bool':
          fields.push(
            { name: 'Data', path: 'data', type: 'bool' }
          )
          break
        case 'std_msgs/msg/String':
          fields.push(
            { name: 'Data', path: 'data', type: 'string' }
          )
          break
        case 'diagnostic_msgs/msg/DiagnosticArray':
          fields.push(
            { name: 'Status Count', path: 'status', type: 'computed' }
          )
          break
        case 'diagnostic_msgs/msg/DiagnosticStatus':
          fields.push(
            { name: 'Level', path: 'level', type: 'int8' },
            { name: 'Name', path: 'name', type: 'string' },
            { name: 'Message', path: 'message', type: 'string' },
            { name: 'Hardware ID', path: 'hardware_id', type: 'string' }
          )
          break
        case 'diagnostic_msgs/msg/KeyValue':
          fields.push(
            { name: 'Key', path: 'key', type: 'string' },
            { name: 'Value', path: 'value', type: 'string' }
          )
          break
        case 'control_msgs/msg/JointControllerState':
          fields.push(
            { name: 'Set Point', path: 'set_point', type: 'float64' },
            { name: 'Process Value', path: 'process_value', type: 'float64' },
            { name: 'Process Value Dot', path: 'process_value_dot', type: 'float64' },
            { name: 'Error', path: 'error', type: 'float64' },
            { name: 'Time Step', path: 'time_step', type: 'float64' },
            { name: 'Command', path: 'command', type: 'float64' }
          )
          break
        case 'control_msgs/msg/PidState':
          fields.push(
            { name: 'Timestamp', path: 'header.stamp.sec', type: 'uint32' },
            { name: 'P', path: 'p', type: 'float64' },
            { name: 'I', path: 'i', type: 'float64' },
            { name: 'D', path: 'd', type: 'float64' },
            { name: 'I Clamp', path: 'i_clamp', type: 'float64' },
            { name: 'Antiwindup', path: 'antiwindup', type: 'bool' }
          )
          break
        case 'trajectory_msgs/msg/JointTrajectory':
          fields.push(
            { name: 'Joint Count', path: 'joint_names', type: 'computed' },
            { name: 'Point Count', path: 'points', type: 'computed' }
          )
          break
        case 'trajectory_msgs/msg/JointTrajectoryPoint':
          fields.push(
            { name: 'Position Count', path: 'positions', type: 'computed' },
            { name: 'Velocity Count', path: 'velocities', type: 'computed' },
            { name: 'Acceleration Count', path: 'accelerations', type: 'computed' },
            { name: 'Effort Count', path: 'effort', type: 'computed' },
            { name: 'Time From Start', path: 'time_from_start.sec', type: 'int32' }
          )
          break
        default:
          // 对于真正未知的类型，返回解析占位符
          fields.push({ 
            name: '正在解析...', 
            path: '_parsing', 
            type: 'parsing',
            isParsing: true
          })
      }

      return fields
    }

    // 检查字段是否已被选中
    const isFieldSelected = (topicName, fieldPath) => {
      return dataSeries.value.some(s => s.topic === topicName && s.fieldPath === fieldPath)
    }

    // 检查字段是否可以绘制（只支持数值类型）
    const isFieldPlottable = (fieldType) => {
      if (!fieldType) return false
      
      const lowerType = fieldType.toLowerCase()
      
      // 明确支持的基本数值类型
      const plottableTypes = [
        'float64', 'float32', 'double', 'float',
        'int32', 'int64', 'int16', 'int8', 'int',
        'uint32', 'uint64', 'uint16', 'uint8', 'uint',
        'bool', 'boolean',
        'computed' // 计算字段
      ]
      
      // 明确不支持的数据类型（点云、图像等）
      const nonPlottableTypes = [
        'pointcloud2', 'point_cloud2', 'pointcloud', 'point_cloud',
        'image', 'compressedimage', 'compressed_image',
        'camerainfo', 'camera_info',
        'laserscan', 'laser_scan', // 激光扫描数据通常不适合直接绘制
        'occupancygrid', 'occupancy_grid', // 占用网格图
        'map', 'nav_msgs/msg/map',
        'path', 'nav_msgs/msg/path', // 路径数据
        'tfmessage', 'tf_message', // TF变换数据
        'string', 'std_msgs/msg/string',
        'byte', 'std_msgs/msg/byte',
        'char', 'std_msgs/msg/char',
        'time', 'std_msgs/msg/time',
        'duration', 'std_msgs/msg/duration',
        'header', 'std_msgs/msg/header',
        'quaternion', 'geometry_msgs/msg/quaternion',
        'pose', 'geometry_msgs/msg/pose',
        'pose_stamped', 'geometry_msgs/msg/pose_stamped',
        'pose_with_covariance', 'geometry_msgs/msg/pose_with_covariance',
        'pose_with_covariance_stamped', 'geometry_msgs/msg/pose_with_covariance_stamped',
        'transform', 'geometry_msgs/msg/transform',
        'transform_stamped', 'geometry_msgs/msg/transform_stamped',
        'vector3', 'geometry_msgs/msg/vector3',
        'vector3_stamped', 'geometry_msgs/msg/vector3_stamped',
        'point', 'geometry_msgs/msg/point',
        'point_stamped', 'geometry_msgs/msg/point_stamped',
        'wrench', 'geometry_msgs/msg/wrench',
        'wrench_stamped', 'geometry_msgs/msg/wrench_stamped',
        'twist', 'geometry_msgs/msg/twist',
        'twist_stamped', 'geometry_msgs/msg/twist_stamped',
        'twist_with_covariance', 'geometry_msgs/msg/twist_with_covariance',
        'twist_with_covariance_stamped', 'geometry_msgs/msg/twist_with_covariance_stamped',
        'accel', 'geometry_msgs/msg/accel',
        'accel_stamped', 'geometry_msgs/msg/accel_stamped',
        'accel_with_covariance', 'geometry_msgs/msg/accel_with_covariance',
        'accel_with_covariance_stamped', 'geometry_msgs/msg/accel_with_covariance_stamped',
        'polygon', 'geometry_msgs/msg/polygon',
        'polygon_stamped', 'geometry_msgs/msg/polygon_stamped',
        'polygon_stamped', 'geometry_msgs/msg/polygon_stamped',
        'imu', 'sensor_msgs/msg/imu',
        'joint_state', 'sensor_msgs/msg/joint_state',
        'battery_state', 'sensor_msgs/msg/battery_state',
        'temperature', 'sensor_msgs/msg/temperature',
        'magnetic_field', 'sensor_msgs/msg/magnetic_field',
        'fluid_pressure', 'sensor_msgs/msg/fluid_pressure',
        'illuminance', 'sensor_msgs/msg/illuminance',
        'range', 'sensor_msgs/msg/range',
        'relative_humidity', 'sensor_msgs/msg/relative_humidity',
        'time_reference', 'sensor_msgs/msg/time_reference',
        'nav_sat_fix', 'sensor_msgs/msg/nav_sat_fix',
        'joy', 'sensor_msgs/msg/joy',
        'joy_feedback', 'sensor_msgs/msg/joy_feedback',
        'joy_feedback_array', 'sensor_msgs/msg/joy_feedback_array',
        'multi_dof_joint_state', 'sensor_msgs/msg/multi_dof_joint_state',
        'point_field', 'sensor_msgs/msg/point_field',
        'region_of_interest', 'sensor_msgs/msg/region_of_interest',
        'channel_float32', 'sensor_msgs/msg/channel_float32',
        'camera_info', 'sensor_msgs/msg/camera_info',
        'compressed_image', 'sensor_msgs/msg/compressed_image',
        'image', 'sensor_msgs/msg/image',
        'laser_scan', 'sensor_msgs/msg/laser_scan',
        'multi_echo_laser_scan', 'sensor_msgs/msg/multi_echo_laser_scan',
        'point_cloud2', 'sensor_msgs/msg/point_cloud2',
        'point_cloud', 'sensor_msgs/msg/point_cloud',
        'point_field', 'sensor_msgs/msg/point_field',
        'nav_msgs/msg/occupancy_grid',
        'nav_msgs/msg/path',
        'nav_msgs/msg/odometry',
        'nav_msgs/msg/grid_cells',
        'nav_msgs/msg/map_meta_data',
        'nav_msgs/msg/odometry',
        'tf2_msgs/msg/tf_message',
        'actionlib_msgs/msg/goal_status',
        'actionlib_msgs/msg/goal_status_array',
        'actionlib_msgs/msg/goal_id',
        'actionlib_msgs/msg/goal_id',
        'diagnostic_msgs/msg/diagnostic_array',
        'diagnostic_msgs/msg/diagnostic_status',
        'diagnostic_msgs/msg/key_value',
        'control_msgs/msg/joint_controller_state',
        'control_msgs/msg/pid_state',
        'trajectory_msgs/msg/joint_trajectory',
        'trajectory_msgs/msg/joint_trajectory_point'
      ]
      
      // 首先检查是否在明确不支持的类型中
      if (nonPlottableTypes.some(type => lowerType.includes(type))) {
        return false
      }
      
      // 然后检查是否在明确支持的类型中
      if (plottableTypes.includes(lowerType)) {
        return true
      }
      
      // 最后进行启发式匹配
      const heuristicPatterns = [
        /^float\d*$/,
        /^int\d*$/,
        /^uint\d*$/,
        /^double$/,
        /^bool$/,
        /^boolean$/,
        /computed$/
      ]
      
      return heuristicPatterns.some(pattern => pattern.test(lowerType))
    }

    // 获取字段的数据类型分类和提示信息
    const getFieldTypeInfo = (fieldType) => {
      if (!fieldType) return { category: 'unknown', description: '未知类型', icon: '❓' }
      
      const lowerType = fieldType.toLowerCase()
      
      // 数值类型
      if (['float64', 'float32', 'double', 'float'].some(type => lowerType.includes(type))) {
        return { category: 'numeric', description: '浮点数值', icon: '📊' }
      }
      if (['int32', 'int64', 'int16', 'int8', 'int', 'uint32', 'uint64', 'uint16', 'uint8', 'uint'].some(type => lowerType.includes(type))) {
        return { category: 'numeric', description: '整数值', icon: '📊' }
      }
      if (['bool', 'boolean'].some(type => lowerType.includes(type))) {
        return { category: 'numeric', description: '布尔值', icon: '📊' }
      }
      
      // 点云和图像类型
      if (['pointcloud2', 'point_cloud2', 'pointcloud', 'point_cloud'].some(type => lowerType.includes(type))) {
        return { category: 'pointcloud', description: '点云数据', icon: '☁️' }
      }
      if (['image', 'compressedimage', 'compressed_image'].some(type => lowerType.includes(type))) {
        return { category: 'image', description: '图像数据', icon: '🖼️' }
      }
      if (['camerainfo', 'camera_info'].some(type => lowerType.includes(type))) {
        return { category: 'image', description: '相机信息', icon: '📷' }
      }
      
      // 几何类型
      if (['pose', 'point', 'vector3', 'quaternion', 'transform'].some(type => lowerType.includes(type))) {
        return { category: 'geometry', description: '几何数据', icon: '📐' }
      }
      if (['twist', 'wrench', 'accel'].some(type => lowerType.includes(type))) {
        return { category: 'geometry', description: '运动数据', icon: '⚡' }
      }
      
      // 传感器类型
      if (['imu', 'laserscan', 'laser_scan', 'battery_state', 'temperature', 'magnetic_field'].some(type => lowerType.includes(type))) {
        return { category: 'sensor', description: '传感器数据', icon: '🔍' }
      }
      
      // 导航类型
      if (['odometry', 'path', 'occupancygrid', 'occupancy_grid', 'map'].some(type => lowerType.includes(type))) {
        return { category: 'navigation', description: '导航数据', icon: '🗺️' }
      }
      
      // 字符串和文本类型
      if (['string', 'char', 'byte'].some(type => lowerType.includes(type))) {
        return { category: 'text', description: '文本数据', icon: '📝' }
      }
      
      // 时间类型
      if (['time', 'duration', 'header'].some(type => lowerType.includes(type))) {
        return { category: 'time', description: '时间数据', icon: '⏰' }
      }
      
      // 计算字段
      if (lowerType.includes('computed')) {
        return { category: 'computed', description: '计算字段', icon: '🧮' }
      }
      
      // 默认未知类型
      return { category: 'unknown', description: '未知类型', icon: '❓' }
    }

    // 展开/折叠主题
    const expandTopic = (topic) => {
      const index = expandedTopics.value.indexOf(topic.value)
      if (index === -1) {
        expandedTopics.value.push(topic.value)
      } else {
        expandedTopics.value.splice(index, 1)
      }
    }

    // 添加或移除数据系列（再次点击删除）
    const addDataSeries = (topicName, field, messageType) => {
      // 检查是否已经存在相同的数据系列
      const existingSeriesIndex = dataSeries.value.findIndex(s =>
        s.topic === topicName && s.fieldPath === field.path
      )

      if (existingSeriesIndex !== -1) {
        // 如果已经存在，删除它
        const existingSeries = dataSeries.value[existingSeriesIndex]
        removeDataSeries(existingSeries.id)
        ElMessage.info(`已移除数据系列: ${field.name}`)
        return
      }

      // 如果不存在，添加新的数据系列
      const seriesId = `${topicName}_${field.path}_${++seriesIdCounter}`
      const color = predefinedColors[colorIndex % predefinedColors.length]
      colorIndex++

      const newSeries = {
        id: seriesId,
        name: field.name,
        fullName: `${topicName}/${field.name}`,
        topic: topicName,
        fieldPath: field.path,
        messageType: messageType,
        color: color,
        data: [],
        visible: true,
        yAxisIndex: 0
      }

      dataSeries.value.push(newSeries)

      // 订阅主题如果还未订阅
      if (!subscriptions.has(topicName)) {
        subscribeToTopic(topicName, messageType, seriesId)
      }

      ElMessage.success(`已添加数据系列: ${field.name}`)
    }

    // 移除数据系列
    const removeDataSeries = (seriesId) => {
      const index = dataSeries.value.findIndex(s => s.id === seriesId)
      if (index !== -1) {
        const series = dataSeries.value[index]
        dataSeries.value.splice(index, 1)

        // 检查是否还有其他系列使用该主题
        const hasOtherSeries = dataSeries.value.some(s => s.topic === series.topic)
        if (!hasOtherSeries && subscriptions.has(series.topic)) {
          rosbridge.unsubscribe(subscriptions.get(series.topic))
          subscriptions.delete(series.topic)
        }

        ElMessage.info(`已移除数据系列: ${series.name}`)
      }
    }

    // 切换系列可见性
    const toggleSeriesVisibility = (seriesId) => {
      const series = dataSeries.value.find(s => s.id === seriesId)
      if (series) {
        series.visible = !series.visible
      }
    }

    // 订阅主题
    const subscribeToTopic = (topicName, messageType, firstSeriesId) => {
      console.log(`Subscribing to topic: ${topicName}, type: ${messageType}`)

      const subscription = rosbridge.subscribe(topicName, messageType, (message) => {
        if (isPaused.value) return

        const timestamp = Date.now()

        // 如果是未知类型且还没有解析过字段，尝试解析消息结构
        if (!parsedTopicFields.value.has(topicName)) {
          console.log(`[ChartPanel] 尝试解析未知类型topic: ${topicName}`)
          const parsedFields = parseMessageStructure(message)
          
          if (parsedFields.length > 0) {
            // 过滤出可绘制的字段
            const plottableFields = parsedFields.filter(field => isFieldPlottable(field.type))
            
            if (plottableFields.length > 0) {
              console.log(`[ChartPanel] 发现 ${plottableFields.length} 个可绘制字段:`, plottableFields)
              parsedTopicFields.value.set(topicName, plottableFields)
              
              // 触发UI更新
              nextTick(() => {
                console.log(`[ChartPanel] 已更新topic ${topicName} 的字段列表`)
              })
            } else {
              console.log(`[ChartPanel] topic ${topicName} 没有发现可绘制的字段`)
              // 存储空结果，避免重复解析
              parsedTopicFields.value.set(topicName, [])
            }
          }
        }

        // 为该主题的所有系列更新数据
        dataSeries.value.forEach(series => {
          if (series.topic === topicName) {
            const value = extractFieldValue(message, series.fieldPath, messageType)
            if (value !== null && value !== undefined) {
              addDataPointToSeries(series.id, timestamp, value)
            }
          }
        })
      })

      subscriptions.set(topicName, subscription)
    }

    // 提取字段值
    const extractFieldValue = (message, fieldPath, messageType) => {
      if (fieldPath.startsWith('_computed_')) {
        // 特殊计算字段
        switch (fieldPath) {
          case '_computed_min_range':
            if (message.ranges && Array.isArray(message.ranges)) {
              const validRanges = message.ranges.filter(r => r > (message.range_min || 0) && r < (message.range_max || 100))
              return validRanges.length > 0 ? Math.min(...validRanges) : 0
            }
            return 0
          case '_computed_max_range':
            if (message.ranges && Array.isArray(message.ranges)) {
              const validRanges = message.ranges.filter(r => r > (message.range_min || 0) && r < (message.range_max || 100))
              return validRanges.length > 0 ? Math.max(...validRanges) : 0
            }
            return 0
          case '_computed_avg_range':
            if (message.ranges && Array.isArray(message.ranges)) {
              const validRanges = message.ranges.filter(r => r > (message.range_min || 0) && r < (message.range_max || 100))
              return validRanges.length > 0 ? validRanges.reduce((a, b) => a + b, 0) / validRanges.length : 0
            }
            return 0
          default:
            // 处理动态解析的计算字段
            if (fieldPath.includes('_computed_min')) {
              const arrayPath = fieldPath.replace('_computed_min', '')
              const array = getNestedValue(message, arrayPath)
              if (Array.isArray(array) && array.length > 0) {
                return Math.min(...array.filter(v => typeof v === 'number'))
              }
            } else if (fieldPath.includes('_computed_max')) {
              const arrayPath = fieldPath.replace('_computed_max', '')
              const array = getNestedValue(message, arrayPath)
              if (Array.isArray(array) && array.length > 0) {
                return Math.max(...array.filter(v => typeof v === 'number'))
              }
            } else if (fieldPath.includes('_computed_avg')) {
              const arrayPath = fieldPath.replace('_computed_avg', '')
              const array = getNestedValue(message, arrayPath)
              if (Array.isArray(array) && array.length > 0) {
                const numbers = array.filter(v => typeof v === 'number')
                return numbers.length > 0 ? numbers.reduce((a, b) => a + b, 0) / numbers.length : 0
              }
            }
            return 0
        }
      }

      // 普通字段路径 - 处理ROS消息的下划线前缀
      return getNestedValue(message, fieldPath)
    }

    // 获取嵌套对象的值
    const getNestedValue = (obj, path) => {
      const parts = path.split('.')
      let value = obj

      for (const part of parts) {
        if (value && typeof value === 'object') {
          // 首先尝试直接访问字段
          if (part in value) {
            value = value[part]
          } else {
            // 如果直接访问失败，尝试下划线前缀
            const underscorePart = `_${part}`
            if (underscorePart in value) {
              value = value[underscorePart]
            } else {
              // 如果都失败，返回null
              console.warn(`[ChartPanel] 字段 ${part} 不存在，尝试了 ${part} 和 ${underscorePart}`)
              return null
            }
          }
        } else {
          return null
        }
      }

      // 处理不同类型的返回值
      if (typeof value === 'number') {
        return value
      } else if (typeof value === 'boolean') {
        return value ? 1 : 0  // 将布尔值转换为数值
      } else if (Array.isArray(value)) {
        return value.length  // 返回数组长度
      } else if (typeof value === 'string') {
        return value.length  // 返回字符串长度
      } else if (value && typeof value === 'object') {
        return Object.keys(value).length  // 返回对象属性数量
      }
      
      return null
    }

    // 更新topic频率检测
    const updateTopicFrequency = (topicName) => {
      const now = Date.now()
      const lastTime = lastUpdateTime.value.get(topicName)
      
      if (lastTime) {
        const timeDiff = now - lastTime
        if (timeDiff > 0) {
          const currentFreq = 1000 / timeDiff // 转换为Hz
          const existingFreq = topicFrequencies.value.get(topicName) || 0
          
          // 使用指数移动平均来平滑频率变化，避免频率抖动
          const alpha = 0.3 // 平滑因子，越小越平滑
          const smoothedFreq = existingFreq * (1 - alpha) + currentFreq * alpha
          topicFrequencies.value.set(topicName, smoothedFreq)
        }
      }
      
      lastUpdateTime.value.set(topicName, now)
    }

    // 计算智能采样步长
    const getSamplingStep = (topicName) => {
      const actualFreq = topicFrequencies.value.get(topicName) || 1
      const maxPoints = getMaxDataPoints()
      const timeWindowMs = timeWindow.value * 1000
      const expectedPoints = (actualFreq * timeWindowMs) / 1000
      
      if (expectedPoints <= maxPoints) {
        return 1 // 不需要采样
      } else {
        // 计算采样步长，确保不超过最大点数
        return Math.ceil(expectedPoints / maxPoints)
      }
    }

    // 检查是否应该添加数据点（基于采样策略）
    const shouldAddDataPoint = (topicName) => {
      const samplingStep = getSamplingStep(topicName)
      const counter = samplingCounters.value.get(topicName) || 0
      
      // 更新计数器
      samplingCounters.value.set(topicName, counter + 1)
      
      // 当计数器达到采样步长时，重置计数器并返回true
      if (counter >= samplingStep - 1) {
        samplingCounters.value.set(topicName, 0)
        return true
      }
      
      return false
    }

    // 添加数据点到特定系列
    const addDataPointToSeries = (seriesId, timestamp, value) => {
      const series = dataSeries.value.find(s => s.id === seriesId)
      if (!series) return

      // 更新频率检测
      updateTopicFrequency(series.topic)

      // 检查是否应该添加数据点（基于智能采样）
      if (shouldAddDataPoint(series.topic)) {
        series.data.push({ time: timestamp, value })

        // 限制数据点数量
        const maxPoints = getMaxDataPoints()
        if (series.data.length > maxPoints) {
          series.data.shift()
        }
      } else {
        // 即使不添加新点，也要更新最后一个点的时间戳（保持实时性）
        if (series.data.length > 0) {
          series.data[series.data.length - 1].time = timestamp
        }
      }
    }

    // 清理数据系列
    const cleanupDataSeries = () => {
      const currentMaxPoints = getMaxDataPoints()
      
      let totalPointsBefore = 0
      let totalPointsAfter = 0

      dataSeries.value.forEach(series => {
        totalPointsBefore += series.data.length
        
        // 只按数量限制清理，智能采样已经控制了数据量
        if (series.data.length > currentMaxPoints) {
          series.data = series.data.slice(-currentMaxPoints)
        }
        
        totalPointsAfter += series.data.length
      })

      if (totalPointsBefore > totalPointsAfter) {
        console.log(`[ChartPanel] 清理数据: ${totalPointsBefore} -> ${totalPointsAfter} 个数据点，最大点数: ${currentMaxPoints}`)
      }
    }

    // 更新图表尺寸
    const updateChartSize = () => {
      if (!chartContainer.value) return

      let newWidth, newHeight

      if (isFullscreen.value) {
        // 全屏模式：使用视口尺寸
        newWidth = window.innerWidth
        newHeight = window.innerHeight
        console.log(`[ChartPanel] 全屏模式 - 使用视口尺寸: ${newWidth}x${newHeight}`)
      } else {
        // 非全屏模式：使用容器尺寸，但确保容器有正确的尺寸
        const rect = chartContainer.value.getBoundingClientRect()
        const parentRect = chartContainer.value.parentElement?.getBoundingClientRect()

        // 如果容器尺寸为0，尝试使用父容器尺寸
        if (rect.width === 0 || rect.height === 0) {
          console.warn(`[ChartPanel] 容器尺寸异常: ${rect.width}x${rect.height}，使用父容器尺寸`)
          newWidth = parentRect ? Math.max(parentRect.width - 16, 400) : 800  // 减去margin
          newHeight = parentRect ? Math.max(parentRect.height - 16, 300) : 600
        } else {
          newWidth = Math.max(rect.width, 400)
          newHeight = Math.max(rect.height, 300)
        }

        console.log(`[ChartPanel] 正常模式 - 容器尺寸: ${rect.width}x${rect.height}, 使用尺寸: ${newWidth}x${newHeight}`)
      }

      // 强制最小尺寸
      newWidth = Math.max(newWidth, 400)
      newHeight = Math.max(newHeight, 300)

      chartSize.value = {
        width: newWidth,
        height: newHeight
      }

      console.log(`[ChartPanel] 最终图表尺寸: ${newWidth}x${newHeight}`)
      console.log(`[ChartPanel] 可用绘图区域: ${newWidth - margin.left - margin.right}x${newHeight - margin.top - margin.bottom}`)
    }

    // 检测全屏状态变化
    const handleFullscreenChange = () => {
      const previousState = isFullscreen.value

      // 更新全屏状态
      isFullscreen.value = !!(
        document.fullscreenElement ||
        document.webkitFullscreenElement ||
        document.mozFullScreenElement ||
        document.msFullscreenElement
      )

      console.log(`[ChartPanel] 全屏状态变化: ${previousState} -> ${isFullscreen.value}`)

      // 立即更新图表尺寸
      nextTick(() => {
        updateChartSize()
        console.log(`[ChartPanel] 全屏状态变化后尺寸: ${chartSize.value.width}x${chartSize.value.height}`)
      })
    }

    // 加载真实的topic数据
    const loadTopics = async () => {
      try {
        console.log('[ChartPanel] 开始加载真实的ROS topics...')

        if (!rosbridge.isConnected) {
          console.warn('[ChartPanel] ROS未连接，尝试初始化连接...')
          if (rosbridge.initializeConnection) {
            await rosbridge.initializeConnection()
            await new Promise(resolve => setTimeout(resolve, 2000))
          }

          if (!rosbridge.isConnected) {
            console.error('[ChartPanel] ROS连接失败')
            ElMessage.error('ROS连接失败，请检查服务器状态和网络连接')
            availableTopics.value = []
            return
          }
        }

        // 并行获取topics、类型和频率信息
        console.log('[ChartPanel] 获取ROS系统信息...')
        const [topicsData, topicTypes, topicFrequencies] = await Promise.all([
          rosbridge.getTopics(),
          rosbridge.getTopicTypes(),
          rosbridge.getTopicFrequencies()
        ])

        console.log('[ChartPanel] 获取到的原始数据:')
        console.log('- Topics Data:', topicsData, '类型:', typeof topicsData, '是数组:', Array.isArray(topicsData))
        console.log('- Topic Types:', topicTypes, '类型:', typeof topicTypes)
        console.log('- Topic Frequencies:', topicFrequencies, '类型:', typeof topicFrequencies)

        // 检查第一个topic的类型
        if (topicsData && topicsData.length > 0) {
          console.log('- 第一个topic:', topicsData[0], '类型:', typeof topicsData[0])
        }

        if (!topicsData || !Array.isArray(topicsData) || topicsData.length === 0) {
          console.error('[ChartPanel] 没有获取到任何topic')
          ElMessage.warning('当前ROS系统中没有发现任何topic，请检查ROS节点是否正在运行')
          availableTopics.value = []
          return
        }

        // 处理topic数据 - 支持两种格式：字符串数组或TopicInfo对象数组
        let topics, topicTypesMap
        if (typeof topicsData[0] === 'string') {
          // 旧格式：字符串数组
          topics = topicsData
          topicTypesMap = topicTypes || {}
        } else {
          // 新格式：TopicInfo对象数组
          topics = topicsData.map(topic => topic.name)
          topicTypesMap = {}
          topicsData.forEach(topic => {
            topicTypesMap[topic.name] = topic.message_type
          })
        }

        console.log('[ChartPanel] 处理后的数据:')
        console.log('- Topics:', topics)
        console.log('- Topic Types Map:', topicTypesMap)

        if (!topicTypesMap || Object.keys(topicTypesMap).length === 0) {
          console.error('[ChartPanel] 没有获取到topic类型信息')
          ElMessage.warning('无法获取topic类型信息')
          availableTopics.value = []
          return
        }

        // 支持的数据类型（适合绘制图表的消息类型）
        const supportedTypes = [
          // Navigation messages
          'nav_msgs/msg/Odometry',
          'nav_msgs/msg/Path',
          'nav_msgs/msg/OccupancyGrid',

          // Geometry messages
          'geometry_msgs/msg/Twist',
          'geometry_msgs/msg/TwistStamped',
          'geometry_msgs/msg/Pose',
          'geometry_msgs/msg/PoseStamped',
          'geometry_msgs/msg/PoseWithCovariance',
          'geometry_msgs/msg/PoseWithCovarianceStamped',
          'geometry_msgs/msg/Transform',
          'geometry_msgs/msg/TransformStamped',
          'geometry_msgs/msg/Vector3',
          'geometry_msgs/msg/Vector3Stamped',
          'geometry_msgs/msg/Point',
          'geometry_msgs/msg/PointStamped',
          'geometry_msgs/msg/Quaternion',
          'geometry_msgs/msg/QuaternionStamped',
          'geometry_msgs/msg/Wrench',
          'geometry_msgs/msg/WrenchStamped',

          // Sensor messages
          'sensor_msgs/msg/Imu',
          'sensor_msgs/msg/JointState',
          'sensor_msgs/msg/LaserScan',
          'sensor_msgs/msg/BatteryState',
          'sensor_msgs/msg/Temperature',
          'sensor_msgs/msg/MagneticField',
          'sensor_msgs/msg/FluidPressure',
          'sensor_msgs/msg/Illuminance',
          'sensor_msgs/msg/Range',
          'sensor_msgs/msg/RelativeHumidity',
          'sensor_msgs/msg/TimeReference',
          'sensor_msgs/msg/NavSatFix',
          'sensor_msgs/msg/Joy',

          // Standard messages
          'std_msgs/msg/Float64',
          'std_msgs/msg/Float32',
          'std_msgs/msg/Int32',
          'std_msgs/msg/Int64',
          'std_msgs/msg/Int16',
          'std_msgs/msg/Int8',
          'std_msgs/msg/UInt32',
          'std_msgs/msg/UInt64',
          'std_msgs/msg/UInt16',
          'std_msgs/msg/UInt8',
          'std_msgs/msg/Bool',
          'std_msgs/msg/Byte',
          'std_msgs/msg/Char',
          'std_msgs/msg/String',

          // TF messages
          'tf2_msgs/msg/TFMessage',

          // Action and service types that might contain numerical data
          'actionlib_msgs/msg/GoalStatus',
          'actionlib_msgs/msg/GoalStatusArray',

          // Diagnostic messages
          'diagnostic_msgs/msg/DiagnosticArray',
          'diagnostic_msgs/msg/DiagnosticStatus',
          'diagnostic_msgs/msg/KeyValue',

          // Control messages
          'control_msgs/msg/JointControllerState',
          'control_msgs/msg/PidState',

          // Trajectory messages
          'trajectory_msgs/msg/JointTrajectory',
          'trajectory_msgs/msg/JointTrajectoryPoint'
        ]

        const topicList = []
        let activeTopicCount = 0
        let supportedTopicCount = 0
        const unsupportedTypes = new Set()
        const filteredTopics = []

        console.log(`[ChartPanel] 开始过滤 ${topics.length} 个topic...`)

        topics.forEach(topic => {
          // 确保topic是字符串类型
          const topicName = typeof topic === 'string' ? topic : String(topic)
          const messageType = topicTypesMap[topicName]

          console.log(`[ChartPanel] 检查topic: ${topicName} (原始:${topic}), 类型: ${messageType}`)

          if (!messageType) {
            console.warn(`[ChartPanel] Topic ${topicName} 没有类型信息`)
            return
          }

          // 检查是否是明确支持的类型
          const isExplicitlySupported = supportedTypes.includes(messageType)

          // 启发式判断：如果消息类型可能包含数值字段
          const isLikelyNumeric = messageType && (
            messageType.includes('msgs/msg/') && (
              messageType.includes('Float') ||
              messageType.includes('Int') ||
              messageType.includes('UInt') ||
              messageType.includes('Double') ||
              messageType.includes('Bool') ||
              messageType.includes('Twist') ||
              messageType.includes('Pose') ||
              messageType.includes('Point') ||
              messageType.includes('Vector') ||
              messageType.includes('Quaternion') ||
              messageType.includes('Transform') ||
              messageType.includes('Imu') ||
              messageType.includes('Odom') ||
              messageType.includes('Joint') ||
              messageType.includes('Laser') ||
              messageType.includes('Battery') ||
              messageType.includes('Temperature') ||
              messageType.includes('Pressure') ||
              messageType.includes('Range') ||
              messageType.includes('Nav')
            )
          )

          if (isExplicitlySupported || isLikelyNumeric) {
            supportedTopicCount++

            // 检查topic是否有数据传输（频率>0）
            const frequency = topicFrequencies && topicFrequencies[topicName] ? topicFrequencies[topicName] : 0
            let isActive = frequency > 0
            
            // 如果没有频率信息，尝试通过其他方式判断是否活跃
            // 比如检查topic名称是否包含活跃的标识
            if (!isActive && !topicFrequencies) {
              // 如果完全没有频率信息，假设所有topic都是活跃的（用于测试）
              const isLikelyActive = topicName.includes('odom') || 
                                   topicName.includes('pose') || 
                                   topicName.includes('scan') || 
                                   topicName.includes('cloud') ||
                                   topicName.includes('cmd_vel') ||
                                   topicName.includes('map')
              if (isLikelyActive) {
                isActive = true
              }
            }

            const supportType = isExplicitlySupported ? '明确支持' : '启发式支持'
            console.log(`[ChartPanel] ✅ ${supportType}的topic: ${topicName}, 频率: ${frequency} Hz`)

            if (isActive) {
              activeTopicCount++
            }

            // 创建更好的显示标签
            let label = topicName
            try {
              if (typeof topicName === 'string' && topicName.startsWith('/')) {
                const parts = topicName.split('/')
                label = parts[parts.length - 1] || topicName
              }
            } catch (error) {
              console.warn(`[ChartPanel] 处理topic标签失败: ${topicName}`, error)
              label = topicName
            }

            topicList.push({
              value: topicName,
              label: label,
              fullName: topicName,
              messageType: messageType,
              frequency: frequency,
              isActive: isActive,
              status: isActive ? `${frequency.toFixed(1)} Hz` : '无数据',
              supportType: supportType
            })
          } else {
            unsupportedTypes.add(messageType)
            filteredTopics.push({topic: topicName, messageType})
            console.log(`[ChartPanel] ❌ 不支持的topic: ${topicName}, 类型: ${messageType}`)
          }
        })

        console.log(`[ChartPanel] 过滤结果:`)
        console.log(`- 总topic数: ${topics.length}`)
        console.log(`- 支持的topic数: ${supportedTopicCount}`)
        console.log(`- 活跃的topic数: ${activeTopicCount}`)
        console.log(`- 不支持的消息类型:`, Array.from(unsupportedTypes))
        console.log(`- 被过滤的topic样例:`, filteredTopics.slice(0, 5))

        // 按频率排序，活跃的topic排在前面
        topicList.sort((a, b) => {
          if (a.isActive && !b.isActive) return -1
          if (!a.isActive && b.isActive) return 1
          return b.frequency - a.frequency
        })

        availableTopics.value = topicList

        console.log(`[ChartPanel] 最终结果: topicList长度 = ${topicList.length}`)

        if (supportedTopicCount === 0) {
          console.error(`[ChartPanel] 在 ${topics.length} 个topic中没有找到支持的消息类型`)
          console.error('[ChartPanel] 不支持的类型:', Array.from(unsupportedTypes))

          // 临时降级方案：如果没有找到支持的类型，显示前几个topic让用户测试
          console.warn('[ChartPanel] 启用兼容模式，显示前几个topic供测试')
          const fallbackTopics = topics.slice(0, Math.min(10, topics.length)).map(topic => {
            const topicName = typeof topic === 'string' ? topic : String(topic)
            let label = topicName
            try {
              if (typeof topicName === 'string' && topicName.includes('/')) {
                label = topicName.split('/').pop() || topicName
              }
            } catch (error) {
              console.warn('[ChartPanel] 兼容模式标签处理失败:', topicName, error)
              label = topicName
            }

            return {
              value: topicName,
              label: label,
              fullName: topicName,
              messageType: topicTypesMap[topicName] || 'unknown',
              frequency: 0,
              isActive: false,
              status: '兼容模式'
            }
          })

          availableTopics.value = fallbackTopics
          ElMessage.warning(`没有找到明确支持的消息类型，显示前 ${fallbackTopics.length} 个topic供测试。不支持的类型包括: ${Array.from(unsupportedTypes).slice(0, 3).join(', ')}`)
        } else {
          ElMessage.success(`发现 ${supportedTopicCount} 个支持的topic（${activeTopicCount} 个活跃，${supportedTopicCount - activeTopicCount} 个无数据传输）`)
        }

      } catch (error) {
        console.error('[ChartPanel] 加载topic失败:', error)
        ElMessage.error(`获取topic列表失败: ${error.message}`)
        availableTopics.value = []
      }
    }


    // 在外层声明变量，以便在onUnmounted中清理
    let resizeObserver = null
    let sizeCheckInterval = null

    onMounted(async () => {
      await nextTick()
      updateChartSize()
      chartReady.value = true

      // 简化resize处理，提高响应速度
      let resizeTimeout = null
      const handleResize = () => {
        // 减少防抖延迟，提高响应速度
        if (resizeTimeout) {
          clearTimeout(resizeTimeout)
        }

        resizeTimeout = setTimeout(() => {
          updateChartSize()
        }, 16) // 16ms约等于60FPS，提高响应速度
      }

      // 监听多种resize相关事件
      window.addEventListener('resize', handleResize)
      window.addEventListener('orientationchange', handleResize)

      // 监听全屏状态变化
      document.addEventListener('fullscreenchange', handleFullscreenChange)
      document.addEventListener('webkitfullscreenchange', handleFullscreenChange)
      document.addEventListener('mozfullscreenchange', handleFullscreenChange)
      document.addEventListener('MSFullscreenChange', handleFullscreenChange)

      // 定期检查容器尺寸，确保响应性（每500ms检查一次）
      sizeCheckInterval = setInterval(() => {
        if (chartContainer.value) {
          const rect = chartContainer.value.getBoundingClientRect()
          const currentWidth = chartSize.value.width
          const currentHeight = chartSize.value.height

          // 如果尺寸发生显著变化，更新图表
          if (Math.abs(rect.width - currentWidth) > 10 || Math.abs(rect.height - currentHeight) > 10) {
            console.log(`[ChartPanel] 检测到容器尺寸变化: ${currentWidth}x${currentHeight} -> ${rect.width}x${rect.height}`)
            updateChartSize()
          }
        }
      }, 500)

      // 使用ResizeObserver API (如果支持) 来监听容器尺寸变化
      if (window.ResizeObserver) {
        resizeObserver = new ResizeObserver((entries) => {
          for (let entry of entries) {
            console.log(`[ChartPanel] ResizeObserver: 容器尺寸变化`, entry.contentRect)
            updateChartSize()
          }
        })

        // 在nextTick后开始观察，确保DOM已就绪
        nextTick(() => {
          if (chartContainer.value && resizeObserver) {
            resizeObserver.observe(chartContainer.value)
            console.log('[ChartPanel] ResizeObserver 已启动')
          }
        })
      }

      // 定期清理过期数据
      setInterval(cleanupDataSeries, 5000)

      // 初始化ROS连接
      console.log('[ChartPanel] 初始化ROS连接...')
      if (rosbridge.initializeConnection) {
        try {
          await rosbridge.initializeConnection()
          console.log('[ChartPanel] ROS连接初始化完成')
        } catch (error) {
          console.error('[ChartPanel] ROS连接初始化失败:', error)
        }
      }

      // 等待连接建立后加载topic数据
      setTimeout(() => {
        loadTopics()
      }, 2000)

      // 定期刷新topic列表（每30秒）
      setInterval(loadTopics, 30000)
    })

    onUnmounted(() => {
      // 清理所有订阅
      subscriptions.forEach(subscription => {
        rosbridge.unsubscribe(subscription)
      })
      subscriptions.clear()

      // 移除事件监听器
      window.removeEventListener('resize', handleResize)
      window.removeEventListener('orientationchange', handleResize)

      // 移除全屏状态监听器
      document.removeEventListener('fullscreenchange', handleFullscreenChange)
      document.removeEventListener('webkitfullscreenchange', handleFullscreenChange)
      document.removeEventListener('mozfullscreenchange', handleFullscreenChange)
      document.removeEventListener('MSFullscreenChange', handleFullscreenChange)

      // 清理ResizeObserver
      if (resizeObserver) {
        resizeObserver.disconnect()
        console.log('[ChartPanel] ResizeObserver 已清理')
      }

      // 清理定时器
      if (sizeCheckInterval) {
        clearInterval(sizeCheckInterval)
        console.log('[ChartPanel] 尺寸检查定时器已清理')
      }
    })

    // 调试ROS连接的函数
    const debugRosConnection = async () => {
      console.log('=== ROS连接调试开始 ===')
      console.log('1. 连接状态:', rosbridge.isConnected)
      console.log('2. rosbridge对象:', rosbridge)

      if (!rosbridge.isConnected) {
        console.log('3. 尝试重新连接...')
        try {
          await rosbridge.initializeConnection()
          await new Promise(resolve => setTimeout(resolve, 1000))
          console.log('4. 重连后状态:', rosbridge.isConnected)
        } catch (error) {
          console.error('5. 重连失败:', error)
          ElMessage.error('ROS重连失败: ' + error.message)
          return
        }
      }

      if (rosbridge.isConnected) {
        console.log('6. 开始获取ROS数据...')
        try {
          // 测试基本API调用
          const topics = await rosbridge.getTopics()
          console.log('7. Topics返回:', topics)

          const topicTypes = await rosbridge.getTopicTypes()
          console.log('8. TopicTypes返回:', topicTypes)

          const topicFrequencies = await rosbridge.getTopicFrequencies()
          console.log('9. TopicFrequencies返回:', topicFrequencies)

          if (topics && topics.length > 0) {
            ElMessage.success(`成功获取到 ${topics.length} 个topic`)
            console.log('10. 手动触发loadTopics...')
            loadTopics()
          } else {
            ElMessage.warning('ROS连接正常，但没有找到任何topic')
          }
        } catch (error) {
          console.error('11. API调用失败:', error)
          ElMessage.error('ROS API调用失败: ' + error.message)
        }
      } else {
        ElMessage.error('ROS连接失败，请检查服务器状态')
      }
      console.log('=== ROS连接调试结束 ===')
    }

    return {
      // DOM引用
      chartContainer,
      chartReady,
      chartSize,
      margin,
      currentMargin,
      gridSpacing,

      // 状态
      isPaused,
      showTopicSelector,
      showLegendPanel,
      isFullscreen,
      timeWindow,

      // 主题管理
      availableTopics,
      topicSearchText,
      filteredAvailableTopics,
      expandedTopics,
      expandTopic,
      getTopicFields,
      isFieldSelected,
      isFieldPlottable,
      getFieldTypeInfo,
      parsedTopicFields,
      parseMessageStructure,

      // 数据系列
      dataSeries,
      visibleDataSeries,
      addDataSeries,
      removeDataSeries,
      toggleSeriesVisibility,

      // 图表计算
      yTicks,
      xTicks,
      getX,
      getY,
      getLinePath,
      getCurrentValue,
      getVisibleDataPoints,

      // 控制方法
      pauseChart,
      clearChart,
      onTimeWindowChange,
      resetZoom,
      toggleFullscreen,
      handleZoom,
      startPan,
      handlePan,
      endPan,

      // 调试方法
      debugRosConnection,
      loadTopics,
      
      // 测试动态解析功能
      testMessageParsing: () => {
        const testMessage = {
          position: { x: 1.5, y: 2.3, z: 0.8 },
          velocity: { linear: 0.5, angular: 0.2 },
          status: true,
          data: [1, 2, 3, 4, 5],
          config: {
            max_speed: 10.0,
            min_speed: 0.1
          }
        }
        
        console.log('[ChartPanel] 测试消息解析:')
        const parsedFields = parseMessageStructure(testMessage)
        console.log('解析结果:', parsedFields)
        
        const plottableFields = parsedFields.filter(field => isFieldPlottable(field.type))
        console.log('可绘制字段:', plottableFields)
        
        return plottableFields
      },
      
      // 频率检测
      topicFrequencies
    }
  },

  props: {
    compact: {
      type: Boolean,
      default: false
    }
  }
}
</script>

<style scoped>
.chart-panel {
  width: 100%;
  height: 100vh; /* 使用视口高度确保全尺寸 */
  min-height: 500px; /* 最小高度 */
  display: flex;
  flex-direction: column;
  overflow: hidden; /* 防止滚动条 */
}

.chart-controls {
  height: 45px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px;
  background: rgba(15, 23, 42, 0.8);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(148, 163, 184, 0.1);
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.controls-left,
.controls-center,
.controls-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.controls-center {
  flex: 1;
  justify-content: center;
}

.time-range-label {
  color: #e2e8f0;
  font-size: 12px;
  margin-right: 6px;
}

.chart-main {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.chart-main.with-sidebar .chart-container {
  flex: 1;
}

.chart-container {
  flex: 1;
  overflow: hidden;
  position: relative;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(148, 163, 184, 0.1);
  border-radius: 8px;
  margin: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
  min-height: 400px; /* 确保有足够的高度 */
  width: 100%; /* 确保宽度填满 */
  height: 100%; /* 使用父容器的100%高度，自适应全屏 */
}

/* 全屏时的样式 - 使用更具体的选择器 */
.chart-container:fullscreen,
.chart-container:-webkit-full-screen,
.chart-container:-moz-full-screen,
.chart-container:-ms-fullscreen {
  margin: 0 !important;
  border-radius: 0 !important;
  background: rgba(0, 0, 0, 0.95) !important;
  width: 100vw !important;
  height: 100vh !important;
  position: fixed !important;
  top: 0 !important;
  left: 0 !important;
  z-index: 9999 !important;
  max-width: none !important;
  max-height: none !important;
  overflow: hidden !important;
}

/* 全屏时的SVG样式 */
.chart-container:fullscreen .chart-svg,
.chart-container:-webkit-full-screen .chart-svg,
.chart-container:-moz-full-screen .chart-svg,
.chart-container:-ms-fullscreen .chart-svg {
  width: 100vw !important;
  height: 100vh !important;
  max-width: none !important;
  max-height: none !important;
}

/* 全屏时的图表面板样式 */
.chart-container:fullscreen .chart-panel,
.chart-container:-webkit-full-screen .chart-panel,
.chart-container:-moz-full-screen .chart-panel,
.chart-container:-ms-fullscreen .chart-panel {
  height: 100vh !important;
  width: 100vw !important;
}

/* 全屏时的图表主区域样式 */
.chart-container:fullscreen .chart-main,
.chart-container:-webkit-full-screen .chart-main,
.chart-container:-moz-full-screen .chart-main,
.chart-container:-ms-fullscreen .chart-main {
  width: 100vw !important;
  height: calc(100vh - 45px) !important; /* 减去控制栏高度 */
}

/* 侧边面板样式 */
.topic-selector-panel,
.legend-panel {
  width: 280px;
  background: rgba(15, 23, 42, 0.9);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(148, 163, 184, 0.1);
  border-radius: 8px;
  margin: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-header {
  height: 40px;
  background: rgba(15, 23, 42, 0.95);
  border-bottom: 1px solid rgba(148, 163, 184, 0.1);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px;
}

.panel-header h4 {
  margin: 0;
  color: #e2e8f0;
  font-size: 14px;
  font-weight: 500;
}

.panel-header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.panel-content {
  flex: 1;
  padding: 8px;
  overflow-y: auto;
}

/* 主题选择器样式 */
.topic-search {
  margin-bottom: 12px;
}

.topic-tree {
  space-y: 4px;
}

.topic-stats {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
  padding: 8px;
  background: rgba(148, 163, 184, 0.05);
  border-radius: 6px;
  border: 1px solid rgba(148, 163, 184, 0.1);
}

.stats-item {
  font-size: 12px;
  color: #94a3b8;
}

.stats-item.active {
  color: #00ff88;
  font-weight: 500;
}

.empty-state {
  text-align: center;
  padding: 40px 20px;
  color: #94a3b8;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
  opacity: 0.6;
}

.empty-state p {
  margin: 8px 0;
  font-size: 14px;
}

.empty-hint {
  color: #64748b;
  font-size: 12px;
  margin-top: 16px;
}

.empty-checklist {
  text-align: left;
  margin: 12px auto;
  display: inline-block;
  color: #64748b;
  font-size: 12px;
}

.empty-checklist li {
  margin: 4px 0;
}

.topic-item {
  margin-bottom: 8px;
  border-radius: 6px;
  border: 1px solid rgba(148, 163, 184, 0.1);
  transition: all 0.2s ease;
}

.topic-item:hover {
  border-color: rgba(148, 163, 184, 0.3);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.topic-item.inactive {
  opacity: 0.6;
  background: rgba(148, 163, 184, 0.05);
}

.topic-name {
  display: flex;
  align-items: center;
  padding: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.topic-info {
  flex: 1;
  margin-left: 8px;
}

.topic-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}

.topic-label {
  font-weight: 500;
  color: #e2e8f0;
}

.status-tag {
  font-size: 10px;
  padding: 2px 6px;
}

.topic-details {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.topic-path {
  font-size: 11px;
  color: #94a3b8;
  font-family: 'Courier New', monospace;
}

.topic-type {
  font-size: 10px;
  color: #64748b;
  background: rgba(148, 163, 184, 0.2);
  padding: 1px 4px;
  border-radius: 3px;
  align-self: flex-start;
}

.topic-name:hover {
  background: rgba(59, 130, 246, 0.2);
}

.expand-icon {
  margin-right: 6px;
  transition: transform 0.2s;
  color: #94a3b8;
}

.expand-icon.expanded {
  transform: rotate(90deg);
}

.topic-type {
  margin-left: auto;
  font-size: 10px;
  color: #64748b;
  background: rgba(148, 163, 184, 0.2);
  padding: 2px 6px;
  border-radius: 4px;
}

.topic-fields {
  margin-left: 20px;
  margin-top: 4px;
}

.field-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 8px;
  background: rgba(59, 130, 246, 0.1);
  border-radius: 6px;
  margin-bottom: 3px;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 11px;
  border: 1px solid transparent;
}

.field-main {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
}

.field-icon {
  font-size: 12px;
  width: 16px;
  text-align: center;
}

.field-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.field-item:hover {
  background: rgba(59, 130, 246, 0.3);
  transform: translateX(4px);
}

.field-item.selected {
  background: rgba(0, 212, 255, 0.2);
  border: 1px solid rgba(0, 212, 255, 0.5);
  box-shadow: 0 0 8px rgba(0, 212, 255, 0.3);
}

.field-item.selected:hover {
  background: rgba(0, 212, 255, 0.3);
}

/* 可绘制的字段样式 */
.field-item.plottable {
  background: rgba(34, 197, 94, 0.1);
  border-color: rgba(34, 197, 94, 0.2);
}

.field-item.plottable:hover {
  background: rgba(34, 197, 94, 0.2);
  border-color: rgba(34, 197, 94, 0.4);
}

/* 不可绘制的字段样式 */
.field-item.non-plottable {
  background: rgba(148, 163, 184, 0.1);
  color: #64748b;
  cursor: not-allowed;
  opacity: 0.6;
  border-color: rgba(148, 163, 184, 0.2);
}

.field-item.non-plottable:hover {
  background: rgba(148, 163, 184, 0.15);
  transform: none;
  border-color: rgba(148, 163, 184, 0.3);
}

.field-item.disabled {
  background: rgba(148, 163, 184, 0.1);
  color: #64748b;
  cursor: not-allowed;
  opacity: 0.5;
}

.field-item.disabled:hover {
  background: rgba(148, 163, 184, 0.1);
  transform: none;
}

.field-name {
  color: #e2e8f0;
  font-weight: 500;
}

.field-type {
  font-size: 9px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* 字段类型分类样式 */
.field-type.numeric {
  color: #22c55e;
  background: rgba(34, 197, 94, 0.2);
  border: 1px solid rgba(34, 197, 94, 0.3);
}

.field-type.pointcloud {
  color: #3b82f6;
  background: rgba(59, 130, 246, 0.2);
  border: 1px solid rgba(59, 130, 246, 0.3);
}

.field-type.image {
  color: #8b5cf6;
  background: rgba(139, 92, 246, 0.2);
  border: 1px solid rgba(139, 92, 246, 0.3);
}

.field-type.geometry {
  color: #f59e0b;
  background: rgba(245, 158, 11, 0.2);
  border: 1px solid rgba(245, 158, 11, 0.3);
}

.field-type.sensor {
  color: #06b6d4;
  background: rgba(6, 182, 212, 0.2);
  border: 1px solid rgba(6, 182, 212, 0.3);
}

.field-type.navigation {
  color: #84cc16;
  background: rgba(132, 204, 22, 0.2);
  border: 1px solid rgba(132, 204, 22, 0.3);
}

.field-type.text {
  color: #64748b;
  background: rgba(100, 116, 139, 0.2);
  border: 1px solid rgba(100, 116, 139, 0.3);
}

.field-type.time {
  color: #f97316;
  background: rgba(249, 115, 22, 0.2);
  border: 1px solid rgba(249, 115, 22, 0.3);
}

.field-type.computed {
  color: #ec4899;
  background: rgba(236, 72, 153, 0.2);
  border: 1px solid rgba(236, 72, 153, 0.3);
}

.field-type.unknown {
  color: #94a3b8;
  background: rgba(148, 163, 184, 0.2);
  border: 1px solid rgba(148, 163, 184, 0.3);
}

.field-status {
  font-size: 12px;
  font-weight: bold;
  width: 16px;
  text-align: center;
}

.field-status.selected {
  color: #22c55e;
}

.field-status.disabled {
  color: #ef4444;
}

.field-status.available {
  color: #3b82f6;
  opacity: 0.7;
}

.field-status.parsing {
  color: #f59e0b;
  animation: spin 1s linear infinite;
}

/* 解析中的字段样式 */
.field-item.parsing {
  background: rgba(245, 158, 11, 0.1);
  border-color: rgba(245, 158, 11, 0.3);
  color: #f59e0b;
}

.field-item.parsing:hover {
  background: rgba(245, 158, 11, 0.15);
  transform: none;
}

.field-type.parsing {
  color: #f59e0b;
  background: rgba(245, 158, 11, 0.2);
  border: 1px solid rgba(245, 158, 11, 0.3);
}

.parsing-spinner {
  animation: spin 1s linear infinite;
  display: inline-block;
}

/* 图例面板样式 */
.legend-list {
  space-y: 6px;
}

.legend-item {
  background: rgba(148, 163, 184, 0.1);
  border-radius: 6px;
  padding: 8px;
  transition: all 0.2s;
}

.legend-item:hover {
  background: rgba(148, 163, 184, 0.2);
}

.legend-item.disabled {
  opacity: 0.5;
}

.legend-item-main {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.color-indicator {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  flex-shrink: 0;
}

.series-name {
  flex: 1;
  color: #e2e8f0;
  font-size: 12px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.legend-controls {
  display: flex;
  gap: 2px;
}

.legend-item-details {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 10px;
  color: #94a3b8;
  margin-left: 20px;
}

.topic-info {
  font-family: monospace;
}

.field-info {
  font-style: italic;
}

.chart-svg {
  width: 100%;
  height: 100%;
  cursor: grab;
}

.chart-svg:active {
  cursor: grabbing;
}

.axis-label {
  font-size: 10px;
  fill: #94a3b8;
}

.legend-text {
  font-size: 11px;
  fill: #e2e8f0;
}

.current-value-title {
  font-size: 11px;
  font-weight: bold;
  fill: #e2e8f0;
}

.current-value-text {
  font-size: 10px;
  font-family: monospace;
  fill: #94a3b8;
}

.data-line {
  opacity: 0.8;
}

.data-point {
  opacity: 0.7;
}

.data-point:hover {
  opacity: 1;
  r: 4;
}

.data-point-end {
  opacity: 1;
  filter: drop-shadow(0 0 3px rgba(0, 0, 0, 0.3));
}

.data-point-end:hover {
  opacity: 1;
  r: 5;
  filter: drop-shadow(0 0 5px rgba(0, 0, 0, 0.5));
}

.chart-loading {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  color: #94a3b8;
  font-size: 12px;
}

.loading-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid rgba(148, 163, 184, 0.3);
  border-top: 2px solid #00d4ff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

/* 滚动条样式 */
.panel-content::-webkit-scrollbar {
  width: 6px;
}

.panel-content::-webkit-scrollbar-track {
  background: rgba(148, 163, 184, 0.1);
  border-radius: 3px;
}

.panel-content::-webkit-scrollbar-thumb {
  background: rgba(148, 163, 184, 0.4);
  border-radius: 3px;
  transition: background 0.3s;
}

.panel-content::-webkit-scrollbar-thumb:hover {
  background: rgba(148, 163, 184, 0.6);
}

/* 紧凑模式样式 */
.chart-panel.compact .chart-controls {
  height: 35px;
  padding: 0 8px;
}

.chart-panel.compact .controls-center {
  display: none;
}

.chart-panel.compact .topic-selector-panel,
.chart-panel.compact .legend-panel {
  width: 220px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .chart-main.with-sidebar {
    flex-direction: column;
  }

  .topic-selector-panel,
  .legend-panel {
    width: 100%;
    height: 200px;
  }

  .controls-center {
    display: none;
  }
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* 动画效果 */
.topic-selector-panel,
.legend-panel {
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(-20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.field-item {
  animation: fadeIn 0.2s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>