/**
 * 图形布局算法模块
 * 
 * 提供多种布局算法用于ROS节点-主题关系图的可视化
 * 遵循RQT Node Graph的视觉风格和层次结构
 * 
 * @author ROS Web Viz Team
 * @version 1.0.0
 */

/**
 * 节点类型定义
 * @typedef {Object} GraphNode
 * @property {string} id - 节点唯一标识
 * @property {string} name - 节点名称
 * @property {string} type - 节点类型 ('node' | 'topic')
 * @property {number} x - X坐标
 * @property {number} y - Y坐标
 * @property {number} width - 宽度
 * @property {number} height - 高度
 * @property {string[]} publishers - 发布的主题列表
 * @property {string[]} subscribers - 订阅的主题列表
 * @property {boolean} fixed - 是否固定位置
 */

/**
 * 连接类型定义
 * @typedef {Object} GraphConnection
 * @property {string} id - 连接唯一标识
 * @property {string} from - 源节点ID
 * @property {string} to - 目标节点ID
 * @property {string} type - 连接类型 ('publisher' | 'subscriber')
 * @property {string} topicName - 主题名称
 */

/**
 * 布局配置类型定义
 * @typedef {Object} LayoutConfig
 * @property {number} width - 画布宽度
 * @property {number} height - 画布高度
 * @property {number} nodeSpacing - 节点间距
 * @property {number} levelSpacing - 层级间距
 * @property {number} iterations - 力导向布局迭代次数
 * @property {boolean} enablePhysics - 是否启用物理引擎
 */

/**
 * 分层布局算法类
 * 
 * 实现类似RQT Node Graph的分层显示效果：
 * - 节点按层级分布
 * - 主题作为中间层连接节点
 * - 支持拖拽和动画
 * - 自动缩放适应内容
 */
export class HierarchicalLayout {
  /**
   * 初始化布局算法
   * @param {LayoutConfig} config - 布局配置
   */
  constructor(config = {}) {
    this.config = {
      width: 800,
      height: 600,
      nodeSpacing: 120,
      levelSpacing: 200,
      iterations: 100,
      enablePhysics: true,
      minNodeSpacing: 80,
      maxNodeSpacing: 180,
      minLevelSpacing: 120,
      maxLevelSpacing: 300,
      padding: 50,
      autoScale: true,
      maxZoomLevel: 3.0,
      minZoomLevel: 0.2,
      ...config
    }
    
    // 布局状态
    this.nodes = new Map()
    this.connections = []
    this.levels = new Map()
    
    // 自动缩放相关
    this.boundingBox = {
      minX: Infinity,
      maxX: -Infinity,
      minY: Infinity,
      maxY: -Infinity
    }
    this.currentScale = 1.0
    this.recommendedZoom = 1.0
    
    // 物理引擎参数
    this.physics = {
      springLength: 100,
      springStrength: 0.1,
      damping: 0.9,
      repulsionStrength: 1000
    }
  }
  
  /**
   * 设置图形数据
   * @param {GraphNode[]} nodes - 节点列表
   * @param {GraphConnection[]} connections - 连接列表
   */
  setData(nodes, connections) {
    this.nodes.clear()
    nodes.forEach(node => this.nodes.set(node.id, { ...node }))
    this.connections = connections.map(conn => ({ ...conn }))
    
    // 分析层级结构
    this.analyzeLevels()
  }
  
  /**
   * 分析节点层级结构
   * 
   * 优化算法：
   * 1. 分离节点和主题，实现清晰的层次化布局
   * 2. 将节点放在外层，主题放在中间层
   * 3. 创建类似RQT的清晰布局结构
   */
  analyzeLevels() {
    this.levels.clear()
    
    // 分离节点和主题
    const rosNodes = new Map()      // ROS节点
    const rosTopics = new Map()     // ROS主题
    
    this.nodes.forEach(node => {
      if (node.type === 'node') {
        rosNodes.set(node.id, node)
      } else if (node.type === 'topic') {
        rosTopics.set(node.id, node)
      }
    })
    
    // console.log(`发现 ${rosNodes.size} 个节点和 ${rosTopics.size} 个主题`)
    
    // 分析节点的发布/订阅关系
    const nodeConnections = new Map()
    rosNodes.forEach(node => {
      nodeConnections.set(node.id, {
        publishes: new Set(node.publishers || []),
        subscribes: new Set(node.subscribers || []),
        level: -1
      })
    })
    
    // 采用改进的层次分配策略
    let currentLevel = 0
    
    // Level 0: 主要发布者节点（发布多于订阅的节点）
    const publisherNodes = []
    nodeConnections.forEach((conn, nodeId) => {
      if (conn.publishes.size > conn.subscribes.size) {
        conn.level = 0
        publisherNodes.push(nodeId)
      }
    })
    if (publisherNodes.length > 0) {
      this.levels.set(0, publisherNodes)
      currentLevel = 1
    }
    
    // 按主题类型分组，分配到不同层级
    const topicsByType = this.groupTopicsByType(rosTopics)
    
    // Level 1-N: 根据主题类型和重要性分层
    Object.keys(topicsByType).forEach(messageType => {
      const topics = topicsByType[messageType]
      if (topics.length > 0) {
        // 如果该类型主题过多，分成多个层级
        if (topics.length > 6) {
          const chunkedTopics = this.chunkArray(topics, 4)
          chunkedTopics.forEach(chunk => {
            this.levels.set(currentLevel, chunk.map(t => t.id))
            currentLevel++
          })
        } else {
          this.levels.set(currentLevel, topics.map(t => t.id))
          currentLevel++
        }
      }
    })
    
    // 最后几个层级: 订阅者节点
    const subscriberNodes = []
    const balancedNodes = []
    
    nodeConnections.forEach((conn, nodeId) => {
      if (conn.subscribes.size > conn.publishes.size) {
        subscriberNodes.push(nodeId)
      } else if (conn.level === -1) { // 未分配层级的节点
        balancedNodes.push(nodeId)
      }
    })
    
    if (subscriberNodes.length > 0) {
      this.levels.set(currentLevel, subscriberNodes)
      currentLevel++
    }
    
    if (balancedNodes.length > 0) {
      this.levels.set(currentLevel, balancedNodes)
    }
    
    // console.log('优化层级分析完成:', this.levels)
  }
  
  /**
   * 执行分层布局
   * @returns {GraphNode[]} 布局后的节点列表
   */
  applyHierarchicalLayout() {
    const layoutNodes = []
    
    // 动态调整间距以适应内容
    this.optimizeSpacing()

    const centerX = this.config.width / 2

    // 重置边界框
    this.resetBoundingBox()

    // RQT风格优化：更紧凑的布局
    this.config.levelSpacing = Math.max(80, this.config.levelSpacing * 0.7)
    this.config.nodeSpacing = Math.max(60, this.config.nodeSpacing * 0.8)
    
    // 按层级布局节点
    this.levels.forEach((nodeIds, level) => {
      const levelY = this.config.padding + level * this.config.levelSpacing
      
      // 对节点进行智能排序以减少连接线交叉
      const sortedNodeIds = this.sortNodesForOptimalLayout(nodeIds, level)
      const nodeCount = sortedNodeIds.length
      
      // 计算合适的间距
      const levelSpacing = this.calculateOptimalSpacing(nodeCount, level)
      const totalWidth = Math.max(nodeCount - 1, 0) * levelSpacing
      const startX = centerX - totalWidth / 2
      
      sortedNodeIds.forEach((nodeId, index) => {
        const node = this.nodes.get(nodeId)
        if (node) {
          const layoutNode = {
            ...node,
            x: startX + index * levelSpacing,
            y: levelY,
            level: level,
            // 根据节点类型设置样式
            style: this.getNodeStyle(node)
          }
          layoutNodes.push(layoutNode)
          
          // 更新边界框
          this.updateBoundingBox(layoutNode)
        }
      })
    })
    
    // 计算推荐的缩放级别
    if (this.config.autoScale) {
      this.calculateRecommendedZoom()
    }
    
    // console.log(`分层布局完成，共${layoutNodes.length}个节点，推荐缩放: ${this.recommendedZoom}`)
    return layoutNodes
  }
  
  /**
   * 执行环形布局
   * @returns {GraphNode[]} 布局后的节点列表
   */
  applyCircularLayout() {
    const layoutNodes = []
    
    // 动态调整间距以适应内容
    this.optimizeSpacing()
    
    const centerX = this.config.width / 2
    const centerY = this.config.height / 2
    
    // 重置边界框
    this.resetBoundingBox()
    
    // 分离节点和主题
    const rosNodes = []
    const rosTopics = []
    
    this.nodes.forEach(node => {
      if (node.type === 'node') {
        rosNodes.push(node)
      } else if (node.type === 'topic') {
        rosTopics.push(node)
      }
    })
    
    // 计算半径
    const nodeCount = rosNodes.length
    const topicCount = rosTopics.length
    
    // 节点外圈半径
    const nodeRadius = Math.min(this.config.width, this.config.height) * 0.35
    // 主题内圈半径  
    const topicRadius = nodeRadius * 0.6
    
    // 布局节点（外圈）
    rosNodes.forEach((node, index) => {
      const angle = (index / nodeCount) * 2 * Math.PI
      const layoutNode = {
        ...node,
        x: centerX + Math.cos(angle) * nodeRadius,
        y: centerY + Math.sin(angle) * nodeRadius,
        level: 0,
        style: this.getNodeStyle(node)
      }
      layoutNodes.push(layoutNode)
      this.updateBoundingBox(layoutNode)
    })
    
    // 布局主题（内圈）
    rosTopics.forEach((topic, index) => {
      const angle = (index / topicCount) * 2 * Math.PI
      const layoutNode = {
        ...topic,
        x: centerX + Math.cos(angle) * topicRadius,
        y: centerY + Math.sin(angle) * topicRadius,
        level: 1,
        style: this.getNodeStyle(topic)
      }
      layoutNodes.push(layoutNode)
      this.updateBoundingBox(layoutNode)
    })
    
    // 计算推荐的缩放级别
    if (this.config.autoScale) {
      this.calculateRecommendedZoom()
    }
    
    console.log(`环形布局完成，共${layoutNodes.length}个节点，推荐缩放: ${this.recommendedZoom}`)
    return layoutNodes
  }
  
  /**
   * 获取节点样式
   * @param {GraphNode} node - 节点对象
   * @returns {Object} 样式对象
   */
  getNodeStyle(node) {
    if (node.type === 'node') {
      return {
        shape: 'ellipse',
        width: 100,
        height: 50,
        fill: '#f8f9fa',
        stroke: '#212529',
        strokeWidth: 2,
        textColor: '#212529'
      }
    } else if (node.type === 'topic') {
      // 根据消息类型返回不同颜色
      const messageType = node.messageType || 'unknown'
      return {
        shape: 'rectangle',
        width: 120,
        height: 30,
        fill: this.getTopicColorByType(messageType),
        stroke: '#212529',
        strokeWidth: 1,
        textColor: '#212529'
      }
    }

    return {
      shape: 'circle',
      width: 40,
      height: 40,
      fill: '#f8f9fa',
      stroke: '#212529',
      strokeWidth: 1,
      textColor: '#212529'
    }
  }
  
  /**
   * 力导向布局优化
   * 
   * 在分层布局的基础上进行微调，避免节点重叠
   * @param {GraphNode[]} nodes - 节点列表
   * @returns {GraphNode[]} 优化后的节点列表
   */
  applyForceDirectedOptimization(nodes) {
    if (!this.config.enablePhysics) {
      return nodes
    }
    
    const layoutNodes = nodes.map(node => ({ ...node }))
    
    // 执行物理模拟
    for (let i = 0; i < this.config.iterations; i++) {
      this.updatePhysics(layoutNodes)
    }
    
    return layoutNodes
  }
  
  /**
   * 更新物理引擎
   * @param {GraphNode[]} nodes - 节点列表
   */
  updatePhysics(nodes) {
    const forces = new Map()
    
    // 初始化力
    nodes.forEach(node => {
      forces.set(node.id, { fx: 0, fy: 0 })
    })
    
    // 计算排斥力
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const nodeA = nodes[i]
        const nodeB = nodes[j]
        
        // 同一层级的节点之间有更强的排斥力
        const levelMultiplier = nodeA.level === nodeB.level ? 2 : 1
        
        this.applyRepulsionForce(nodeA, nodeB, forces, levelMultiplier)
      }
    }
    
    // 计算连接的弹簧力
    this.connections.forEach(conn => {
      const nodeA = nodes.find(n => n.id === conn.from)
      const nodeB = nodes.find(n => n.id === conn.to)
      
      if (nodeA && nodeB) {
        this.applySpringForce(nodeA, nodeB, forces)
      }
    })
    
    // 应用力并更新位置
    nodes.forEach(node => {
      if (!node.fixed) {
        const force = forces.get(node.id)
        
        // 应用阻尼
        force.fx *= this.physics.damping
        force.fy *= this.physics.damping
        
        // 更新位置
        node.x += force.fx
        node.y += force.fy
        
        // 边界约束
        node.x = Math.max(50, Math.min(this.config.width - 50, node.x))
        node.y = Math.max(50, Math.min(this.config.height - 50, node.y))
      }
    })
  }
  
  /**
   * 应用排斥力
   * @param {GraphNode} nodeA - 节点A
   * @param {GraphNode} nodeB - 节点B
   * @param {Map} forces - 力映射
   * @param {number} multiplier - 力的倍数
   */
  applyRepulsionForce(nodeA, nodeB, forces, multiplier = 1) {
    const dx = nodeA.x - nodeB.x
    const dy = nodeA.y - nodeB.y
    const distance = Math.sqrt(dx * dx + dy * dy)
    
    if (distance > 0 && distance < 200) {
      const force = (this.physics.repulsionStrength * multiplier) / (distance * distance)
      const fx = (dx / distance) * force
      const fy = (dy / distance) * force
      
      const forceA = forces.get(nodeA.id)
      const forceB = forces.get(nodeB.id)
      
      forceA.fx += fx
      forceA.fy += fy
      forceB.fx -= fx
      forceB.fy -= fy
    }
  }
  
  /**
   * 应用弹簧力
   * @param {GraphNode} nodeA - 节点A
   * @param {GraphNode} nodeB - 节点B
   * @param {Map} forces - 力映射
   */
  applySpringForce(nodeA, nodeB, forces) {
    const dx = nodeB.x - nodeA.x
    const dy = nodeB.y - nodeA.y
    const distance = Math.sqrt(dx * dx + dy * dy)
    
    if (distance > 0) {
      const displacement = distance - this.physics.springLength
      const force = displacement * this.physics.springStrength
      const fx = (dx / distance) * force
      const fy = (dy / distance) * force
      
      const forceA = forces.get(nodeA.id)
      const forceB = forces.get(nodeB.id)
      
      forceA.fx += fx
      forceA.fy += fy
      forceB.fx -= fx
      forceB.fy -= fy
    }
  }
  
  /**
   * 更新布局配置
   * @param {Partial<LayoutConfig>} newConfig - 新的配置
   */
  updateConfig(newConfig) {
    this.config = { ...this.config, ...newConfig }
  }
  
  /**
   * 动态优化节点间距
   * 根据节点数量和可用空间自动调整间距
   */
  optimizeSpacing() {
    if (this.levels.size === 0) return
    
    // 找出最宽的层级
    let maxNodesInLevel = 0
    this.levels.forEach((nodeIds) => {
      maxNodesInLevel = Math.max(maxNodesInLevel, nodeIds.length)
    })
    
    // 根据最宽层级调整节点间距
    const availableWidth = this.config.width - 2 * this.config.padding
    const optimalNodeSpacing = maxNodesInLevel > 1 ? 
      Math.min(this.config.maxNodeSpacing, Math.max(this.config.minNodeSpacing, availableWidth / (maxNodesInLevel - 1))) :
      this.config.nodeSpacing
    
    this.config.nodeSpacing = optimalNodeSpacing
    
    // 根据层级数量调整层级间距
    const levelCount = this.levels.size
    const availableHeight = this.config.height - 2 * this.config.padding
    const optimalLevelSpacing = levelCount > 1 ?
      Math.min(this.config.maxLevelSpacing, Math.max(this.config.minLevelSpacing, availableHeight / (levelCount - 1))) :
      this.config.levelSpacing
    
    this.config.levelSpacing = optimalLevelSpacing
    
    // console.log(`间距优化完成 - 节点间距: ${this.config.nodeSpacing}, 层级间距: ${this.config.levelSpacing}`)
  }
  
  /**
   * 重置边界框
   */
  resetBoundingBox() {
    this.boundingBox = {
      minX: Infinity,
      maxX: -Infinity,
      minY: Infinity,
      maxY: -Infinity
    }
  }
  
  /**
   * 更新边界框
   * @param {GraphNode} node - 节点对象
   */
  updateBoundingBox(node) {
    const style = node.style || this.getNodeStyle(node)
    const halfWidth = (style.width || 100) / 2
    const halfHeight = (style.height || 50) / 2
    
    this.boundingBox.minX = Math.min(this.boundingBox.minX, node.x - halfWidth)
    this.boundingBox.maxX = Math.max(this.boundingBox.maxX, node.x + halfWidth)
    this.boundingBox.minY = Math.min(this.boundingBox.minY, node.y - halfHeight)
    this.boundingBox.maxY = Math.max(this.boundingBox.maxY, node.y + halfHeight)
  }
  
  /**
   * 计算推荐的缩放级别
   * 确保所有内容都能在视窗中可见
   */
  calculateRecommendedZoom() {
    if (this.boundingBox.minX === Infinity) {
      this.recommendedZoom = 1.0
      return
    }
    
    const contentWidth = this.boundingBox.maxX - this.boundingBox.minX
    const contentHeight = this.boundingBox.maxY - this.boundingBox.minY
    
    // 添加额外的边距
    const margin = 100
    const availableWidth = this.config.width - 2 * margin
    const availableHeight = this.config.height - 2 * margin
    
    // 计算适合宽度和高度的缩放比例
    const scaleX = contentWidth > 0 ? availableWidth / contentWidth : 1.0
    const scaleY = contentHeight > 0 ? availableHeight / contentHeight : 1.0
    
    // 选择较小的缩放比例以确保内容完全可见
    let recommendedScale = Math.min(scaleX, scaleY)
    
    // 限制缩放范围
    recommendedScale = Math.max(this.config.minZoomLevel, Math.min(this.config.maxZoomLevel, recommendedScale))
    
    this.recommendedZoom = recommendedScale
    this.currentScale = recommendedScale
  }
  
  /**
   * 获取推荐的视图中心点
   * @returns {{x: number, y: number}} 中心点坐标
   */
  getRecommendedCenter() {
    if (this.boundingBox.minX === Infinity) {
      return { x: this.config.width / 2, y: this.config.height / 2 }
    }
    
    return {
      x: (this.boundingBox.minX + this.boundingBox.maxX) / 2,
      y: (this.boundingBox.minY + this.boundingBox.maxY) / 2
    }
  }
  
  /**
   * 获取推荐的变换参数
   * @returns {{scale: number, translateX: number, translateY: number}} 变换参数
   */
  getRecommendedTransform() {
    const center = this.getRecommendedCenter()
    const viewCenterX = this.config.width / 2
    const viewCenterY = this.config.height / 2
    
    return {
      scale: this.recommendedZoom,
      translateX: viewCenterX - center.x * this.recommendedZoom,
      translateY: viewCenterY - center.y * this.recommendedZoom
    }
  }
  
  /**
   * 智能排序节点以减少连接线交叉
   * @param {string[]} nodeIds - 节点ID列表
   * @param {number} level - 当前层级
   * @returns {string[]} 排序后的节点ID列表
   */
  sortNodesForOptimalLayout(nodeIds, level) {
    if (nodeIds.length <= 1) return nodeIds
    
    // 获取节点详细信息
    const nodeInfos = nodeIds.map(nodeId => {
      const node = this.nodes.get(nodeId)
      return {
        id: nodeId,
        node: node,
        connectionCount: (node.publishers?.length || 0) + (node.subscribers?.length || 0),
        name: node.name || nodeId
      }
    })
    
    // 按连接数量和名称排序
    nodeInfos.sort((a, b) => {
      // 首先按连接数量排序（连接多的在中间）
      if (a.connectionCount !== b.connectionCount) {
        return b.connectionCount - a.connectionCount
      }
      
      // 然后按名称排序保证一致性
      return a.name.localeCompare(b.name)
    })
    
    return nodeInfos.map(info => info.id)
  }
  
  /**
   * 计算最优间距
   * @param {number} nodeCount - 节点数量
   * @param {number} level - 层级
   * @returns {number} 间距值
   */
  calculateOptimalSpacing(nodeCount, level) {
    if (nodeCount <= 1) return this.config.nodeSpacing
    
    // 根据节点数量动态调整间距
    const baseSpacing = this.config.nodeSpacing
    let spacing = baseSpacing
    
    // 节点数量越多，间距适当减小（但不低于最小值）
    if (nodeCount > 5) {
      const reductionFactor = Math.min(0.8, 1 - (nodeCount - 5) * 0.05)
      spacing = Math.max(this.config.minNodeSpacing, baseSpacing * reductionFactor)
    }
    
    // 主题层可以使用稍微紧凑的间距
    const isTopicLayer = this.isTopicLayer(level)
    if (isTopicLayer) {
      spacing = Math.max(this.config.minNodeSpacing, spacing * 0.9)
    }
    
    return spacing
  }
  
  /**
   * 判断是否为主题层
   * @param {number} level - 层级
   * @returns {boolean} 是否为主题层
   */
  isTopicLayer(level) {
    // 检查该层级是否主要包含主题节点
    const levelNodes = this.levels.get(level) || []
    let topicCount = 0
    
    levelNodes.forEach(nodeId => {
      const node = this.nodes.get(nodeId)
      if (node && node.type === 'topic') {
        topicCount++
      }
    })
    
    return topicCount > levelNodes.length / 2
  }
  
  /**
   * 按消息类型分组主题
   * @param {Map} rosTopics - 主题Map
   * @returns {Object} 按类型分组的主题
   */
  groupTopicsByType(rosTopics) {
    const grouped = {}
    
    // 定义主题类型优先级
    const typePriority = {
      'sensor_msgs/msg/PointCloud2': 1,
      'sensor_msgs/msg/LaserScan': 2,
      'sensor_msgs/msg/Image': 3,
      'nav_msgs/msg/OccupancyGrid': 4,
      'nav_msgs/msg/Odometry': 5,
      'geometry_msgs/msg/Twist': 6,
      'tf2_msgs/msg/TFMessage': 7,
      'std_msgs/msg/String': 8,
      'diagnostic_msgs/msg/DiagnosticArray': 9
    }
    
    rosTopics.forEach(topic => {
      const messageType = topic.messageType || 'unknown'
      if (!grouped[messageType]) {
        grouped[messageType] = []
      }
      grouped[messageType].push(topic)
    })
    
    // 按优先级排序分组
    const sortedTypes = Object.keys(grouped).sort((a, b) => {
      const priorityA = typePriority[a] || 999
      const priorityB = typePriority[b] || 999
      return priorityA - priorityB
    })
    
    const result = {}
    sortedTypes.forEach(type => {
      result[type] = grouped[type]
    })
    
    return result
  }
  
  /**
   * 将数组分割成指定大小的块
   * @param {Array} array - 要分割的数组
   * @param {number} chunkSize - 每块大小
   * @returns {Array[]} 分割后的数组块
   */
  chunkArray(array, chunkSize) {
    const chunks = []
    for (let i = 0; i < array.length; i += chunkSize) {
      chunks.push(array.slice(i, i + chunkSize))
    }
    return chunks
  }

  /**
   * 根据消息类型获取主题颜色
   * @param {string} messageType - 消息类型
   * @returns {string} 颜色值
   */
  getTopicColorByType(messageType) {
    const colorMap = {
      // 传感器消息 - 绿色系
      'sensor_msgs/msg/PointCloud2': '#bde7bd',
      'sensor_msgs/msg/LaserScan': '#a6d4fa',
      'sensor_msgs/msg/Image': '#f4c2a6',
      'sensor_msgs/msg/CompressedImage': '#f4c2a6',
      'sensor_msgs/msg/CameraInfo': '#f4c2a6',
      'sensor_msgs/msg/Imu': '#c8e6c9',
      'sensor_msgs/msg/NavSatFix': '#a5d6a7',
      
      // 导航消息 - 蓝色系
      'nav_msgs/msg/OccupancyGrid': '#d1c4e9',
      'nav_msgs/msg/Odometry': '#a6f4de',
      'nav_msgs/msg/Path': '#81d4fa',
      'nav_msgs/msg/MapMetaData': '#90caf9',
      
      // 几何消息 - 紫色系
      'geometry_msgs/msg/Twist': '#ce93d8',
      'geometry_msgs/msg/Pose': '#ba68c8',
      'geometry_msgs/msg/PoseStamped': '#ab47bc',
      'geometry_msgs/msg/Transform': '#9c27b0',
      'geometry_msgs/msg/Vector3': '#8e24aa',
      'geometry_msgs/msg/Point': '#7b1fa2',
      
      // TF消息 - 灰色系
      'tf2_msgs/msg/TFMessage': '#d3d3d3',
      'tf2_msgs/msg/TF2Error': '#bdbdbd',
      
      // 标准消息 - 橙色系
      'std_msgs/msg/String': '#ffcc80',
      'std_msgs/msg/Bool': '#ffb74d',
      'std_msgs/msg/Int32': '#ffa726',
      'std_msgs/msg/Float32': '#ff9800',
      'std_msgs/msg/Header': '#ff8f00',
      
      // 诊断消息 - 红色系
      'diagnostic_msgs/msg/DiagnosticArray': '#ffcdd2',
      'diagnostic_msgs/msg/DiagnosticStatus': '#ef9a9a',
      
      // 动作消息 - 黄色系
      'actionlib_msgs/msg/GoalStatus': '#fff9c4',
      'actionlib_msgs/msg/GoalID': '#f9fbe7',
      
      // 可视化消息 - 青色系
      'visualization_msgs/msg/Marker': '#b2dfdb',
      'visualization_msgs/msg/MarkerArray': '#80cbc4',
      
      // 其他常见消息类型
      'rosgraph_msgs/msg/Log': '#e0e0e0',
      'rcl_interfaces/msg/ParameterEvent': '#f5f5f5',
      'builtin_interfaces/msg/Time': '#eeeeee'
    }

    // 如果没有精确匹配，尝试部分匹配
    if (!colorMap[messageType]) {
      if (messageType.includes('sensor_msgs')) {
        return '#bde7bd'  // 传感器消息默认绿色
      } else if (messageType.includes('nav_msgs')) {
        return '#a6f4de'  // 导航消息默认青色
      } else if (messageType.includes('geometry_msgs')) {
        return '#ce93d8'  // 几何消息默认紫色
      } else if (messageType.includes('std_msgs')) {
        return '#ffcc80'  // 标准消息默认橙色
      } else if (messageType.includes('diagnostic_msgs')) {
        return '#ffcdd2'  // 诊断消息默认红色
      } else if (messageType.includes('visualization_msgs')) {
        return '#b2dfdb'  // 可视化消息默认青色
      } else {
        return '#bde7bd'  // 默认绿色
      }
    }

    return colorMap[messageType]
  }
}

/**
 * 创建默认的分层布局实例
 * @param {Partial<LayoutConfig>} config - 布局配置
 * @returns {HierarchicalLayout} 布局实例
 */
export function createHierarchicalLayout(config = {}) {
  return new HierarchicalLayout(config)
}

/**
 * 工具函数：计算两点距离
 * @param {GraphNode} nodeA - 节点A
 * @param {GraphNode} nodeB - 节点B
 * @returns {number} 距离
 */
export function calculateDistance(nodeA, nodeB) {
  const dx = nodeA.x - nodeB.x
  const dy = nodeA.y - nodeB.y
  return Math.sqrt(dx * dx + dy * dy)
}

/**
 * 工具函数：检查两个矩形是否重叠
 * @param {GraphNode} nodeA - 节点A
 * @param {GraphNode} nodeB - 节点B
 * @returns {boolean} 是否重叠
 */
export function checkNodeOverlap(nodeA, nodeB) {
  const buffer = 20 // 缓冲区
  
  return !(
    nodeA.x + nodeA.width / 2 + buffer < nodeB.x - nodeB.width / 2 ||
    nodeB.x + nodeB.width / 2 + buffer < nodeA.x - nodeA.width / 2 ||
    nodeA.y + nodeA.height / 2 + buffer < nodeB.y - nodeB.height / 2 ||
    nodeB.y + nodeB.height / 2 + buffer < nodeA.y - nodeA.height / 2
  )
}