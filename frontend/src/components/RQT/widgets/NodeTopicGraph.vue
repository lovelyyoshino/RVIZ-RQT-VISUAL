<template>
  <div class="hierarchical-node-graph">
    <!-- 工具栏 -->
    <div class="graph-toolbar">
      <div class="toolbar-left">
        <h4>ROS通信拓扑图</h4>
        <el-button @click="refreshGraph" :loading="loading" size="small" type="primary">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
        <el-button @click="resetView" size="small">
          <el-icon><Aim /></el-icon>
          重置视图
        </el-button>
      </div>
      
      <div class="toolbar-right">
        <el-input
          v-model="filterText"
          placeholder="过滤节点/主题"
          size="small"
          style="width: 180px;"
          clearable>
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        
        <el-tooltip content="布局算法">
          <el-select v-model="layoutType" size="small" style="width: 120px;" @change="applyLayout">
            <el-option label="分层布局" value="hierarchical" />
            <el-option label="力导向" value="force" />
            <el-option label="环形布局" value="circular" />
          </el-select>
        </el-tooltip>
        
        <el-tooltip content="显示设置">
          <el-popover placement="bottom" :width="240" trigger="click">
            <template #reference>
              <el-button size="small">
                <el-icon><Setting /></el-icon>
              </el-button>
            </template>
            
            <div class="display-settings">
              <div class="setting-item">
                <span>显示未连接节点</span>
                <el-switch v-model="showIsolatedNodes" size="small" />
              </div>
              <div class="setting-item">
                <span>显示连接动画</span>
                <el-switch v-model="enableAnimation" size="small" />
              </div>
              <div class="setting-item">
                <span>节点标签显示</span>
                <el-select v-model="labelMode" size="small" style="width: 100%;">
                  <el-option label="完整名称" value="full" />
                  <el-option label="简短名称" value="short" />
                  <el-option label="隐藏标签" value="none" />
                </el-select>
              </div>
            </div>
          </el-popover>
        </el-tooltip>
      </div>
    </div>

    <!-- 图形显示区域 -->
    <div class="graph-container" ref="graphContainer">
      <div class="zoom-controls">
        <el-button-group size="small">
          <el-button @click="zoomIn">
            <el-icon><Plus /></el-icon>
          </el-button>
          <el-button @click="zoomOut">
            <el-icon><Minus /></el-icon>
          </el-button>
          <el-button @click="resetView">
            <el-icon><Refresh /></el-icon>
          </el-button>
        </el-button-group>
        <div class="zoom-level">{{ Math.round(currentZoom * 100) }}%</div>
      </div>
      
      <svg 
        ref="svgRef" 
        class="rqt-topology-svg" 
        width="100%" 
        height="100%"
      >
        <g 
          class="graph-content" 
          :transform="`translate(${transform.translateX}, ${transform.translateY}) scale(${transform.scale})`"
        >
        <!-- SVG定义 -->
        <defs>
          <!-- RQT风格箭头 -->
          <marker id="publish-arrow" markerWidth="10" markerHeight="6" 
            refX="9" refY="3" orient="auto" markerUnits="strokeWidth">
            <path d="M0,0 L0,6 L9,3 z" fill="#2c5aa0" />
          </marker>
          
          <marker id="subscribe-arrow" markerWidth="10" markerHeight="6" 
            refX="9" refY="3" orient="auto" markerUnits="strokeWidth">
            <path d="M0,0 L0,6 L9,3 z" fill="#48bb78" />
          </marker>
          
          <!-- 节点阴影滤镜 -->
          <filter id="node-shadow" x="-50%" y="-50%" width="200%" height="200%">
            <feDropShadow dx="2" dy="2" stdDeviation="3" flood-color="rgba(0,0,0,0.3)"/>
          </filter>
          
          <!-- 选中效果滤镜 -->
          <filter id="selected-glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
            <feMerge> 
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>
        
        <!-- 连接线层 -->
        <g class="connections-layer">
          <path
            v-for="connection in filteredConnections"
            :key="connection.id"
            :d="connection.path"
            :class="getConnectionClass(connection)"
            :marker-end="getConnectionMarker(connection)"
            :stroke="getConnectionColor(connection)"
            :stroke-width="getConnectionWidth(connection)"
            :opacity="connection.opacity || 0.7"
            @click="onConnectionClick(connection)"
          >
            <title>{{ getConnectionTooltip(connection) }}</title>
            
            <!-- 数据流动画 -->
            <animate 
              v-if="enableAnimation && connection.type === 'publisher'"
              attributeName="stroke-dashoffset"
              values="0;20"
              dur="2s"
              repeatCount="indefinite"
            />
          </path>
        </g>
        
        <!-- ROS节点层 -->
        <g class="nodes-layer">
          <g
            v-for="node in filteredNodes"
            :key="node.id"
            :class="getNodeClass(node)"
            :transform="`translate(${node.x}, ${node.y})`"
            @click="onNodeClick(node)"
            @contextmenu.prevent="showNodeMenu(node, $event)"
          >
            <!-- 节点形状 (椭圆，类似RQT) -->
            <ellipse
              :rx="node.style.width / 2"
              :ry="node.style.height / 2"
              :fill="node.style.fill"
              :stroke="getNodeStroke(node)"
              :stroke-width="getNodeStrokeWidth(node)"
              :filter="node.selected ? 'url(#selected-glow)' : 'url(#node-shadow)'"
              :opacity="0.9"
            />
            
            <!-- 节点标签 -->
            <text
              v-if="labelMode !== 'none'"
              y="4"
              text-anchor="middle"
              :fill="node.style.textColor"
              :font-size="getNodeFontSize(node)"
              font-weight="500"
              font-family="Arial, sans-serif"
            >
              {{ getNodeLabel(node) }}
            </text>
            
            <!-- 节点统计信息 -->
            <text
              v-if="node.type === 'node' && (node.publishers.length > 0 || node.subscribers.length > 0)"
              y="16"
              text-anchor="middle"
              fill="#94a3b8"
              font-size="9"
            >
              ↑{{ node.publishers.length }} ↓{{ node.subscribers.length }}
            </text>
          </g>
        </g>
        
        <!-- 主题节点层 -->
        <g class="topics-layer">
          <g
            v-for="topic in filteredTopics"
            :key="topic.id"
            :class="getTopicClass(topic)"
            :transform="`translate(${topic.x}, ${topic.y})`"
            @click="onTopicClick(topic)"
            @contextmenu.prevent="showTopicMenu(topic, $event)"
          >
            <!-- 主题形状 (矩形，类似RQT) -->
            <rect
              :x="-(topic.style.width / 2)"
              :y="-(topic.style.height / 2)"
              :width="topic.style.width"
              :height="topic.style.height"
              :rx="4"
              :ry="4"
              :fill="topic.style.fill"
              :stroke="getTopicStroke(topic)"
              :stroke-width="getTopicStrokeWidth(topic)"
              :filter="topic.selected ? 'url(#selected-glow)' : 'url(#node-shadow)'"
              :opacity="0.85"
            />
            
            <!-- 主题标签 -->
            <text
              v-if="labelMode !== 'none'"
              y="4"
              text-anchor="middle"
              :fill="topic.style.textColor"
              :font-size="getTopicFontSize(topic)"
              font-weight="400"
              font-family="Arial, sans-serif"
            >
              {{ getTopicLabel(topic) }}
            </text>
            
            <!-- 消息类型提示 -->
            <title>{{ topic.name }} ({{ topic.messageType }})</title>
          </g>
        </g>
        </g>
      </svg>
    </div>

    <!-- 右键菜单 -->
    <div
      v-show="contextMenu.visible"
      class="context-menu"
      :style="{ left: contextMenu.x + 'px', top: contextMenu.y + 'px' }"
    >
      <div
        v-for="action in contextMenu.actions"
        :key="action.key"
        class="menu-item"
        @click="executeAction(action)"
      >
        <el-icon v-if="action.icon">
          <component :is="action.icon" />
        </el-icon>
        {{ action.label }}
      </div>
    </div>
  </div>
</template>

<script>
/**
 * 分层ROS节点-主题关系图组件
 * 
 * 实现类似RQT Node Graph的可视化效果：
 * - 分层布局算法
 * - 拖拽和缩放交互  
 * - 椭圆节点和矩形主题
 * - 实时数据连接
 * 
 * @author ROS Web Viz Team
 * @version 2.0.0
 */
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { Refresh, Search, Setting, Aim, Plus, Minus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useRosbridge } from '../../../composables/useRosbridge'
import { createHierarchicalLayout } from '../utils/GraphLayout.js'
import { GraphInteractionController } from '../utils/GraphInteraction.js'

export default {
  name: 'HierarchicalNodeGraph',
  components: {
    Refresh, Search, Setting, Aim, Plus, Minus
  },
  emits: ['topic-subscribe', 'topic-unsubscribe', 'topic-visualize', 'node-select'],
  
  setup(props, { emit }) {
    // ===== 核心依赖 =====
    const rosbridge = useRosbridge()
    
    // ===== DOM引用 =====
    const svgRef = ref(null)
    const graphContainer = ref(null)
    
    // ===== 基础状态 =====
    const loading = ref(false)
    const filterText = ref('')
    const layoutType = ref('hierarchical')
    const showIsolatedNodes = ref(true)
    const enableAnimation = ref(true)
    const labelMode = ref('short')
    
    // ===== 图形数据 =====
    const rawNodes = ref([])
    const rawTopics = ref([])
    const connections = ref([])
    
    // ===== 布局和交互控制器 =====
    const layoutEngine = ref(null)
    const interactionController = ref(null)
    
    // ===== 视图变换状态 =====
    const transform = ref({
      translateX: 0,
      translateY: 0,
      scale: 1.0
    })
    const hasInitialTransform = ref(false)
    
    // ===== 选中状态 =====
    const selectedNodeId = ref(null)
    const selectedTopicId = ref(null)
    
    // ===== 右键菜单 =====
    const contextMenu = ref({
      visible: false,
      x: 0,
      y: 0,
      actions: []
    })
    
    // ===== 计算属性 =====
    const currentZoom = computed(() => transform.value.scale)
    
    const filteredNodes = computed(() => {
      let nodes = rawNodes.value
      
      // 应用过滤器
      if (filterText.value) {
        const filter = filterText.value.toLowerCase()
        nodes = nodes.filter(node => 
          node.name.toLowerCase().includes(filter)
        )
      }
      
      // 调试：输出所有节点的订阅信息
      if (!showIsolatedNodes.value) {
        console.log('=== 节点过滤调试信息 ===')
        nodes.forEach(node => {
          console.log(`节点 ${node.name}:`, {
            publishers: node.publishers?.length || 0,
            subscribers: node.subscribers?.length || 0,
            publisherList: node.publishers || [],
            subscriberList: node.subscribers || []
          })
        })
        
        // 暂时使用宽松的过滤条件
        const beforeFilter = nodes.length
        nodes = nodes.filter(node => {
          // 有发布者或有订阅者的节点都保留
          const hasPublishers = node.publishers && node.publishers.length > 0
          const hasSubscribers = node.subscribers && node.subscribers.length > 0
          const keep = hasPublishers || hasSubscribers
          
          if (!keep) {
            console.log(`过滤掉节点 ${node.name}: 无发布者且无订阅者`)
          }
          return keep
        })
        console.log(`节点过滤：${beforeFilter} -> ${nodes.length}`)
      }
      
      return nodes
    })
    
    const filteredTopics = computed(() => {
      let topics = rawTopics.value
      
      // 应用过滤器
      if (filterText.value) {
        const filter = filterText.value.toLowerCase()
        topics = topics.filter(topic => 
          topic.name.toLowerCase().includes(filter) ||
          topic.messageType.toLowerCase().includes(filter)
        )
      }
      
      // 是否显示孤立主题（没有发布者和订阅者的主题被省略）
      if (!showIsolatedNodes.value) {
        const beforeFilter = topics.length
        topics = topics.filter(topic => {
          const hasConnections = (topic.publishers && topic.publishers.length > 0) || 
                                (topic.subscribers && topic.subscribers.length > 0)
          console.log(`主题 ${topic.name}: publishers=${topic.publishers?.length || 0}, subscribers=${topic.subscribers?.length || 0}, hasConnections=${hasConnections}`)
          return hasConnections
        })
        console.log(`主题过滤：${beforeFilter} -> ${topics.length}`)
      }
      
      return topics
    })
    
    const filteredConnections = computed(() => {
      // 计算可见节点和主题的连接
      const visibleNodeIds = new Set(filteredNodes.value.map(n => n.id))
      const visibleTopicIds = new Set(filteredTopics.value.map(t => t.id))
      
      return connections.value.filter(conn => 
        (visibleNodeIds.has(conn.from) || visibleTopicIds.has(conn.from)) &&
        (visibleNodeIds.has(conn.to) || visibleTopicIds.has(conn.to))
      )
    })
    
    // ===== 核心方法 =====
    
    /**
     * 刷新图形数据
     */
    const refreshGraph = async () => {
      if (loading.value) return
      
      loading.value = true
      try {
        console.log('刷新ROS通信拓扑图...')
        
        // 并行获取所有数据
        const [nodeList, topicList, topicTypes] = await Promise.all([
          rosbridge.getNodes(),
          rosbridge.getTopics(),
          rosbridge.getTopicTypes()
        ])
        
        console.log(`获取到 ${nodeList.length} 个节点, ${topicList.length} 个主题`)
        
        // 调试：输出一些节点数据
        if (nodeList.length > 0) {
          const sampleNode = nodeList[0]
          console.log('样本节点数据:', sampleNode)
        }
        
        // 调试：输出主题数据
        if (topicList.length > 0) {
          const sampleTopic = topicList[0]
          console.log('样本主题数据:', sampleTopic)
        }
        
        // 处理节点数据
        rawNodes.value = nodeList.map((nodeInfo, index) => {
          const nodeName = typeof nodeInfo === 'string' ? nodeInfo : nodeInfo.name
          return {
            id: `node_${index}`,
            name: nodeName,
            label: nodeName.split('/').pop() || nodeName,
            type: 'node',
            publishers: typeof nodeInfo === 'object' ? (nodeInfo.publishers || []) : [],
            subscribers: typeof nodeInfo === 'object' ? (nodeInfo.subscribers || []) : [],
            services: typeof nodeInfo === 'object' ? (nodeInfo.services || []) : [],
            x: 0,
            y: 0,
            selected: false,
            style: {
              width: 100,
              height: 50,
              fill: '#2c5aa0',
              stroke: '#1a365d',
              strokeWidth: 2,
              textColor: '#ffffff'
            }
          }
        })
        
        // 处理主题数据
        rawTopics.value = topicList.map((topicInfo, index) => {
          const topicName = typeof topicInfo === 'string' ? topicInfo : topicInfo.name
          const messageType = topicTypes[topicName] || 'unknown'
          
          return {
            id: `topic_${index}`,
            name: topicName,
            label: topicName.split('/').pop() || topicName,
            type: 'topic',
            messageType: messageType,
            publishers: typeof topicInfo === 'object' ? (topicInfo.publishers || []) : [],
            subscribers: typeof topicInfo === 'object' ? (topicInfo.subscribers || []) : [],
            x: 0,
            y: 0,
            selected: false,
            style: {
              width: 120,
              height: 30,
              fill: getTopicColor(messageType),
              stroke: '#2f855a',
              strokeWidth: 1,
              textColor: '#ffffff'
            }
          }
        })
        
        // 应用布局
        await nextTick()
        applyLayout()
        
        ElMessage.success(`加载了 ${rawNodes.value.length} 个节点和 ${rawTopics.value.length} 个主题`)
        
      } catch (error) {
        console.error('刷新图形失败:', error)
        ElMessage.error('刷新图形失败: ' + error.message)
      } finally {
        loading.value = false
      }
    }
    
    /**
     * 应用布局算法
     */
    const applyLayout = () => {
      if (!layoutEngine.value) return
      
      console.log(`应用 ${layoutType.value} 布局算法`)
      
      // 更新容器尺寸
      updateLayoutSize()
      
      // 设置布局数据
      const allNodes = [...rawNodes.value, ...rawTopics.value]
      layoutEngine.value.setData(allNodes, connections.value)
      
      // 执行布局
      let layoutNodes = []
      if (layoutType.value === 'hierarchical') {
        layoutNodes = layoutEngine.value.applyHierarchicalLayout()
      } else if (layoutType.value === 'force') {
        layoutNodes = layoutEngine.value.applyForceDirectedOptimization(allNodes)
      } else if (layoutType.value === 'circular') {
        layoutNodes = layoutEngine.value.applyCircularLayout()
      }
      
      // 更新节点位置
      layoutNodes.forEach(layoutNode => {
        if (layoutNode.type === 'node') {
          const node = rawNodes.value.find(n => n.id === layoutNode.id)
          if (node) {
            node.x = layoutNode.x
            node.y = layoutNode.y
            node.style = layoutNode.style || node.style
          }
        } else if (layoutNode.type === 'topic') {
          const topic = rawTopics.value.find(t => t.id === layoutNode.id)
          if (topic) {
            topic.x = layoutNode.x
            topic.y = layoutNode.y
            topic.style = layoutNode.style || topic.style
          }
        }
      })
      
      // 重新计算连接
      calculateConnections()
      
      // 只在初次加载时应用推荐变换，避免跳动
      if (!hasInitialTransform.value) {
        nextTick(() => {
          applyRecommendedTransform()
          hasInitialTransform.value = true
        })
      }
    }
    
    /**
     * 计算连接关系
     */
    const calculateConnections = () => {
      const newConnections = []
      
      // 遍历所有节点，建立与主题的连接
      rawNodes.value.forEach(node => {
        // 发布者连接 (node -> topic)
        node.publishers.forEach(topicName => {
          const topic = rawTopics.value.find(t => t.name === topicName)
          if (topic) {
            newConnections.push({
              id: `${node.id}_pub_${topic.id}`,
              from: node.id,
              to: topic.id,
              type: 'publisher',
              topicName: topicName,
              path: `M${node.x},${node.y} L${topic.x},${topic.y}`,
              opacity: 0.7
            })
          }
        })
        
        // 订阅者连接 (topic -> node)
        node.subscribers.forEach(topicName => {
          const topic = rawTopics.value.find(t => t.name === topicName)
          if (topic) {
            newConnections.push({
              id: `${topic.id}_sub_${node.id}`,
              from: topic.id,
              to: node.id,
              type: 'subscriber',
              topicName: topicName,
              path: `M${topic.x},${topic.y} L${node.x},${node.y}`,
              opacity: 0.5
            })
          }
        })
      })
      
      connections.value = newConnections
      console.log(`计算了 ${newConnections.length} 个连接`)
    }
    
    /**
     * 获取主题颜色
     * @param {string} messageType - 消息类型
     * @returns {string} 颜色
     */
    const getTopicColor = (messageType) => {
      const colorMap = {
        'sensor_msgs/msg/PointCloud2': '#e74c3c',
        'sensor_msgs/msg/LaserScan': '#f39c12',
        'nav_msgs/msg/OccupancyGrid': '#9b59b6',
        'geometry_msgs/msg/Twist': '#3498db',
        'nav_msgs/msg/Odometry': '#1abc9c',
        'sensor_msgs/msg/Image': '#e67e22',
        'tf2_msgs/msg/TFMessage': '#34495e'
      }
      
      return colorMap[messageType] || '#48bb78'
    }
    
    // ===== 交互事件处理 =====
    
    /**
     * 节点点击事件
     */
    const onNodeClick = (node) => {
      selectedNodeId.value = node.id
      selectedTopicId.value = null
      
      // 更新节点选中状态
      rawNodes.value.forEach(n => n.selected = (n.id === node.id))
      rawTopics.value.forEach(t => t.selected = false)
      
      emit('node-select', node)
      console.log('选中节点:', node.name)
    }
    
    /**
     * 主题点击事件
     */
    const onTopicClick = (topic) => {
      selectedTopicId.value = topic.id
      selectedNodeId.value = null
      
      // 更新主题选中状态
      rawTopics.value.forEach(t => t.selected = (t.id === topic.id))
      rawNodes.value.forEach(n => n.selected = false)
      
      console.log('选中主题:', topic.name)
    }
    
    /**
     * 连接点击事件
     */
    const onConnectionClick = (connection) => {
      console.log('选中连接:', connection.topicName)
    }
    
    /**
     * 显示节点菜单
     */
    const showNodeMenu = (node, event) => {
      contextMenu.value = {
        visible: true,
        x: event.clientX,
        y: event.clientY,
        actions: [
          {
            key: 'inspect',
            label: '检查节点',
            icon: 'View',
            handler: () => inspectNode(node)
          }
        ]
      }
    }
    
    /**
     * 显示主题菜单
     */
    const showTopicMenu = (topic, event) => {
      contextMenu.value = {
        visible: true,
        x: event.clientX,
        y: event.clientY,
        actions: [
          {
            key: 'subscribe',
            label: '订阅主题',
            icon: 'Plus',
            handler: () => subscribeTopic(topic)
          },
          {
            key: 'visualize',
            label: '可视化',
            icon: 'View',
            handler: () => visualizeTopic(topic)
          }
        ]
      }
    }
    
    // ===== 样式和渲染方法 =====
    
    const getNodeClass = (node) => {
      return {
        'rqt-node': true,
        'selected': node.selected,
        'active': true
      }
    }
    
    const getTopicClass = (topic) => {
      return {
        'rqt-topic': true,
        'selected': topic.selected,
        'active': true
      }
    }
    
    const getConnectionClass = (connection) => {
      return {
        'rqt-connection': true,
        'publisher': connection.type === 'publisher',
        'subscriber': connection.type === 'subscriber'
      }
    }
    
    const getConnectionMarker = (connection) => {
      return connection.type === 'publisher' 
        ? 'url(#publish-arrow)' 
        : 'url(#subscribe-arrow)'
    }
    
    const getConnectionColor = (connection) => {
      return connection.type === 'publisher' ? '#2c5aa0' : '#48bb78'
    }
    
    const getConnectionWidth = (connection) => {
      return connection.type === 'publisher' ? 2 : 1.5
    }
    
    const getConnectionTooltip = (connection) => {
      const type = connection.type === 'publisher' ? '发布到' : '订阅自'
      return `${type}: ${connection.topicName}`
    }
    
    const getNodeStroke = (node) => {
      return node.selected ? '#409eff' : node.style.stroke
    }
    
    const getNodeStrokeWidth = (node) => {
      return node.selected ? 3 : node.style.strokeWidth
    }
    
    const getTopicStroke = (topic) => {
      return topic.selected ? '#409eff' : topic.style.stroke
    }
    
    const getTopicStrokeWidth = (topic) => {
      return topic.selected ? 3 : topic.style.strokeWidth
    }
    
    const getNodeLabel = (node) => {
      return labelMode.value === 'full' ? node.name : node.label
    }
    
    const getTopicLabel = (topic) => {
      return labelMode.value === 'full' ? topic.name : topic.label
    }
    
    const getNodeFontSize = (node) => {
      return 12
    }
    
    const getTopicFontSize = (topic) => {
      return 11
    }
    
    // ===== 缩放和平移控制 =====
    
    const zoomIn = () => {
      if (interactionController.value) {
        interactionController.value.zoomIn()
      }
    }
    
    const zoomOut = () => {
      if (interactionController.value) {
        interactionController.value.zoomOut()
      }
    }
    
    const resetView = () => {
      if (layoutEngine.value && interactionController.value) {
        // 强制重新应用推荐变换
        hasInitialTransform.value = false
        nextTick(() => {
          applyRecommendedTransform()
          hasInitialTransform.value = true
        })
      } else if (interactionController.value) {
        interactionController.value.resetZoom()
      }
    }
    
    /**
     * 更新布局容器尺寸
     */
    const updateLayoutSize = () => {
      if (!layoutEngine.value || !graphContainer.value) return
      
      const rect = graphContainer.value.getBoundingClientRect()
      const width = Math.max(800, rect.width)
      const height = Math.max(600, rect.height)
      
      layoutEngine.value.updateConfig({
        width,
        height
      })
      
      console.log(`更新布局尺寸: ${width} x ${height}`)
    }
    
    /**
     * 应用推荐的变换参数
     */
    const applyRecommendedTransform = () => {
      if (!layoutEngine.value || !interactionController.value) return
      
      const recommendedTransform = layoutEngine.value.getRecommendedTransform()
      
      // 应用推荐的变换
      transform.value = { ...recommendedTransform }
      
      // 同时更新交互控制器的状态
      if (interactionController.value.setTransform) {
        interactionController.value.setTransform(recommendedTransform)
      }
      
      console.log('应用推荐变换:', recommendedTransform)
    }
    
    // ===== 菜单操作 =====
    
    const executeAction = (action) => {
      contextMenu.value.visible = false
      if (action.handler) {
        action.handler()
      }
    }
    
    const subscribeTopic = (topic) => {
      emit('topic-subscribe', topic.name, topic.messageType)
    }
    
    const visualizeTopic = (topic) => {
      emit('topic-visualize', topic.name, topic.messageType)
    }
    
    const inspectNode = (node) => {
      console.log('检查节点:', node)
    }
    
    // ===== 生命周期 =====
    
    onMounted(async () => {
      console.log('分层节点图组件挂载')
      
      // 获取容器尺寸
      await nextTick()
      const rect = graphContainer.value?.getBoundingClientRect() || { width: 800, height: 600 }
      const initialWidth = Math.max(800, rect.width)
      const initialHeight = Math.max(600, rect.height)
      
      // 初始化布局引擎
      layoutEngine.value = createHierarchicalLayout({
        width: initialWidth,
        height: initialHeight,
        nodeSpacing: 120,
        levelSpacing: 200,
        enablePhysics: true,
        autoScale: true,
        padding: 60
      })
      
      // 初始化交互控制器
      if (graphContainer.value) {
        interactionController.value = new GraphInteractionController(
          graphContainer.value, 
          {
            enablePan: true,
            enableZoom: true,
            enableDrag: true,
            minScale: 0.1,
            maxScale: 5.0
          }
        )
        
        // 监听变换事件
        graphContainer.value.addEventListener('graph-transformUpdate', (event) => {
          transform.value = { ...event.detail }
        })
        
        // 监听平移事件以确保拖拽功能正常工作
        graphContainer.value.addEventListener('graph-mousemove', (event) => {
          // 确保平移时光标正确显示
          if (interactionController.value.getState().isPanning) {
            graphContainer.value.style.cursor = 'move'
          }
        })
        
        // 监听鼠标释放事件
        graphContainer.value.addEventListener('graph-mouseup', (event) => {
          graphContainer.value.style.cursor = 'default'
        })
        
        // 设置节点命中测试
        interactionController.value.setNodeHitTest((x, y) => {
          // 简单的命中测试实现
          const node = filteredNodes.value.find(n => {
            const dx = x - n.x
            const dy = y - n.y
            const rx = n.style.width / 2
            const ry = n.style.height / 2
            return (dx * dx) / (rx * rx) + (dy * dy) / (ry * ry) <= 1
          })
          
          const topic = filteredTopics.value.find(t => {
            const dx = x - t.x
            const dy = y - t.y
            return Math.abs(dx) <= t.style.width / 2 && Math.abs(dy) <= t.style.height / 2
          })
          
          return node?.id || topic?.id || null
        })
      }
      
      // 添加窗口大小变化监听器（防抖处理避免频繁重布局）
      let resizeTimeout = null
      const handleResize = () => {
        if (resizeTimeout) {
          clearTimeout(resizeTimeout)
        }
        resizeTimeout = setTimeout(() => {
          updateLayoutSize()
          // 窗口大小变化时不重新应用推荐变换，保持当前视图
          applyLayout()
        }, 300)
      }
      
      window.addEventListener('resize', handleResize)
      
      // 保存清理函数
      onUnmounted(() => {
        window.removeEventListener('resize', handleResize)
      })
      
      // 加载初始数据
      await refreshGraph()
    })
    
    onUnmounted(() => {
      if (interactionController.value) {
        interactionController.value.destroy()
      }
      
      // 移除事件监听器
      window.removeEventListener('resize', () => {})
      
      console.log('分层节点图组件卸载')
    })
    
    // ===== 监听器 =====
    
    watch(layoutType, () => {
      applyLayout()
    })
    
    // ===== 返回API =====
    return {
      // DOM引用
      svgRef,
      graphContainer,
      
      // 状态
      loading,
      filterText,
      layoutType,
      showIsolatedNodes,
      enableAnimation,
      labelMode,
      currentZoom,
      transform,
      contextMenu,
      
      // 数据
      filteredNodes,
      filteredTopics,
      filteredConnections,
      
      // 方法
      refreshGraph,
      applyLayout,
      resetView,
      zoomIn,
      zoomOut,
      onNodeClick,
      onTopicClick,
      onConnectionClick,
      showNodeMenu,
      showTopicMenu,
      executeAction,
      
      // 样式方法
      getNodeClass,
      getTopicClass,
      getConnectionClass,
      getConnectionMarker,
      getConnectionColor,
      getConnectionWidth,
      getConnectionTooltip,
      getNodeStroke,
      getNodeStrokeWidth,
      getTopicStroke,
      getTopicStrokeWidth,
      getNodeLabel,
      getTopicLabel,
      getNodeFontSize,
      getTopicFontSize
    }
  }
}
</script>

<style scoped>
/* ===== 主容器样式 ===== */
.hierarchical-node-graph {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 400px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 8px;
  overflow: hidden;
}

/* ===== 工具栏样式 ===== */
.graph-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.toolbar-left h4 {
  margin: 0;
  color: #2c3e50;
  font-weight: 600;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.display-settings {
  padding: 8px;
}

.setting-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
}

.setting-item:last-child {
  border-bottom: none;
}

/* ===== 图形容器样式 ===== */
.graph-container {
  flex: 1;
  position: relative;
  overflow: hidden;
  width: 100%;
  min-height: 500px;
  background: radial-gradient(circle at 50% 50%, rgba(255,255,255,0.05) 0%, transparent 70%);
}

.zoom-controls {
  position: absolute;
  top: 16px;
  right: 16px;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(10px);
  border-radius: 6px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.zoom-level {
  font-size: 12px;
  color: #666;
  min-width: 40px;
  text-align: center;
}

/* ===== SVG样式 ===== */
.rqt-topology-svg {
  width: 100%;
  height: 100%;
  cursor: default;
  user-select: none;
}

.rqt-topology-svg:active {
  cursor: move;
}

.graph-content {
  transition: transform 0.2s ease;
}

/* ===== 连接线样式 ===== */
.rqt-connection {
  fill: none;
  cursor: pointer;
  transition: all 0.3s ease;
}

.rqt-connection:hover {
  opacity: 1 !important;
  stroke-width: 3 !important;
}

.rqt-connection.publisher {
  stroke-dasharray: none;
}

.rqt-connection.subscriber {
  stroke-dasharray: 5,5;
}

/* ===== 节点样式 ===== */
.rqt-node {
  cursor: pointer;
  transition: all 0.3s ease;
}

.rqt-node:hover {
  transform: scale(1.05);
}

.rqt-node.selected {
  filter: url(#selected-glow);
}

/* ===== 主题样式 ===== */
.rqt-topic {
  cursor: pointer;
  transition: all 0.3s ease;
}

.rqt-topic:hover {
  transform: scale(1.05);
}

.rqt-topic.selected {
  filter: url(#selected-glow);
}

/* ===== 右键菜单样式 ===== */
.context-menu {
  position: fixed;
  z-index: 1000;
  background: white;
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  border: 1px solid #e1e5e9;
  min-width: 150px;
  overflow: hidden;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  cursor: pointer;
  font-size: 14px;
  color: #333;
  transition: background-color 0.2s;
}

.menu-item:hover {
  background-color: #f5f7fa;
}

.menu-item:active {
  background-color: #e1e5e9;
}

/* ===== 响应式样式 ===== */
@media (max-width: 768px) {
  .toolbar-right {
    flex-wrap: wrap;
    gap: 4px;
  }
  
  .toolbar-right .el-input {
    width: 140px !important;
  }
  
  .zoom-controls {
    top: 8px;
    right: 8px;
    padding: 6px 8px;
  }
}
</style>