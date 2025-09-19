<template>
  <div class="rqt-professional-graph">
    <!-- RQT风格专业工具栏 -->
    <div class="rqt-toolbar">
      <div class="toolbar-section">
        <h3 class="rqt-title">
          <el-icon class="title-icon"><Grid /></el-icon>
          ROS Node Graph
        </h3>
        <el-button @click="refreshGraph" :loading="loading" size="small" type="primary">
          <el-icon><Refresh /></el-icon>
          Refresh
        </el-button>
      </div>

      <div class="toolbar-section center-section">
        <div class="statistics-display">
          <div class="stat-item">
            <span class="stat-label">Nodes:</span>
            <span class="stat-value">{{ filteredNodes.length }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">Topics:</span>
            <span class="stat-value">{{ filteredTopics.length }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">Connections:</span>
            <span class="stat-value">{{ filteredConnections.length }}</span>
          </div>
        </div>
      </div>

      <div class="toolbar-section">
        <el-button @click="resetView" size="small">
          <el-icon><Aim /></el-icon>
          Reset View
        </el-button>
        <el-button @click="toggleDetailPanel" size="small">
          <el-icon><Document /></el-icon>
          Details
        </el-button>
      </div>
    </div>

    <!-- 三栏式主体布局 -->
    <div class="rqt-main-layout">
      <!-- 左侧控制面板 -->
      <div class="rqt-control-panel" :class="{ 'collapsed': controlPanelCollapsed }">
        <div class="panel-header">
          <h4>Controls</h4>
          <el-button @click="controlPanelCollapsed = !controlPanelCollapsed" size="small" text>
            <el-icon><ArrowLeft v-if="!controlPanelCollapsed" /><ArrowRight v-else /></el-icon>
          </el-button>
        </div>

        <div v-show="!controlPanelCollapsed" class="panel-content">
          <!-- 命名空间过滤 -->
          <div class="control-group">
            <label class="control-label">Namespace</label>
            <el-select v-model="selectedNamespace" size="small" style="width: 100%;" @change="applyFilters">
              <el-option label="All Namespaces" value="" />
              <el-option
                v-for="ns in availableNamespaces"
                :key="ns"
                :label="ns"
                :value="ns"
              />
            </el-select>
          </div>

          <!-- 节点类型过滤 -->
          <div class="control-group">
            <label class="control-label">Show</label>
            <el-radio-group v-model="showType" size="small" @change="applyFilters">
              <el-radio label="all">All</el-radio>
              <el-radio label="nodes">Nodes only</el-radio>
              <el-radio label="topics">Topics only</el-radio>
            </el-radio-group>
          </div>

          <!-- RQT风格复选框 -->
          <div class="control-group">
            <label class="control-label">Options</label>
            <div class="checkbox-list">
              <el-checkbox v-model="hideUnconnected" @change="applyFilters">
                Hide unconnected
              </el-checkbox>
              <el-checkbox v-model="hideSystemNodes" @change="applyFilters">
                Hide system nodes
              </el-checkbox>
              <el-checkbox v-model="hideDeadSinks" @change="applyFilters">
                Hide dead sinks
              </el-checkbox>
              <el-checkbox v-model="hideLeafTopics" @change="applyFilters">
                Hide leaf topics
              </el-checkbox>
              <el-checkbox v-model="hideDebugTopics" @change="applyFilters">
                Hide debug topics
              </el-checkbox>
              <el-checkbox v-model="groupByNamespace" @change="applyLayout">
                Group by namespace
              </el-checkbox>
              <el-checkbox v-model="enableAnimation">
                Enable animations
              </el-checkbox>
            </div>
          </div>

          <!-- 布局控制 -->
          <div class="control-group">
            <label class="control-label">Layout</label>
            <el-select v-model="layoutType" size="small" style="width: 100%;" @change="applyLayout">
              <el-option label="Hierarchical" value="hierarchical" />
              <el-option label="Circular" value="circular" />
            </el-select>
          </div>

          <!-- 搜索过滤 -->
          <div class="control-group">
            <label class="control-label">Filter</label>
            <el-input
              v-model="filterText"
              placeholder="Search nodes/topics..."
              size="small"
              clearable>
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
          </div>
        </div>
      </div>

      <!-- 中央图形区域 -->
      <div class="rqt-graph-area">

        <div class="graph-container" ref="graphContainer">
          <!-- 缩放控制 -->
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

          <!-- SVG图形 -->
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
                <marker id="arrow" markerWidth="10" markerHeight="10"
                  refX="8" refY="5" orient="auto" markerUnits="strokeWidth">
                  <path d="M0,2 L0,8 L8,5 z" fill="#444444" />
                </marker>

                <!-- 节点阴影 -->
                <filter id="node-shadow" x="-50%" y="-50%" width="200%" height="200%">
                  <feDropShadow dx="1" dy="1" stdDeviation="2" flood-color="rgba(0,0,0,0.25)"/>
                </filter>

                <!-- 选中效果 -->
                <filter id="selected-glow" x="-50%" y="-50%" width="200%" height="200%">
                  <feDropShadow dx="0" dy="0" stdDeviation="3" flood-color="#1890ff"/>
                </filter>
              </defs>

              <!-- 连接线层 -->
              <g class="connections-layer">
                <path
                  v-for="connection in filteredConnections"
                  :key="connection.id"
                  :d="connection.path"
                  :class="getConnectionClass(connection)"
                  marker-end="url(#arrow)"
                  stroke="#444444"
                  :stroke-width="connection.selected ? 2 : 1"
                  :opacity="connection.opacity || 0.7"
                  fill="none"
                  @click="onConnectionClick(connection)"
                  @mouseenter="onConnectionHover(connection, $event)"
                  @mouseleave="onConnectionLeave(connection)"
                />
              </g>

              <!-- 节点层 -->
              <g class="nodes-layer">
                <g
                  v-for="node in filteredNodes"
                  :key="node.id"
                  :class="getNodeClass(node)"
                  :transform="`translate(${node.x}, ${node.y})`"
                  @click="onNodeClick(node)"
                  @mouseenter="onNodeHover(node, $event)"
                  @mouseleave="onNodeLeave(node)"
                >
                  <!-- 椭圆节点 -->
                  <ellipse
                    :rx="node.style.width / 2"
                    :ry="node.style.height / 2"
                    :fill="node.style.fill"
                    :stroke="getNodeStroke(node)"
                    :stroke-width="getNodeStrokeWidth(node)"
                    :filter="node.selected ? 'url(#selected-glow)' : 'url(#node-shadow)'"
                  />

                  <!-- 节点标签 -->
                  <text
                    y="3"
                    text-anchor="middle"
                    :fill="node.style.textColor"
                    font-size="11"
                    font-weight="500"
                    font-family="system-ui, sans-serif"
                  >
                    {{ getNodeLabel(node) }}
                  </text>
                </g>
              </g>

              <!-- 主题层 -->
              <g class="topics-layer">
                <g
                  v-for="topic in filteredTopics"
                  :key="topic.id"
                  :class="getTopicClass(topic)"
                  :transform="`translate(${topic.x}, ${topic.y})`"
                  @click="onTopicClick(topic)"
                  @mouseenter="onTopicHover(topic, $event)"
                  @mouseleave="onTopicLeave(topic)"
                >
                  <!-- 矩形主题 -->
                  <rect
                    :x="-(topic.style.width / 2)"
                    :y="-(topic.style.height / 2)"
                    :width="topic.style.width"
                    :height="topic.style.height"
                    :rx="3"
                    :ry="3"
                    :fill="topic.style.fill"
                    :stroke="getTopicStroke(topic)"
                    :stroke-width="getTopicStrokeWidth(topic)"
                    :filter="topic.selected ? 'url(#selected-glow)' : 'url(#node-shadow)'"
                  />

                  <!-- 主题标签 -->
                  <text
                    y="3"
                    text-anchor="middle"
                    :fill="topic.style.textColor"
                    font-size="10"
                    font-weight="400"
                    font-family="system-ui, sans-serif"
                  >
                    {{ getTopicLabel(topic) }}
                  </text>
                  
                  <!-- 频率指示器 -->
                  <text
                    y="12"
                    text-anchor="middle"
                    :fill="getFrequencyColor(topic.name)"
                    font-size="8"
                    font-weight="500"
                    font-family="system-ui, sans-serif"
                  >
                    {{ getTopicFrequencyDisplay(topic.name) }}
                  </text>
                </g>
              </g>

              <!-- 数据流动画层 -->
              <g class="animation-layer" v-if="enableAnimation">
                <circle
                  v-for="particle in dataFlowParticles"
                  :key="particle.id"
                  :cx="particle.currentX"
                  :cy="particle.currentY"
                  :r="particle.size"
                  :fill="particle.connectionId.includes('pub') ? '#67c23a' : '#409eff'"
                  :opacity="particle.opacity"
                  class="data-flow-particle"
                />
              </g>
            </g>
          </svg>
        </div>
      </div>

      <!-- 右侧详情面板 -->
      <div class="rqt-detail-panel" :class="{ 'collapsed': detailPanelCollapsed }">
        <div class="panel-header">
          <h4>Details</h4>
          <el-button @click="detailPanelCollapsed = !detailPanelCollapsed" size="small" text>
            <el-icon><ArrowRight v-if="!detailPanelCollapsed" /><ArrowLeft v-else /></el-icon>
          </el-button>
        </div>

        <div v-show="!detailPanelCollapsed" class="panel-content">
          <div v-if="selectedItem" class="detail-content">
            <div class="detail-header">
              <h5>{{ selectedItem.name }}</h5>
              <el-tag :type="selectedItem.type === 'node' ? 'primary' : 'success'" size="small">
                {{ selectedItem.type === 'node' ? 'Node' : 'Topic' }}
              </el-tag>
            </div>

            <div class="detail-info">
              <div v-if="selectedItem.type === 'topic'" class="info-item">
                <label>Message Type:</label>
                <span>{{ selectedItem.messageType }}</span>
              </div>
              <div v-if="selectedItem.type === 'topic'" class="info-item">
                <label>Frequency:</label>
                <span>{{ getTopicFrequencyDisplay(selectedItem.name) }}</span>
              </div>
              <div class="info-item">
                <label>Publishers:</label>
                <span>{{ selectedItem.publishers?.length || 0 }}</span>
              </div>
              <div class="info-item">
                <label>Subscribers:</label>
                <span>{{ selectedItem.subscribers?.length || 0 }}</span>
              </div>
              <div v-if="selectedItem.namespace" class="info-item">
                <label>Namespace:</label>
                <span>{{ selectedItem.namespace }}</span>
              </div>
            </div>

            <!-- 连接列表 -->
            <div v-if="selectedItem.publishers?.length || selectedItem.subscribers?.length" class="connections-list">
              <h6>Connections</h6>
              <div v-if="selectedItem.publishers?.length" class="connection-group">
                <label>Publishes:</label>
                <ul>
                  <li v-for="pub in selectedItem.publishers" :key="pub">{{ pub }}</li>
                </ul>
              </div>
              <div v-if="selectedItem.subscribers?.length" class="connection-group">
                <label>Subscribes:</label>
                <ul>
                  <li v-for="sub in selectedItem.subscribers" :key="sub">{{ sub }}</li>
                </ul>
              </div>
            </div>
          </div>

          <div v-else class="no-selection">
            <p>Select a node or topic to view details</p>
          </div>
        </div>
      </div>
    </div>

    <!-- 增强的悬浮提示 -->
    <div
      v-if="tooltip.visible"
      class="rqt-tooltip"
      :style="{
        left: tooltip.x + 'px',
        top: tooltip.y + 'px',
        position: 'fixed'
      }"
    >
      <div class="tooltip-header">
        <strong>{{ tooltip.data.name }}</strong>
        <el-tag :type="tooltip.data.type === 'node' ? 'primary' : 'success'" size="small">
          {{ tooltip.data.type === 'node' ? 'Node' : 'Topic' }}
        </el-tag>
      </div>
      <div class="tooltip-content">
        <div v-if="tooltip.data.type === 'topic'" class="tooltip-item">
          <span class="tooltip-label">Type:</span>
          <span class="tooltip-value">{{ tooltip.data.messageType }}</span>
        </div>
        <div v-if="tooltip.data.type === 'topic'" class="tooltip-item">
          <span class="tooltip-label">Frequency:</span>
          <span class="tooltip-value">{{ getTopicFrequencyDisplay(tooltip.data.name) }}</span>
        </div>
        <div class="tooltip-item">
          <span class="tooltip-label">Publishers:</span>
          <span class="tooltip-value">{{ tooltip.data.publishers?.length || 0 }}</span>
        </div>
        <div class="tooltip-item">
          <span class="tooltip-label">Subscribers:</span>
          <span class="tooltip-value">{{ tooltip.data.subscribers?.length || 0 }}</span>
        </div>
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
import { Refresh, Search, Setting, Aim, Plus, Minus, Grid, Document, ArrowLeft, ArrowRight } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useRosbridge } from '../../../composables/useRosbridge'
import { createHierarchicalLayout } from '../utils/GraphLayout.js'
import { GraphInteractionController } from '../utils/GraphInteraction.js'

export default {
  name: 'RQTProfessionalGraph',
  components: {
    Refresh, Search, Setting, Aim, Plus, Minus, Grid, Document, ArrowLeft, ArrowRight
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

    // ===== RQT风格新增状态 =====
    const controlPanelCollapsed = ref(false)
    const detailPanelCollapsed = ref(false)
    const selectedNamespace = ref('')
    const showType = ref('all')
    const hideUnconnected = ref(false) // 默认显示未连接节点，让用户看到完整图形
    const hideSystemNodes = ref(false) // 默认显示系统节点，让用户看到完整图形
    const groupByNamespace = ref(false)
    const selectedItem = ref(null)
    const availableNamespaces = ref([])

    // ===== 新增的RQT过滤选项 =====
    const hideDeadSinks = ref(false)     // 默认显示Dead Sinks，让用户看到完整图形
    const hideLeafTopics = ref(false)    // 默认显示Leaf Topics，让用户看到完整图形
    const hideDebugTopics = ref(true)    // 默认隐藏Debug Topics (调试相关主题)
    
    // ===== 动画相关状态 =====
    const animationFrameId = ref(null)
    const animationStartTime = ref(0)
    const dataFlowParticles = ref([])
    const animationSpeed = ref(1.0)
    
    // ===== 频率监控状态 =====
    const topicFrequency = ref(new Map()) // 主题频率监控
    const nodeActivity = ref(new Map())   // 节点活跃度监控
    const frequencyUpdateInterval = ref(null) // 频率更新定时器

    // ===== 悬浮提示状态 =====
    const tooltip = ref({
      visible: false,
      x: 0,
      y: 0,
      data: {}
    })
    
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
      // 首先获取所有节点的连接信息
      const nodeConnections = buildNodeConnectionMap()
      let nodes = rawNodes.value

      // 应用过滤器
      if (filterText.value) {
        const filter = filterText.value.toLowerCase()
        nodes = nodes.filter(node =>
          node.name.toLowerCase().includes(filter)
        )
      }

      // RQT风格的过滤逻辑 - 按照RQT graph的实际行为

      // 隐藏系统节点 - 优先处理
      if (hideSystemNodes.value) {
        const systemPatterns = [
          '/rosout',
          '/parameter_events',
          'launch_ros',
          '_static_transform_publisher',
          '/robot_state_publisher',
          '/tf2_web_republisher',
          '/rosapi',
          '/rosbridge',
          'rqt_gui',
          'rqt_',
          'rviz'
        ]
        
        const beforeCount = nodes.length
        nodes = nodes.filter(node => {
          const isSystemNode = systemPatterns.some(pattern => node.name.includes(pattern))
          if (isSystemNode) {
            console.log(`过滤系统节点: ${node.name}`)
          }
          return !isSystemNode
        })
        console.log(`系统节点过滤: ${beforeCount} -> ${nodes.length} 个节点`)
      }

      // 隐藏Dead Sinks - 根据新定义：订阅了主题但没有正确处理消息的节点
      if (hideDeadSinks.value) {
        const deadSinkNodes = detectDeadSinkNodes(nodes)
        console.log(`检测到 ${deadSinkNodes.length} 个Dead Sink节点:`, deadSinkNodes.map(n => n.name))
        const deadSinkNames = new Set(deadSinkNodes.map(n => n.name))
        nodes = nodes.filter(node => !deadSinkNames.has(node.name))
      }

      // 隐藏未连接节点 - RQT定义：没有任何发布或订阅连接的节点
      if (hideUnconnected.value) {
        nodes = nodes.filter(node => {
          const connections = nodeConnections.get(node.name) || { publishedTopics: new Set(), subscribedTopics: new Set() }
          return connections.publishedTopics.size > 0 || connections.subscribedTopics.size > 0
        })
      }

      // 命名空间过滤
      if (selectedNamespace.value) {
        nodes = nodes.filter(node => {
          const nodeNamespace = extractNamespace(node.name)
          return nodeNamespace === selectedNamespace.value
        })
      }

      return nodes
    })
    
    const filteredTopics = computed(() => {
      // 获取当前过滤后的节点信息
      const activeNodeNames = new Set(filteredNodes.value.map(n => n.name))
      const topicConnections = buildTopicConnectionMap(activeNodeNames)

      let topics = rawTopics.value

      // 应用过滤器
      if (filterText.value) {
        const filter = filterText.value.toLowerCase()
        topics = topics.filter(topic =>
          topic.name.toLowerCase().includes(filter) ||
          topic.messageType.toLowerCase().includes(filter)
        )
      }

      // RQT风格的主题过滤逻辑

      // 隐藏未连接主题 - RQT定义：没有任何活跃节点发布或订阅的主题
      if (hideUnconnected.value) {
        topics = topics.filter(topic => {
          const connections = topicConnections.get(topic.name) || { publishers: new Set(), subscribers: new Set() }
          return connections.publishers.size > 0 || connections.subscribers.size > 0
        })
      }

      // 隐藏Leaf Topics - 根据新定义：没有其他话题依赖于它的消息输出的主题
      if (hideLeafTopics.value) {
        const leafTopics = detectLeafTopics(topics)

        const leafTopicNames = new Set(leafTopics.map(t => t.name))
        topics = topics.filter(topic => !leafTopicNames.has(topic.name))
      }

      // 隐藏Dead Sinks对应的主题 - 根据Hz数和订阅关系判断
      if (hideDeadSinks.value) {
        const deadSinkTopics = detectDeadSinkTopics(topics)
        console.log(`检测到 ${deadSinkTopics.length} 个Dead Sink主题:`, deadSinkTopics.map(t => t.name))
        const deadSinkTopicNames = new Set(deadSinkTopics.map(t => t.name))
        topics = topics.filter(topic => !deadSinkTopicNames.has(topic.name))
      }

      // 隐藏Debug Topics (调试相关主题)
      if (hideDebugTopics.value) {
        topics = topics.filter(topic => {
          const debugPatterns = [
            '/debug',
            '_debug',
            '/diagnostics',
            'rosout',
            '/parameter_events',
            '/clock'
          ]
          return !debugPatterns.some(pattern => topic.name.includes(pattern))
        })
      }

      // 隐藏系统主题
      if (hideSystemNodes.value) {
        topics = topics.filter(topic => {
          const systemPatterns = [
            '/rosout',
            '/parameter_events',
            '/clock',
            '/tf_static'
          ]
          return !systemPatterns.some(pattern => topic.name.includes(pattern))
        })
      }

      // 命名空间过滤
      if (selectedNamespace.value) {
        topics = topics.filter(topic => {
          const topicNamespace = extractNamespace(topic.name)
          return topicNamespace === selectedNamespace.value
        })
      }

      // 调试：输出过滤结果
      console.log(`Topic filtering result: ${topics.length} topics remaining`)
      if (hideLeafTopics.value) {
        const leafTopics = rawTopics.value.filter(topic => {
          const connections = topicConnections.get(topic.name) || { publishers: new Set(), subscribers: new Set() }
          return connections.publishers.size > 0 && connections.subscribers.size === 0
        })
      }

      return topics
    })
    
    const filteredConnections = computed(() => {
      // 计算可见节点和主题的连接
      const visibleNodeIds = new Set(filteredNodes.value.map(n => n.id))
      const visibleTopicIds = new Set(filteredTopics.value.map(t => t.id))

      // 过滤出只连接可见节点的连接，并去重
      const validConnections = connections.value.filter(conn =>
        (visibleNodeIds.has(conn.from) || visibleTopicIds.has(conn.from)) &&
        (visibleNodeIds.has(conn.to) || visibleTopicIds.has(conn.to))
      )

      // 去重：根据 from-to-type 组合去重
      const uniqueConnections = []
      const connectionSet = new Set()

      validConnections.forEach(conn => {
        const key = `${conn.from}-${conn.to}-${conn.type}`
        if (!connectionSet.has(key)) {
          connectionSet.add(key)
          uniqueConnections.push(conn)
        }
      })

      return uniqueConnections
    })
    
    // ===== 连接分析辅助函数 =====

    /**
     * 构建节点连接映射表
     * 根据实际的publisher/subscriber关系构建连接信息
     */
    const buildNodeConnectionMap = () => {
      const nodeConnections = new Map()

      // 初始化所有节点
      rawNodes.value.forEach(node => {
        nodeConnections.set(node.name, {
          publishedTopics: new Set(),
          subscribedTopics: new Set()
        })
      })

      // 根据节点的publishers和subscribers属性构建连接
      rawNodes.value.forEach(node => {
        const connections = nodeConnections.get(node.name)

        // 添加发布的主题
        if (node.publishers) {
          node.publishers.forEach(topicName => {
            connections.publishedTopics.add(topicName)
          })
        }

        // 添加订阅的主题
        if (node.subscribers) {
          node.subscribers.forEach(topicName => {
            connections.subscribedTopics.add(topicName)
          })
        }
      })

      return nodeConnections
    }

    /**
     * 构建主题连接映射表
     * 根据所有节点计算每个主题的发布者和订阅者（不限制于活跃节点）
     */
    const buildTopicConnectionMap = (activeNodeNames) => {
      const topicConnections = new Map()

      // 初始化所有主题
      rawTopics.value.forEach(topic => {
        topicConnections.set(topic.name, {
          publishers: new Set(),
          subscribers: new Set()
        })
      })

      // 遍历所有节点，构建主题的连接信息（不限制于活跃节点）
      // 这样确保主题连接信息完整，过滤在后续步骤进行
      rawNodes.value.forEach(node => {
        // 记录该节点发布的主题
        if (node.publishers) {
          node.publishers.forEach(topicName => {
            const connections = topicConnections.get(topicName)
            if (connections) {
              connections.publishers.add(node.name)
            }
          })
        }

        // 记录该节点订阅的主题
        if (node.subscribers) {
          node.subscribers.forEach(topicName => {
            const connections = topicConnections.get(topicName)
            if (connections) {
              connections.subscribers.add(node.name)
            }
          })
        }
      })

      console.log('Topic connections built:', topicConnections)
      return topicConnections
    }

    // ===== 动画方法 =====
    
    /**
     * 创建数据流粒子
     */
    const createDataFlowParticles = () => {
      if (!enableAnimation.value) return
      
      dataFlowParticles.value = []
      
      // 为每个连接创建粒子
      filteredConnections.value.forEach(connection => {
        const fromNode = [...filteredNodes.value, ...filteredTopics.value].find(n => n.id === connection.from)
        const toNode = [...filteredNodes.value, ...filteredTopics.value].find(n => n.id === connection.to)
        
        if (fromNode && toNode) {
          // 创建多个粒子以显示数据流
          for (let i = 0; i < 3; i++) {
            dataFlowParticles.value.push({
              id: `${connection.id}_particle_${i}`,
              connectionId: connection.id,
              progress: (i * 0.3) % 1, // 错开粒子的起始位置
              fromX: fromNode.x,
              fromY: fromNode.y,
              toX: toNode.x,
              toY: toNode.y,
              speed: 0.5 + Math.random() * 0.5, // 随机速度
              opacity: 0.8,
              size: 3 + Math.random() * 2
            })
          }
        }
      })
    }
    
    /**
     * 更新数据流粒子动画
     */
    const updateDataFlowAnimation = () => {
      if (!enableAnimation.value || dataFlowParticles.value.length === 0) return
      
      const currentTime = Date.now()
      const deltaTime = Math.max(16, currentTime - animationStartTime.value) // 确保最小16ms间隔
      
      dataFlowParticles.value.forEach(particle => {
        // 更新粒子进度
        particle.progress += (particle.speed * animationSpeed.value * deltaTime) / 3000
        
        // 如果粒子到达终点，重新开始
        if (particle.progress >= 1) {
          particle.progress = 0
        }
        
        // 计算当前位置
        const t = particle.progress
        particle.currentX = particle.fromX + (particle.toX - particle.fromX) * t
        particle.currentY = particle.fromY + (particle.toY - particle.fromY) * t
        
        // 计算透明度（在开始和结束时淡入淡出）
        if (t < 0.1) {
          particle.opacity = t / 0.1 * 0.8
        } else if (t > 0.9) {
          particle.opacity = (1 - t) / 0.1 * 0.8
        } else {
          particle.opacity = 0.8
        }
      })
      
      animationStartTime.value = currentTime
    }
    
    /**
     * 启动动画循环
     */
    const startAnimation = () => {
      if (animationFrameId.value) return
      
      animationStartTime.value = Date.now()
      createDataFlowParticles()
      
      const animate = () => {
        updateDataFlowAnimation()
        animationFrameId.value = requestAnimationFrame(animate)
      }
      
      animate()
    }
    
    /**
     * 停止动画循环
     */
    const stopAnimation = () => {
      if (animationFrameId.value) {
        cancelAnimationFrame(animationFrameId.value)
        animationFrameId.value = null
      }
      dataFlowParticles.value = []
    }
    
    /**
     * 切换动画状态
     */
    const toggleAnimation = () => {
      if (enableAnimation.value) {
        startAnimation()
      } else {
        stopAnimation()
      }
    }

    // ===== 频率监控方法 =====
    
    /**
     * 开始频率监控
     */
    const startFrequencyMonitoring = async () => {
      try {
        // 从后端API获取真实的频率信息
        const frequencies = await rosbridge.getTopicFrequencies()
        console.log('从后端获取的频率数据:', frequencies)
        
        // 更新频率数据
        Object.entries(frequencies).forEach(([topicName, frequency]) => {
          topicFrequency.value.set(topicName, frequency)
          
          // 处理频率显示
          let frequencyDisplay = 'N/A'
          if (isNaN(frequency)) {
            frequencyDisplay = 'N/A'
          } else if (frequency === 0) {
            frequencyDisplay = '0Hz'
          } else {
            frequencyDisplay = `${frequency.toFixed(2)}Hz`
          }
          
          console.log(`主题 ${topicName} 频率: ${frequencyDisplay}`)
        })
        
        console.log('频率监控数据更新完成')
        
        // 启动定期更新频率监控
        if (frequencyUpdateInterval.value) {
          clearInterval(frequencyUpdateInterval.value)
        }
        
        frequencyUpdateInterval.value = setInterval(async () => {
          await startFrequencyMonitoring()
        }, 5000) // 每5秒更新一次频率数据
        
      } catch (error) {
        console.error('频率监控失败:', error)
        // 如果API调用失败，使用模拟数据作为后备
        console.log('使用模拟频率数据作为后备')
        await startFrequencyMonitoringFallback()
      }
    }
    
    /**
     * 频率监控后备方案（模拟数据）
     */
    const startFrequencyMonitoringFallback = async () => {
      try {
        const topics = await rosbridge.getTopics()
        const frequencyPromises = topics.map(async (topicName) => {
          try {
            // 模拟不同主题的频率数据
            let frequency = 0
            
            // 根据主题名称模拟不同的频率
            if (topicName.includes('odom') || topicName.includes('pose')) {
              frequency = 10 + Math.random() * 20 // 10-30Hz
            } else if (topicName.includes('image') || topicName.includes('camera')) {
              frequency = 15 + Math.random() * 15 // 15-30Hz
            } else if (topicName.includes('scan') || topicName.includes('laser')) {
              frequency = 5 + Math.random() * 10 // 5-15Hz
            } else if (topicName.includes('diagnostics') || topicName.includes('status')) {
              frequency = 1 + Math.random() * 2 // 1-3Hz
            } else if (topicName.includes('parameter_events') || topicName.includes('rosout')) {
              frequency = 0.1 + Math.random() * 0.5 // 0.1-0.6Hz (低频)
            } else {
              frequency = 1 + Math.random() * 5 // 1-6Hz 正常频率
            }
            
            topicFrequency.value.set(topicName, frequency)
            console.log(`主题 ${topicName} 频率(模拟): ${frequency.toFixed(2)}Hz`)
          } catch (error) {
            console.warn(`无法获取主题 ${topicName} 的频率:`, error)
            topicFrequency.value.set(topicName, 0)
          }
        })
        
        await Promise.all(frequencyPromises)
        console.log('模拟频率监控数据更新完成')
        
      } catch (error) {
        console.error('模拟频率监控失败:', error)
      }
    }
    
    /**
     * 停止频率监控
     */
    const stopFrequencyMonitoring = () => {
      if (frequencyUpdateInterval.value) {
        clearInterval(frequencyUpdateInterval.value)
        frequencyUpdateInterval.value = null
      }
    }
    
    /**
     * 检测Dead Sink节点
     * 根据正确定义：订阅了主题但没有正确处理消息的节点
     * 或者节点已经停止运行而未取消订阅
     */
    const detectDeadSinkNodes = (nodes) => {
      return nodes.filter(node => {
        const connections = nodeConnections.get(node.name) || { publishedTopics: new Set(), subscribedTopics: new Set() }
        
        // 如果节点没有订阅任何主题，不是dead sink
        if (connections.subscribedTopics.size === 0) return false
        
        // 检查节点订阅的主题是否都有活跃的发布者和数据流
        let hasActiveDataFlow = false
        let allTopicsDead = true
        
        connections.subscribedTopics.forEach(topicName => {
          const topicConnections = buildTopicConnectionMap(new Set())
          const topicInfo = topicConnections.get(topicName)
          const frequency = topicFrequency.value.get(topicName) || 0
          
          console.log(`节点 ${node.name} 订阅主题 ${topicName}: 发布者=${topicInfo?.publishers.size || 0}, 频率=${frequency}Hz`)
          
          // 如果主题有发布者且频率正常，说明有活跃的数据流
          if (topicInfo && topicInfo.publishers.size > 0 && frequency > 0.1) {
            hasActiveDataFlow = true
            allTopicsDead = false
          }
        })
        
        // 如果节点订阅了主题但没有活跃的数据流，则是dead sink
        const isDeadSink = !hasActiveDataFlow && allTopicsDead
        if (isDeadSink) {
          console.log(`检测到Dead Sink节点: ${node.name} (订阅的主题没有活跃数据流)`)
        }
        
        return isDeadSink
      })
    }
    
    /**
     * 检测Dead Sink主题
     * 根据正确定义：
     * 1. 有发布者但没有订阅者的主题（数据被发布但没人消费）
     * 2. 有订阅者但没有发布者的主题（有人想消费但没有数据）
     * 3. 频率为0或NA的主题
     */
    const detectDeadSinkTopics = (topics) => {
      return topics.filter(topic => {
        const connections = buildTopicConnectionMap(new Set())
        const topicInfo = connections.get(topic.name)
        
        if (!topicInfo) return false
        
        const frequency = topicFrequency.value.get(topic.name) || 0
        const hasPublishers = topicInfo.publishers.size > 0
        const hasSubscribers = topicInfo.subscribers.size > 0
        
        console.log(`主题 ${topic.name}: 发布者=${hasPublishers ? topicInfo.publishers.size : 0}, 订阅者=${hasSubscribers ? topicInfo.subscribers.size : 0}, 频率=${frequency}Hz`)
        
        // 情况1：有发布者但没有订阅者（数据被发布但没人消费）
        const case1 = hasPublishers && !hasSubscribers
        
        // 情况2：有订阅者但没有发布者（有人想消费但没有数据）
        const case2 = !hasPublishers && hasSubscribers
        
        // 情况3：频率为0或NA（没有数据流）
        const case3 = frequency === 0 || isNaN(frequency)
        
        const isDeadSinkTopic = case1 || case2 || case3
        
        if (isDeadSinkTopic) {
          console.log(`检测到Dead Sink主题: ${topic.name} (原因: ${case1 ? '有发布无订阅' : case2 ? '有订阅无发布' : '频率为0'})`)
        }
        
        return isDeadSinkTopic
      })
    }
    
    /**
     * 检测Leaf Topic
     * 根据新定义：没有其他话题依赖于它的消息输出的主题
     */
    const detectLeafTopics = (topics) => {
      return topics.filter(topic => {
        const connections = buildTopicConnectionMap(new Set())
        const topicInfo = connections.get(topic.name)
        
        if (!topicInfo) return false
        
        // 如果主题没有发布者，不是leaf topic
        if (topicInfo.publishers.size === 0) return false
        
        // 检查是否有其他主题依赖于这个主题的输出
        // 这里需要检查主题之间的依赖关系，暂时简化处理
        // 如果主题有订阅者，则不是leaf topic
        return topicInfo.subscribers.size === 0
      })
    }

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
              fill: '#ffffff',
              stroke: '#303133',
              strokeWidth: 2,
              textColor: '#303133'
            }
          }
        })
        
        // 处理主题数据
        rawTopics.value = topicList.map((topicInfo, index) => {
          const topicName = typeof topicInfo === 'string' ? topicInfo : topicInfo.name
          const messageType = topicTypes[topicName] || 'unknown'
          
          // 计算该主题的实际发布者和订阅者
          const topicPublishers = []
          const topicSubscribers = []
          
          // 遍历所有节点，找到发布和订阅该主题的节点
          nodeList.forEach(nodeInfo => {
            const nodeName = typeof nodeInfo === 'string' ? nodeInfo : nodeInfo.name
            const nodePublishers = typeof nodeInfo === 'object' ? (nodeInfo.publishers || []) : []
            const nodeSubscribers = typeof nodeInfo === 'object' ? (nodeInfo.subscribers || []) : []
            
            if (nodePublishers.includes(topicName)) {
              topicPublishers.push(nodeName)
            }
            if (nodeSubscribers.includes(topicName)) {
              topicSubscribers.push(nodeName)
            }
          })
          
          return {
            id: `topic_${index}`,
            name: topicName,
            label: topicName.split('/').pop() || topicName,
            type: 'topic',
            messageType: messageType,
            publishers: topicPublishers,
            subscribers: topicSubscribers,
            x: 0,
            y: 0,
            selected: false,
            style: {
              width: 120,
              height: 30,
              fill: getTopicColor(messageType),
              stroke: '#67c23a',
              strokeWidth: 1,
              textColor: '#ffffff'
            }
          }
        })
        
        // 启动频率监控
        await startFrequencyMonitoring()
        
        // 初始加载后，等待一小段时间再应用布局，确保过滤器正常工作
        await nextTick()
        setTimeout(() => {
          applyLayout()
          // 在布局完成后启动动画
          if (enableAnimation.value) {
            setTimeout(() => {
              createDataFlowParticles()
              startAnimation()
            }, 100)
          }
        }, 50)
        
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
      
      // console.log(`应用 ${layoutType.value} 布局算法`)
      
      // 更新容器尺寸
      updateLayoutSize()
      
      // 使用过滤后的数据进行布局
      const allFilteredNodes = [...filteredNodes.value, ...filteredTopics.value]
      layoutEngine.value.setData(allFilteredNodes, filteredConnections.value)

      // console.log(`布局数据: ${filteredNodes.value.length} 个节点, ${filteredTopics.value.length} 个主题, ${filteredConnections.value.length} 个连接`)
      
      // 执行布局
      let layoutNodes = []
      if (layoutType.value === 'hierarchical') {
        layoutNodes = layoutEngine.value.applyHierarchicalLayout()
      } else if (layoutType.value === 'circular') {
        layoutNodes = layoutEngine.value.applyCircularLayout()
      }
      
      // 更新过滤后节点的位置
      layoutNodes.forEach(layoutNode => {
        if (layoutNode.type === 'node') {
          const node = filteredNodes.value.find(n => n.id === layoutNode.id)
          if (node) {
            node.x = layoutNode.x
            node.y = layoutNode.y
            node.style = layoutNode.style || node.style

            // 同时更新原始数据中的位置
            const rawNode = rawNodes.value.find(n => n.id === layoutNode.id)
            if (rawNode) {
              rawNode.x = layoutNode.x
              rawNode.y = layoutNode.y
            }
          }
        } else if (layoutNode.type === 'topic') {
          const topic = filteredTopics.value.find(t => t.id === layoutNode.id)
          if (topic) {
            topic.x = layoutNode.x
            topic.y = layoutNode.y
            topic.style = layoutNode.style || topic.style

            // 同时更新原始数据中的位置
            const rawTopic = rawTopics.value.find(t => t.id === layoutNode.id)
            if (rawTopic) {
              rawTopic.x = layoutNode.x
              rawTopic.y = layoutNode.y
            }
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
     * 只计算在过滤后数据中显示的连接
     */
    const calculateConnections = () => {
      const newConnections = []
      const visibleTopicNames = new Set(filteredTopics.value.map(t => t.name))

      // 遍历过滤后的节点，建立与过滤后主题的连接
      filteredNodes.value.forEach(node => {
        // 发布者连接 (node -> topic)
        if (node.publishers) {
          node.publishers.forEach((topicName, topicIndex) => {
            const topic = filteredTopics.value.find(t => t.name === topicName)
            if (topic && visibleTopicNames.has(topicName)) {
              newConnections.push({
                id: `${node.id}_pub_topic_${topicIndex}_${topic.id}`,
                from: node.id,
                to: topic.id,
                type: 'publisher',
                topicName: topicName,
                path: `M${node.x},${node.y} L${topic.x},${topic.y}`,
                opacity: 0.7
              })
            }
          })
        }

        // 订阅者连接 (topic -> node)
        if (node.subscribers) {
          node.subscribers.forEach((topicName, topicIndex) => {
            const topic = filteredTopics.value.find(t => t.name === topicName)
            if (topic && visibleTopicNames.has(topicName)) {
              newConnections.push({
                id: `${node.id}_sub_topic_${topicIndex}_${topic.id}`,
                from: topic.id,
                to: node.id,
                type: 'subscriber',
                topicName: topicName,
                path: `M${topic.x},${topic.y} L${node.x},${node.y}`,
                opacity: 0.5
              })
            }
          })
        }
      })

      connections.value = newConnections
      // console.log(`计算了 ${newConnections.length} 个连接`)
    }
    
    /**
     * 获取主题颜色
     * @param {string} messageType - 消息类型
     * @returns {string} 颜色
     */
    const getTopicColor = (messageType) => {
      const colorMap = {
        'sensor_msgs/msg/PointCloud2': '#67c23a',
        'sensor_msgs/msg/LaserScan': '#67c23a',
        'nav_msgs/msg/OccupancyGrid': '#67c23a',
        'geometry_msgs/msg/Twist': '#67c23a',
        'nav_msgs/msg/Odometry': '#67c23a',
        'sensor_msgs/msg/Image': '#67c23a',
        'tf2_msgs/msg/TFMessage': '#67c23a',
        'diagnostic_msgs/msg/DiagnosticArray': '#67c23a',
        'geometry_msgs/msg/PoseWithCovarianceStamped': '#67c23a',
        'geometry_msgs/msg/PoseStamped': '#67c23a',
        'std_msgs/msg/String': '#67c23a',
        'rcl_interfaces/msg/ParameterEvent': '#67c23a'
      }
      
      return colorMap[messageType] || '#67c23a'
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
    
    /**
     * 获取主题频率显示文本
     */
    const getTopicFrequencyDisplay = (topicName) => {
      const frequency = topicFrequency.value.get(topicName)
      if (frequency === undefined || frequency === null) {
        return 'N/A'
      } else if (isNaN(frequency)) {
        return 'N/A'
      } else if (frequency === 0) {
        return '0Hz'
      } else {
        return `${frequency.toFixed(2)}Hz`
      }
    }
    
    /**
     * 获取频率颜色指示器
     */
    const getFrequencyColor = (topicName) => {
      const frequency = topicFrequency.value.get(topicName)
      if (frequency === undefined || frequency === null || isNaN(frequency)) {
        return '#f56c6c' // 红色 - N/A
      } else if (frequency === 0) {
        return '#f56c6c' // 红色 - 0Hz (Dead Sink)
      } else if (frequency < 0.1) {
        return '#e6a23c' // 橙色 - 极低频
      } else if (frequency < 1) {
        return '#909399' // 灰色 - 低频
      } else if (frequency < 10) {
        return '#67c23a' // 绿色 - 中频
      } else {
        return '#409eff' // 蓝色 - 高频
      }
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
      
      // console.log(`更新布局尺寸: ${width} x ${height}`)
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
            maxScale: 1.0  // 最大缩放限制为100%
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
      
      // 启动动画（如果启用）
      if (enableAnimation.value) {
        startAnimation()
      }
    })
    
    onUnmounted(() => {
      // 停止动画
      stopAnimation()
      
      // 停止频率监控
      stopFrequencyMonitoring()
      
      if (interactionController.value) {
        interactionController.value.destroy()
      }
      
      // 移除事件监听器
      window.removeEventListener('resize', () => {})
      
      console.log('分层节点图组件卸载')
    })
    
    // ===== RQT风格新增方法 =====

    /**
     * 切换详情面板
     */
    const toggleDetailPanel = () => {
      detailPanelCollapsed.value = !detailPanelCollapsed.value
    }

    /**
     * 应用过滤器
     */
    const applyFilters = () => {
      console.log('应用过滤器:', {
        selectedNamespace: selectedNamespace.value,
        showType: showType.value,
        hideUnconnected: hideUnconnected.value,
        hideSystemNodes: hideSystemNodes.value
      })

      // 提取命名空间
      extractNamespaces()

      // 触发重新布局
      nextTick(() => {
        applyLayout()
      })
    }

    /**
     * 提取可用的命名空间
     */
    const extractNamespaces = () => {
      const namespaces = new Set()

      const allItems = rawNodes.value.concat(rawTopics.value)
      allItems.forEach(item => {
        const namespace = extractNamespace(item.name)
        if (namespace) {
          namespaces.add(namespace)
        }
      })

      availableNamespaces.value = Array.from(namespaces).sort()
    }

    /**
     * 从名称中提取命名空间
     */
    const extractNamespace = (name) => {
      const parts = name.split('/')
      return parts.length > 2 ? `/${parts[1]}` : '/'
    }

    /**
     * RQT风格的节点过滤逻辑
     */
    const shouldFilterOutNodeRQT = (node) => {
      // 系统节点过滤
      if (hideSystemNodes.value) {
        const systemPatterns = [
          '/rosout',
          '/parameter_events',
          'launch_ros',
          '_static_transform_publisher',
          '/robot_state_publisher'
        ]

        if (systemPatterns.some(pattern => node.name.includes(pattern))) {
          return true
        }
      }

      // 未连接节点过滤
      if (hideUnconnected.value) {
        const hasConnections = node.publishers.length > 0 || node.subscribers.length > 0
        if (!hasConnections) {
          return true
        }
      }

      // 命名空间过滤
      if (selectedNamespace.value) {
        const nodeNamespace = extractNamespace(node.name)
        if (nodeNamespace !== selectedNamespace.value) {
          return true
        }
      }

      return false
    }

    /**
     * RQT风格的主题过滤逻辑
     */
    const shouldFilterOutTopicRQT = (topic) => {
      // 系统主题过滤
      if (hideSystemNodes.value) {
        const systemPatterns = [
          '/rosout',
          '/parameter_events',
          '/clock',
          '/tf_static'
        ]

        if (systemPatterns.some(pattern => topic.name.includes(pattern))) {
          return true
        }
      }

      // 未连接主题过滤
      if (hideUnconnected.value) {
        const hasConnections = topic.publishers.length > 0 || topic.subscribers.length > 0
        if (!hasConnections) {
          return true
        }
      }

      // 命名空间过滤
      if (selectedNamespace.value) {
        const topicNamespace = extractNamespace(topic.name)
        if (topicNamespace !== selectedNamespace.value) {
          return true
        }
      }

      return false
    }

    /**
     * 增强的节点点击处理
     */
    const onNodeClickEnhanced = (node) => {
      selectedItem.value = {
        ...node,
        namespace: extractNamespace(node.name)
      }
      onNodeClick(node)
    }

    /**
     * 增强的主题点击处理
     */
    const onTopicClickEnhanced = (topic) => {
      selectedItem.value = {
        ...topic,
        namespace: extractNamespace(topic.name)
      }
      onTopicClick(topic)
    }

    /**
     * 改进的悬浮提示
     */
    const showTooltipEnhanced = (data, event) => {
      // 使用固定位置策略，避免跳动
      const rect = graphContainer.value.getBoundingClientRect()

      // 计算相对于容器的位置
      const x = rect.left + data.x * transform.value.scale + transform.value.translateX + 80
      const y = rect.top + data.y * transform.value.scale + transform.value.translateY - 10

      // 确保提示框在视口内
      const maxX = window.innerWidth - 300
      const maxY = window.innerHeight - 150

      tooltip.value = {
        visible: true,
        x: Math.min(Math.max(10, x), maxX),
        y: Math.min(Math.max(10, y), maxY),
        data: {
          ...data,
          namespace: extractNamespace(data.name)
        }
      }
    }

    const hideTooltipEnhanced = () => {
      tooltip.value.visible = false
    }

    // ===== 监听器 =====

    watch(layoutType, () => {
      applyLayout()
    })

    let layoutTimeout = null

    watch([hideUnconnected, hideSystemNodes, hideDeadSinks, hideLeafTopics, hideDebugTopics, selectedNamespace, showType, filterText], () => {
      applyFilters()
    }, { deep: true })

    // 优化：仅在数据实际变化时重新布局
    watch([filteredNodes, filteredTopics], () => {
      // 防抖处理，避免频繁重新布局
      if (layoutTimeout) {
        clearTimeout(layoutTimeout)
      }
      layoutTimeout = setTimeout(() => {
        applyLayout()
        // 重新创建动画粒子
        if (enableAnimation.value) {
          createDataFlowParticles()
        }
      }, 100)
    }, { deep: true })

    // 监听动画开关
    watch(enableAnimation, (newValue) => {
      if (newValue) {
        startAnimation()
      } else {
        stopAnimation()
      }
    })

    // ===== 返回API =====
    return {
      // DOM引用
      svgRef,
      graphContainer,

      // 基础状态
      loading,
      filterText,
      layoutType,
      showIsolatedNodes,
      enableAnimation,
      labelMode,
      currentZoom,
      transform,
      tooltip,

      // RQT风格新增状态
      controlPanelCollapsed,
      detailPanelCollapsed,
      selectedNamespace,
      showType,
      hideUnconnected,
      hideSystemNodes,
      hideDeadSinks,
      hideLeafTopics,
      hideDebugTopics,
      groupByNamespace,
      selectedItem,
      availableNamespaces,

      // 数据
      filteredNodes,
      filteredTopics,
      filteredConnections,

      // 基础方法
      refreshGraph,
      applyLayout,
      resetView,
      zoomIn,
      zoomOut,

      // RQT风格增强方法
      toggleDetailPanel,
      applyFilters,
      onNodeClick: onNodeClickEnhanced,
      onTopicClick: onTopicClickEnhanced,
      onConnectionClick,
      onNodeHover: showTooltipEnhanced,
      onNodeLeave: hideTooltipEnhanced,
      onTopicHover: showTooltipEnhanced,
      onTopicLeave: hideTooltipEnhanced,
      onConnectionHover: (conn) => { conn.selected = true },
      onConnectionLeave: (conn) => { conn.selected = false },

      // 样式方法
      getNodeClass,
      getTopicClass,
      getConnectionClass,
      getNodeStroke,
      getNodeStrokeWidth,
      getTopicStroke,
      getTopicStrokeWidth,
      getNodeLabel,
      getTopicLabel,
      getTopicFrequencyDisplay,
      getFrequencyColor
    }
  }
}
</script>

<style scoped>
/* ===== RQT专业风格样式 ===== */
.rqt-professional-graph {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #ffffff;
  font-family: system-ui, -apple-system, sans-serif;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  overflow: hidden;
}

/* ===== 专业工具栏样式 ===== */
.rqt-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  background: #f5f7fa;
  border-bottom: 1px solid #e4e7ed;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.toolbar-section {
  display: flex;
  align-items: center;
  gap: 12px;
}

.rqt-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #495057;
}

.title-icon {
  color: #007bff;
}

.center-section {
  flex: 1;
  justify-content: center;
}

.statistics-display {
  display: flex;
  gap: 24px;
  padding: 4px 16px;
  background: rgba(255,255,255,0.8);
  border-radius: 6px;
  border: 1px solid #dee2e6;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.stat-label {
  font-size: 12px;
  color: #6c757d;
  font-weight: 500;
}

.stat-value {
  font-size: 14px;
  color: #007bff;
  font-weight: 600;
}

/* ===== 三栏式主体布局 ===== */
.rqt-main-layout {
  display: flex;
  flex: 1;
  height: calc(100% - 50px);
  overflow: hidden;
}

/* ===== 左侧控制面板 ===== */
.rqt-control-panel {
  width: 250px;
  background: #ffffff;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease;
  overflow: hidden;
}

.rqt-control-panel.collapsed {
  width: 50px;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: #f5f7fa;
  border-bottom: 1px solid #e4e7ed;
  font-weight: 600;
  color: #606266;
}

.panel-content {
  flex: 1;
  padding: 16px;
  overflow-y: auto;
  overflow-x: hidden;
}

.control-group {
  margin-bottom: 20px;
}

.control-label {
  display: block;
  margin-bottom: 8px;
  font-size: 12px;
  font-weight: 600;
  color: #495057;
  text-transform: uppercase;
}

.checkbox-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* ===== 中央图形区域 ===== */
.rqt-graph-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #ffffff;
  position: relative;
}

.graph-container {
  flex: 1;
  position: relative;
  overflow: hidden;
  background: #ffffff;
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
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid #dee2e6;
  border-radius: 6px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.zoom-level {
  font-size: 12px;
  color: #6c757d;
  min-width: 40px;
  text-align: center;
  font-weight: 500;
}

.rqt-topology-svg {
  width: 100%;
  height: 100%;
  cursor: default;
}

/* ===== 右侧详情面板 ===== */
.rqt-detail-panel {
  width: 280px;
  background: #ffffff;
  border-left: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease;
  overflow: hidden;
}

.rqt-detail-panel.collapsed {
  width: 50px;
}

.detail-content {
  padding: 16px;
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid #dee2e6;
}

.detail-header h5 {
  margin: 0;
  font-size: 14px;
  color: #495057;
  font-weight: 600;
}

.detail-info {
  margin-bottom: 16px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
  border-bottom: 1px solid #f8f9fa;
}

.info-item label {
  font-size: 12px;
  color: #6c757d;
  font-weight: 500;
}

.info-item span {
  font-size: 12px;
  color: #495057;
  font-weight: 600;
}

.connections-list h6 {
  margin: 0 0 8px 0;
  font-size: 12px;
  color: #495057;
  font-weight: 600;
  text-transform: uppercase;
}

.connection-group {
  margin-bottom: 12px;
}

.connection-group label {
  font-size: 11px;
  color: #6c757d;
  font-weight: 500;
  display: block;
  margin-bottom: 4px;
}

.connection-group ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.connection-group li {
  font-size: 11px;
  color: #495057;
  padding: 2px 0;
  padding-left: 8px;
  border-left: 2px solid #007bff;
  margin-bottom: 2px;
}

.no-selection {
  text-align: center;
  color: #6c757d;
  font-style: italic;
  padding: 32px 16px;
}

/* ===== 节点和连接样式 ===== */
.rqt-node, .rqt-topic {
  cursor: pointer;
}

.rqt-node ellipse, .rqt-topic rect {
  transition: stroke-width 0.15s ease, stroke 0.15s ease, filter 0.15s ease;
}

.rqt-connection {
  cursor: pointer;
  transition: all 0.2s ease;
}

.rqt-connection:hover,
.rqt-connection.selected {
  stroke: #007bff !important;
  stroke-width: 2 !important;
}

/* ===== 增强的悬浮提示 ===== */
.rqt-tooltip {
  z-index: 1000;
  background: #ffffff;
  border: 1px solid #dee2e6;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  min-width: 200px;
  max-width: 300px;
  font-size: 12px;
  pointer-events: none;
  position: fixed;
}

.tooltip-header {
  padding: 8px 12px;
  border-bottom: 1px solid #f8f9fa;
  background: #f8f9fa;
  border-radius: 8px 8px 0 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.tooltip-header strong {
  color: #495057;
  font-weight: 600;
  font-size: 13px;
}

.tooltip-content {
  padding: 8px 12px;
}

.tooltip-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 4px 0;
}

.tooltip-label {
  color: #6c757d;
  font-weight: 500;
  font-size: 11px;
}

.tooltip-value {
  color: #495057;
  font-weight: 600;
  font-size: 11px;
  max-width: 120px;
  text-align: right;
  word-break: break-all;
}

/* ===== 滚动条样式 ===== */
.panel-content::-webkit-scrollbar {
  width: 6px;
}

.panel-content::-webkit-scrollbar-track {
  background: #f8f9fa;
}

.panel-content::-webkit-scrollbar-thumb {
  background: #dee2e6;
  border-radius: 3px;
}

.panel-content::-webkit-scrollbar-thumb:hover {
  background: #adb5bd;
}

/* ===== 响应式设计 ===== */
@media (max-width: 1200px) {
  .rqt-control-panel {
    width: 200px;
  }

  .rqt-detail-panel {
    width: 240px;
  }
}

@media (max-width: 768px) {
  .rqt-toolbar {
    flex-wrap: wrap;
    gap: 8px;
  }

  .statistics-display {
    gap: 12px;
  }

  .rqt-control-panel {
    width: 180px;
  }

  .rqt-detail-panel {
    width: 200px;
  }
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
  transition: filter 0.15s ease;
}

.rqt-node:hover ellipse {
  stroke-width: 3 !important;
  stroke: #409eff !important;
  filter: drop-shadow(0 2px 4px rgba(64, 158, 255, 0.3)) !important;
}

.rqt-node.selected {
  filter: url(#selected-glow);
}

/* ===== 主题样式 ===== */
.rqt-topic {
  cursor: pointer;
  transition: filter 0.15s ease;
}

.rqt-topic:hover rect {
  stroke-width: 3 !important;
  stroke: #409eff !important;
  filter: drop-shadow(0 2px 4px rgba(64, 158, 255, 0.3)) !important;
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

/* ===== 数据流动画样式 ===== */
.data-flow-particle {
  filter: drop-shadow(0 0 4px rgba(64, 158, 255, 0.6));
  animation: particle-pulse 2s ease-in-out infinite;
}

@keyframes particle-pulse {
  0%, 100% {
    transform: scale(1);
    opacity: 0.8;
  }
  50% {
    transform: scale(1.2);
    opacity: 1;
  }
}

.animation-layer {
  pointer-events: none;
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