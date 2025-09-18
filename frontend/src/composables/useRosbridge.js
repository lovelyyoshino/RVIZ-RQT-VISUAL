/**
 * ROS Bridge 通信 Composable
 */

import { ref, onUnmounted } from 'vue'
import { useConnectionStore } from './useConnectionStore'

export function useRosbridge() {
  const connectionStore = useConnectionStore()
  const subscribedTopics = ref(new Map())
  
  /**
   * 订阅 ROS 主题
   * @param {string} topic 主题名称
   * @param {string} messageType 消息类型
   * @param {Function} callback 消息回调函数
   */
  const subscribe = (topic, messageType, callback) => {
    console.log(`[useRosbridge] 订阅请求: ${topic}, 连接状态: ${connectionStore.isConnected}`)
    
    if (!connectionStore.isConnected) {
      console.warn(`[useRosbridge] ❌ 未连接到ROS bridge. 状态: ${connectionStore.connectionStatus}`)
      return null
    }
    
    const success = connectionStore.subscribeTopic(topic, messageType, callback)
    console.log(`[useRosbridge] connectionStore.subscribeTopic返回:`, success)
    
    if (success) {
      const subscription = {
        topic,
        messageType,
        callback,
        timestamp: Date.now()
      }
      
      subscribedTopics.value.set(topic, subscription)
      console.log(`[useRosbridge] ✅ 订阅成功: ${topic}`)
      return subscription
    } else {
      console.error(`[useRosbridge] ❌ 订阅失败: ${topic}`)
      return null
    }
  }
  
  /**
   * 取消订阅主题
   * @param {string|object} topicOrSubscription 主题名称或订阅对象
   */
  const unsubscribe = (topicOrSubscription) => {
    let topic
    let subscription
    
    if (typeof topicOrSubscription === 'string') {
      topic = topicOrSubscription
      subscription = subscribedTopics.value.get(topic)
    } else if (topicOrSubscription && topicOrSubscription.topic) {
      subscription = topicOrSubscription
      topic = subscription.topic
    } else {
      console.error('[useRosbridge] ❌ 无效的取消订阅参数:', topicOrSubscription)
      return false
    }
    
    if (subscription) {
      console.log(`[useRosbridge] 取消订阅: ${topic}`)
      const success = connectionStore.unsubscribeTopic(topic, subscription.callback)
      subscribedTopics.value.delete(topic)
      console.log(`[useRosbridge] ✅ 取消订阅成功: ${topic}`)
      return success
    } else {
      console.warn(`[useRosbridge] ⚠️ 未找到订阅: ${topic}`)
      return false
    }
  }
  
  /**
   * 发布消息到主题
   * @param {string} topic 主题名称
   * @param {string} messageType 消息类型
   * @param {Object} message 消息内容
   */
  const publish = (topic, messageType, message) => {
    return connectionStore.publishMessage(topic, messageType, message)
  }
  
  /**
   * 获取主题列表
   */
  const getTopics = () => {
    return connectionStore.getTopics()
  }
  
  /**
   * 获取节点列表
   */
  const getNodes = () => {
    return connectionStore.getNodes()
  }
  
  /**
   * 获取主题类型映射
   */
  const getTopicTypes = () => {
    return connectionStore.getTopicTypes()
  }
  
  /**
   * 获取主题频率信息
   */
  const getTopicFrequencies = () => {
    return connectionStore.getTopicFrequencies()
  }
  
  /**
   * 获取服务列表
   */
  const getServices = () => {
    return connectionStore.getServices()
  }
  
  /**
   * 获取服务类型映射
   */
  const getServiceTypes = () => {
    return connectionStore.getServiceTypes()
  }
  
  /**
   * 获取参数列表
   */
  const getParams = () => {
    return connectionStore.getParams()
  }
  
  /**
   * 创建点云订阅
   * @param {string} topic 点云主题
   * @param {Function} callback 回调函数
   */
  const subscribePointCloud = (topic, callback) => {
    return subscribe(topic, 'sensor_msgs/msg/PointCloud2', callback)
  }
  
  /**
   * 创建激光雷达订阅
   * @param {string} topic 激光雷达主题
   * @param {Function} callback 回调函数
   */
  const subscribeLaserScan = (topic, callback) => {
    return subscribe(topic, 'sensor_msgs/msg/LaserScan', callback)
  }
  
  /**
   * 创建标记订阅
   * @param {string} topic 标记主题
   * @param {Function} callback 回调函数
   */
  const subscribeMarker = (topic, callback) => {
    return subscribe(topic, 'visualization_msgs/msg/Marker', callback)
  }
  
  /**
   * 创建标记数组订阅
   * @param {string} topic 标记数组主题
   * @param {Function} callback 回调函数
   */
  const subscribeMarkerArray = (topic, callback) => {
    return subscribe(topic, 'visualization_msgs/msg/MarkerArray', callback)
  }
  
  /**
   * 创建图像订阅
   * @param {string} topic 图像主题
   * @param {Function} callback 回调函数
   */
  const subscribeImage = (topic, callback) => {
    return subscribe(topic, 'sensor_msgs/msg/Image', callback)
  }
  
  /**
   * 创建路径订阅
   * @param {string} topic 路径主题
   * @param {Function} callback 回调函数
   */
  const subscribePath = (topic, callback) => {
    return subscribe(topic, 'nav_msgs/msg/Path', callback)
  }
  
  /**
   * 创建栅格地图订阅
   * @param {string} topic 栅格地图主题
   * @param {Function} callback 回调函数
   */
  const subscribeOccupancyGrid = (topic, callback) => {
    return subscribe(topic, 'nav_msgs/msg/OccupancyGrid', callback)
  }
  
  /**
   * 发布速度命令
   * @param {Object} twist 速度命令 {linear: {x, y, z}, angular: {x, y, z}}
   */
  const publishTwist = (topic, twist) => {
    return publish(topic, 'geometry_msgs/msg/Twist', twist)
  }
  
  /**
   * 发布姿态
   * @param {Object} pose 姿态 {position: {x, y, z}, orientation: {x, y, z, w}}
   */
  const publishPose = (topic, pose) => {
    return publish(topic, 'geometry_msgs/msg/Pose', pose)
  }
  
  // 组件卸载时清理订阅
  onUnmounted(() => {
    subscribedTopics.value.forEach((_, topic) => {
      unsubscribe(topic)
    })
  })
  
  return {
    // 基础方法
    subscribe,
    unsubscribe,
    publish,
    getTopics,
    getNodes,
    getTopicTypes,
    getTopicFrequencies,
    getServices,
    getServiceTypes,
    getParams,
    
    // 传感器数据订阅
    subscribePointCloud,
    subscribeLaserScan,
    subscribeImage,
    
    // 可视化订阅
    subscribeMarker,
    subscribeMarkerArray,
    subscribePath,
    subscribeOccupancyGrid,
    
    // 发布方法
    publishTwist,
    publishPose,
    
    // 状态
    isConnected: connectionStore.isConnected,
    subscribedTopics: subscribedTopics.value
  }
}
