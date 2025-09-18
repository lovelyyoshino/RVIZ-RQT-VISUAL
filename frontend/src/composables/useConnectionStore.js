/**
 * ROS2 连接状态管理 Composable
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'

export const useConnectionStore = defineStore('connection', () => {
  // 连接状态
  const isConnected = ref(false)
  const isConnecting = ref(false)
  const connectionError = ref(null)
  const websocket = ref(null)
  
  // 连接配置 - 修正为正确的 WebSocket 地址
  const wsUrl = ref('ws://localhost:8000/ws')  // 后端 FastAPI WebSocket 端点
  const reconnectAttempts = ref(0)
  const maxReconnectAttempts = ref(5)
  const reconnectInterval = ref(3000)
  
  // 订阅的主题
  const subscribedTopics = ref(new Set())
  const messageHandlers = ref(new Map())
  
  // API调用的Promise管理
  const pendingRequests = ref(new Map())
  let requestIdCounter = 0
  
  // 计算属性
  const connectionStatus = computed(() => {
    if (isConnecting.value) return 'connecting'
    if (isConnected.value) return 'connected'
    if (connectionError.value) return 'error'
    return 'disconnected'
  })
  
  const connectionStatusText = computed(() => {
    switch (connectionStatus.value) {
      case 'connecting':
        return '连接中...'
      case 'connected':
        return '已连接'
      case 'error':
        return `连接错误: ${connectionError.value}`
      default:
        return '未连接'
    }
  })
  
  // 初始化连接
  const initializeConnection = async () => {
    if (isConnected.value || isConnecting.value) {
      return
    }
    
    await connect()
  }
  
  // 连接 WebSocket
  const connect = async () => {
    try {
      isConnecting.value = true
      connectionError.value = null
      
      websocket.value = new WebSocket(wsUrl.value)
      
      websocket.value.onopen = () => {
        isConnected.value = true
        isConnecting.value = false
        reconnectAttempts.value = 0
        console.log('WebSocket connected')
        ElMessage.success('已连接到 ROS2 服务')
      }
      
      websocket.value.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)
          console.debug(`[ConnectionStore] 📨 收到消息:`, message)
          handleMessage(message)
        } catch (error) {
          console.error('[ConnectionStore] ❌ 解析消息失败:', error, event.data)
        }
      }
      
      websocket.value.onclose = (event) => {
        isConnected.value = false
        isConnecting.value = false
        clearPendingRequests()
        
        if (event.code !== 1000) {
          // 非正常关闭，尝试重连
          connectionError.value = `连接关闭 (${event.code})`
          console.warn('WebSocket closed unexpectedly:', event)
          attemptReconnect()
        } else {
          console.log('WebSocket closed normally')
        }
      }
      
      websocket.value.onerror = (error) => {
        isConnected.value = false
        isConnecting.value = false
        connectionError.value = '连接失败'
        console.error('WebSocket error:', error)
        ElMessage.error('连接失败')
      }
      
    } catch (error) {
      isConnecting.value = false
      connectionError.value = error.message
      console.error('Failed to connect:', error)
    }
  }
  
  // 断开连接
  const disconnect = () => {
    if (websocket.value) {
      websocket.value.close(1000, 'Normal closure')
      websocket.value = null
    }
    isConnected.value = false
    isConnecting.value = false
    connectionError.value = null
    subscribedTopics.value.clear()
    messageHandlers.value.clear()
    advertisedTopics.value.clear()  // 清理发布者声明
    clearPendingRequests()
  }
  
  // 重连逻辑
  const attemptReconnect = () => {
    if (reconnectAttempts.value >= maxReconnectAttempts.value) {
      console.error('Max reconnect attempts reached')
      ElMessage.error('连接失败，请检查服务器状态')
      return
    }
    
    reconnectAttempts.value++
    console.log(`Attempting to reconnect (${reconnectAttempts.value}/${maxReconnectAttempts.value})`)
    
    setTimeout(() => {
      connect()
    }, reconnectInterval.value)
  }
  
  // 发送消息
  const sendMessage = (message) => {
    if (!isConnected.value || !websocket.value) {
      console.warn('WebSocket not connected')
      return false
    }
    
    try {
      websocket.value.send(JSON.stringify(message))
      return true
    } catch (error) {
      console.error('Failed to send message:', error)
      return false
    }
  }
  
  // 处理接收到的消息
  const handleMessage = (message) => {
    const { op, topic, id } = message
    
    console.debug(`[ConnectionStore] 🔀 处理消息 - 操作: ${op}, 主题: ${topic || 'N/A'}`)

    // 根据操作类型处理消息
    switch (op) {
      case 'publish':
        console.debug(`[ConnectionStore] 📢 发布消息到主题: ${topic}`)
        handleTopicMessage(topic, message.msg)
        break
      case 'get_topics_result':
        console.log(`[ConnectionStore] 📋 收到主题列表，数量: ${(message.topics || []).length}`)
        resolveRequest(id, message.topics || [])
        break
      case 'get_nodes_result':
        console.log(`[ConnectionStore] 🏢 收到节点列表，数量: ${(message.nodes || []).length}`)
        resolveRequest(id, message.nodes || [])
        break
      case 'get_topic_types_result':
        console.log(`[ConnectionStore] 🏷️ 收到主题类型映射`)
        resolveRequest(id, message.topic_types || {})
        break
      case 'get_topic_frequencies_result':
        console.log(`[ConnectionStore] 📊 收到主题频率信息`)
        resolveRequest(id, message.frequencies || {})
        break
      case 'get_services_result':
        console.log(`[ConnectionStore] 🔧 收到服务列表，数量: ${(message.services || []).length}`)
        resolveRequest(id, message.services || [])
        break
      case 'get_service_types_result':
        console.log(`[ConnectionStore] 🔧 收到服务类型映射`)
        resolveRequest(id, message.service_types || {})
        break
      case 'get_params_result':
        console.log(`[ConnectionStore] ⚙️ 收到参数列表，数量: ${(message.params || []).length}`)
        resolveRequest(id, message.params || [])
        break
      case 'error':
        console.error(`[ConnectionStore] ❌ 收到错误消息:`, message.error)
        rejectRequest(id, message.error || 'Unknown error')
        break
      default:
        console.warn(`[ConnectionStore] ⚠️ 未知的消息操作: ${op}`, message)
    }
  }
  
  // 生成请求ID
  const generateRequestId = () => {
    return `req_${++requestIdCounter}_${Date.now()}`
  }
  
  // 解决请求Promise
  const resolveRequest = (requestId, data) => {
    if (requestId && pendingRequests.value.has(requestId)) {
      const { resolve } = pendingRequests.value.get(requestId)
      resolve(data)
      pendingRequests.value.delete(requestId)
    }
  }
  
  // 拒绝请求Promise
  const rejectRequest = (requestId, error) => {
    if (requestId && pendingRequests.value.has(requestId)) {
      const { reject } = pendingRequests.value.get(requestId)
      reject(new Error(error))
      pendingRequests.value.delete(requestId)
    }
  }
  
  // 发送API请求并返回Promise
  const sendApiRequest = (operation, params = {}) => {
    return new Promise((resolve, reject) => {
      if (!isConnected.value) {
        reject(new Error('Not connected to ROS'))
        return
      }
      
      const requestId = generateRequestId()
      const message = {
        op: operation,
        id: requestId,
        ...params
      }
      
      // 存储Promise的resolve/reject
      pendingRequests.value.set(requestId, { resolve, reject })
      
      // 设置超时
      setTimeout(() => {
        if (pendingRequests.value.has(requestId)) {
          pendingRequests.value.delete(requestId)
          reject(new Error(`Request timeout: ${operation}`))
        }
      }, 10000) // 10秒超时
      
      if (!sendMessage(message)) {
        pendingRequests.value.delete(requestId)
        reject(new Error(`Failed to send message: ${operation}`))
      }
    })
  }
  
  // 处理主题消息
  const handleTopicMessage = (topic, message) => {
    const handlers = messageHandlers.value.get(topic)

    // 减少详细日志输出，只保留关键信息
    console.debug(`[ConnectionStore] 🎯 处理主题消息: ${topic}`)

    if (handlers && handlers.size > 0) {
      let handlerIndex = 0
      handlers.forEach(handler => {
        try {
          handlerIndex++
          handler(message)
          // 只在出错时输出详细信息
        } catch (error) {
          console.error(`[ConnectionStore] - ❌ 处理器 #${handlerIndex} 执行失败:`, error)
          console.error(`[ConnectionStore] - 消息内容:`, message)
        }
      })
    } else {
      console.warn(`[ConnectionStore] ⚠️ 主题 ${topic} 没有注册处理器`)
      console.warn(`[ConnectionStore] - 所有已注册的处理器:`)
      messageHandlers.value.forEach((handlerSet, handlerTopic) => {
        console.warn(`  - ${handlerTopic}: ${handlerSet.size} handlers`)
      })
    }
  }
  
  // 清理待处理请求（连接关闭时）
  const clearPendingRequests = () => {
    pendingRequests.value.forEach(({ reject }, requestId) => {
      reject(new Error('Connection closed'))
    })
    pendingRequests.value.clear()
  }
  
  // 订阅主题
  const subscribeTopic = (topic, messageType, handler) => {
    console.log(`[ConnectionStore] 🔔 subscribeTopic called: topic=${topic}, type=${messageType}, connected=${isConnected.value}`)

    if (!isConnected.value) {
      console.warn('[ConnectionStore] ❌ Not connected to ROS')
      return false
    }

    // 添加消息处理器
    if (!messageHandlers.value.has(topic)) {
      messageHandlers.value.set(topic, new Set())
    }
    messageHandlers.value.get(topic).add(handler)
    console.log(`[ConnectionStore] ✅ Added handler for ${topic}, total handlers: ${messageHandlers.value.get(topic).size}`)

    // 如果还没有订阅这个主题，发送订阅请求
    if (!subscribedTopics.value.has(topic)) {
      const subscribeMsg = {
        op: 'subscribe',
        topic: topic,
        type: messageType
      }

      console.log(`[ConnectionStore] 📤 Sending subscription request:`, subscribeMsg)

      if (sendMessage(subscribeMsg)) {
        subscribedTopics.value.add(topic)
        console.log(`[ConnectionStore] ✅ Subscribed to ${topic}`)
        console.log(`[ConnectionStore] 📊 Current subscriptions: ${Array.from(subscribedTopics.value)}`)
        return true
      } else {
        console.error(`[ConnectionStore] ❌ Failed to send subscription message for ${topic}`)
        return false
      }
    } else {
      console.log(`[ConnectionStore] 📝 Already subscribed to ${topic}`)
      return true
    }
  }
  
  // 取消订阅主题
  const unsubscribeTopic = (topic, handler) => {
    // 移除消息处理器
    const handlers = messageHandlers.value.get(topic)
    if (handlers) {
      handlers.delete(handler)
      
      // 如果没有处理器了，取消订阅
      if (handlers.size === 0) {
        messageHandlers.value.delete(topic)
        subscribedTopics.value.delete(topic)
        
        if (isConnected.value) {
          const unsubscribeMsg = {
            op: 'unsubscribe',
            topic: topic
          }
          sendMessage(unsubscribeMsg)
          console.log(`Unsubscribed from ${topic}`)
        }
      }
    }
  }
  
  // 已声明的发布者
  const advertisedTopics = ref(new Set())

  // 声明发布者
  const advertise = (topic, messageType) => {
    if (!isConnected.value) {
      console.warn('Not connected to ROS')
      return false
    }

    if (advertisedTopics.value.has(topic)) {
      console.log(`[ConnectionStore] 话题 ${topic} 已经声明过发布者`)
      return true
    }

    const advertiseMsg = {
      op: 'advertise',
      topic: topic,
      type: messageType
    }

    console.log(`[ConnectionStore] 声明发布者:`, advertiseMsg)
    const result = sendMessage(advertiseMsg)
    if (result) {
      advertisedTopics.value.add(topic)
      console.log(`[ConnectionStore] ✅ 成功声明发布者: ${topic}`)
    } else {
      console.error(`[ConnectionStore] ❌ 声明发布者失败: ${topic}`)
    }
    return result
  }

  // 取消声明发布者
  const unadvertise = (topic) => {
    if (!isConnected.value) {
      return false
    }

    const unadvertiseMsg = {
      op: 'unadvertise',
      topic: topic
    }

    console.log(`[ConnectionStore] 取消声明发布者: ${topic}`)
    const result = sendMessage(unadvertiseMsg)
    if (result) {
      advertisedTopics.value.delete(topic)
      console.log(`[ConnectionStore] ✅ 成功取消声明发布者: ${topic}`)
    }
    return result
  }

  // 发布消息到主题
  const publishMessage = (topic, messageType, message) => {
    if (!isConnected.value) {
      console.warn('[ConnectionStore] Not connected to ROS')
      return false
    }

    // 自动声明发布者（如果尚未声明）
    if (!advertisedTopics.value.has(topic)) {
      console.log(`[ConnectionStore] 自动声明发布者: ${topic}`)
      if (!advertise(topic, messageType)) {
        console.error(`[ConnectionStore] ❌ 无法声明发布者: ${topic}`)
        return false
      }
    }

    const publishMsg = {
      op: 'publish',
      topic: topic,
      type: messageType,
      msg: message
    }

    console.log(`[ConnectionStore] 发布消息:`, publishMsg)
    const result = sendMessage(publishMsg)
    console.log(`[ConnectionStore] 发布结果: ${result}`)
    return result
  }
  
  // ROS API 方法 - 返回Promise
  
  // 获取主题列表
  const getTopics = async () => {
    try {
      const topics = await sendApiRequest('get_topics')
      console.log('获取到主题列表:', topics)
      return topics
    } catch (error) {
      console.error('获取主题列表失败:', error)
      return []
    }
  }
  
  // 获取节点列表
  const getNodes = async () => {
    try {
      const nodes = await sendApiRequest('get_nodes')
      console.log('获取到节点列表:', nodes)
      return nodes
    } catch (error) {
      console.error('获取节点列表失败:', error)
      return []
    }
  }
  
  // 获取主题类型映射
  const getTopicTypes = async () => {
    try {
      const topicTypes = await sendApiRequest('get_topic_types')
      console.log('获取到主题类型:', topicTypes)
      return topicTypes
    } catch (error) {
      console.error('获取主题类型失败:', error)
      return {}
    }
  }
  
  // 获取主题频率信息
  const getTopicFrequencies = async () => {
    try {
      const frequencies = await sendApiRequest('get_topic_frequencies')
      console.log('获取到主题频率:', frequencies)
      return frequencies
    } catch (error) {
      console.error('获取主题频率失败:', error)
      return {}
    }
  }
  
  // 获取服务列表
  const getServices = async () => {
    try {
      const services = await sendApiRequest('get_services')
      console.log('获取到服务列表:', services)
      return services
    } catch (error) {
      console.error('获取服务列表失败:', error)
      return []
    }
  }
  
  // 获取服务类型映射
  const getServiceTypes = async () => {
    try {
      const serviceTypes = await sendApiRequest('get_service_types')
      console.log('获取到服务类型:', serviceTypes)
      return serviceTypes
    } catch (error) {
      console.error('获取服务类型失败:', error)
      return {}
    }
  }
  
  // 获取参数列表
  const getParams = async () => {
    try {
      const params = await sendApiRequest('get_params')
      console.log('获取到参数列表:', params)
      return params
    } catch (error) {
      console.error('获取参数列表失败:', error)
      return []
    }
  }
  
  return {
    // 状态
    isConnected,
    isConnecting,
    connectionError,
    connectionStatus,
    connectionStatusText,
    subscribedTopics: computed(() => Array.from(subscribedTopics.value)),
    
    // 配置
    wsUrl,
    maxReconnectAttempts,
    reconnectInterval,
    
    // 方法
    initializeConnection,
    connect,
    disconnect,
    sendMessage,
    subscribeTopic,
    unsubscribeTopic,
    advertise,
    unadvertise,
    publishMessage,
    
    // ROS API方法
    getTopics,
    getNodes,
    getTopicTypes,
    getTopicFrequencies,
    getServices,
    getServiceTypes,
    getParams
  }
})
