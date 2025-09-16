<template>
  <div class="visualization-plugins">
    <div class="plugin-list">
      <div 
        v-for="plugin in plugins" 
        :key="plugin.id"
        class="plugin-item"
      >
        <div class="plugin-header">
          <el-switch 
            v-model="plugin.enabled" 
            @change="togglePlugin(plugin.id, plugin.enabled)"
          />
          <span class="plugin-name">{{ plugin.name }}</span>
          <el-button 
            size="small" 
            text 
            @click="plugin.showConfig = !plugin.showConfig"
          >
            <el-icon><Setting /></el-icon>
          </el-button>
        </div>
        
        <div class="plugin-description">
          {{ plugin.description }}
        </div>
        
        <div class="plugin-types">
          <el-tag 
            v-for="msgType in plugin.supportedMessageTypes" 
            :key="msgType"
            size="small"
            type="info"
          >
            {{ msgType.split('/').pop() }}
          </el-tag>
        </div>
        
        <!-- 插件配置面板 -->
        <el-collapse-transition>
          <div v-show="plugin.showConfig" class="plugin-config">
            <el-divider />
            <plugin-config 
              :plugin="plugin"
              @config-changed="onConfigChanged"
            />
          </div>
        </el-collapse-transition>
      </div>
    </div>
    
    <!-- 添加插件按钮 -->
    <el-divider />
    <el-button 
      type="primary" 
      size="small"
      @click="showAddPlugin = true"
      style="width: 100%"
    >
      <el-icon><Plus /></el-icon>
      添加插件
    </el-button>
    
    <!-- 添加插件对话框 -->
    <el-dialog 
      v-model="showAddPlugin" 
      title="添加插件" 
      width="500px"
    >
      <div class="available-plugins">
        <div 
          v-for="available in availablePlugins" 
          :key="available.id"
          class="available-plugin"
          @click="addPlugin(available)"
        >
          <div class="available-plugin-info">
            <h4>{{ available.name }}</h4>
            <p>{{ available.description }}</p>
            <div class="available-plugin-meta">
              <el-tag size="small">{{ available.version }}</el-tag>
              <el-tag size="small" type="success">{{ available.author }}</el-tag>
            </div>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive } from 'vue'
import { Setting, Plus } from '@element-plus/icons-vue'
import PluginConfig from './PluginConfig.vue'

export default {
  name: 'VisualizationPlugins',
  components: {
    Setting,
    Plus,
    PluginConfig
  },
  emits: ['plugin-toggled', 'plugin-configured'],
  setup(props, { emit }) {
    const showAddPlugin = ref(false)
    
    // 当前启用的插件
    const plugins = reactive([
      {
        id: 'pointcloud_renderer',
        name: '点云渲染器',
        description: '渲染 PointCloud2 消息类型的点云数据',
        version: '1.0.0',
        author: 'ROS Web Viz',
        enabled: true,
        showConfig: false,
        supportedMessageTypes: ['sensor_msgs/msg/PointCloud2'],
        config: {
          pointSize: 1.0,
          colorMode: 'intensity',
          maxPoints: 100000,
          useOctree: true
        }
      },
      {
        id: 'laserscan_renderer',
        name: '激光雷达渲染器',
        description: '渲染 LaserScan 消息类型的激光雷达数据',
        version: '1.0.0',
        author: 'ROS Web Viz',
        enabled: true,
        showConfig: false,
        supportedMessageTypes: ['sensor_msgs/msg/LaserScan'],
        config: {
          pointSize: 2.0,
          color: '#ff0000',
          showLines: false,
          fadeOldScans: true
        }
      },
      {
        id: 'marker_renderer',
        name: '标记渲染器',
        description: '渲染 Marker 和 MarkerArray 消息类型',
        version: '1.0.0',
        author: 'ROS Web Viz',
        enabled: false,
        showConfig: false,
        supportedMessageTypes: [
          'visualization_msgs/msg/Marker',
          'visualization_msgs/msg/MarkerArray'
        ],
        config: {
          showText: true,
          wireframe: false,
          transparency: 1.0
        }
      },
      {
        id: 'path_renderer',
        name: '路径渲染器',
        description: '渲染 Path 消息类型的路径数据',
        version: '1.0.0',
        author: 'ROS Web Viz',
        enabled: false,
        showConfig: false,
        supportedMessageTypes: ['nav_msgs/msg/Path'],
        config: {
          lineWidth: 2.0,
          color: '#00ff00',
          showArrows: true,
          arrowSize: 0.1
        }
      }
    ])
    
    // 可用的插件（未添加的）
    const availablePlugins = ref([
      {
        id: 'occupancy_grid_renderer',
        name: '栅格地图渲染器',
        description: '渲染 OccupancyGrid 消息类型的栅格地图',
        version: '1.0.0',
        author: 'ROS Web Viz',
        supportedMessageTypes: ['nav_msgs/msg/OccupancyGrid']
      },
      {
        id: 'image_renderer',
        name: '图像渲染器',
        description: '渲染 Image 消息类型的图像数据',
        version: '1.0.0',
        author: 'ROS Web Viz',
        supportedMessageTypes: ['sensor_msgs/msg/Image']
      },
      {
        id: 'tf_renderer',
        name: 'TF 渲染器',
        description: '渲染坐标变换关系',
        version: '1.0.0',
        author: 'ROS Web Viz',
        supportedMessageTypes: ['tf2_msgs/msg/TFMessage']
      }
    ])
    
    // 切换插件状态
    const togglePlugin = (pluginId, enabled) => {
      const plugin = plugins.find(p => p.id === pluginId)
      if (plugin) {
        plugin.enabled = enabled
        emit('plugin-toggled', pluginId, enabled)
        
        if (enabled) {
          ElMessage.success(`已启用插件: ${plugin.name}`)
        } else {
          ElMessage.info(`已禁用插件: ${plugin.name}`)
        }
      }
    }
    
    // 配置变更
    const onConfigChanged = (pluginId, config) => {
      const plugin = plugins.find(p => p.id === pluginId)
      if (plugin) {
        plugin.config = { ...plugin.config, ...config }
        emit('plugin-configured', pluginId, plugin.config)
      }
    }
    
    // 添加插件
    const addPlugin = (availablePlugin) => {
      const newPlugin = {
        ...availablePlugin,
        enabled: false,
        showConfig: false,
        config: {}
      }
      
      plugins.push(newPlugin)
      
      // 从可用列表中移除
      const index = availablePlugins.value.findIndex(p => p.id === availablePlugin.id)
      if (index > -1) {
        availablePlugins.value.splice(index, 1)
      }
      
      showAddPlugin.value = false
      ElMessage.success(`已添加插件: ${availablePlugin.name}`)
    }
    
    return {
      plugins,
      availablePlugins,
      showAddPlugin,
      togglePlugin,
      onConfigChanged,
      addPlugin
    }
  }
}
</script>

<style scoped>
.visualization-plugins {
  padding: 10px 0;
}

.plugin-item {
  margin-bottom: 15px;
  padding: 10px;
  border: 1px solid #e6e6e6;
  border-radius: 4px;
  background: #fafafa;
}

.plugin-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.plugin-name {
  flex: 1;
  font-weight: 500;
}

.plugin-description {
  font-size: 12px;
  color: #666;
  margin-bottom: 8px;
}

.plugin-types {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.plugin-config {
  margin-top: 10px;
}

.available-plugins {
  max-height: 400px;
  overflow-y: auto;
}

.available-plugin {
  padding: 15px;
  margin-bottom: 10px;
  border: 1px solid #e6e6e6;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s;
}

.available-plugin:hover {
  border-color: #409eff;
  background: #f0f8ff;
}

.available-plugin h4 {
  margin: 0 0 5px 0;
  color: #333;
}

.available-plugin p {
  margin: 0 0 10px 0;
  font-size: 14px;
  color: #666;
}

.available-plugin-meta {
  display: flex;
  gap: 5px;
}
</style>
