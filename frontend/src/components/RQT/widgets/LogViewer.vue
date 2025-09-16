<template>
  <div class="log-viewer">
    <!-- 控制栏 -->
    <div class="log-controls">
      <el-select
        v-model="selectedLogLevel"
        size="small"
        style="width: 80px"
        @change="filterLogs"
      >
        <el-option label="全部" value="all" />
        <el-option label="DEBUG" value="debug" />
        <el-option label="INFO" value="info" />
        <el-option label="WARN" value="warn" />
        <el-option label="ERROR" value="error" />
      </el-select>
      
      <el-button-group size="small">
        <el-button @click="clearLogs">
          <el-icon><Delete /></el-icon>
          清空
        </el-button>
        <el-button @click="pauseLogging" :type="isPaused ? 'danger' : 'default'">
          <el-icon><VideoPause v-if="!isPaused" /><VideoPlay v-else /></el-icon>
          {{ isPaused ? '继续' : '暂停' }}
        </el-button>
      </el-button-group>
    </div>
    
    <!-- 日志列表 -->
    <div class="log-list">
      <el-scrollbar 
        ref="scrollbarRef" 
        height="200px"
        always
      >
        <div class="log-content">
          <div
            v-for="log in filteredLogs"
            :key="log.id"
            :class="['log-entry', `log-${log.level}`]"
          >
            <div class="log-time">{{ formatTime(log.timestamp) }}</div>
            <div class="log-level">
              <el-tag :type="getLogLevelType(log.level)" size="small">
                {{ log.level }}
              </el-tag>
            </div>
            <div class="log-node">{{ log.node }}</div>
            <div class="log-message">{{ log.message }}</div>
          </div>
          
          <div v-if="filteredLogs.length === 0" class="empty-logs">
            <el-text type="info">{{ isPaused ? '日志已暂停' : '暂无日志' }}</el-text>
          </div>
        </div>
      </el-scrollbar>
    </div>
    
    <!-- 统计信息 -->
    <div class="log-stats">
      <div class="stats-grid">
        <div class="stat-item">
          <span class="stat-label">总数:</span>
          <span class="stat-value">{{ logs.length }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">错误:</span>
          <span class="stat-value error">{{ errorCount }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">警告:</span>
          <span class="stat-value warning">{{ warningCount }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, reactive, computed, nextTick, onMounted, onUnmounted } from 'vue'
import { Delete, VideoPause, VideoPlay } from '@element-plus/icons-vue'

export default {
  name: 'LogViewer',
  components: {
    Delete,
    VideoPause,
    VideoPlay
  },
  setup() {
    const scrollbarRef = ref(null)
    const selectedLogLevel = ref('all')
    const isPaused = ref(false)
    const logs = ref([])
    const maxLogs = 1000 // 最大日志条数
    
    let logCounter = 0
    let logInterval = null
    
    // 过滤后的日志
    const filteredLogs = computed(() => {
      if (selectedLogLevel.value === 'all') {
        return logs.value
      }
      return logs.value.filter(log => log.level.toLowerCase() === selectedLogLevel.value)
    })
    
    // 错误数量
    const errorCount = computed(() => {
      return logs.value.filter(log => log.level === 'ERROR').length
    })
    
    // 警告数量
    const warningCount = computed(() => {
      return logs.value.filter(log => log.level === 'WARN').length
    })
    
    // 格式化时间
    const formatTime = (timestamp) => {
      return timestamp.toLocaleTimeString()
    }
    
    // 获取日志级别类型
    const getLogLevelType = (level) => {
      const typeMap = {
        'DEBUG': 'info',
        'INFO': 'success',
        'WARN': 'warning',
        'ERROR': 'danger'
      }
      return typeMap[level] || 'default'
    }
    
    // 添加日志
    const addLog = (node, level, message) => {
      if (isPaused.value) return
      
      const log = {
        id: ++logCounter,
        timestamp: new Date(),
        node: node,
        level: level,
        message: message
      }
      
      logs.value.push(log)
      
      // 限制日志数量
      if (logs.value.length > maxLogs) {
        logs.value.shift()
      }
      
      // 自动滚动到底部
      nextTick(() => {
        if (scrollbarRef.value) {
          scrollbarRef.value.setScrollTop(scrollbarRef.value.wrapRef.scrollHeight)
        }
      })
    }
    
    // 生成模拟日志
    const generateMockLog = () => {
      const nodes = ['robot_controller', 'laser_node', 'camera_node', 'navigation', 'move_base']
      const levels = ['DEBUG', 'INFO', 'WARN', 'ERROR']
      const messages = [
        'Node initialization completed',
        'Publishing message on topic',
        'Received sensor data',
        'Planning path to goal',
        'Connection established',
        'Warning: High CPU usage detected',
        'Error: Failed to connect to sensor',
        'Goal reached successfully',
        'Obstacle detected, replanning',
        'Parameter updated',
        'Service call received',
        'Transform lookup failed',
        'Battery level: 75%',
        'Emergency stop activated',
        'Normal operation resumed'
      ]
      
      const node = nodes[Math.floor(Math.random() * nodes.length)]
      let level = levels[Math.floor(Math.random() * levels.length)]
      
      // 调整级别分布，减少错误和警告
      const rand = Math.random()
      if (rand < 0.6) level = 'INFO'
      else if (rand < 0.8) level = 'DEBUG'
      else if (rand < 0.95) level = 'WARN'
      else level = 'ERROR'
      
      const message = messages[Math.floor(Math.random() * messages.length)]
      
      addLog(node, level, message)
    }
    
    // 清空日志
    const clearLogs = () => {
      logs.value = []
      logCounter = 0
      ElMessage.success('日志已清空')
    }
    
    // 暂停/继续日志
    const pauseLogging = () => {
      isPaused.value = !isPaused.value
      ElMessage.info(isPaused.value ? '日志已暂停' : '日志已继续')
    }
    
    // 过滤日志
    const filterLogs = () => {
      // 滚动到顶部
      nextTick(() => {
        if (scrollbarRef.value) {
          scrollbarRef.value.setScrollTop(0)
        }
      })
    }
    
    // 刷新日志
    const refresh = () => {
      // 清空并重新开始
      clearLogs()
      ElMessage.success('日志查看器已刷新')
    }
    
    // 获取日志数据（供父组件调用）
    const getLogData = () => {
      return logs.value.map(log => ({
        timestamp: log.timestamp.toISOString(),
        node: log.node,
        level: log.level,
        message: log.message
      }))
    }
    
    onMounted(() => {
      // 添加一些初始日志
      addLog('system', 'INFO', 'ROS2 Web Visualization System started')
      addLog('rosbridge', 'INFO', 'WebSocket server listening on port 9090')
      addLog('web_server', 'INFO', 'HTTP server listening on port 8000')
      
      // 定期生成模拟日志
      logInterval = setInterval(() => {
        if (Math.random() < 0.7) { // 70% 概率生成日志
          generateMockLog()
        }
      }, 2000)
    })
    
    onUnmounted(() => {
      if (logInterval) {
        clearInterval(logInterval)
      }
    })
    
    return {
      scrollbarRef,
      selectedLogLevel,
      isPaused,
      logs,
      filteredLogs,
      errorCount,
      warningCount,
      formatTime,
      getLogLevelType,
      clearLogs,
      pauseLogging,
      filterLogs,
      // 暴露方法供父组件调用
      refresh,
      getLogData
    }
  }
}
</script>

<style scoped>
.log-viewer {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.log-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  padding: 0 5px;
}

.log-list {
  flex: 1;
  overflow: hidden;
}

.log-content {
  padding: 5px;
}

.log-entry {
  display: grid;
  grid-template-columns: 60px 50px 80px 1fr;
  gap: 8px;
  align-items: center;
  padding: 4px 8px;
  margin-bottom: 2px;
  border-radius: 3px;
  font-size: 11px;
  line-height: 1.2;
}

.log-entry.log-debug {
  background: #f8f9fa;
}

.log-entry.log-info {
  background: #e8f5e8;
}

.log-entry.log-warn {
  background: #fff3cd;
}

.log-entry.log-error {
  background: #f8d7da;
}

.log-time {
  font-family: monospace;
  color: #666;
  font-size: 10px;
}

.log-level {
  font-weight: bold;
}

.log-node {
  font-family: monospace;
  color: #007bff;
  font-size: 10px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.log-message {
  color: #333;
  word-break: break-word;
}

.empty-logs {
  text-align: center;
  padding: 40px;
  color: #999;
}

.log-stats {
  margin-top: 10px;
  padding: 5px;
  background: #f9f9f9;
  border-radius: 4px;
}

.stats-grid {
  display: flex;
  justify-content: space-around;
  align-items: center;
}

.stat-item {
  font-size: 12px;
}

.stat-label {
  color: #666;
}

.stat-value {
  font-weight: bold;
  margin-left: 4px;
}

.stat-value.error {
  color: #f56c6c;
}

.stat-value.warning {
  color: #e6a23c;
}
</style>
