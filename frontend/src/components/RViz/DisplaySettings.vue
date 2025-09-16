<template>
  <div class="display-settings">
    <el-form label-width="80px" size="small">
      <!-- 渲染设置 -->
      <el-form-item label="背景色">
        <el-color-picker 
          v-model="settings.backgroundColor" 
          @change="emitChange"
        />
      </el-form-item>
      
      <el-form-item label="网格">
        <el-switch 
          v-model="settings.showGrid" 
          @change="emitChange"
        />
      </el-form-item>
      
      <el-form-item label="坐标轴">
        <el-switch 
          v-model="settings.showAxes" 
          @change="emitChange"
        />
      </el-form-item>
      
      <el-form-item label="阴影">
        <el-switch 
          v-model="settings.enableShadows" 
          @change="emitChange"
        />
      </el-form-item>
      
      <el-form-item label="抗锯齿">
        <el-switch 
          v-model="settings.enableAntialiasing" 
          @change="emitChange"
        />
      </el-form-item>
      
      <!-- 点云设置 -->
      <el-divider>点云设置</el-divider>
      
      <el-form-item label="点大小">
        <el-slider 
          v-model="settings.pointSize" 
          :min="0.1" 
          :max="5" 
          :step="0.1"
          @change="emitChange"
        />
      </el-form-item>
      
      <el-form-item label="最大点数">
        <el-input-number 
          v-model="settings.maxPoints" 
          :min="1000" 
          :max="1000000" 
          :step="1000"
          @change="emitChange"
        />
      </el-form-item>
      
      <!-- 相机设置 -->
      <el-divider>相机设置</el-divider>
      
      <el-form-item label="视野角">
        <el-slider 
          v-model="settings.fov" 
          :min="30" 
          :max="120"
          @change="emitChange"
        />
      </el-form-item>
      
      <el-form-item label="近裁剪">
        <el-input-number 
          v-model="settings.near" 
          :min="0.01" 
          :max="1" 
          :step="0.01"
          @change="emitChange"
        />
      </el-form-item>
      
      <el-form-item label="远裁剪">
        <el-input-number 
          v-model="settings.far" 
          :min="100" 
          :max="10000" 
          :step="100"
          @change="emitChange"
        />
      </el-form-item>
    </el-form>
    
    <!-- 预设配置 -->
    <el-divider>预设配置</el-divider>
    
    <el-button-group size="small" class="preset-buttons">
      <el-button @click="applyPreset('default')">默认</el-button>
      <el-button @click="applyPreset('outdoor')">户外</el-button>
      <el-button @click="applyPreset('indoor')">室内</el-button>
    </el-button-group>
  </div>
</template>

<script>
import { reactive } from 'vue'

export default {
  name: 'DisplaySettings',
  emits: ['settings-changed'],
  setup(props, { emit }) {
    const settings = reactive({
      backgroundColor: '#2c3e50',
      showGrid: true,
      showAxes: true,
      enableShadows: false,
      enableAntialiasing: true,
      pointSize: 1.0,
      maxPoints: 100000,
      fov: 75,
      near: 0.1,
      far: 1000
    })
    
    const presets = {
      default: {
        backgroundColor: '#2c3e50',
        showGrid: true,
        showAxes: true,
        enableShadows: false,
        enableAntialiasing: true,
        pointSize: 1.0,
        maxPoints: 100000,
        fov: 75,
        near: 0.1,
        far: 1000
      },
      outdoor: {
        backgroundColor: '#87CEEB',
        showGrid: false,
        showAxes: false,
        enableShadows: true,
        enableAntialiasing: true,
        pointSize: 0.8,
        maxPoints: 200000,
        fov: 60,
        near: 0.1,
        far: 2000
      },
      indoor: {
        backgroundColor: '#f0f0f0',
        showGrid: true,
        showAxes: true,
        enableShadows: false,
        enableAntialiasing: true,
        pointSize: 1.2,
        maxPoints: 50000,
        fov: 90,
        near: 0.01,
        far: 500
      }
    }
    
    const emitChange = () => {
      emit('settings-changed', { ...settings })
    }
    
    const applyPreset = (presetName) => {
      const preset = presets[presetName]
      if (preset) {
        Object.assign(settings, preset)
        emitChange()
        ElMessage.success(`已应用 ${presetName} 预设`)
      }
    }
    
    return {
      settings,
      emitChange,
      applyPreset
    }
  }
}
</script>

<style scoped>
.display-settings {
  padding: 10px 0;
}

.preset-buttons {
  width: 100%;
}

.preset-buttons .el-button {
  flex: 1;
}
</style>
