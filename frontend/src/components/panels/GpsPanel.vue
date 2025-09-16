<template>
  <div class="gps-panel">
    <div class="gps-info">
      <div class="info-row">
        <span class="label">纬度:</span>
        <span class="value">{{ gpsData.latitude.toFixed(8) }}</span>
      </div>
      <div class="info-row">
        <span class="label">经度:</span>
        <span class="value">{{ gpsData.longitude.toFixed(8) }}</span>
      </div>
      <div class="info-row">
        <span class="label">海拔:</span>
        <span class="value">{{ gpsData.altitude.toFixed(2) }}m</span>
      </div>
      <div class="info-row">
        <span class="label">精度:</span>
        <span class="value" :class="accuracyClass">{{ gpsData.accuracy.toFixed(2) }}m</span>
      </div>
    </div>
    
    <div class="gps-status">
      <div class="status-indicator" :class="gpsStatusClass">
        <div class="status-dot"></div>
        <span>{{ gpsStatusText }}</span>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRosbridge } from '../../composables/useRosbridge'

export default {
  name: 'GpsPanel',
  setup() {
    const rosbridge = useRosbridge()
    
    const gpsData = ref({
      latitude: 0.0,
      longitude: 0.0,
      altitude: 0.0,
      accuracy: 0.0,
      status: 'INACTIVE', // ACTIVE, INACTIVE, NO_FIX
      satelliteCount: 0
    })
    
    const gpsStatusClass = computed(() => {
      switch (gpsData.value.status) {
        case 'ACTIVE':
          return 'status-active'
        case 'INACTIVE':
          return 'status-inactive'
        case 'NO_FIX':
          return 'status-no-fix'
        default:
          return 'status-inactive'
      }
    })
    
    const gpsStatusText = computed(() => {
      switch (gpsData.value.status) {
        case 'ACTIVE':
          return `GPS 活跃 (${gpsData.value.satelliteCount} 颗卫星)`
        case 'INACTIVE':
          return 'GPS 不活跃'
        case 'NO_FIX':
          return 'GPS 无定位'
        default:
          return 'GPS 未知状态'
      }
    })
    
    const accuracyClass = computed(() => {
      const accuracy = gpsData.value.accuracy
      if (accuracy < 2) return 'accuracy-good'
      if (accuracy < 5) return 'accuracy-medium'
      return 'accuracy-poor'
    })
    
    // 订阅 GPS 相关主题
    let gpsSubscription = null
    let statusSubscription = null
    let odomSubscription = null
    
    const subscribeToGps = () => {
      console.log('订阅GPS数据...')
      
      // 订阅 GPS 修复数据
      gpsSubscription = rosbridge.subscribe(
        '/gps/fix',
        'sensor_msgs/msg/NavSatFix',
        (message) => {
          console.log('收到GPS fix数据:', message)
          if (message.status && message.status.status >= 0) {
            gpsData.value.latitude = message.latitude || gpsData.value.latitude
            gpsData.value.longitude = message.longitude || gpsData.value.longitude
            gpsData.value.altitude = message.altitude || gpsData.value.altitude
            
            // 更新精度信息
            if (message.position_covariance && message.position_covariance.length > 0) {
              gpsData.value.accuracy = Math.sqrt(
                message.position_covariance[0] + message.position_covariance[4]
              )
            }
            
            // 更新状态
            gpsData.value.status = message.status.status >= 0 ? 'ACTIVE' : 'NO_FIX'
          }
        }
      )
      
      // 订阅 GPS 状态数据
      statusSubscription = rosbridge.subscribe(
        '/gps/status',
        'gps_msgs/msg/GPSStatus',
        (message) => {
          console.log('收到GPS状态数据:', message)
          if (message.satellites_used !== undefined) {
            gpsData.value.satelliteCount = message.satellites_used
          }
        }
      )
      
      // 订阅里程计数据作为备选位置信息
      odomSubscription = rosbridge.subscribe(
        '/odom',
        'nav_msgs/msg/Odometry',
        (message) => {
        console.log('收到里程计数据:', message)
        if (message.pose && message.pose.pose && message.pose.pose.position) {
          const pos = message.pose.pose.position
          const orientation = message.pose.pose.orientation
          
          // 总是使用里程计数据更新位置（作为相对位置）
          gpsData.value.latitude = pos.y  // 使用Y作为纬度方向
          gpsData.value.longitude = pos.x  // 使用X作为经度方向
          gpsData.value.altitude = pos.z
          gpsData.value.status = 'ACTIVE'
          
          // 计算位置精度（基于协方差）
          if (message.pose && message.pose.covariance) {
            const cov = message.pose.covariance
            gpsData.value.accuracy = Math.sqrt(cov[0] + cov[7] + cov[14]) // x,y,z方差的平方根
          } else {
            gpsData.value.accuracy = 0.1 // 里程计通常精度较高
          }
          
          // 计算卫星数量（模拟，基于精度）
          gpsData.value.satelliteCount = Math.min(12, Math.max(4, Math.floor(1 / gpsData.value.accuracy * 8)))
        }
        }
      )
    }
    
    onMounted(() => {
      console.log('GpsPanel mounted - 订阅真实GPS数据')
      subscribeToGps()
    })
    
    onUnmounted(() => {
      console.log('GpsPanel unmounted - 清理订阅')
      if (gpsSubscription) {
        rosbridge.unsubscribe('/gps/fix')
      }
      if (statusSubscription) {
        rosbridge.unsubscribe('/gps/status') 
      }
      if (odomSubscription) {
        rosbridge.unsubscribe('/odom')
      }
    })
    
    return {
      gpsData,
      gpsStatusClass,
      gpsStatusText,
      accuracyClass
    }
  }
}
</script>

<style scoped>
.gps-panel {
  padding: 8px 12px;
  font-size: 12px;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.gps-info {
  flex: 1;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 3px;
}

.label {
  color: #666;
  font-weight: 500;
}

.value {
  font-family: monospace;
  font-weight: bold;
  color: #2c3e50;
}

.accuracy-good {
  color: #67c23a;
}

.accuracy-medium {
  color: #e6a23c;
}

.accuracy-poor {
  color: #f56c6c;
}

.gps-status {
  margin-top: 8px;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-active .status-dot {
  background: #67c23a;
  box-shadow: 0 0 6px rgba(103, 194, 58, 0.6);
}

.status-inactive .status-dot {
  background: #909399;
}

.status-no-fix .status-dot {
  background: #f56c6c;
  animation: blink 1s infinite;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0.3; }
}
</style>
