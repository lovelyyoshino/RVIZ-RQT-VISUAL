<template>
  <div class="topic-subscription">
    <!-- 订阅列表 -->
    <div class="subscribed-topics">
      <h4>已订阅主题</h4>
      <div v-if="subscribedTopics.length === 0" class="empty-state">
        <el-text type="info">暂无订阅主题</el-text>
      </div>
      <div v-else class="topic-list">
        <div 
          v-for="topic in subscribedTopics" 
          :key="topic.name"
          class="topic-item"
        >
          <div class="topic-info">
            <div class="topic-name">{{ topic.name }}</div>
            <div class="topic-type">{{ topic.messageType.split('/').pop() }}</div>
          </div>
          <el-button 
            size="small" 
            type="danger" 
            @click="unsubscribeTopic(topic.name)"
          >
            取消订阅
          </el-button>
        </div>
      </div>
    </div>
    
    <el-divider />
    
    <!-- 添加订阅 -->
    <div class="add-subscription">
      <h4>添加订阅</h4>
      <el-form :model="newSubscription" label-width="80px" size="small">
        <el-form-item label="主题">
          <el-autocomplete
            v-model="newSubscription.topic"
            :fetch-suggestions="fetchTopicSuggestions"
            placeholder="输入主题名称"
            style="width: 100%"
            @select="onTopicSelected"
          >
            <template #default="{ item }">
              <div class="suggestion-item">
                <div class="suggestion-name">{{ item.name }}</div>
                <div class="suggestion-type">{{ item.message_type }}</div>
              </div>
            </template>
          </el-autocomplete>
        </el-form-item>
        
        <el-form-item label="消息类型">
          <el-select 
            v-model="newSubscription.messageType" 
            placeholder="选择消息类型"
            style="width: 100%"
            filterable
          >
            <el-option-group label="传感器消息">
              <el-option 
                label="PointCloud2" 
                value="sensor_msgs/msg/PointCloud2" 
              />
              <el-option 
                label="LaserScan" 
                value="sensor_msgs/msg/LaserScan" 
              />
              <el-option 
                label="Image" 
                value="sensor_msgs/msg/Image" 
              />
            </el-option-group>
            
            <el-option-group label="几何消息">
              <el-option 
                label="Twist" 
                value="geometry_msgs/msg/Twist" 
              />
              <el-option 
                label="Pose" 
                value="geometry_msgs/msg/Pose" 
              />
              <el-option 
                label="Transform" 
                value="geometry_msgs/msg/Transform" 
              />
            </el-option-group>
            
            <el-option-group label="可视化消息">
              <el-option 
                label="Marker" 
                value="visualization_msgs/msg/Marker" 
              />
              <el-option 
                label="MarkerArray" 
                value="visualization_msgs/msg/MarkerArray" 
              />
            </el-option-group>
            
            <el-option-group label="导航消息">
              <el-option 
                label="Path" 
                value="nav_msgs/msg/Path" 
              />
              <el-option 
                label="OccupancyGrid" 
                value="nav_msgs/msg/OccupancyGrid" 
              />
              <el-option 
                label="Odometry" 
                value="nav_msgs/msg/Odometry" 
              />
            </el-option-group>
          </el-select>
        </el-form-item>
        
        <el-form-item>
          <el-button 
            type="primary" 
            @click="subscribeTopic"
            :disabled="!newSubscription.topic || !newSubscription.messageType"
            style="width: 100%"
          >
            <el-icon><Plus /></el-icon>
            订阅主题
          </el-button>
        </el-form-item>
      </el-form>
    </div>
    
    <el-divider />
    
    <!-- 快速订阅 -->
    <div class="quick-subscription">
      <h4>快速订阅</h4>
      <div class="quick-buttons">
        <el-button 
          size="small" 
          @click="quickSubscribe('/scan', 'sensor_msgs/msg/LaserScan')"
        >
          激光雷达
        </el-button>
        <el-button 
          size="small" 
          @click="quickSubscribe('/cloud', 'sensor_msgs/msg/PointCloud2')"
        >
          点云
        </el-button>
        <el-button 
          size="small" 
          @click="quickSubscribe('/visualization_marker', 'visualization_msgs/msg/Marker')"
        >
          标记
        </el-button>
        <el-button 
          size="small" 
          @click="quickSubscribe('/path', 'nav_msgs/msg/Path')"
        >
          路径
        </el-button>
      </div>
    </div>
    
    <!-- 消息统计 -->
    <el-divider />
    <div class="message-stats">
      <h4>消息统计</h4>
      <div class="stats-grid">
        <div class="stat-item">
          <div class="stat-value">{{ totalMessages }}</div>
          <div class="stat-label">总消息数</div>
        </div>
        <div class="stat-item">
          <div class="stat-value">{{ messageRate.toFixed(1) }}</div>
          <div class="stat-label">消息频率 (Hz)</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, reactive, computed } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { useConnectionStore } from '../../composables/useConnectionStore'

export default {
  name: 'TopicSubscription',
  components: {
    Plus
  },
  emits: ['topic-subscribed', 'topic-unsubscribed'],
  setup(props, { emit }) {
    const connectionStore = useConnectionStore()
    
    const subscribedTopics = ref([])
    const totalMessages = ref(0)
    const messageRate = ref(0)
    
    const newSubscription = reactive({
      topic: '',
      messageType: ''
    })
    
    // 可用主题列表（模拟数据）
    const availableTopics = ref([
      { name: '/scan', message_type: 'sensor_msgs/msg/LaserScan' },
      { name: '/cloud', message_type: 'sensor_msgs/msg/PointCloud2' },
      { name: '/camera/image_raw', message_type: 'sensor_msgs/msg/Image' },
      { name: '/cmd_vel', message_type: 'geometry_msgs/msg/Twist' },
      { name: '/odom', message_type: 'nav_msgs/msg/Odometry' },
      { name: '/visualization_marker', message_type: 'visualization_msgs/msg/Marker' },
      { name: '/path', message_type: 'nav_msgs/msg/Path' },
      { name: '/map', message_type: 'nav_msgs/msg/OccupancyGrid' }
    ])
    
    // 主题建议
    const fetchTopicSuggestions = (queryString, callback) => {
      const suggestions = availableTopics.value.filter(topic => 
        topic.name.toLowerCase().includes(queryString.toLowerCase())
      )
      callback(suggestions)
    }
    
    // 选择主题时自动填充消息类型
    const onTopicSelected = (item) => {
      newSubscription.topic = item.name
      newSubscription.messageType = item.message_type
    }
    
    // 订阅主题
    const subscribeTopic = () => {
      if (!newSubscription.topic || !newSubscription.messageType) {
        ElMessage.warning('请输入主题名称和选择消息类型')
        return
      }
      
      // 检查是否已订阅
      const exists = subscribedTopics.value.find(t => t.name === newSubscription.topic)
      if (exists) {
        ElMessage.warning('该主题已订阅')
        return
      }
      
      // 添加到订阅列表
      const topic = {
        name: newSubscription.topic,
        messageType: newSubscription.messageType,
        subscribedAt: new Date(),
        messageCount: 0
      }
      
      subscribedTopics.value.push(topic)
      
      // 发送订阅事件
      emit('topic-subscribed', newSubscription.topic, newSubscription.messageType)
      
      // 重置表单
      newSubscription.topic = ''
      newSubscription.messageType = ''
      
      ElMessage.success(`已订阅主题: ${topic.name}`)
    }
    
    // 取消订阅主题
    const unsubscribeTopic = (topicName) => {
      const index = subscribedTopics.value.findIndex(t => t.name === topicName)
      if (index > -1) {
        subscribedTopics.value.splice(index, 1)
        emit('topic-unsubscribed', topicName)
        ElMessage.info(`已取消订阅: ${topicName}`)
      }
    }
    
    // 快速订阅
    const quickSubscribe = (topic, messageType) => {
      const exists = subscribedTopics.value.find(t => t.name === topic)
      if (exists) {
        ElMessage.warning('该主题已订阅')
        return
      }
      
      newSubscription.topic = topic
      newSubscription.messageType = messageType
      subscribeTopic()
    }
    
    // 更新消息统计
    const updateMessageStats = () => {
      let total = 0
      subscribedTopics.value.forEach(topic => {
        total += topic.messageCount || 0
      })
      totalMessages.value = total
      
      // 计算消息频率（简化实现）
      messageRate.value = Math.random() * 50 // 模拟数据
    }
    
    // 定期更新统计信息
    setInterval(updateMessageStats, 1000)
    
    return {
      subscribedTopics,
      newSubscription,
      totalMessages,
      messageRate,
      fetchTopicSuggestions,
      onTopicSelected,
      subscribeTopic,
      unsubscribeTopic,
      quickSubscribe
    }
  }
}
</script>

<style scoped>
.topic-subscription {
  padding: 10px 0;
}

.topic-subscription h4 {
  margin: 0 0 10px 0;
  font-size: 14px;
  color: #333;
}

.empty-state {
  text-align: center;
  padding: 20px;
  color: #999;
}

.topic-list {
  max-height: 200px;
  overflow-y: auto;
}

.topic-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px;
  margin-bottom: 5px;
  background: #f9f9f9;
  border-radius: 4px;
}

.topic-info {
  flex: 1;
}

.topic-name {
  font-weight: 500;
  font-size: 13px;
}

.topic-type {
  font-size: 11px;
  color: #666;
}

.suggestion-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.suggestion-name {
  font-weight: 500;
}

.suggestion-type {
  font-size: 12px;
  color: #666;
}

.quick-buttons {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 15px;
}

.stat-item {
  text-align: center;
  padding: 10px;
  background: #f0f8ff;
  border-radius: 4px;
}

.stat-value {
  font-size: 18px;
  font-weight: bold;
  color: #409eff;
}

.stat-label {
  font-size: 12px;
  color: #666;
  margin-top: 2px;
}
</style>
