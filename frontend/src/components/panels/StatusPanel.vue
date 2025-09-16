<template>
  <div class="status-panel">
    <div class="status-grid">
      <!-- 连接状态 -->
      <div class="status-item connection" :class="connectionStatusClass">
        <div class="status-icon">
          <el-icon size="20" :color="connectionColor">
            <Link />
          </el-icon>
        </div>
        <div class="status-content">
          <div class="status-label">连接</div>
          <div class="status-value">{{ connectionData.status }}</div>
          <div class="status-extra">{{ connectionData.latency }}ms</div>
        </div>
      </div>
      
      <!-- 运行状态 -->
      <div class="status-item system" :class="systemStatusClass">
        <div class="status-icon">
          <el-icon size="20" :color="systemColor">
            <Setting />
          </el-icon>
        </div>
        <div class="status-content">
          <div class="status-label">系统</div>
          <div class="status-value">{{ systemData.status }}</div>
          <div class="status-extra">{{ systemData.uptime }}</div>
        </div>
      </div>
      
      <!-- 模式状态 -->
      <div class="status-item mode" :class="modeStatusClass">
        <div class="status-icon">
          <el-icon size="20" :color="modeColor">
            <Monitor />
          </el-icon>
        </div>
        <div class="status-content">
          <div class="status-label">模式</div>
          <div class="status-value">{{ modeData.current }}</div>
          <div class="status-extra">{{ modeData.detail }}</div>
        </div>
      </div>
      
      <!-- 网络状态 -->
      <div class="status-item network" :class="networkStatusClass">
        <div class="status-icon">
          <el-icon size="20" :color="networkColor">
            <Connection />
          </el-icon>
        </div>
        <div class="status-content">
          <div class="status-label">网络</div>
          <div class="status-value">{{ networkData.status }}</div>
          <div class="status-extra">{{ networkData.signal }}%</div>
        </div>
      </div>
    </div>
    
    <!-- 详细状态指示器 -->
    <div class="indicator-bar">
      <div 
        v-for="indicator in indicators" 
        :key="indicator.name"
        class="indicator-item" 
        :class="indicator.status"
        :title="indicator.tooltip"
      >
        <div class="indicator-dot"></div>
        <span class="indicator-label">{{ indicator.name }}</span>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { 
  Monitor, 
  Setting,
  Link,
  CircleCheck,
  Warning,
  CircleClose,
  Connection
} from '@element-plus/icons-vue'
import { useRosbridge } from '../../composables/useRosbridge'
import { useConnectionStore } from '../../composables/useConnectionStore'

export default {
  name: 'StatusPanel',
  components: {
    Monitor,
    Setting,
    Link,
    CircleCheck,
    Warning,
    CircleClose,
    Connection
  },
  setup() {
    const rosbridge = useRosbridge()
    const connectionStore = useConnectionStore()
    
    // 状态数据
    const connectionData = ref({
      status: '已连接',
      latency: 25,
      quality: 'GOOD',
      packetsLost: 0
    })
    
    const systemData = ref({
      status: '运行中',
      uptime: '02:15:30',
      cpuUsage: 45,
      memUsage: 67,
      temperature: 42.5
    })
    
    const modeData = ref({
      current: '可视化',
      detail: '数据展示',
      mode: 'VIZ',
      subMode: 'DISPLAY'
    })
    
    const networkData = ref({
      status: '良好',
      signal: 85,
      bandwidth: '100 Mbps'
    })
    
    // 详细指示器
    const indicators = ref([
      { name: 'ROS', status: 'active', tooltip: 'ROS2系统正常' },
      { name: '3D', status: 'active', tooltip: '3D渲染正常' },
      { name: 'WS', status: 'active', tooltip: 'WebSocket连接正常' },
      { name: 'Data', status: 'warning', tooltip: '数据流较少' },
      { name: 'GPU', status: 'active', tooltip: 'GPU渲染正常' },
      { name: 'API', status: 'active', tooltip: 'API服务正常' }
    ])
    
    // 连接相关计算属性
    const connectionStatusClass = computed(() => {
      switch (connectionData.value.quality) {
        case 'GOOD': return 'status-good'
        case 'POOR': return 'status-warning'
        case 'DISCONNECTED': return 'status-critical'
        default: return 'status-inactive'
      }
    })
    
    const connectionColor = computed(() => {
      switch (connectionData.value.quality) {
        case 'GOOD': return '#67c23a'
        case 'POOR': return '#e6a23c'
        case 'DISCONNECTED': return '#f56c6c'
        default: return '#909399'
      }
    })
    
    // 系统相关计算属性
    const systemStatusClass = computed(() => {
      const cpu = systemData.value.cpuUsage
      const mem = systemData.value.memUsage
      const temp = systemData.value.temperature
      
      if (cpu > 80 || mem > 80 || temp > 60) return 'status-critical'
      if (cpu > 60 || mem > 60 || temp > 50) return 'status-warning'
      return 'status-good'
    })
    
    const systemColor = computed(() => {
      const cpu = systemData.value.cpuUsage
      const mem = systemData.value.memUsage
      const temp = systemData.value.temperature
      
      if (cpu > 80 || mem > 80 || temp > 60) return '#f56c6c'
      if (cpu > 60 || mem > 60 || temp > 50) return '#e6a23c'
      return '#67c23a'
    })
    
    // 模式相关计算属性
    const modeStatusClass = computed(() => {
      switch (modeData.value.mode) {
        case 'VIZ': return 'status-good'
        case 'DEBUG': return 'status-warning'
        case 'ERROR': return 'status-critical'
        default: return 'status-inactive'
      }
    })
    
    const modeColor = computed(() => {
      switch (modeData.value.mode) {
        case 'VIZ': return '#67c23a'
        case 'DEBUG': return '#e6a23c'
        case 'ERROR': return '#f56c6c'
        default: return '#909399'
      }
    })
    
    // 网络相关计算属性
    const networkStatusClass = computed(() => {
      const signal = networkData.value.signal
      if (signal > 70) return 'status-good'
      if (signal > 40) return 'status-warning'
      return 'status-critical'
    })
    
    const networkColor = computed(() => {
      const signal = networkData.value.signal
      if (signal > 70) return '#67c23a'
      if (signal > 40) return '#e6a23c'
      return '#f56c6c'
    })
    
    // 订阅状态相关主题
    let subscriptions = []
    
    const subscribeToStatus = () => {
      // 诊断信息
      subscriptions.push(rosbridge.subscribe('/diagnostics', 'diagnostic_msgs/msg/DiagnosticArray', (message) => {
        if (message.status && message.status.length > 0) {
          message.status.forEach(status => {
            const indicator = indicators.value.find(ind => 
              status.name.toLowerCase().includes(ind.name.toLowerCase())
            )
            
            if (indicator) {
              switch (status.level) {
                case 0: indicator.status = 'active'; break  // OK
                case 1: indicator.status = 'warning'; break // WARN
                case 2: indicator.status = 'inactive'; break // ERROR
                case 3: indicator.status = 'inactive'; break // STALE
              }
              indicator.tooltip = status.message || indicator.tooltip
            }
          })
        }
      }))
      
      // 系统状态
      subscriptions.push(rosbridge.subscribe('/system_status', 'std_msgs/msg/String', (message) => {
        try {
          const statusData = JSON.parse(message.data)
          if (statusData.cpu_usage !== undefined) {
            systemData.value.cpuUsage = statusData.cpu_usage
          }
          if (statusData.mem_usage !== undefined) {
            systemData.value.memUsage = statusData.mem_usage
          }
          if (statusData.temperature !== undefined) {
            systemData.value.temperature = statusData.temperature
          }
        } catch (error) {
          console.warn('Failed to parse system status:', error)
        }
      }))
    }
    
    // 实时运行时间追踪
    let uptimeTimer = null
    const startTime = Date.now()
    
    const startUptimeTracking = () => {
      uptimeTimer = setInterval(() => {
        const uptime = Date.now() - startTime
        const hours = Math.floor(uptime / 3600000)
        const minutes = Math.floor((uptime % 3600000) / 60000)
        const seconds = Math.floor((uptime % 60000) / 1000)
        
        systemData.value.uptime = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
      }, 1000)
    }
    
    // 监听连接状态
    const updateConnectionStatus = () => {
      if (connectionStore.isConnected) {
        connectionData.value.status = '已连接'
        connectionData.value.quality = 'GOOD'
      } else {
        connectionData.value.status = '未连接'
        connectionData.value.quality = 'DISCONNECTED'
        connectionData.value.latency = 0
      }
    }
    
    onMounted(() => {
      console.log('StatusPanel mounted - 使用真实ROS数据')
      subscribeToStatus()
      updateConnectionStatus()
      startUptimeTracking()
      
      // 监听连接状态变化
      setInterval(updateConnectionStatus, 5000)
    })
    
    onUnmounted(() => {
      subscriptions.forEach(subscription => {
        if (subscription) {
          rosbridge.unsubscribe(subscription)
        }
      })
      
      if (uptimeTimer) {
        clearInterval(uptimeTimer)
      }
    })
    
    return {
      connectionData,
      systemData,
      modeData,
      networkData,
      indicators,
      connectionStatusClass,
      connectionColor,
      systemStatusClass,
      systemColor,
      modeStatusClass,
      modeColor,
      networkStatusClass,
      networkColor
    }
  }
}
</script>

<style scoped>
.status-panel {
  padding: 8px;
  font-size: 12px;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.status-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  flex: 1;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px;
  border-radius: 6px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(10px);
  transition: all 0.3s ease;
}

.status-item.status-good {
  border-color: #67c23a;
  background: rgba(103, 194, 58, 0.1);
}

.status-item.status-warning {
  border-color: #e6a23c;
  background: rgba(230, 162, 60, 0.1);
}

.status-item.status-critical {
  border-color: #f56c6c;
  background: rgba(245, 108, 108, 0.1);
}

.status-item.status-inactive {
  border-color: #909399;
  background: rgba(144, 147, 153, 0.1);
  opacity: 0.7;
}

.status-icon {
  flex-shrink: 0;
}

.status-content {
  flex: 1;
  min-width: 0;
}

.status-label {
  font-weight: 500;
  color: #e2e8f0;
  margin-bottom: 2px;
}

.status-value {
  font-weight: bold;
  color: #ffffff;
  font-size: 13px;
}

.status-extra {
  color: #94a3b8;
  font-size: 10px;
  margin-top: 1px;
}

.indicator-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 4px;
}

.indicator-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 10px;
  padding: 2px 4px;
  border-radius: 3px;
  background: rgba(15, 23, 42, 0.8);
  cursor: help;
  transition: all 0.3s ease;
}

.indicator-item:hover {
  background: rgba(15, 23, 42, 0.9);
  transform: translateY(-1px);
}

.indicator-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.indicator-item.active .indicator-dot {
  background: #67c23a;
  box-shadow: 0 0 8px rgba(103, 194, 58, 0.6);
}

.indicator-item.warning .indicator-dot {
  background: #e6a23c;
  box-shadow: 0 0 8px rgba(230, 162, 60, 0.6);
}

.indicator-item.inactive .indicator-dot {
  background: #f56c6c;
  box-shadow: 0 0 8px rgba(245, 108, 108, 0.6);
}

.indicator-label {
  color: #e2e8f0;
  font-size: 9px;
  white-space: nowrap;
}
</style>