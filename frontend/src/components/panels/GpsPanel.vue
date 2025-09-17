<template>
  <div class="position-panel">
    <div class="position-info">
      <div class="info-row">
        <span class="label">X位置:</span>
        <span class="value">{{ positionData.x.toFixed(3) }}m</span>
      </div>
      <div class="info-row">
        <span class="label">Y位置:</span>
        <span class="value">{{ positionData.y.toFixed(3) }}m</span>
      </div>
      <div class="info-row">
        <span class="label">Z位置:</span>
        <span class="value">{{ positionData.z.toFixed(3) }}m</span>
      </div>
      <div class="info-row">
        <span class="label">朝向:</span>
        <span class="value">{{ positionData.yaw.toFixed(1) }}°</span>
      </div>
    </div>

    <div class="position-status">
      <div class="status-indicator" :class="positionStatusClass">
        <div class="status-dot"></div>
        <span>{{ positionStatusText }}</span>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRosbridge } from '../../composables/useRosbridge'

export default {
  name: 'PositionPanel',
  setup() {
    const rosbridge = useRosbridge()

    const positionData = ref({
      x: 0.0,
      y: 0.0,
      z: 0.0,
      yaw: 0.0, // 朝向角度（度）
      status: 'INACTIVE', // ACTIVE, INACTIVE, NO_DATA
      lastUpdate: null
    })

    const positionStatusClass = computed(() => {
      switch (positionData.value.status) {
        case 'ACTIVE':
          return 'status-active'
        case 'INACTIVE':
          return 'status-inactive'
        case 'NO_DATA':
          return 'status-no-fix'
        default:
          return 'status-inactive'
      }
    })

    const positionStatusText = computed(() => {
      switch (positionData.value.status) {
        case 'ACTIVE':
          return '位置活跃'
        case 'INACTIVE':
          return '位置不活跃'
        case 'NO_DATA':
          return '无位置数据'
        default:
          return '位置未知状态'
      }
    })
    
    // 存储订阅引用
    const subscriptions = []

    const subscribeToPosition = () => {
      console.log('[PositionPanel] 订阅位置数据...')

      // 订阅多个可能的位置信息源
      const positionTopics = [
        { topic: '/odom', type: 'nav_msgs/msg/Odometry' },
        { topic: '/robot_pose', type: 'geometry_msgs/msg/PoseStamped' },
        { topic: '/amcl_pose', type: 'geometry_msgs/msg/PoseWithCovarianceStamped' },
        { topic: '/pose', type: 'geometry_msgs/msg/PoseStamped' },
        { topic: '/localization', type: 'nav_msgs/msg/Odometry' },
        { topic: '/localization_2d', type: 'nav_msgs/msg/Odometry' }
      ]

      positionTopics.forEach(({ topic, type }) => {
        console.log(`[PositionPanel] 尝试订阅位置主题: ${topic} (${type})`)

        try {
          const subscription = rosbridge.subscribe(topic, type, (message) => {
            console.debug(`[PositionPanel] 收到${topic}数据:`, message)

            let position = null
            let orientation = null

            // 根据消息类型解析位置信息，兼容下划线前缀字段
            if (type === 'nav_msgs/msg/Odometry') {
              // 支持标准格式和下划线前缀格式
              const pose = message.pose || message._pose
              if (pose && (pose.pose || pose._pose)) {
                const poseData = pose.pose || pose._pose || pose
                position = poseData.position || poseData._position
                orientation = poseData.orientation || poseData._orientation
              }
            } else if (type === 'geometry_msgs/msg/PoseStamped') {
              const poseMsg = message.pose || message._pose
              if (poseMsg) {
                position = poseMsg.position || poseMsg._position
                orientation = poseMsg.orientation || poseMsg._orientation
              }
            } else if (type === 'geometry_msgs/msg/PoseWithCovarianceStamped') {
              const pose = message.pose || message._pose
              if (pose && (pose.pose || pose._pose)) {
                const poseData = pose.pose || pose._pose || pose
                position = poseData.position || poseData._position
                orientation = poseData.orientation || poseData._orientation
              }
            }

            if (position) {
              console.debug(`[PositionPanel] 解析到位置信息:`, position)

              // 更新位置信息（直接使用XYZ坐标），兼容下划线前缀
              positionData.value.x = position.x || position._x || 0.0
              positionData.value.y = position.y || position._y || 0.0
              positionData.value.z = position.z || position._z || 0.0
              positionData.value.status = 'ACTIVE'
              positionData.value.lastUpdate = new Date()

              // 计算yaw角度（从四元数转换），兼容下划线前缀
              if (orientation) {
                const qx = orientation.x || orientation._x || 0
                const qy = orientation.y || orientation._y || 0
                const qz = orientation.z || orientation._z || 0
                const qw = orientation.w || orientation._w || 1

                // 从四元数计算yaw角度（绕Z轴旋转）
                const yaw = Math.atan2(2 * (qw * qz + qx * qy), 1 - 2 * (qy * qy + qz * qz))
                positionData.value.yaw = yaw * 180 / Math.PI // 转换为度
              } else {
                positionData.value.yaw = 0.0
              }

              // 减少位置更新的日志输出频率
              if (!subscribeToPosition._lastLogTime || Date.now() - subscribeToPosition._lastLogTime > 5000) {
                console.log(`[PositionPanel] 位置更新: (${positionData.value.x.toFixed(3)}, ${positionData.value.y.toFixed(3)}, ${positionData.value.z.toFixed(3)})`)
                subscribeToPosition._lastLogTime = Date.now()
              }
            } else {
              console.warn(`[PositionPanel] 无法从${topic}解析位置信息`)
            }
          })

          subscriptions.push({ topic, subscription })
          console.log(`[PositionPanel] 成功订阅位置主题: ${topic}`)
        } catch (error) {
          console.warn(`[PositionPanel] 订阅${topic}失败:`, error)
        }
      })
    }
    
    onMounted(() => {
      console.log('[PositionPanel] mounted - 订阅位置数据')
      subscribeToPosition()
    })

    onUnmounted(() => {
      console.log('[PositionPanel] 组件卸载 - 清理所有订阅')

      // 清理所有位置订阅
      subscriptions.forEach(({ topic, subscription }) => {
        try {
          rosbridge.unsubscribe(topic)
          console.log(`[PositionPanel] 清理位置订阅: ${topic}`)
        } catch (e) {
          console.warn(`[PositionPanel] 清理${topic}订阅失败:`, e)
        }
      })

      // 清空订阅数组
      subscriptions.length = 0
    })

    return {
      positionData,
      positionStatusClass,
      positionStatusText
    }
  }
}
</script>

<style scoped>
.position-panel {
  padding: 8px 12px;
  font-size: 12px;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.position-info {
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

.position-status {
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
