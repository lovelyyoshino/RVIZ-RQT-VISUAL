<template>
  <div class="service-caller">
    <!-- 服务选择 -->
    <div class="service-selector">
      <el-select
        v-model="selectedService"
        placeholder="选择服务"
        size="small"
        style="width: 100%"
        @change="onServiceChange"
        filterable
      >
        <el-option
          v-for="service in availableServices"
          :key="service.name"
          :label="service.name"
          :value="service.name"
        >
          <div class="service-option">
            <span class="service-name">{{ service.name }}</span>
            <span class="service-type">{{ service.type }}</span>
          </div>
        </el-option>
      </el-select>
    </div>
    
    <!-- 服务信息 -->
    <div v-if="currentService" class="service-info">
      <el-descriptions :column="1" size="small" border>
        <el-descriptions-item label="服务名称">
          {{ currentService.name }}
        </el-descriptions-item>
        <el-descriptions-item label="服务类型">
          {{ currentService.type }}
        </el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="currentService.available ? 'success' : 'danger'">
            {{ currentService.available ? '可用' : '不可用' }}
          </el-tag>
        </el-descriptions-item>
      </el-descriptions>
    </div>
    
    <!-- 请求参数编辑器 -->
    <div v-if="currentService" class="request-editor">
      <el-divider>请求参数</el-divider>
      <el-scrollbar height="120px">
        <div class="request-form">
          <el-form :model="requestData" label-width="80px" size="small">
            <el-form-item
              v-for="field in currentService.requestFields"
              :key="field.name"
              :label="field.name"
            >
              <!-- 布尔值 -->
              <el-switch
                v-if="field.type === 'bool'"
                v-model="requestData[field.name]"
              />
              
              <!-- 数值 -->
              <el-input-number
                v-else-if="field.type === 'int' || field.type === 'float'"
                v-model="requestData[field.name]"
                :step="field.type === 'int' ? 1 : 0.1"
                style="width: 100%"
              />
              
              <!-- 字符串 -->
              <el-input
                v-else
                v-model="requestData[field.name]"
                :placeholder="`输入 ${field.name}`"
              />
            </el-form-item>
          </el-form>
        </div>
      </el-scrollbar>
    </div>
    
    <!-- 调用按钮 -->
    <div class="call-controls">
      <el-button
        type="primary"
        @click="callService"
        :loading="calling"
        :disabled="!currentService?.available"
        style="width: 100%"
      >
        <el-icon><Phone /></el-icon>
        调用服务
      </el-button>
    </div>
    
    <!-- 响应结果 -->
    <div v-if="lastResponse" class="response-result">
      <el-divider>响应结果</el-divider>
      <el-alert
        :type="lastResponse.success ? 'success' : 'error'"
        :title="lastResponse.success ? '调用成功' : '调用失败'"
        show-icon
        :closable="false"
      />
      
      <div class="response-content">
        <el-scrollbar height="80px">
          <pre class="response-data">{{ formatResponse(lastResponse.data) }}</pre>
        </el-scrollbar>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, reactive, computed } from 'vue'
import { Phone } from '@element-plus/icons-vue'

export default {
  name: 'ServiceCaller',
  components: {
    Phone
  },
  setup() {
    const selectedService = ref('')
    const calling = ref(false)
    const requestData = reactive({})
    const lastResponse = ref(null)
    
    // 可用服务列表
    const availableServices = ref([
      {
        name: '/start_navigation',
        type: 'std_srvs/srv/Empty',
        available: true,
        requestFields: []
      },
      {
        name: '/stop_robot',
        type: 'std_srvs/srv/Empty',
        available: true,
        requestFields: []
      },
      {
        name: '/set_pose',
        type: 'geometry_msgs/srv/SetPose',
        available: true,
        requestFields: [
          { name: 'x', type: 'float' },
          { name: 'y', type: 'float' },
          { name: 'z', type: 'float' },
          { name: 'roll', type: 'float' },
          { name: 'pitch', type: 'float' },
          { name: 'yaw', type: 'float' }
        ]
      },
      {
        name: '/make_plan',
        type: 'nav_msgs/srv/GetPlan',
        available: true,
        requestFields: [
          { name: 'start_x', type: 'float' },
          { name: 'start_y', type: 'float' },
          { name: 'goal_x', type: 'float' },
          { name: 'goal_y', type: 'float' },
          { name: 'tolerance', type: 'float' }
        ]
      },
      {
        name: '/get_map',
        type: 'nav_msgs/srv/GetMap',
        available: true,
        requestFields: []
      },
      {
        name: '/clear_costmaps',
        type: 'std_srvs/srv/Empty',
        available: false,
        requestFields: []
      },
      {
        name: '/spawn_entity',
        type: 'gazebo_msgs/srv/SpawnEntity',
        available: true,
        requestFields: [
          { name: 'name', type: 'string' },
          { name: 'xml', type: 'string' },
          { name: 'robot_namespace', type: 'string' },
          { name: 'initial_pose_x', type: 'float' },
          { name: 'initial_pose_y', type: 'float' },
          { name: 'initial_pose_z', type: 'float' }
        ]
      }
    ])
    
    // 当前选中的服务
    const currentService = computed(() => {
      return availableServices.value.find(s => s.name === selectedService.value)
    })
    
    // 服务选择变化
    const onServiceChange = () => {
      if (currentService.value) {
        // 重置请求数据
        Object.keys(requestData).forEach(key => {
          delete requestData[key]
        })
        
        // 初始化请求字段
        currentService.value.requestFields.forEach(field => {
          switch (field.type) {
            case 'bool':
              requestData[field.name] = false
              break
            case 'int':
              requestData[field.name] = 0
              break
            case 'float':
              requestData[field.name] = 0.0
              break
            case 'string':
              requestData[field.name] = ''
              break
            default:
              requestData[field.name] = ''
          }
        })
        
        // 清除上次响应
        lastResponse.value = null
      }
    }
    
    // 调用服务
    const callService = async () => {
      if (!currentService.value) {
        ElMessage.warning('请选择一个服务')
        return
      }
      
      calling.value = true
      
      try {
        // 模拟服务调用延迟
        await new Promise(resolve => setTimeout(resolve, 1000))
        
        // 模拟不同服务的响应
        const mockResponses = {
          '/start_navigation': {
            success: true,
            data: { message: '导航已启动' }
          },
          '/stop_robot': {
            success: true,
            data: { message: '机器人已停止' }
          },
          '/set_pose': {
            success: Math.random() > 0.2,
            data: {
              success: true,
              pose: {
                position: { x: requestData.x, y: requestData.y, z: requestData.z },
                orientation: { roll: requestData.roll, pitch: requestData.pitch, yaw: requestData.yaw }
              }
            }
          },
          '/make_plan': {
            success: Math.random() > 0.3,
            data: {
              plan: {
                poses: [
                  { position: { x: requestData.start_x, y: requestData.start_y } },
                  { position: { x: (requestData.start_x + requestData.goal_x) / 2, y: (requestData.start_y + requestData.goal_y) / 2 } },
                  { position: { x: requestData.goal_x, y: requestData.goal_y } }
                ]
              }
            }
          },
          '/get_map': {
            success: true,
            data: {
              map: {
                info: {
                  resolution: 0.05,
                  width: 384,
                  height: 384,
                  origin: { position: { x: -9.6, y: -9.6, z: 0 } }
                }
              }
            }
          },
          '/clear_costmaps': {
            success: false,
            data: { error: '服务不可用' }
          },
          '/spawn_entity': {
            success: Math.random() > 0.4,
            data: {
              success: true,
              status_message: `实体 ${requestData.name} 已生成`
            }
          }
        }
        
        const response = mockResponses[selectedService.value] || {
          success: false,
          data: { error: '未知服务' }
        }
        
        lastResponse.value = response
        
        if (response.success) {
          ElMessage.success('服务调用成功')
        } else {
          ElMessage.error('服务调用失败')
        }
        
      } catch (error) {
        lastResponse.value = {
          success: false,
          data: { error: error.message }
        }
        ElMessage.error('服务调用异常')
      } finally {
        calling.value = false
      }
    }
    
    // 格式化响应数据
    const formatResponse = (data) => {
      return JSON.stringify(data, null, 2)
    }
    
    // 刷新服务列表
    const refresh = async () => {
      // 模拟刷新服务可用性
      availableServices.value.forEach(service => {
        service.available = Math.random() > 0.2
      })
      ElMessage.success('服务列表已刷新')
    }
    
    return {
      selectedService,
      calling,
      requestData,
      lastResponse,
      availableServices,
      currentService,
      onServiceChange,
      callService,
      formatResponse,
      // 暴露方法供父组件调用
      refresh
    }
  }
}
</script>

<style scoped>
.service-caller {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.service-selector {
  padding: 0 5px;
}

.service-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.service-name {
  font-weight: 500;
}

.service-type {
  font-size: 12px;
  color: #666;
}

.service-info {
  padding: 0 5px;
}

.request-editor {
  padding: 0 5px;
}

.request-form {
  padding: 5px;
}

.call-controls {
  padding: 0 5px;
}

.response-result {
  flex: 1;
  padding: 0 5px;
  overflow: hidden;
}

.response-content {
  margin-top: 10px;
}

.response-data {
  background: #f5f5f5;
  padding: 10px;
  border-radius: 4px;
  font-size: 12px;
  line-height: 1.4;
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
}
</style>
