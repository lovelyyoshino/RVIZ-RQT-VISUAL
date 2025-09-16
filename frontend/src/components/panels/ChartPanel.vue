<template>
  <div class="chart-panel">
    <div class="chart-controls">
      <el-select v-model="selectedTopic" size="small" placeholder="选择主题" style="width: 120px" @change="onTopicChange">
        <el-option
          v-for="topic in availableTopics"
          :key="topic.value"
          :label="topic.label"
          :value="topic.value"
        />
      </el-select>
      
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
    
    <div class="chart-container" ref="chartContainer">
      <svg class="chart-svg" :width="chartSize.width" :height="chartSize.height" v-if="chartReady">
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
            v-for="(series, index) in dataSeries" 
            :key="`series-${index}`"
            :d="getLinePath(series.data)" 
            :stroke="series.color" 
            stroke-width="2" 
            fill="none"
            class="data-line"
          />
        </g>
        
        <!-- 数据点 -->
        <g class="data-points">
          <g v-for="(series, seriesIndex) in dataSeries" :key="`points-${seriesIndex}`">
            <circle
              v-for="(point, pointIndex) in series.data.slice(-10)"
              :key="`point-${seriesIndex}-${pointIndex}`"
              :cx="getX(point.time)"
              :cy="getY(point.value)"
              r="3"
              :fill="series.color"
              class="data-point"
            />
          </g>
        </g>
        
        <!-- 图例 -->
        <g class="legend">
          <g v-for="(series, index) in dataSeries" :key="`legend-${index}`">
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
              {{ series.name }}
            </text>
          </g>
        </g>
        
        <!-- 当前值显示 -->
        <g class="current-values" v-if="dataSeries.length > 0">
          <rect 
            :x="chartSize.width - margin.right - 80" 
            :y="margin.top" 
            width="75" 
            height="60" 
            fill="rgba(255, 255, 255, 0.9)" 
            stroke="#ddd" 
            rx="4"
          />
          <text 
            :x="chartSize.width - margin.right - 75" 
            :y="margin.top + 15" 
            class="current-value-title"
          >
            当前值
          </text>
          <g v-for="(series, index) in dataSeries" :key="`current-${index}`">
            <text 
              :x="chartSize.width - margin.right - 75" 
              :y="margin.top + 30 + index * 15" 
              :fill="series.color" 
              class="current-value-text"
            >
              {{ series.name }}: {{ getCurrentValue(series) }}
            </text>
          </g>
        </g>
      </svg>
      
      <div v-if="!chartReady" class="chart-loading">
        <div class="loading-spinner"></div>
        <span>初始化图表...</span>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { VideoPause, VideoPlay, Delete } from '@element-plus/icons-vue'
import { useRosbridge } from '../../composables/useRosbridge'

export default {
  name: 'ChartPanel',
  components: {
    VideoPause,
    VideoPlay,
    Delete
  },
  setup() {
    const rosbridge = useRosbridge()
    const chartContainer = ref(null)
    const chartReady = ref(false)
    
    // 图表配置
    const margin = { top: 30, right: 90, bottom: 40, left: 60 }
    const chartSize = ref({ width: 300, height: 200 })
    const maxDataPoints = 100
    const timeWindow = 30 // 30秒时间窗口
    
    // 控制状态
    const selectedTopic = ref('/odom')
    const isPaused = ref(false)
    
    // 可用主题列表
    const availableTopics = ref([
      { value: '/odom', label: '里程计', messageType: 'nav_msgs/msg/Odometry' },
      { value: '/cmd_vel', label: '速度命令', messageType: 'geometry_msgs/msg/Twist' },
      { value: '/scan', label: '激光雷达', messageType: 'sensor_msgs/msg/LaserScan' },
      { value: '/imu', label: 'IMU数据', messageType: 'sensor_msgs/msg/Imu' },
      { value: '/battery', label: '电池状态', messageType: 'sensor_msgs/msg/BatteryState' },
      { value: '/joint_states', label: '关节状态', messageType: 'sensor_msgs/msg/JointState' },
      { value: '/tf', label: '坐标变换', messageType: 'tf2_msgs/msg/TFMessage' },
      { value: '/temperature', label: '温度传感器', messageType: 'sensor_msgs/msg/Temperature' },
      { value: '/diagnostics', label: '诊断信息', messageType: 'diagnostic_msgs/msg/DiagnosticArray' }
    ])
    
    // 数据系列
    const dataSeries = ref([
      {
        name: 'Linear X',
        color: '#409eff',
        data: []
      },
      {
        name: 'Angular Z',
        color: '#67c23a',
        data: []
      }
    ])
    
    // 计算Y轴刻度
    const yTicks = computed(() => {
      if (dataSeries.value.length === 0) return []
      
      const allValues = dataSeries.value.flatMap(series => 
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
        const time = now - (timeWindow * 1000) * (1 - i / (tickCount - 1))
        const x = margin.left + (chartSize.value.width - margin.left - margin.right) * (i / (tickCount - 1))
        const label = new Date(time).toLocaleTimeString().slice(0, 8)
        ticks.push({ x, label, time })
      }
      
      return ticks
    })
    
    // 坐标转换
    const getX = (timestamp) => {
      const now = Date.now()
      const ratio = Math.max(0, Math.min(1, (timestamp - (now - timeWindow * 1000)) / (timeWindow * 1000)))
      return margin.left + (chartSize.value.width - margin.left - margin.right) * ratio
    }
    
    const getY = (value) => {
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
      const validData = data.filter(point => (now - point.time) <= timeWindow * 1000)
      
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
    
    const onTopicChange = (topic) => {
      clearChart()
      subscribeToTopic(topic)
    }
    
    // 订阅主题
    let currentSubscription = null
    
    const subscribeToTopic = (topic) => {
      if (currentSubscription) {
        rosbridge.unsubscribe(currentSubscription)
        currentSubscription = null
      }
      
      console.log(`Subscribing to topic: ${topic}`)
      
      switch (topic) {
        case '/odom':
          currentSubscription = rosbridge.subscribe(topic, 'nav_msgs/msg/Odometry', (message) => {
            if (isPaused.value) return
            
            const timestamp = Date.now()
            const linearX = message.twist?.twist?.linear?.x || 0
            const angularZ = message.twist?.twist?.angular?.z || 0
            
            addDataPoint(0, timestamp, linearX)
            addDataPoint(1, timestamp, angularZ)
          })
          dataSeries.value = [
            { name: 'Linear X', color: '#409eff', data: [] },
            { name: 'Angular Z', color: '#67c23a', data: [] }
          ]
          break
          
        case '/cmd_vel':
          currentSubscription = rosbridge.subscribe(topic, 'geometry_msgs/msg/Twist', (message) => {
            if (isPaused.value) return
            
            const timestamp = Date.now()
            const linearX = message.linear?.x || 0
            const angularZ = message.angular?.z || 0
            
            addDataPoint(0, timestamp, linearX)
            addDataPoint(1, timestamp, angularZ)
          })
          dataSeries.value = [
            { name: 'Cmd Linear X', color: '#409eff', data: [] },
            { name: 'Cmd Angular Z', color: '#67c23a', data: [] }
          ]
          break
          
        case '/imu':
          currentSubscription = rosbridge.subscribe(topic, 'sensor_msgs/msg/Imu', (message) => {
            if (isPaused.value) return
            
            const timestamp = Date.now()
            const accelX = message.linear_acceleration?.x || 0
            const accelY = message.linear_acceleration?.y || 0
            const accelZ = message.linear_acceleration?.z || 0
            
            addDataPoint(0, timestamp, accelX)
            addDataPoint(1, timestamp, accelY)
            addDataPoint(2, timestamp, accelZ)
          })
          dataSeries.value = [
            { name: 'Accel X', color: '#409eff', data: [] },
            { name: 'Accel Y', color: '#67c23a', data: [] },
            { name: 'Accel Z', color: '#e6a23c', data: [] }
          ]
          break
          
        case '/battery':
          currentSubscription = rosbridge.subscribe(topic, 'sensor_msgs/msg/BatteryState', (message) => {
            if (isPaused.value) return
            
            const timestamp = Date.now()
            const voltage = message.voltage || 0
            const current = message.current || 0
            const percentage = (message.percentage || 0) * 100
            
            addDataPoint(0, timestamp, voltage)
            addDataPoint(1, timestamp, current)
            addDataPoint(2, timestamp, percentage)
          })
          dataSeries.value = [
            { name: 'Voltage (V)', color: '#409eff', data: [] },
            { name: 'Current (A)', color: '#67c23a', data: [] },
            { name: 'Percentage (%)', color: '#e6a23c', data: [] }
          ]
          break
          
        case '/joint_states':
          currentSubscription = rosbridge.subscribe(topic, 'sensor_msgs/msg/JointState', (message) => {
            if (isPaused.value) return
            
            const timestamp = Date.now()
            if (message.position && message.position.length > 0) {
              // 显示前3个关节的位置
              for (let i = 0; i < Math.min(3, message.position.length); i++) {
                addDataPoint(i, timestamp, message.position[i])
              }
            }
          })
          dataSeries.value = [
            { name: 'Joint 1', color: '#409eff', data: [] },
            { name: 'Joint 2', color: '#67c23a', data: [] },
            { name: 'Joint 3', color: '#e6a23c', data: [] }
          ]
          break
          
        case '/temperature':
          currentSubscription = rosbridge.subscribe(topic, 'sensor_msgs/msg/Temperature', (message) => {
            if (isPaused.value) return
            
            const timestamp = Date.now()
            const temperature = message.temperature || 0
            const variance = message.variance || 0
            
            addDataPoint(0, timestamp, temperature)
            addDataPoint(1, timestamp, Math.sqrt(variance))
          })
          dataSeries.value = [
            { name: 'Temperature (°C)', color: '#409eff', data: [] },
            { name: 'Std Dev', color: '#67c23a', data: [] }
          ]
          break
          
        case '/scan':
          currentSubscription = rosbridge.subscribe(topic, 'sensor_msgs/msg/LaserScan', (message) => {
            if (isPaused.value) return
            
            const timestamp = Date.now()
            if (message.ranges && message.ranges.length > 0) {
              // 计算统计信息
              const validRanges = message.ranges.filter(r => r > message.range_min && r < message.range_max)
              const minRange = Math.min(...validRanges)
              const maxRange = Math.max(...validRanges) 
              const avgRange = validRanges.reduce((a, b) => a + b, 0) / validRanges.length
              
              addDataPoint(0, timestamp, minRange)
              addDataPoint(1, timestamp, avgRange)
              addDataPoint(2, timestamp, maxRange)
            }
          })
          dataSeries.value = [
            { name: 'Min Range (m)', color: '#f56c6c', data: [] },
            { name: 'Avg Range (m)', color: '#409eff', data: [] },
            { name: 'Max Range (m)', color: '#67c23a', data: [] }
          ]
          break
          
        case '/diagnostics':
          currentSubscription = rosbridge.subscribe(topic, 'diagnostic_msgs/msg/DiagnosticArray', (message) => {
            if (isPaused.value) return
            
            const timestamp = Date.now()
            if (message.status && message.status.length > 0) {
              // 统计各种诊断级别的数量
              let okCount = 0, warnCount = 0, errorCount = 0
              
              message.status.forEach(status => {
                switch (status.level) {
                  case 0: okCount++; break
                  case 1: warnCount++; break
                  case 2:
                  case 3: errorCount++; break
                }
              })
              
              addDataPoint(0, timestamp, okCount)
              addDataPoint(1, timestamp, warnCount)
              addDataPoint(2, timestamp, errorCount)
            }
          })
          dataSeries.value = [
            { name: 'OK', color: '#67c23a', data: [] },
            { name: 'Warning', color: '#e6a23c', data: [] },
            { name: 'Error', color: '#f56c6c', data: [] }
          ]
          break
          
        default:
          console.warn(`暂不支持主题类型: ${topic} (${messageType})`)
          ElMessage.warning(`主题 ${topic} 的消息类型 ${messageType} 暂不支持图表显示`)
      }
    }
    
    // 添加数据点
    const addDataPoint = (seriesIndex, timestamp, value) => {
      if (seriesIndex >= dataSeries.value.length) return
      
      dataSeries.value[seriesIndex].data.push({ time: timestamp, value })
      
      // 限制数据点数量
      if (dataSeries.value[seriesIndex].data.length > maxDataPoints) {
        dataSeries.value[seriesIndex].data.shift()
      }
    }
    
    // 清理数据系列
    const cleanupDataSeries = () => {
      // 清理过期数据点
      const now = Date.now()
      const expiredTime = now - timeWindow * 1000
      
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
    
    onMounted(async () => {
      await nextTick()
      updateChartSize()
      chartReady.value = true
      
      subscribeToTopic(selectedTopic.value)
      
      // 监听窗口大小变化
      window.addEventListener('resize', updateChartSize)
    })
    
    onUnmounted(() => {
      if (currentSubscription) {
        rosbridge.unsubscribe(currentSubscription)
      }
      window.removeEventListener('resize', updateChartSize)
    })
    
    return {
      chartContainer,
      chartReady,
      chartSize,
      margin,
      selectedTopic,
      isPaused,
      availableTopics,
      dataSeries,
      yTicks,
      xTicks,
      getX,
      getY,
      getLinePath,
      getCurrentValue,
      pauseChart,
      clearChart,
      onTopicChange
    }
  }
}
</script>

<style scoped>
.chart-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.chart-controls {
  height: 35px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 8px;
  background: #fafafa;
  border-bottom: 1px solid #e8e8e8;
}

.chart-container {
  flex: 1;
  overflow: hidden;
  position: relative;
}

.chart-svg {
  width: 100%;
  height: 100%;
}

.axis-label {
  font-size: 10px;
  fill: #666;
}

.legend-text {
  font-size: 11px;
  fill: #333;
}

.current-value-title {
  font-size: 11px;
  font-weight: bold;
  fill: #333;
}

.current-value-text {
  font-size: 10px;
  font-family: monospace;
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
  color: #666;
  font-size: 12px;
}

.loading-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid #e0e0e0;
  border-top: 2px solid #409eff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
</style>
