// 测试字段提取逻辑
function extractFieldValue(message, fieldPath) {
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

  // 普通字段路径 - 处理ROS消息的下划线前缀
  const parts = fieldPath.split('.')
  let value = message

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
          return null
        }
      }
    } else {
      return null
    }
  }

  return typeof value === 'number' ? value : null
}

// 测试数据 - 模拟ROS消息结构
const testMessage = {
  _header: {
    stamp: { sec: 1234567890, nanosec: 123456789 },
    frame_id: "map"
  },
  _child_frame_id: "base_link",
  _pose: {
    _pose: {
      _position: {
        _x: 1.5,
        _y: 2.3,
        _z: 0.1
      },
      _orientation: {
        _x: 0,
        _y: 0,
        _z: 0,
        _w: 1
      }
    },
    _covariance: []
  },
  _twist: {
    _twist: {
      _linear: {
        _x: 0.1,
        _y: 0.2,
        _z: 0.0
      },
      _angular: {
        _x: 0.0,
        _y: 0.0,
        _z: 0.05
      }
    },
    _covariance: []
  }
}

// 测试字段提取
console.log('测试字段提取:')
console.log('pose.pose.position.x:', extractFieldValue(testMessage, 'pose.pose.position.x'))
console.log('twist.twist.linear.x:', extractFieldValue(testMessage, 'twist.twist.linear.x'))
console.log('twist.twist.angular.z:', extractFieldValue(testMessage, 'twist.twist.angular.z'))
console.log('pose.pose.position.y:', extractFieldValue(testMessage, 'pose.pose.position.y'))
