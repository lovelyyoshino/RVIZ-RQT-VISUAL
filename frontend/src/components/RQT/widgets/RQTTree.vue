<template>
  <div class="rqt-tree">
    <div class="tree-controls">
      <el-button-group size="small">
        <el-button @click="refreshTree" :loading="loading">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
        <el-button @click="expandAll">
          <el-icon><Plus /></el-icon>
          展开所有
        </el-button>
        <el-button @click="collapseAll">
          <el-icon><Minus /></el-icon>
          收起所有
        </el-button>
      </el-button-group>
      
      <el-input
        v-model="searchQuery"
        placeholder="搜索节点/主题..."
        size="small"
        style="width: 120px"
        @input="filterTree"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
    </div>
    
    <div class="tree-container">
      <el-tree
        ref="treeRef"
        :data="filteredTreeData"
        :props="treeProps"
        :expand-on-click-node="false"
        :default-expand-all="false"
        :filter-node-method="filterNode"
        @node-click="onNodeClick"
        @node-contextmenu="onNodeRightClick"
        show-checkbox
        check-strictly
        @check="onNodeCheck"
        class="ros-tree"
      >
        <template #default="{ node, data }">
          <div class="tree-node">
            <!-- 节点图标 -->
            <el-icon :class="getNodeIconClass(data)" :style="{ color: getNodeColor(data) }">
              <component :is="getNodeIcon(data)" />
            </el-icon>
            
            <!-- 节点名称 -->
            <span class="node-name" :class="{ 'node-active': data.active }">
              {{ data.label }}
            </span>
            
            <!-- 节点状态指示 -->
            <div class="node-status">
              <el-badge 
                v-if="data.type === 'topic' && data.messageCount > 0"
                :value="data.messageCount" 
                :max="999"
                type="primary"
                :show-zero="false"
              />
              
              <el-tag 
                v-if="data.messageType"
                size="small" 
                type="info"
                class="message-type-tag"
              >
                {{ data.messageType.split('/').pop() }}
              </el-tag>
              
              <div 
                v-if="data.frequency !== undefined"
                class="frequency-indicator"
                :class="getFrequencyClass(data.frequency)"
              >
                {{ data.frequency.toFixed(1) }}Hz
              </div>
            </div>
          </div>
        </template>
      </el-tree>
    </div>
    
    <!-- 右键上下文菜单 -->
    <el-dropdown
      ref="contextMenu"
      trigger="manual"
      :teleported="false"
      @command="handleContextMenu"
    >
      <span></span>
      <template #dropdown>
        <el-dropdown-menu>
          <el-dropdown-item 
            v-if="selectedNode?.type === 'topic'" 
            command="subscribe"
            :disabled="selectedNode?.subscribed"
          >
            <el-icon><View /></el-icon>
            订阅主题
          </el-dropdown-item>
          <el-dropdown-item 
            v-if="selectedNode?.type === 'topic'" 
            command="unsubscribe"
            :disabled="!selectedNode?.subscribed"
          >
            <el-icon><Hide /></el-icon>
            取消订阅
          </el-dropdown-item>
          <el-dropdown-item 
            v-if="selectedNode?.type === 'service'" 
            command="call"
          >
            <el-icon><Connection /></el-icon>
            调用服务
          </el-dropdown-item>
          <el-dropdown-item 
            v-if="selectedNode?.type === 'node'" 
            command="inspect"
          >
            <el-icon><View /></el-icon>
            检查节点
          </el-dropdown-item>
          <el-dropdown-item command="copy">
            <el-icon><CopyDocument /></el-icon>
            复制名称
          </el-dropdown-item>
        </el-dropdown-menu>
      </template>
    </el-dropdown>
    
    <!-- 节点详情面板 -->
    <el-drawer
      v-model="showNodeDetail"
      :title="selectedNode?.label"
      direction="rtl"
      size="350px"
    >
      <div v-if="selectedNode" class="node-detail">
        <el-descriptions :column="1" border size="small">
          <el-descriptions-item label="类型">
            {{ selectedNode.type }}
          </el-descriptions-item>
          <el-descriptions-item label="完整名称">
            {{ selectedNode.fullName }}
          </el-descriptions-item>
          <el-descriptions-item v-if="selectedNode.messageType" label="消息类型">
            {{ selectedNode.messageType }}
          </el-descriptions-item>
          <el-descriptions-item v-if="selectedNode.frequency !== undefined" label="频率">
            {{ selectedNode.frequency.toFixed(2) }} Hz
          </el-descriptions-item>
          <el-descriptions-item v-if="selectedNode.messageCount !== undefined" label="消息数">
            {{ selectedNode.messageCount }}
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="selectedNode.active ? 'success' : 'danger'">
              {{ selectedNode.active ? '活跃' : '不活跃' }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>
        
        <el-divider v-if="selectedNode.type === 'node'">发布者/订阅者</el-divider>
        <div v-if="selectedNode.publishers?.length > 0">
          <h5>发布者:</h5>
          <el-tag
            v-for="pub in selectedNode.publishers"
            :key="pub"
            size="small"
            type="success"
            style="margin: 2px;"
          >
            {{ pub }}
          </el-tag>
        </div>
        
        <div v-if="selectedNode.subscribers?.length > 0" style="margin-top: 10px;">
          <h5>订阅者:</h5>
          <el-tag
            v-for="sub in selectedNode.subscribers"
            :key="sub"
            size="small"
            type="warning"
            style="margin: 2px;"
          >
            {{ sub }}
          </el-tag>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { 
  Refresh, Plus, Minus, Search, View, Hide, Connection, 
  CopyDocument, Document, Folder, Monitor, Service 
} from '@element-plus/icons-vue'
import { useRosbridge } from '../../../composables/useRosbridge'

export default {
  name: 'RQTTree',
  components: {
    Refresh, Plus, Minus, Search, View, Hide, Connection,
    CopyDocument, Document, Folder, Monitor, Service
  },
  emits: ['node-selected', 'topic-subscribe', 'topic-unsubscribe'],
  setup(props, { emit }) {
    const rosbridge = useRosbridge()
    const treeRef = ref(null)
    const contextMenu = ref(null)
    const loading = ref(false)
    const searchQuery = ref('')
    const selectedNode = ref(null)
    const showNodeDetail = ref(false)
    
    // 树形结构配置
    const treeProps = {
      children: 'children',
      label: 'label',
      disabled: (data) => !data.active
    }
    
    // 原始树数据
    const treeData = ref([])
    
    // 过滤后的树数据
    const filteredTreeData = computed(() => {
      if (!searchQuery.value) {
        return treeData.value
      }
      return filterTreeData(treeData.value, searchQuery.value.toLowerCase())
    })
    
    // 初始化树数据
    const initializeTree = () => {
      treeData.value = [
        {
          id: 'nodes',
          label: 'ROS节点',
          type: 'category',
          active: true,
          children: []
        },
        {
          id: 'topics',
          label: '主题',
          type: 'category', 
          active: true,
          children: []
        },
        {
          id: 'services',
          label: '服务',
          type: 'category',
          active: true,
          children: []
        },
        {
          id: 'parameters',
          label: '参数',
          type: 'category',
          active: true,
          children: []
        }
      ]
    }
    
    // 获取节点图标
    const getNodeIcon = (data) => {
      switch (data.type) {
        case 'category': return Folder
        case 'node': return Monitor
        case 'topic': return Document
        case 'service': return Service
        case 'parameter': return Document
        default: return Document
      }
    }
    
    // 获取节点图标样式类
    const getNodeIconClass = (data) => {
      return `node-icon node-icon-${data.type}`
    }
    
    // 获取节点颜色
    const getNodeColor = (data) => {
      switch (data.type) {
        case 'category': return '#409eff'
        case 'node': return '#409eff'
        case 'topic': return '#67c23a'
        case 'service': return '#f56c6c'
        case 'parameter': return '#909399'
        default: return '#909399'
      }
    }
    
    // 获取频率样式类
    const getFrequencyClass = (frequency) => {
      if (frequency > 10) return 'freq-high'
      if (frequency > 1) return 'freq-medium'
      if (frequency > 0) return 'freq-low'
      return 'freq-none'
    }
    
    // 过滤树数据
    const filterTreeData = (data, query) => {
      return data.map(item => {
        const matchesQuery = item.label.toLowerCase().includes(query) ||
                           item.fullName?.toLowerCase().includes(query)
        
        let filteredChildren = []
        if (item.children) {
          filteredChildren = filterTreeData(item.children, query)
        }
        
        if (matchesQuery || filteredChildren.length > 0) {
          return {
            ...item,
            children: filteredChildren
          }
        }
        return null
      }).filter(item => item !== null)
    }
    
    // 过滤节点方法
    const filterNode = (value, data) => {
      if (!value) return true
      return data.label.toLowerCase().includes(value.toLowerCase()) ||
             data.fullName?.toLowerCase().includes(value.toLowerCase())
    }
    
    // 树控制方法
    const refreshTree = async () => {
      loading.value = true
      try {
        await loadRosData()
        ElMessage.success('ROS树已刷新')
      } catch (error) {
        console.error('刷新ROS树失败:', error)
        ElMessage.error('刷新失败')
      } finally {
        loading.value = false
      }
    }
    
    const expandAll = () => {
      Object.keys(treeRef.value.store.nodesMap).forEach(key => {
        treeRef.value.store.nodesMap[key].expanded = true
      })
    }
    
    const collapseAll = () => {
      Object.keys(treeRef.value.store.nodesMap).forEach(key => {
        if (treeRef.value.store.nodesMap[key].level > 0) {
          treeRef.value.store.nodesMap[key].expanded = false
        }
      })
    }
    
    const filterTree = () => {
      treeRef.value.filter(searchQuery.value)
    }
    
    // 加载ROS数据
    const loadRosData = async () => {
      try {
        console.log('开始加载真实ROS数据...')
        
        // 检查rosbridge连接状态
        if (!rosbridge.isConnected) {
          console.warn('Rosbridge未连接，无法加载ROS数据')
          ElMessage.warning('ROS连接未建立，显示的可能不是实时数据')
          // 仍然尝试加载，可能有缓存数据
        }
        
        // 并行加载所有数据
        const [nodes, topics, services, parameters] = await Promise.allSettled([
          loadNodes(),
          loadTopics(),
          loadServices(),
          loadParameters()
        ])
        
        // 更新各个分类的数据
        const nodesCategory = treeData.value.find(item => item.id === 'nodes')
        if (nodesCategory && nodes.status === 'fulfilled') {
          nodesCategory.children = nodes.value
        }
        
        const topicsCategory = treeData.value.find(item => item.id === 'topics')
        if (topicsCategory && topics.status === 'fulfilled') {
          topicsCategory.children = topics.value
        }
        
        const servicesCategory = treeData.value.find(item => item.id === 'services')
        if (servicesCategory && services.status === 'fulfilled') {
          servicesCategory.children = services.value
        }
        
        const parametersCategory = treeData.value.find(item => item.id === 'parameters')
        if (parametersCategory && parameters.status === 'fulfilled') {
          parametersCategory.children = parameters.value
        }
        
        console.log('ROS数据加载完成')
        
      } catch (error) {
        console.error('加载ROS数据失败:', error)
        ElMessage.error('加载ROS数据失败，请检查ROS连接')
      }
    }
    
    // 加载节点列表 - 使用真实的rosbridge API
    const loadNodes = async () => {
      try {
        if (!rosbridge.isConnected) {
          console.warn('Rosbridge未连接，无法获取节点列表')
          return []
        }
        
        // 调用rosbridge API获取节点列表
        const nodeList = await rosbridge.getNodes()
        console.log('获取到的节点列表:', nodeList)
        
        return nodeList.map((nodeInfo, index) => ({
          id: `node_${index}`,
          label: (typeof nodeInfo === 'string' ? nodeInfo : nodeInfo.name).split('/').pop() || (typeof nodeInfo === 'string' ? nodeInfo : nodeInfo.name),
          fullName: typeof nodeInfo === 'string' ? nodeInfo : nodeInfo.name,
          type: 'node',
          active: true,
          publishers: typeof nodeInfo === 'object' ? (nodeInfo.publishers || []) : [],
          subscribers: typeof nodeInfo === 'object' ? (nodeInfo.subscribers || []) : []
        }))
        
      } catch (error) {
        console.error('获取节点列表失败:', error)
        return []
      }
    }
    
    // 加载主题列表 - 使用真实的rosbridge API
    const loadTopics = async () => {
      try {
        if (!rosbridge.isConnected) {
          console.warn('Rosbridge未连接，无法获取主题列表')
          return []
        }
        
        // 调用rosbridge API获取主题列表和类型
        const [topicList, topicTypes] = await Promise.all([
          rosbridge.getTopics(),
          rosbridge.getTopicTypes()
        ])
        
        console.log('获取到的主题列表:', topicList)
        console.log('获取到的主题类型:', topicTypes)
        
        return topicList.map((topicName, index) => ({
          id: `topic_${index}`,
          label: topicName,
          fullName: topicName,
          type: 'topic',
          active: true,
          messageType: topicTypes[topicName] || 'unknown',
          frequency: 0,
          messageCount: 0,
          subscribed: false
        }))
        
      } catch (error) {
        console.error('获取主题列表失败:', error)
        return []
      }
    }
    
    // 加载服务列表 - 使用真实的rosbridge API
    const loadServices = async () => {
      try {
        if (!rosbridge.isConnected) {
          console.warn('Rosbridge未连接，无法获取服务列表')
          return []
        }
        
        // 调用rosbridge API获取服务列表和类型
        const [serviceList, serviceTypes] = await Promise.all([
          rosbridge.getServices(),
          rosbridge.getServiceTypes()
        ])
        
        console.log('获取到的服务列表:', serviceList)
        
        return serviceList.map((serviceName, index) => ({
          id: `service_${index}`,
          label: serviceName,
          fullName: serviceName,
          type: 'service',
          active: true,
          serviceType: serviceTypes[serviceName] || 'unknown'
        }))
        
      } catch (error) {
        console.error('获取服务列表失败:', error)
        return []
      }
    }
    
    // 加载参数列表 - 使用真实的rosbridge API
    const loadParameters = async () => {
      try {
        if (!rosbridge.isConnected) {
          console.warn('Rosbridge未连接，无法获取参数列表')
          return []
        }
        
        // 调用rosbridge API获取参数列表
        const paramList = await rosbridge.getParams()
        console.log('获取到的参数列表:', paramList)
        
        return paramList.map((paramName, index) => ({
          id: `param_${index}`,
          label: paramName.split('/').pop() || paramName,
          fullName: paramName,
          type: 'parameter',
          active: true,
          value: 'loading...'
        }))
        
      } catch (error) {
        console.error('获取参数列表失败:', error)
        return []
      }
    }
    
    // 事件处理
    const onNodeClick = (data) => {
      selectedNode.value = data
      emit('node-selected', data)
      
      if (data.type !== 'category') {
        showNodeDetail.value = true
      }
    }
    
    const onNodeRightClick = (event, data) => {
      selectedNode.value = data
      event.preventDefault()
      
      // 显示上下文菜单
      contextMenu.value.handleOpen()
    }
    
    const onNodeCheck = (data, checkedInfo) => {
      if (data.type === 'topic') {
        if (checkedInfo.checkedKeys.includes(data.id)) {
          emit('topic-subscribe', data.fullName, data.messageType)
          data.subscribed = true
        } else {
          emit('topic-unsubscribe', data.fullName)
          data.subscribed = false
        }
      }
    }
    
    // 上下文菜单处理
    const handleContextMenu = (command) => {
      if (!selectedNode.value) return
      
      switch (command) {
        case 'subscribe':
          if (selectedNode.value.type === 'topic') {
            emit('topic-subscribe', selectedNode.value.fullName, selectedNode.value.messageType)
            selectedNode.value.subscribed = true
            ElMessage.success(`已订阅主题: ${selectedNode.value.label}`)
          }
          break
        case 'unsubscribe':
          if (selectedNode.value.type === 'topic') {
            emit('topic-unsubscribe', selectedNode.value.fullName)
            selectedNode.value.subscribed = false
            ElMessage.info(`已取消订阅主题: ${selectedNode.value.label}`)
          }
          break
        case 'call':
          if (selectedNode.value.type === 'service') {
            ElMessage.info(`调用服务: ${selectedNode.value.label}`)
          }
          break
        case 'inspect':
          showNodeDetail.value = true
          break
        case 'copy':
          navigator.clipboard.writeText(selectedNode.value.fullName)
          ElMessage.success('已复制到剪贴板')
          break
      }
    }
    
    onMounted(async () => {
      await nextTick()
      initializeTree()
      await loadRosData()
    })
    
    return {
      treeRef,
      contextMenu,
      loading,
      searchQuery,
      selectedNode,
      showNodeDetail,
      treeProps,
      filteredTreeData,
      getNodeIcon,
      getNodeIconClass,
      getNodeColor,
      getFrequencyClass,
      filterNode,
      refreshTree,
      expandAll,
      collapseAll,
      filterTree,
      onNodeClick,
      onNodeRightClick,
      onNodeCheck,
      handleContextMenu
    }
  }
}
</script>

<style scoped>
.rqt-tree {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.tree-controls {
  height: 35px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 8px;
  background: #fafafa;
  border-bottom: 1px solid #e8e8e8;
}

.tree-container {
  flex: 1;
  overflow-y: auto;
  padding: 5px 0;
  background: rgba(15, 23, 42, 0.4);
  border-radius: 8px;
}

.ros-tree {
  background: transparent;
}

.tree-node {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding-right: 10px;
}

.node-icon {
  font-size: 14px;
}

.node-name {
  flex: 1;
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: #e2e8f0 !important;
  font-weight: 500;
}

.node-name.node-active {
  font-weight: 600;
  color: #ffffff !important;
}

.node-status {
  display: flex;
  align-items: center;
  gap: 4px;
}

.message-type-tag {
  font-size: 10px;
  height: 16px;
  line-height: 14px;
  padding: 0 4px;
}

.frequency-indicator {
  font-size: 10px;
  padding: 1px 4px;
  border-radius: 2px;
  background: #f0f0f0;
  color: #666;
  min-width: 35px;
  text-align: center;
}

.freq-high {
  background: #67c23a;
  color: white;
}

.freq-medium {
  background: #e6a23c;
  color: white;
}

.freq-low {
  background: #409eff;
  color: white;
}

.freq-none {
  background: #f56c6c;
  color: white;
}

.node-detail {
  padding: 10px;
}

.node-detail h5 {
  margin: 10px 0 5px 0;
  color: #333;
  font-size: 13px;
}

/* Element Plus 树组件样式覆盖 */
:deep(.el-tree-node__content) {
  height: auto;
  min-height: 28px;
  padding: 2px 0;
  background: transparent !important;
}

:deep(.el-tree-node__content:hover) {
  background: rgba(148, 163, 184, 0.1) !important;
}

:deep(.el-tree-node__expand-icon) {
  font-size: 12px;
  color: #94a3b8 !important;
}

:deep(.el-tree-node__label) {
  font-size: 12px;
  color: #e2e8f0 !important;
}

:deep(.el-tree-node__children) {
  overflow: visible;
}

:deep(.el-checkbox) {
  margin-right: 4px;
}

:deep(.el-checkbox__inner) {
  width: 12px;
  height: 12px;
  background: rgba(15, 23, 42, 0.8) !important;
  border-color: #94a3b8 !important;
}

:deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
  background: #409eff !important;
  border-color: #409eff !important;
}

:deep(.el-tree-node.is-expanded > .el-tree-node__children) {
  display: block;
}

:deep(.el-tree-node.is-current > .el-tree-node__content) {
  background: rgba(64, 158, 255, 0.1) !important;
}
</style>
