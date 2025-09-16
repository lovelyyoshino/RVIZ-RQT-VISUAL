<template>
  <div class="plugin-config">
    <!-- 点云渲染器配置 -->
    <div v-if="plugin.id === 'pointcloud_renderer'" class="config-section">
      <el-form label-width="80px" size="small">
        <el-form-item label="点大小">
          <el-slider 
            v-model="localConfig.pointSize" 
            :min="0.1" 
            :max="5" 
            :step="0.1"
            @change="emitChange"
          />
        </el-form-item>
        
        <el-form-item label="颜色模式">
          <el-select v-model="localConfig.colorMode" @change="emitChange">
            <el-option label="强度" value="intensity" />
            <el-option label="高度" value="height" />
            <el-option label="RGB" value="rgb" />
            <el-option label="单色" value="solid" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="最大点数">
          <el-input-number 
            v-model="localConfig.maxPoints" 
            :min="1000" 
            :max="1000000" 
            :step="1000"
            @change="emitChange"
          />
        </el-form-item>
        
        <el-form-item label="八叉树">
          <el-switch v-model="localConfig.useOctree" @change="emitChange" />
        </el-form-item>
      </el-form>
    </div>
    
    <!-- 激光雷达渲染器配置 -->
    <div v-else-if="plugin.id === 'laserscan_renderer'" class="config-section">
      <el-form label-width="80px" size="small">
        <el-form-item label="点大小">
          <el-slider 
            v-model="localConfig.pointSize" 
            :min="0.5" 
            :max="10" 
            :step="0.5"
            @change="emitChange"
          />
        </el-form-item>
        
        <el-form-item label="颜色">
          <el-color-picker v-model="localConfig.color" @change="emitChange" />
        </el-form-item>
        
        <el-form-item label="显示线条">
          <el-switch v-model="localConfig.showLines" @change="emitChange" />
        </el-form-item>
        
        <el-form-item label="淡化旧扫描">
          <el-switch v-model="localConfig.fadeOldScans" @change="emitChange" />
        </el-form-item>
      </el-form>
    </div>
    
    <!-- 标记渲染器配置 -->
    <div v-else-if="plugin.id === 'marker_renderer'" class="config-section">
      <el-form label-width="80px" size="small">
        <el-form-item label="显示文本">
          <el-switch v-model="localConfig.showText" @change="emitChange" />
        </el-form-item>
        
        <el-form-item label="线框模式">
          <el-switch v-model="localConfig.wireframe" @change="emitChange" />
        </el-form-item>
        
        <el-form-item label="透明度">
          <el-slider 
            v-model="localConfig.transparency" 
            :min="0" 
            :max="1" 
            :step="0.1"
            @change="emitChange"
          />
        </el-form-item>
      </el-form>
    </div>
    
    <!-- 路径渲染器配置 -->
    <div v-else-if="plugin.id === 'path_renderer'" class="config-section">
      <el-form label-width="80px" size="small">
        <el-form-item label="线宽">
          <el-slider 
            v-model="localConfig.lineWidth" 
            :min="1" 
            :max="10" 
            :step="1"
            @change="emitChange"
          />
        </el-form-item>
        
        <el-form-item label="颜色">
          <el-color-picker v-model="localConfig.color" @change="emitChange" />
        </el-form-item>
        
        <el-form-item label="显示箭头">
          <el-switch v-model="localConfig.showArrows" @change="emitChange" />
        </el-form-item>
        
        <el-form-item v-if="localConfig.showArrows" label="箭头大小">
          <el-slider 
            v-model="localConfig.arrowSize" 
            :min="0.05" 
            :max="0.5" 
            :step="0.05"
            @change="emitChange"
          />
        </el-form-item>
      </el-form>
    </div>
    
    <!-- 通用配置 -->
    <div v-else class="config-section">
      <el-text type="info">该插件暂无可配置项</el-text>
    </div>
  </div>
</template>

<script>
import { ref, watch } from 'vue'

export default {
  name: 'PluginConfig',
  props: {
    plugin: {
      type: Object,
      required: true
    }
  },
  emits: ['config-changed'],
  setup(props, { emit }) {
    const localConfig = ref({ ...props.plugin.config })
    
    // 监听插件变化
    watch(() => props.plugin.config, (newConfig) => {
      localConfig.value = { ...newConfig }
    }, { deep: true })
    
    const emitChange = () => {
      emit('config-changed', props.plugin.id, localConfig.value)
    }
    
    return {
      localConfig,
      emitChange
    }
  }
}
</script>

<style scoped>
.plugin-config {
  padding: 10px 0;
}

.config-section {
  background: #f9f9f9;
  padding: 15px;
  border-radius: 4px;
}
</style>
