<template>
  <div class="topic-list">
    <el-table 
      :data="filteredTopics" 
      stripe
      style="width: 100%"
      max-height="400px"
    >
      <el-table-column prop="name" label="主题名称" min-width="200">
        <template #default="{ row }">
          <el-text type="primary">{{ row.name }}</el-text>
        </template>
      </el-table-column>
      
      <el-table-column prop="message_type" label="消息类型" min-width="150">
        <template #default="{ row }">
          <el-tag size="small" type="info">{{ row.message_type }}</el-tag>
        </template>
      </el-table-column>
      
      <el-table-column label="发布者" width="80">
        <template #default="{ row }">
          <el-badge :value="row.publishers?.length || 0" type="success" />
        </template>
      </el-table-column>
      
      <el-table-column label="订阅者" width="80">
        <template #default="{ row }">
          <el-badge :value="row.subscribers?.length || 0" type="warning" />
        </template>
      </el-table-column>
      
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <el-button 
            v-if="!isSubscribed(row.name)"
            type="primary" 
            size="small"
            @click="subscribeTopic(row)"
          >
            订阅
          </el-button>
          <el-button 
            v-else
            type="danger" 
            size="small"
            @click="unsubscribeTopic(row.name)"
          >
            取消订阅
          </el-button>
        </template>
      </el-table-column>
    </el-table>
    
    <!-- 搜索和过滤 -->
    <div class="topic-filters">
      <el-input
        v-model="searchText"
        placeholder="搜索主题..."
        size="small"
        clearable
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      
      <el-select
        v-model="selectedMessageType"
        placeholder="消息类型过滤"
        size="small"
        clearable
        style="margin-left: 10px; width: 200px"
      >
        <el-option
          v-for="type in messageTypes"
          :key="type"
          :label="type"
          :value="type"
        />
      </el-select>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { useConnectionStore } from '../../composables/useConnectionStore'
import { useRosbridge } from '../../composables/useRosbridge'

export default {
  name: 'TopicList',
  components: {
    Search
  },
  setup() {
    const connectionStore = useConnectionStore()
    const rosbridge = useRosbridge()
    
    const topics = ref([])
    const searchText = ref('')
    const selectedMessageType = ref('')
    const loading = ref(false)
    
    // 计算属性
    const filteredTopics = computed(() => {
      let result = topics.value
      
      // 文本搜索
      if (searchText.value) {
        result = result.filter(topic => 
          topic.name.toLowerCase().includes(searchText.value.toLowerCase())
        )
      }
      
      // 消息类型过滤
      if (selectedMessageType.value) {
        result = result.filter(topic => 
          topic.message_type === selectedMessageType.value
        )
      }
      
      return result
    })
    
    const messageTypes = computed(() => {
      const types = new Set(topics.value.map(topic => topic.message_type))
      return Array.from(types).sort()
    })
    
    // 检查主题是否已订阅
    const isSubscribed = (topicName) => {
      return connectionStore.subscribedTopics.includes(topicName)
    }
    
    // 订阅主题
    const subscribeTopic = (topic) => {
      const success = rosbridge.subscribe(
        topic.name,
        topic.message_type,
        (message) => {
          console.log(`Message from ${topic.name}:`, message)
        }
      )
      
      if (success) {
        ElMessage.success(`已订阅主题: ${topic.name}`)
      } else {
        ElMessage.error(`订阅失败: ${topic.name}`)
      }
    }
    
    // 取消订阅主题
    const unsubscribeTopic = (topicName) => {
      rosbridge.unsubscribe(topicName)
      ElMessage.info(`已取消订阅: ${topicName}`)
    }
    
    // 获取主题列表
    const fetchTopics = async () => {
      if (!connectionStore.isConnected) {
        return
      }
      
      loading.value = true
      try {
        // 这里应该通过 API 获取主题列表
        // 暂时使用模拟数据
        topics.value = [
          {
            name: '/scan',
            message_type: 'sensor_msgs/msg/LaserScan',
            publishers: ['laser_node'],
            subscribers: []
          },
          {
            name: '/camera/image_raw',
            message_type: 'sensor_msgs/msg/Image',
            publishers: ['camera_node'],
            subscribers: []
          },
          {
            name: '/cmd_vel',
            message_type: 'geometry_msgs/msg/Twist',
            publishers: [],
            subscribers: ['robot_controller']
          },
          {
            name: '/point_cloud',
            message_type: 'sensor_msgs/msg/PointCloud2',
            publishers: ['lidar_node'],
            subscribers: []
          },
          {
            name: '/visualization_marker',
            message_type: 'visualization_msgs/msg/Marker',
            publishers: ['marker_publisher'],
            subscribers: []
          }
        ]
      } catch (error) {
        console.error('Failed to fetch topics:', error)
        ElMessage.error('获取主题列表失败')
      } finally {
        loading.value = false
      }
    }
    
    // 组件挂载时获取主题列表
    onMounted(() => {
      fetchTopics()
    })
    
    return {
      topics,
      filteredTopics,
      messageTypes,
      searchText,
      selectedMessageType,
      loading,
      isSubscribed,
      subscribeTopic,
      unsubscribeTopic,
      fetchTopics
    }
  }
}
</script>

<style scoped>
.topic-list {
  padding: 10px 0;
}

.topic-filters {
  display: flex;
  margin-top: 15px;
  gap: 10px;
}
</style>
