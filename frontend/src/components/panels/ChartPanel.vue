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
                  @click="addDataSeries(topic.value, field, topic.messageType)"
                >
                  <span class="field-name">{{ field.name }}</span>
                  <span class="field-type">{{ field.type }}</span>
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
              <pattern id="chartGrid" width="40" height="30" patternUnits="userSpaceOnUse">
                <path d="M 40 0 L 0 0 0 30" fill="none" stroke="#f0f0f0" stroke-width="1"/>
              </pattern>
            </defs>
            <rect width="100%" height="100%" fill="url(#chartGrid)" />
          </g>

        <!-- Y轴 -->
        <g class="y-axis">
          <line
            :x1="margin.left"
            :y1="margin.top"
            :x2="margin.left"
            :y2="chartSize.height - margin.bottom"
            stroke="#333"
            stroke-width="2"
          />
          <g v-for="(tick, index) in yTicks" :key="`y-${index}`">
            <line
              :x1="margin.left - 5"
              :y1="tick.y"
              :x2="margin.left"
              :y2="tick.y"
              stroke="#333"
              stroke-width="1"
            />
            <text
              :x="margin.left - 8"
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
            :x1="margin.left"
            :y1="chartSize.height - margin.bottom"
            :x2="chartSize.width - margin.right"
            :y2="chartSize.height - margin.bottom"
            stroke="#333"
            stroke-width="2"
          />
          <g v-for="(tick, index) in xTicks" :key="`x-${index}`">
            <line
              :x1="tick.x"
              :y1="chartSize.height - margin.bottom"
              :x2="tick.x"
              :y2="chartSize.height - margin.bottom + 5"
              stroke="#333"
              stroke-width="1"
            />
            <text
              :x="tick.x"
              :y="chartSize.height - margin.bottom + 15"
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
                v-for="(point, pointIndex) in series.data.slice(-10)"
                :key="`point-${series.id}-${pointIndex}`"
                :cx="getX(point.time)"
                :cy="getY(point.value, series.yAxisIndex)"
                r="3"
                :fill="series.color"
                class="data-point"
                :style="{ opacity: series.visible ? 0.7 : 0 }"
              />
            </g>
          </g>

          <!-- 简化的内嵌图例 -->
          <g class="legend" v-if="!showLegendPanel && visibleDataSeries.length > 0">
            <g v-for="(series, index) in visibleDataSeries.slice(0, 3)" :key="`legend-${series.id}`">
              <rect
                :x="margin.left + index * 80"
                :y="5"
                width="12"
                height="12"
                :fill="series.color"
              />
              <text
                :x="margin.left + index * 80 + 16"
                :y="15"
                class="legend-text"
              >
                {{ series.name.length > 8 ? series.name.substring(0, 8) + '...' : series.name }}
              </text>
            </g>
            <text v-if="visibleDataSeries.length > 3" :x="margin.left + 3 * 80" :y="15" class="legend-text">
              +{{ visibleDataSeries.length - 3 }}更多
            </text>
          </g>

          <!-- 当前值显示 -->
          <g class="current-values" v-if="visibleDataSeries.length > 0">
            <rect
              :x="chartSize.width - margin.right - 100"
              :y="margin.top"
              width="95"
              :height="Math.min(60 + visibleDataSeries.length * 15, 150)"
              fill="rgba(255, 255, 255, 0.9)"
              stroke="#ddd"
              rx="4"
            />
            <text
              :x="chartSize.width - margin.right - 95"
              :y="margin.top + 15"
              class="current-value-title"
            >
              当前值
            </text>
            <g v-for="(series, index) in visibleDataSeries.slice(0, 8)" :key="`current-${series.id}`">
              <text
                :x="chartSize.width - margin.right - 95"
                :y="margin.top + 30 + index * 15"
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
    const margin = { top: 30, right: 90, bottom: 40, left: 60 }
    const chartSize = ref({ width: 300, height: 200 })
    const maxDataPoints = 500
    const timeWindow = ref(30) // 30秒时间窗口

    // 控制状态
    const isPaused = ref(false)
    const showTopicSelector = ref(false)
    const showLegendPanel = ref(false)

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

      const tickCount = 5
      const ticks = []

      for (let i = 0; i <= tickCount; i++) {
        const value = yMin + (yMax - yMin) * (i / tickCount)
        const y = margin.top + (chartSize.value.height - margin.top - margin.bottom) * (1 - i / tickCount)
        ticks.push({ value, y })
      }

      return ticks
    })

    // 计算X轴刻度
    const xTicks = computed(() => {
      const now = Date.now()
      const ticks = []
      const tickCount = 6

      for (let i = 0; i < tickCount; i++) {
        const time = now - (timeWindow.value * 1000) * (1 - i / (tickCount - 1))
        const x = margin.left + (chartSize.value.width - margin.left - margin.right) * (i / (tickCount - 1))
        const label = new Date(time).toLocaleTimeString().slice(0, 8)
        ticks.push({ x, label, time })
      }

      return ticks
    })

    // 坐标转换
    const getX = (timestamp) => {
      const now = Date.now()
      const ratio = Math.max(0, Math.min(1, (timestamp - (now - timeWindow.value * 1000)) / (timeWindow.value * 1000)))
      return margin.left + (chartSize.value.width - margin.left - margin.right) * ratio
    }

    const getY = (value, yAxisIndex = 0) => {
      if (yTicks.value.length < 2) return chartSize.value.height / 2

      const minY = yTicks.value[0].value
      const maxY = yTicks.value[yTicks.value.length - 1].value
      const ratio = (value - minY) / (maxY - minY) || 0
      return margin.top + (chartSize.value.height - margin.top - margin.bottom) * (1 - ratio)
    }

    // 生成线条路径
    const getLinePath = (data) => {
      if (data.length < 2) return ''

      const now = Date.now()
      const validData = data.filter(point => (now - point.time) <= timeWindow.value * 1000)

      if (validData.length < 2) return ''

      let path = `M ${getX(validData[0].time)} ${getY(validData[0].value)}`

      for (let i = 1; i < validData.length; i++) {
        path += ` L ${getX(validData[i].time)} ${getY(validData[i].value)}`
      }

      return path
    }

    // 获取当前值
    const getCurrentValue = (series) => {
      if (series.data.length === 0) return 'N/A'
      const latestPoint = series.data[series.data.length - 1]
      return latestPoint.value.toFixed(2)
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
      timeWindow.value = newWindow
      // 清理过期数据
      cleanupDataSeries()
    }

    const resetZoom = () => {
      zoomLevel.value = 1
      panOffset.value = { x: 0, y: 0 }
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

    // 获取主题字段
    const getTopicFields = (topic) => {
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
        default:
          fields.push({ name: 'Raw Data', path: '_raw', type: 'unknown' })
      }

      return fields
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

    // 添加数据系列
    const addDataSeries = (topicName, field, messageType) => {
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

      showTopicSelector.value = false
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
            return 0
        }
      }

      // 普通字段路径
      const parts = fieldPath.split('.')
      let value = message

      for (const part of parts) {
        if (value && typeof value === 'object' && part in value) {
          value = value[part]
        } else {
          return null
        }
      }

      return typeof value === 'number' ? value : null
    }

    // 添加数据点到特定系列
    const addDataPointToSeries = (seriesId, timestamp, value) => {
      const series = dataSeries.value.find(s => s.id === seriesId)
      if (!series) return

      series.data.push({ time: timestamp, value })

      // 限制数据点数量
      if (series.data.length > maxDataPoints) {
        series.data.shift()
      }
    }

    // 清理数据系列
    const cleanupDataSeries = () => {
      // 清理过期数据点
      const now = Date.now()
      const expiredTime = now - timeWindow.value * 1000

      dataSeries.value.forEach(series => {
        series.data = series.data.filter(point => point.time > expiredTime)
      })
    }

    // 更新图表尺寸
    const updateChartSize = () => {
      if (chartContainer.value) {
        const rect = chartContainer.value.getBoundingClientRect()
        chartSize.value = {
          width: Math.max(rect.width, 200),
          height: Math.max(rect.height, 150)
        }
      }
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


    onMounted(async () => {
      await nextTick()
      updateChartSize()
      chartReady.value = true

      // 监听窗口大小变化
      window.addEventListener('resize', updateChartSize)

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
      window.removeEventListener('resize', updateChartSize)
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

      // 状态
      isPaused,
      showTopicSelector,
      showLegendPanel,
      timeWindow,

      // 主题管理
      availableTopics,
      topicSearchText,
      filteredAvailableTopics,
      expandedTopics,
      expandTopic,
      getTopicFields,

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

      // 控制方法
      pauseChart,
      clearChart,
      onTimeWindowChange,
      resetZoom,
      handleZoom,
      startPan,
      handlePan,
      endPan,

      // 调试方法
      debugRosConnection,
      loadTopics
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
  height: 100vh; /* 使用视口高度 */
  min-height: 500px; /* 最小高度 */
  display: flex;
  flex-direction: column;
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
  height: calc(100vh - 200px); /* 使用视口高度减去工具栏等空间 */
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
  padding: 4px 8px;
  background: rgba(59, 130, 246, 0.1);
  border-radius: 4px;
  margin-bottom: 2px;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 11px;
}

.field-item:hover {
  background: rgba(59, 130, 246, 0.3);
  transform: translateX(4px);
}

.field-name {
  color: #e2e8f0;
  font-weight: 500;
}

.field-type {
  color: #94a3b8;
  font-size: 10px;
  background: rgba(148, 163, 184, 0.2);
  padding: 1px 4px;
  border-radius: 3px;
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