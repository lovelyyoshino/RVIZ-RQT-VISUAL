/**
 * 图形交互控制模块
 * 
 * 处理ROS节点图的所有交互操作：
 * - 鼠标拖拽和平移
 * - 滚轮缩放
 * - 节点选择和高亮
 * - 上下文菜单
 * 
 * @author ROS Web Viz Team
 * @version 1.0.0
 */

/**
 * 视图变换类型定义
 * @typedef {Object} ViewTransform
 * @property {number} translateX - X轴平移
 * @property {number} translateY - Y轴平移
 * @property {number} scale - 缩放比例
 */

/**
 * 交互状态类型定义
 * @typedef {Object} InteractionState
 * @property {boolean} isDragging - 是否正在拖拽
 * @property {boolean} isPanning - 是否正在平移
 * @property {string|null} selectedNodeId - 选中的节点ID
 * @property {string|null} hoveredNodeId - 悬停的节点ID
 * @property {Object|null} contextMenu - 上下文菜单信息
 */

/**
 * 鼠标事件数据类型定义
 * @typedef {Object} MouseEventData
 * @property {number} x - X坐标
 * @property {number} y - Y坐标
 * @property {number} deltaX - X轴偏移
 * @property {number} deltaY - Y轴偏移
 * @property {string} button - 鼠标按键 ('left' | 'right' | 'middle')
 * @property {boolean} ctrlKey - 是否按下Ctrl键
 * @property {boolean} shiftKey - 是否按下Shift键
 */

/**
 * 图形交互控制器类
 * 
 * 管理所有用户交互操作，提供流畅的用户体验
 */
export class GraphInteractionController {
  /**
   * 初始化交互控制器
   * @param {HTMLElement} container - 容器元素
   * @param {Object} options - 配置选项
   */
  constructor(container, options = {}) {
    this.container = container
    this.options = {
      enablePan: true,
      enableZoom: true,
      enableDrag: true,
      enableSelection: true,
      minScale: 0.1,
      maxScale: 5.0,
      zoomSensitivity: 0.1,
      ...options
    }
    
    // 视图变换状态
    this.transform = {
      translateX: 0,
      translateY: 0,
      scale: 1.0
    }
    
    // 交互状态
    this.state = {
      isDragging: false,
      isPanning: false,
      selectedNodeId: null,
      hoveredNodeId: null,
      contextMenu: null
    }
    
    // 拖拽状态
    this.dragState = {
      startX: 0,
      startY: 0,
      currentX: 0,
      currentY: 0,
      draggedNodeId: null,
      originalNodePosition: null
    }
    
    // 平移状态
    this.panState = {
      startX: 0,
      startY: 0,
      startTranslateX: 0,
      startTranslateY: 0
    }
    
    // 事件监听器映射
    this.eventListeners = new Map()

    // 防抖定时器
    this.hoverTimeout = null

    // 初始化事件监听
    this.initEventListeners()
  }
  
  /**
   * 初始化事件监听器
   */
  initEventListeners() {
    // 鼠标事件
    this.addEventListener('mousedown', this.handleMouseDown.bind(this))
    this.addEventListener('mousemove', this.handleMouseMove.bind(this))
    this.addEventListener('mouseup', this.handleMouseUp.bind(this))
    this.addEventListener('wheel', this.handleWheel.bind(this))
    this.addEventListener('contextmenu', this.handleContextMenu.bind(this))
    
    // 键盘事件
    this.addEventListener('keydown', this.handleKeyDown.bind(this))
    this.addEventListener('keyup', this.handleKeyUp.bind(this))
    
    // 防止默认的拖拽行为
    this.addEventListener('dragstart', (e) => e.preventDefault())
    
    console.log('图形交互控制器初始化完成')
  }
  
  /**
   * 添加事件监听器
   * @param {string} eventType - 事件类型
   * @param {Function} handler - 事件处理函数
   */
  addEventListener(eventType, handler) {
    this.container.addEventListener(eventType, handler)
    this.eventListeners.set(eventType, handler)
  }
  
  /**
   * 移除事件监听器
   * @param {string} eventType - 事件类型
   */
  removeEventListener(eventType) {
    const handler = this.eventListeners.get(eventType)
    if (handler) {
      this.container.removeEventListener(eventType, handler)
      this.eventListeners.delete(eventType)
    }
  }
  
  /**
   * 处理鼠标按下事件
   * @param {MouseEvent} event - 鼠标事件
   */
  handleMouseDown(event) {
    event.preventDefault()
    
    const rect = this.container.getBoundingClientRect()
    const x = event.clientX - rect.left
    const y = event.clientY - rect.top
    
    // 转换为图形坐标
    const graphX = (x - this.transform.translateX) / this.transform.scale
    const graphY = (y - this.transform.translateY) / this.transform.scale
    
    if (event.button === 0) { // 左键
      const nodeId = this.findNodeAtPosition(graphX, graphY)
      
      if (nodeId && this.options.enableDrag) {
        // 开始拖拽节点
        this.startNodeDrag(nodeId, x, y, graphX, graphY)
      } else if (this.options.enablePan) {
        // 开始平移画布
        this.startPanning(x, y)
      }
      
      // 更新选中状态
      this.setSelectedNode(nodeId)
    }
    
    // 隐藏上下文菜单
    this.hideContextMenu()
    
    this.emitEvent('mousedown', { x, y, graphX, graphY, nodeId: this.findNodeAtPosition(graphX, graphY) })
  }
  
  /**
   * 处理鼠标移动事件
   * @param {MouseEvent} event - 鼠标事件
   */
  handleMouseMove(event) {
    const rect = this.container.getBoundingClientRect()
    const x = event.clientX - rect.left
    const y = event.clientY - rect.top
    
    // 转换为图形坐标
    const graphX = (x - this.transform.translateX) / this.transform.scale
    const graphY = (y - this.transform.translateY) / this.transform.scale
    
    if (this.state.isDragging && this.dragState.draggedNodeId) {
      // 拖拽节点
      this.updateNodeDrag(x, y, graphX, graphY)
    } else if (this.state.isPanning) {
      // 平移画布
      this.updatePanning(x, y)
    } else {
      // 更新悬停状态
      const hoveredNodeId = this.findNodeAtPosition(graphX, graphY)
      this.setHoveredNode(hoveredNodeId)
      
      // 更新光标样式
      this.updateCursor(hoveredNodeId)
    }
    
    this.emitEvent('mousemove', { x, y, graphX, graphY, nodeId: this.findNodeAtPosition(graphX, graphY) })
  }
  
  /**
   * 处理鼠标释放事件
   * @param {MouseEvent} event - 鼠标事件
   */
  handleMouseUp(event) {
    const rect = this.container.getBoundingClientRect()
    const x = event.clientX - rect.left
    const y = event.clientY - rect.top
    
    if (this.state.isDragging) {
      this.stopNodeDrag()
    }
    
    if (this.state.isPanning) {
      this.stopPanning()
    }
    
    this.emitEvent('mouseup', { x, y })
  }
  
  /**
   * 处理滚轮事件（缩放）
   * @param {WheelEvent} event - 滚轮事件
   */
  handleWheel(event) {
    if (!this.options.enableZoom) return
    
    event.preventDefault()
    
    const rect = this.container.getBoundingClientRect()
    const x = event.clientX - rect.left
    const y = event.clientY - rect.top
    
    // 计算缩放比例
    const zoomDelta = -event.deltaY * this.options.zoomSensitivity
    const newScale = Math.max(
      this.options.minScale,
      Math.min(this.options.maxScale, this.transform.scale * (1 + zoomDelta))
    )
    
    // 以鼠标位置为中心缩放
    const scaleRatio = newScale / this.transform.scale
    this.transform.translateX = x - (x - this.transform.translateX) * scaleRatio
    this.transform.translateY = y - (y - this.transform.translateY) * scaleRatio
    this.transform.scale = newScale
    
    this.updateTransform()
    this.emitEvent('zoom', { scale: newScale, centerX: x, centerY: y })
  }
  
  /**
   * 处理右键菜单事件
   * @param {MouseEvent} event - 鼠标事件
   */
  handleContextMenu(event) {
    event.preventDefault()
    
    const rect = this.container.getBoundingClientRect()
    const x = event.clientX - rect.left
    const y = event.clientY - rect.top
    const graphX = (x - this.transform.translateX) / this.transform.scale
    const graphY = (y - this.transform.translateY) / this.transform.scale
    
    const nodeId = this.findNodeAtPosition(graphX, graphY)
    
    if (nodeId) {
      this.showContextMenu(nodeId, event.clientX, event.clientY)
    }
    
    this.emitEvent('contextmenu', { x, y, graphX, graphY, nodeId })
  }
  
  /**
   * 处理键盘按下事件
   * @param {KeyboardEvent} event - 键盘事件
   */
  handleKeyDown(event) {
    switch (event.key) {
      case 'Escape':
        this.setSelectedNode(null)
        this.hideContextMenu()
        break
      case 'Delete':
        if (this.state.selectedNodeId) {
          this.emitEvent('nodeDelete', { nodeId: this.state.selectedNodeId })
        }
        break
      case '=':
      case '+':
        if (event.ctrlKey) {
          event.preventDefault()
          this.zoomIn()
        }
        break
      case '-':
        if (event.ctrlKey) {
          event.preventDefault()
          this.zoomOut()
        }
        break
      case '0':
        if (event.ctrlKey) {
          event.preventDefault()
          this.resetZoom()
        }
        break
    }
  }
  
  /**
   * 处理键盘释放事件
   * @param {KeyboardEvent} event - 键盘事件
   */
  handleKeyUp(event) {
    // 预留键盘释放事件处理
  }
  
  /**
   * 开始拖拽节点
   * @param {string} nodeId - 节点ID
   * @param {number} x - 屏幕X坐标
   * @param {number} y - 屏幕Y坐标
   * @param {number} graphX - 图形X坐标
   * @param {number} graphY - 图形Y坐标
   */
  startNodeDrag(nodeId, x, y, graphX, graphY) {
    this.state.isDragging = true
    this.dragState.draggedNodeId = nodeId
    this.dragState.startX = x
    this.dragState.startY = y
    this.dragState.currentX = x
    this.dragState.currentY = y
    
    // 记录节点原始位置
    const node = this.findNodeById(nodeId)
    if (node) {
      this.dragState.originalNodePosition = { x: node.x, y: node.y }
    }
    
    this.container.style.cursor = 'grabbing'
    this.emitEvent('nodeDragStart', { nodeId, x: graphX, y: graphY })
  }
  
  /**
   * 更新节点拖拽
   * @param {number} x - 屏幕X坐标
   * @param {number} y - 屏幕Y坐标
   * @param {number} graphX - 图形X坐标
   * @param {number} graphY - 图形Y坐标
   */
  updateNodeDrag(x, y, graphX, graphY) {
    if (!this.dragState.draggedNodeId) return
    
    this.dragState.currentX = x
    this.dragState.currentY = y
    
    this.emitEvent('nodeDragMove', { 
      nodeId: this.dragState.draggedNodeId, 
      x: graphX, 
      y: graphY,
      deltaX: x - this.dragState.startX,
      deltaY: y - this.dragState.startY
    })
  }
  
  /**
   * 停止拖拽节点
   */
  stopNodeDrag() {
    if (this.dragState.draggedNodeId) {
      this.emitEvent('nodeDragEnd', { 
        nodeId: this.dragState.draggedNodeId,
        finalX: this.dragState.currentX,
        finalY: this.dragState.currentY
      })
    }
    
    this.state.isDragging = false
    this.dragState.draggedNodeId = null
    this.dragState.originalNodePosition = null
    this.container.style.cursor = 'default'
  }
  
  /**
   * 开始平移画布
   * @param {number} x - X坐标
   * @param {number} y - Y坐标
   */
  startPanning(x, y) {
    this.state.isPanning = true
    this.panState.startX = x
    this.panState.startY = y
    this.panState.startTranslateX = this.transform.translateX
    this.panState.startTranslateY = this.transform.translateY
    
    this.container.style.cursor = 'move'
  }
  
  /**
   * 更新画布平移
   * @param {number} x - X坐标
   * @param {number} y - Y坐标
   */
  updatePanning(x, y) {
    const deltaX = x - this.panState.startX
    const deltaY = y - this.panState.startY
    
    this.transform.translateX = this.panState.startTranslateX + deltaX
    this.transform.translateY = this.panState.startTranslateY + deltaY
    
    this.updateTransform()
  }
  
  /**
   * 停止平移画布
   */
  stopPanning() {
    this.state.isPanning = false
    this.container.style.cursor = 'default'
  }
  
  /**
   * 显示上下文菜单
   * @param {string} nodeId - 节点ID
   * @param {number} x - 屏幕X坐标
   * @param {number} y - 屏幕Y坐标
   */
  showContextMenu(nodeId, x, y) {
    this.state.contextMenu = {
      nodeId,
      x,
      y,
      visible: true
    }
    
    this.emitEvent('contextMenuShow', this.state.contextMenu)
  }
  
  /**
   * 隐藏上下文菜单
   */
  hideContextMenu() {
    this.state.contextMenu = null
    this.emitEvent('contextMenuHide')
  }
  
  /**
   * 设置选中的节点
   * @param {string|null} nodeId - 节点ID
   */
  setSelectedNode(nodeId) {
    const previousNodeId = this.state.selectedNodeId
    this.state.selectedNodeId = nodeId
    
    if (previousNodeId !== nodeId) {
      this.emitEvent('nodeSelectionChange', { 
        previousNodeId, 
        currentNodeId: nodeId 
      })
    }
  }
  
  /**
   * 设置悬停的节点
   * @param {string|null} nodeId - 节点ID
   */
  setHoveredNode(nodeId) {
    const previousNodeId = this.state.hoveredNodeId

    // 防抖处理，减少频繁的hover状态变化
    if (this.hoverTimeout) {
      clearTimeout(this.hoverTimeout)
    }

    this.hoverTimeout = setTimeout(() => {
      if (this.state.hoveredNodeId !== nodeId) {
        this.state.hoveredNodeId = nodeId

        this.emitEvent('nodeHoverChange', {
          previousNodeId,
          currentNodeId: nodeId
        })
      }
    }, 50) // 50ms防抖延迟
  }
  
  /**
   * 更新光标样式
   * @param {string|null} nodeId - 节点ID
   */
  updateCursor(nodeId) {
    if (this.state.isDragging) {
      this.container.style.cursor = 'grabbing'
    } else if (this.state.isPanning) {
      this.container.style.cursor = 'move'
    } else if (nodeId && this.options.enableDrag) {
      this.container.style.cursor = 'grab'
    } else {
      this.container.style.cursor = 'default'
    }
  }
  
  /**
   * 缩放操作
   * @param {number} factor - 缩放因子
   * @param {number} centerX - 中心X坐标
   * @param {number} centerY - 中心Y坐标
   */
  zoom(factor, centerX = null, centerY = null) {
    const newScale = Math.max(
      this.options.minScale,
      Math.min(this.options.maxScale, this.transform.scale * factor)
    )
    
    if (centerX === null) centerX = this.container.clientWidth / 2
    if (centerY === null) centerY = this.container.clientHeight / 2
    
    const scaleRatio = newScale / this.transform.scale
    this.transform.translateX = centerX - (centerX - this.transform.translateX) * scaleRatio
    this.transform.translateY = centerY - (centerY - this.transform.translateY) * scaleRatio
    this.transform.scale = newScale
    
    this.updateTransform()
    this.emitEvent('zoom', { scale: newScale, centerX, centerY })
  }
  
  /**
   * 放大
   */
  zoomIn() {
    this.zoom(1.2)
  }
  
  /**
   * 缩小
   */
  zoomOut() {
    this.zoom(0.8)
  }
  
  /**
   * 重置缩放
   */
  resetZoom() {
    this.transform.translateX = 0
    this.transform.translateY = 0
    this.transform.scale = 1.0
    this.updateTransform()
    this.emitEvent('zoom', { scale: 1.0, centerX: 0, centerY: 0 })
  }
  
  /**
   * 更新SVG变换
   */
  updateTransform() {
    this.emitEvent('transformUpdate', { ...this.transform })
  }
  
  /**
   * 查找指定位置的节点
   * @param {number} x - X坐标
   * @param {number} y - Y坐标
   * @returns {string|null} 节点ID
   */
  findNodeAtPosition(x, y) {
    // 这个方法需要由使用该模块的组件实现
    // 因为节点数据由外部管理
    if (this.nodeHitTest) {
      return this.nodeHitTest(x, y)
    }
    return null
  }
  
  /**
   * 根据ID查找节点
   * @param {string} nodeId - 节点ID
   * @returns {Object|null} 节点对象
   */
  findNodeById(nodeId) {
    // 这个方法需要由使用该模块的组件实现
    if (this.nodeDataProvider) {
      return this.nodeDataProvider(nodeId)
    }
    return null
  }
  
  /**
   * 设置节点命中测试函数
   * @param {Function} hitTestFn - 命中测试函数
   */
  setNodeHitTest(hitTestFn) {
    this.nodeHitTest = hitTestFn
  }
  
  /**
   * 设置节点数据提供者
   * @param {Function} dataProviderFn - 数据提供者函数
   */
  setNodeDataProvider(dataProviderFn) {
    this.nodeDataProvider = dataProviderFn
  }
  
  /**
   * 发射事件
   * @param {string} eventType - 事件类型
   * @param {Object} eventData - 事件数据
   */
  emitEvent(eventType, eventData = {}) {
    const event = new CustomEvent(`graph-${eventType}`, {
      detail: eventData
    })
    this.container.dispatchEvent(event)
  }
  
  /**
   * 销毁交互控制器
   */
  destroy() {
    // 清理防抖定时器
    if (this.hoverTimeout) {
      clearTimeout(this.hoverTimeout)
      this.hoverTimeout = null
    }

    // 移除所有事件监听器
    this.eventListeners.forEach((handler, eventType) => {
      this.container.removeEventListener(eventType, handler)
    })
    this.eventListeners.clear()

    console.log('图形交互控制器已销毁')
  }
  
  /**
   * 获取当前视图变换
   * @returns {ViewTransform} 变换信息
   */
  getTransform() {
    return { ...this.transform }
  }
  
  /**
   * 获取当前交互状态
   * @returns {InteractionState} 交互状态
   */
  getState() {
    return { ...this.state }
  }
  
  /**
   * 设置变换参数
   * @param {ViewTransform} newTransform - 新的变换参数
   */
  setTransform(newTransform) {
    this.transform = { ...this.transform, ...newTransform }
    this.updateTransform()
  }
  
  /**
   * 平移到指定位置
   * @param {number} x - X坐标
   * @param {number} y - Y坐标
   */
  panTo(x, y) {
    this.transform.translateX = x
    this.transform.translateY = y
    this.updateTransform()
  }
  
  /**
   * 缩放到指定比例并居中
   * @param {number} scale - 缩放比例
   * @param {number} centerX - 中心X坐标
   * @param {number} centerY - 中心Y坐标
   */
  zoomTo(scale, centerX = null, centerY = null) {
    if (centerX === null) centerX = this.container.clientWidth / 2
    if (centerY === null) centerY = this.container.clientHeight / 2
    
    // 限制缩放范围
    const newScale = Math.max(
      this.options.minScale,
      Math.min(this.options.maxScale, scale)
    )
    
    // 以指定点为中心缩放
    const scaleRatio = newScale / this.transform.scale
    this.transform.translateX = centerX - (centerX - this.transform.translateX) * scaleRatio
    this.transform.translateY = centerY - (centerY - this.transform.translateY) * scaleRatio
    this.transform.scale = newScale
    
    this.updateTransform()
    this.emitEvent('zoom', { scale: newScale, centerX, centerY })
  }
}