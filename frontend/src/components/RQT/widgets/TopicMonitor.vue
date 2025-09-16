<template>
  <div class="topic-monitor">
    <!-- 控制栏 -->
    <div class="monitor-controls">
      <el-input
        v-model="searchText"
        placeholder="搜索主题..."
        size="small"
        clearable
        style="width: 200px"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      
      <el-button 
        size="small" 
        @click="refresh"
        :loading="loading"
      >
        <el-icon><Refresh /></el-icon>
        刷新
      </el-button>
    </div>
    
    <!-- 主题表格 -->
    <div class="topic-table">
      <el-table 
        :data="filteredTopics" 
        stripe
        size="small"
        height="250"
        @row-click="onTopicClick"
      >
        <el-table-column prop="name" label="主题名称" min-width="150">
          <template #default="{ row }">
            <el-text 
              :type="row.active ? 'primary' : 'default'"
              class="topic-name"
            >
              {{ row.name }}
            </el-text>
          </template>
        </el-table-column>
        
        <el-table-column prop="messageType" label="消息类型" width="120">
          <template #default="{ row }">
            <el-tag size="small" type="info">
              {{ row.messageType.split('/').pop() }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="frequency" label="频率(Hz)" width="80" align="center">
          <template #default="{ row }">
            <span :class="{ 'high-frequency': row.frequency > 10 }">
              {{ row.frequency?.toFixed(1) || '0.0' }}
            </span>
          </template>
        </el-table-column>
        
        <el-table-column prop="publishers" label="发布者" width="80" align="center">
          <template #default="{ row }">
            <el-badge :value="row.publishers" type="success" />
          </template>
        </el-table-column>
        
        <el-table-column prop="subscribers" label="订阅者" width="80" align="center">
          <template #default="{ row }">
            <el-badge :value="row.subscribers" type="warning" />
          </template>
        </el-table-column>
        
        <el-table-column label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-icon 
              :color="row.active ? '#67C23A' : '#F56C6C'"
              size="16"
            >
              <CircleCheckFilled v-if="row.active" />
              <CircleCloseFilled v-else />
            </el-icon>
          </template>
        </el-table-column>
      </el-table>
    </div>
    
    <!-- 主题详情对话框 -->
    <el-dialog 
      v-model="showTopicDetail" 
      :title="`主题详情: ${selectedTopic?.name}`"
      width="600px"
    >
      <div v-if="selectedTopic" class="topic-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="主题名称">
            {{ selectedTopic.name }}
          </el-descriptions-item>
          <el-descriptions-item label="消息类型">
            {{ selectedTopic.messageType }}
          </el-descriptions-item>
          <el-descriptions-item label="发布频率">
            {{ selectedTopic.frequency?.toFixed(2) || '0.00' }} Hz
          </el-descriptions-item>
          <el-descriptions-item label="最后消息">
            {{ formatTime(selectedTopic.lastMessage) }}
          </el-descriptions-item>
          <el-descriptions-item label="发布者数量">
            {{ selectedTopic.publishers }}
          </el-descriptions-item>
          <el-descriptions-item label="订阅者数量">
            {{ selectedTopic.subscribers }}
          </el-descriptions-item>
        </el-descriptions>
        
        <!-- 消息预览 -->
        <div class="message-preview">
          <h4>最新消息预览</h4>
          <el-scrollbar height="200px">
            <pre class="message-content">{{ formatMessage(selectedTopic.lastMessageData) }}</pre>
          </el-scrollbar>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { 
  Search, 
  Refresh, 
  CircleCheckFilled, 
  CircleCloseFilled 
} from '@element-plus/icons-vue'
import { useConnectionStore } from '../../../composables/useConnectionStore'

export default {
  name: 'TopicMonitor',
  components: {
    Search,
    Refresh,
    CircleCheckFilled,
    CircleCloseFilled
  },
  setup() {
    const connectionStore = useConnectionStore()
    
    const searchText = ref('')
    const loading = ref(false)
    const showTopicDetail = ref(false)
    const selectedTopic = ref(null)
    
    // 主题列表数据
    const topics = ref([
      {
        name: '/scan',
        messageType: 'sensor_msgs/msg/LaserScan',
        frequency: 10.2,
        publishers: 1,
        subscribers: 2,
        active: true,
        lastMessage: new Date(),
        lastMessageData: {
          header: { stamp: { sec: 1234567890, nanosec: 123456789 } },
          angle_min: -3.14159,
          angle_max: 3.14159,
          angle_increment: 0.017453,
          ranges: [1.2, 1.5, 2.0, 1.8, 1.1]
        }
      },
      {
        name: '/cloud',
        messageType: 'sensor_msgs/msg/PointCloud2',
        frequency: 5.1,
        publishers: 1,
        subscribers: 1,
        active: true,
        lastMessage: new Date(Date.now() - 1000),
        lastMessageData: {
          header: { frame_id: 'base_link' },
          height: 1,
          width: 1000,
          point_step: 16,
          row_step: 16000
        }
      },
      {
        name: '/camera/image_raw',
        messageType: 'sensor_msgs/msg/Image',
        frequency: 30.0,
        publishers: 1,
        subscribers: 0,
        active: true,
        lastMessage: new Date(Date.now() - 100),
        lastMessageData: {
          header: { frame_id: 'camera_frame' },
          height: 480,
          width: 640,
          encoding: 'rgb8'
        }
      },
      {
        name: '/cmd_vel',
        messageType: 'geometry_msgs/msg/Twist',
        frequency: 0,
        publishers: 0,
        subscribers: 1,
        active: false,
        lastMessage: new Date(Date.now() - 60000),
        lastMessageData: {
          linear: { x: 0.5, y: 0.0, z: 0.0 },
          angular: { x: 0.0, y: 0.0, z: 0.2 }
        }
      },
      {
        name: '/odom',
        messageType: 'nav_msgs/msg/Odometry',
        frequency: 50.0,
        publishers: 1,
        subscribers: 3,
        active: true,
        lastMessage: new Date(Date.now() - 20),
        lastMessageData: {
          header: { frame_id: 'odom' },
          child_frame_id: 'base_link',
          pose: {
            pose: {
              position: { x: 1.2, y: 0.5, z: 0.0 },
              orientation: { x: 0.0, y: 0.0, z: 0.1, w: 0.995 }
            }
          }
        }
      }
    ])
    
    // 过滤后的主题
    const filteredTopics = computed(() => {
      if (!searchText.value) {
        return topics.value
      }
      return topics.value.filter(topic =>
        topic.name.toLowerCase().includes(searchText.value.toLowerCase()) ||
        topic.messageType.toLowerCase().includes(searchText.value.toLowerCase())
      )
    })
    
    // 刷新主题列表
    const refresh = async () => {
      loading.value = true
      try {
        // 模拟刷新延迟
        await new Promise(resolve => setTimeout(resolve, 500))
        
        // 更新频率和状态（模拟数据）
        topics.value.forEach(topic => {
          topic.frequency = Math.random() * 50
          topic.active = Math.random() > 0.2
          if (topic.active) {
            topic.lastMessage = new Date()
          }
        })
        
        ElMessage.success('主题列表已刷新')
      } catch (error) {
        ElMessage.error('刷新失败')
      } finally {
        loading.value = false
      }
    }
    
    // 点击主题行
    const onTopicClick = (row) => {
      selectedTopic.value = row
      showTopicDetail.value = true
    }
    
    // 格式化时间
    const formatTime = (date) => {
      if (!date) return '无'
      return date.toLocaleTimeString()
    }
    
    // 格式化消息内容
    const formatMessage = (data) => {
      if (!data) return '无消息数据'
      return JSON.stringify(data, null, 2)
    }
    
    // 获取主题数据（供父组件调用）
    const getTopicData = () => {
      return topics.value.map(topic => ({
        name: topic.name,
        messageType: topic.messageType,
        frequency: topic.frequency,
        active: topic.active
      }))
    }
    
    // 定期更新主题状态
    let updateInterval = null
    
    onMounted(() => {
      // 每2秒更新一次状态
      updateInterval = setInterval(() => {
        topics.value.forEach(topic => {
          if (topic.active) {
            // 模拟频率变化
            topic.frequency += (Math.random() - 0.5) * 2
            topic.frequency = Math.max(0, topic.frequency)
            topic.lastMessage = new Date()
          }
        })
      }, 2000)
    })
    
    // 清理定时器
    const cleanup = () => {
      if (updateInterval) {
        clearInterval(updateInterval)
      }
    }
    
    return {
      searchText,
      loading,
      showTopicDetail,
      selectedTopic,
      topics,
      filteredTopics,
      refresh,
      onTopicClick,
      formatTime,
      formatMessage,
      // 暴露方法供父组件调用
      getTopicData,
      cleanup
    }
  }
}
</script>

<style scoped>
.topic-monitor {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.monitor-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding: 0 5px;
}

.topic-table {
  flex: 1;
  overflow: hidden;
}

.topic-name {
  cursor: pointer;
}

.topic-name:hover {
  color: #409eff;
}

.high-frequency {
  color: #e6a23c;
  font-weight: bold;
}

.topic-detail {
  padding: 10px 0;
}

.message-preview {
  margin-top: 20px;
}

.message-preview h4 {
  margin: 0 0 10px 0;
  color: #333;
}

.message-content {
  background: #f5f5f5;
  padding: 10px;
  border-radius: 4px;
  font-size: 12px;
  line-height: 1.4;
  margin: 0;
}
</style>
