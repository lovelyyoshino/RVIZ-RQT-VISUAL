<template>
  <div class="connection-status">
    <el-badge 
      :type="badgeType" 
      is-dot
      class="connection-badge"
    >
      <el-button 
        :type="buttonType"
        size="small"
        @click="toggleConnection"
        :loading="connectionStore.isConnecting"
      >
        <el-icon><Connection /></el-icon>
        {{ connectionStore.connectionStatusText }}
      </el-button>
    </el-badge>
    
    <!-- 连接详情弹窗 -->
    <el-dialog 
      v-model="showDetails" 
      title="连接详情" 
      width="500px"
    >
      <div class="connection-details">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="状态">
            <el-tag :type="tagType">{{ connectionStore.connectionStatusText }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="WebSocket 地址">
            {{ connectionStore.wsUrl }}
          </el-descriptions-item>
          <el-descriptions-item label="已订阅主题">
            {{ connectionStore.subscribedTopics.length }} 个
          </el-descriptions-item>
          <el-descriptions-item label="重连次数">
            {{ connectionStore.reconnectAttempts || 0 }}
          </el-descriptions-item>
        </el-descriptions>
        
        <div v-if="connectionStore.subscribedTopics.length > 0" class="subscribed-topics">
          <h4>已订阅主题：</h4>
          <el-tag 
            v-for="topic in connectionStore.subscribedTopics" 
            :key="topic"
            size="small"
            class="topic-tag"
          >
            {{ topic }}
          </el-tag>
        </div>
      </div>
      
      <template #footer>
        <el-button @click="showDetails = false">关闭</el-button>
        <el-button type="primary" @click="showDetails = false">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, computed } from 'vue'
import { Connection } from '@element-plus/icons-vue'
import { useConnectionStore } from '../../composables/useConnectionStore'

export default {
  name: 'ConnectionStatus',
  components: {
    Connection
  },
  setup() {
    const connectionStore = useConnectionStore()
    const showDetails = ref(false)
    
    // 徽章类型
    const badgeType = computed(() => {
      switch (connectionStore.connectionStatus) {
        case 'connected':
          return 'success'
        case 'connecting':
          return 'warning'
        case 'error':
          return 'danger'
        default:
          return 'info'
      }
    })
    
    // 按钮类型
    const buttonType = computed(() => {
      switch (connectionStore.connectionStatus) {
        case 'connected':
          return 'success'
        case 'connecting':
          return 'warning'
        case 'error':
          return 'danger'
        default:
          return 'default'
      }
    })
    
    // 标签类型
    const tagType = computed(() => {
      switch (connectionStore.connectionStatus) {
        case 'connected':
          return 'success'
        case 'connecting':
          return 'warning'
        case 'error':
          return 'danger'
        default:
          return 'info'
      }
    })
    
    // 切换连接状态
    const toggleConnection = () => {
      if (connectionStore.isConnected) {
        connectionStore.disconnect()
      } else {
        connectionStore.connect()
      }
    }
    
    return {
      connectionStore,
      showDetails,
      badgeType,
      buttonType,
      tagType,
      toggleConnection
    }
  }
}
</script>

<style scoped>
.connection-status {
  display: flex;
  align-items: center;
  gap: 10px;
}

.connection-badge {
  margin-right: 10px;
}

.connection-details {
  margin: 20px 0;
}

.subscribed-topics {
  margin-top: 20px;
}

.subscribed-topics h4 {
  margin-bottom: 10px;
  color: #333;
}

.topic-tag {
  margin: 2px;
}
</style>
