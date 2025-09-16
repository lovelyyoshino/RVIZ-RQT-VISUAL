<template>
  <div class="parameter-editor">
    <!-- 控制栏 -->
    <div class="editor-controls">
      <el-select
        v-model="selectedNode"
        placeholder="选择节点"
        size="small"
        style="width: 150px"
        @change="loadParameters"
      >
        <el-option
          v-for="node in nodeList"
          :key="node"
          :label="node"
          :value="node"
        />
      </el-select>
      
      <el-button 
        size="small" 
        @click="refresh"
        :loading="loading"
      >
        <el-icon><Refresh /></el-icon>
        刷新
      </el-button>
    </div>
    
    <!-- 参数列表 -->
    <div class="parameter-list">
      <el-table 
        :data="filteredParameters" 
        size="small"
        height="220"
        stripe
      >
        <el-table-column prop="name" label="参数名称" min-width="120">
          <template #default="{ row }">
            <el-text class="param-name">{{ row.name }}</el-text>
          </template>
        </el-table-column>
        
        <el-table-column prop="type" label="类型" width="80">
          <template #default="{ row }">
            <el-tag size="small" :type="getTypeColor(row.type)">
              {{ row.type }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="value" label="值" min-width="100">
          <template #default="{ row }">
            <!-- 布尔值 -->
            <el-switch
              v-if="row.type === 'bool'"
              v-model="row.value"
              @change="updateParameter(row)"
              size="small"
            />
            
            <!-- 数值 -->
            <el-input-number
              v-else-if="row.type === 'int' || row.type === 'double'"
              v-model="row.value"
              @change="updateParameter(row)"
              size="small"
              :step="row.type === 'int' ? 1 : 0.1"
              style="width: 100%"
            />
            
            <!-- 字符串 -->
            <el-input
              v-else-if="row.type === 'string'"
              v-model="row.value"
              @blur="updateParameter(row)"
              size="small"
            />
            
            <!-- 数组 -->
            <el-text v-else type="info">{{ formatArrayValue(row.value) }}</el-text>
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="60">
          <template #default="{ row }">
            <el-button
              size="small"
              text
              @click="resetParameter(row)"
              title="重置为默认值"
            >
              <el-icon><RefreshLeft /></el-icon>
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
    
    <!-- 添加参数 -->
    <el-divider />
    <div class="add-parameter">
      <el-collapse>
        <el-collapse-item title="添加新参数" name="1">
          <el-form :model="newParam" label-width="60px" size="small">
            <el-form-item label="名称">
              <el-input v-model="newParam.name" placeholder="参数名称" />
            </el-form-item>
            
            <el-form-item label="类型">
              <el-select v-model="newParam.type" placeholder="选择类型">
                <el-option label="布尔" value="bool" />
                <el-option label="整数" value="int" />
                <el-option label="小数" value="double" />
                <el-option label="字符串" value="string" />
              </el-select>
            </el-form-item>
            
            <el-form-item label="值">
              <el-switch
                v-if="newParam.type === 'bool'"
                v-model="newParam.value"
              />
              <el-input-number
                v-else-if="newParam.type === 'int' || newParam.type === 'double'"
                v-model="newParam.value"
                :step="newParam.type === 'int' ? 1 : 0.1"
                style="width: 100%"
              />
              <el-input
                v-else
                v-model="newParam.value"
                placeholder="参数值"
              />
            </el-form-item>
            
            <el-form-item>
              <el-button type="primary" @click="addParameter" size="small">
                添加参数
              </el-button>
            </el-form-item>
          </el-form>
        </el-collapse-item>
      </el-collapse>
    </div>
  </div>
</template>

<script>
import { ref, reactive, computed } from 'vue'
import { Refresh, RefreshLeft } from '@element-plus/icons-vue'

export default {
  name: 'ParameterEditor',
  components: {
    Refresh,
    RefreshLeft
  },
  setup() {
    const loading = ref(false)
    const selectedNode = ref('')
    
    // 节点列表
    const nodeList = ref([
      'robot_controller',
      'laser_node',
      'camera_node',
      'navigation',
      'move_base'
    ])
    
    // 参数列表
    const parameters = ref([])
    
    // 新参数表单
    const newParam = reactive({
      name: '',
      type: 'string',
      value: ''
    })
    
    // 过滤后的参数（可以添加搜索功能）
    const filteredParameters = computed(() => {
      return parameters.value
    })
    
    // 加载节点参数
    const loadParameters = async () => {
      if (!selectedNode.value) {
        parameters.value = []
        return
      }
      
      loading.value = true
      try {
        // 模拟加载延迟
        await new Promise(resolve => setTimeout(resolve, 300))
        
        // 模拟不同节点的参数
        const parameterData = {
          'robot_controller': [
            { name: 'max_velocity', type: 'double', value: 1.5, default: 1.0 },
            { name: 'enable_safety', type: 'bool', value: true, default: true },
            { name: 'control_frequency', type: 'int', value: 50, default: 30 },
            { name: 'robot_name', type: 'string', value: 'robot_1', default: 'robot' }
          ],
          'laser_node': [
            { name: 'frame_id', type: 'string', value: 'laser_link', default: 'laser' },
            { name: 'min_range', type: 'double', value: 0.1, default: 0.0 },
            { name: 'max_range', type: 'double', value: 30.0, default: 10.0 },
            { name: 'scan_frequency', type: 'int', value: 10, default: 5 }
          ],
          'camera_node': [
            { name: 'width', type: 'int', value: 640, default: 320 },
            { name: 'height', type: 'int', value: 480, default: 240 },
            { name: 'fps', type: 'int', value: 30, default: 15 },
            { name: 'auto_exposure', type: 'bool', value: false, default: true }
          ],
          'navigation': [
            { name: 'base_global_planner', type: 'string', value: 'navfn/NavfnROS', default: 'navfn/NavfnROS' },
            { name: 'base_local_planner', type: 'string', value: 'dwa_local_planner/DWAPlannerROS', default: 'base_local_planner/TrajectoryPlannerROS' },
            { name: 'max_vel_x', type: 'double', value: 0.8, default: 0.5 },
            { name: 'min_vel_x', type: 'double', value: -0.2, default: 0.0 },
            { name: 'recovery_behaviors', type: 'array', value: ['conservative_reset', 'rotate_recovery'], default: [] }
          ],
          'move_base': [
            { name: 'controller_frequency', type: 'double', value: 20.0, default: 10.0 },
            { name: 'planner_patience', type: 'double', value: 5.0, default: 3.0 },
            { name: 'oscillation_timeout', type: 'double', value: 0.0, default: 0.0 },
            { name: 'shutdown_costmaps', type: 'bool', value: false, default: false }
          ]
        }
        
        parameters.value = parameterData[selectedNode.value] || []
        
        ElMessage.success(`已加载 ${selectedNode.value} 的参数`)
      } catch (error) {
        ElMessage.error('加载参数失败')
      } finally {
        loading.value = false
      }
    }
    
    // 刷新参数
    const refresh = async () => {
      if (selectedNode.value) {
        await loadParameters()
      } else {
        ElMessage.warning('请先选择一个节点')
      }
    }
    
    // 更新参数
    const updateParameter = async (param) => {
      try {
        // 模拟参数更新
        console.log(`Updating parameter ${param.name} to ${param.value}`)
        ElMessage.success(`参数 ${param.name} 已更新`)
      } catch (error) {
        ElMessage.error(`更新参数 ${param.name} 失败`)
      }
    }
    
    // 重置参数
    const resetParameter = async (param) => {
      try {
        param.value = param.default
        await updateParameter(param)
        ElMessage.info(`参数 ${param.name} 已重置为默认值`)
      } catch (error) {
        ElMessage.error(`重置参数 ${param.name} 失败`)
      }
    }
    
    // 添加参数
    const addParameter = async () => {
      if (!newParam.name || !selectedNode.value) {
        ElMessage.warning('请填写参数名称并选择节点')
        return
      }
      
      // 检查参数是否已存在
      if (parameters.value.find(p => p.name === newParam.name)) {
        ElMessage.warning('参数已存在')
        return
      }
      
      try {
        // 添加到参数列表
        const parameter = {
          name: newParam.name,
          type: newParam.type,
          value: newParam.value,
          default: newParam.value
        }
        
        parameters.value.push(parameter)
        
        // 重置表单
        newParam.name = ''
        newParam.type = 'string'
        newParam.value = ''
        
        ElMessage.success(`参数 ${parameter.name} 已添加`)
      } catch (error) {
        ElMessage.error('添加参数失败')
      }
    }
    
    // 获取类型颜色
    const getTypeColor = (type) => {
      const colorMap = {
        'bool': 'success',
        'int': 'primary',
        'double': 'warning',
        'string': 'info',
        'array': 'danger'
      }
      return colorMap[type] || 'info'
    }
    
    // 格式化数组值
    const formatArrayValue = (value) => {
      if (Array.isArray(value)) {
        return `[${value.join(', ')}]`
      }
      return String(value)
    }
    
    // 获取参数数据（供父组件调用）
    const getParameterData = () => {
      return {
        node: selectedNode.value,
        parameters: parameters.value.map(param => ({
          name: param.name,
          type: param.type,
          value: param.value
        }))
      }
    }
    
    return {
      loading,
      selectedNode,
      nodeList,
      parameters,
      filteredParameters,
      newParam,
      loadParameters,
      refresh,
      updateParameter,
      resetParameter,
      addParameter,
      getTypeColor,
      formatArrayValue,
      // 暴露方法供父组件调用
      getParameterData
    }
  }
}
</script>

<style scoped>
.parameter-editor {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.editor-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding: 0 5px;
}

.parameter-list {
  flex: 1;
  overflow: hidden;
}

.param-name {
  font-family: monospace;
  font-size: 12px;
}

.add-parameter {
  margin-top: 10px;
}

.add-parameter :deep(.el-collapse-item__header) {
  padding-left: 10px;
  font-size: 13px;
}

.add-parameter :deep(.el-collapse-item__content) {
  padding: 10px;
}
</style>
