<template>
  <div class="scene3d-controller">
    <!-- 激光雷达设置 -->
    <div class="control-section">
      <h4>激光雷达设置</h4>
      <div class="laser-controls">
        <div class="control-item">
          <label>激光类型:</label>
          <el-radio-group v-model="laserType" @change="onLaserTypeChange">
            <el-radio label="2d">2D激光</el-radio>
            <el-radio label="3d">3D点云</el-radio>
          </el-radio-group>
        </div>
        
        <div class="control-item" v-if="laserType === '2d'">
          <label>2D激光主题:</label>
          <el-select 
            v-model="selectedLaser2D" 
            @change="onLaser2DChange"
            placeholder="选择激光雷达主题"
            size="small"
            style="width: 100%"
          >
            <el-option
              v-for="topic in availableLaser2D"
              :key="topic.name"
              :label="topic.label"
              :value="topic.name"
            />
          </el-select>
        </div>
        
        <div class="control-item" v-if="laserType === '3d'">
          <label>3D点云主题:</label>
          <el-select 
            v-model="selectedPointCloud" 
            @change="onPointCloudChange"
            placeholder="选择点云主题"
            size="small"
            style="width: 100%"
          >
            <el-option
              v-for="topic in availablePointClouds"
              :key="topic.name"
              :label="topic.label"
              :value="topic.name"
            />
          </el-select>
        </div>
        
        <div class="control-item">
          <label>显示设置:</label>
          <div class="display-options">
            <el-checkbox v-model="showLaserPoints" @change="updateLaserSettings">显示激光点</el-checkbox>
            <el-checkbox v-model="showLaserLines" v-if="laserType === '2d'" @change="updateLaserSettings">显示连线</el-checkbox>
            <el-checkbox v-model="showIntensity" v-if="laserType === '3d'" @change="updateLaserSettings">显示强度</el-checkbox>
          </div>
        </div>

        <div class="control-item" v-if="laserType === '2d'">
          <label>激光点设置:</label>
          <div class="laser-settings">
            <div class="setting-row">
              <span>点大小:</span>
              <el-slider
                v-model="laserPointSize"
                :min="0.05"
                :max="0.5"
                :step="0.05"
                @change="updateLaserSettings"
                style="flex: 1; margin-left: 12px;"
              />
            </div>
          </div>
        </div>
        
        <div class="control-item" v-if="laserType === '3d'">
          <label>点云设置:</label>
          <div class="pointcloud-settings">
            <div class="setting-row">
              <span>点大小:</span>
              <el-slider
                v-model="pointSize"
                :min="0.01"
                :max="0.2"
                :step="0.01"
                @change="updatePointCloudSettings"
                style="flex: 1; margin-left: 12px;"
              />
            </div>
            <div class="setting-row">
              <span>透明度:</span>
              <el-slider 
                v-model="pointOpacity" 
                :min="0.1" 
                :max="1" 
                :step="0.1"
                @change="updatePointCloudSettings"
                style="flex: 1; margin-left: 12px;"
              />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 地图设置 -->
    <div class="control-section">
      <h4>地图设置</h4>
      <div class="map-controls">
        
        <div class="control-item">
          <label>地图文件:</label>
          <div class="file-controls">
            <el-input
              v-model="mapFilePath"
              placeholder="选择.yaml和.pgm文件（可多选）"
              size="small"
              readonly
            />
            <el-button @click="selectMapFile" size="small" type="primary">
              <el-icon><Folder /></el-icon>
              浏览
            </el-button>
          </div>
          <input
            ref="fileInput"
            type="file"
            accept=".yaml,.yml,.pgm"
            @change="onFileSelected"
            multiple
            style="display: none"
          />
        </div>
        
        <div class="control-item">
          <label>显示设置:</label>
          <div class="map-display-options">
            <el-checkbox v-model="showMap" @change="updateMapSettings">显示地图</el-checkbox>
            <el-checkbox v-model="showMapGrid" @change="updateMapSettings">显示网格</el-checkbox>
            <el-checkbox v-model="showMapOrigin" @change="updateMapSettings">显示原点</el-checkbox>
          </div>
        </div>
        
        <div class="control-item">
          <label>地图透明度:</label>
          <el-slider 
            v-model="mapOpacity" 
            :min="0.1" 
            :max="1" 
            :step="0.1"
            @change="updateMapSettings"
            show-input
            input-size="small"
          />
        </div>
        
        <div class="control-buttons">
          <el-button @click="resetMapView" size="small">
            <el-icon><Refresh /></el-icon>
            重置视图
          </el-button>
          <el-button @click="centerOnMap" size="small" type="success">
            <el-icon><Aim /></el-icon>
            居中显示
          </el-button>
        </div>
      </div>
    </div>

    <!-- 位置信息设置 -->
    <div class="control-section">
      <h4>位置信息</h4>
      <div class="position-controls">
        <div class="control-item">
          <label>里程计主题:</label>
          <el-select 
            v-model="selectedOdomTopic" 
            @change="onOdomTopicChange"
            placeholder="选择里程计主题"
            size="small"
            style="width: 100%"
          >
            <el-option
              v-for="topic in availableOdomTopics"
              :key="topic.name"
              :label="topic.label"
              :value="topic.name"
            />
          </el-select>
        </div>
        
        <div class="control-item">
          <label>显示设置:</label>
          <div class="position-display-options">
            <el-checkbox v-model="showTrajectory" @change="updatePositionSettings">显示轨迹</el-checkbox>
          </div>
        </div>
        
        <div class="control-item" v-if="showTrajectory">
          <label>轨迹长度:</label>
          <el-slider
            v-model="trajectoryLength"
            :min="10"
            :max="100"
            :step="10"
            @change="updateTrajectorySettings"
            show-input
            input-size="small"
          />
        </div>

        <div class="control-item">
          <label>导航工具:</label>
          <div class="navigation-tools">
            <el-button-group size="small">
              <el-button
                :type="currentTool === '2d_goal' ? 'primary' : 'default'"
                @click="setNavigationTool('2d_goal')"
                title="点击并拖拽设置目标位置和方向"
              >
                <el-icon><Aim /></el-icon>
                2D目标点
              </el-button>
              <el-button
                :type="currentTool === '2d_pose' ? 'primary' : 'default'"
                @click="setNavigationTool('2d_pose')"
                title="点击并拖拽设置初始位置和方向"
              >
                <el-icon><Location /></el-icon>
                2D位置估计
              </el-button>
              <el-button
                :type="currentTool === 'none' ? 'primary' : 'default'"
                @click="setNavigationTool('none')"
              >
                <el-icon><Close /></el-icon>
                取消
              </el-button>
            </el-button-group>
          </div>
          <div v-if="currentTool !== 'none'" class="tool-hint">
            <small>{{ currentTool === '2d_goal' ? '拖拽设置目标方向 → 发布到 /goal_pose' : '拖拽设置朝向 → 发布到 /initialpose' }}</small>
          </div>
        </div>
        
        <div class="position-info" v-if="currentPose">
          <div class="info-row">
            <span class="label">位置 X:</span>
            <span class="value">{{ currentPose.position.x.toFixed(3) }}m</span>
          </div>
          <div class="info-row">
            <span class="label">位置 Y:</span>
            <span class="value">{{ currentPose.position.y.toFixed(3) }}m</span>
          </div>
          <div class="info-row">
            <span class="label">航向角:</span>
            <span class="value">{{ currentPose.yaw.toFixed(2) }}°</span>
          </div>
          <div class="info-row">
            <span class="label">线速度:</span>
            <span class="value">{{ currentVelocity.linear.toFixed(3) }}m/s</span>
          </div>
          <div class="info-row">
            <span class="label">角速度:</span>
            <span class="value">{{ currentVelocity.angular.toFixed(3) }}rad/s</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 全局控制 -->
    <div class="control-section">
      <h4>场景控制</h4>
      <div class="global-controls">
        <div class="control-buttons">
          <el-button @click="resetCamera" size="small">
            <el-icon><Refresh /></el-icon>
            重置相机
          </el-button>
          <el-button @click="toggleGrid" size="small">
            <el-icon><Grid /></el-icon>
            {{ showGrid ? '隐藏' : '显示' }}网格
          </el-button>
          <el-button @click="toggleAxes" size="small">
            <el-icon><Coordinate /></el-icon>
            {{ showAxes ? '隐藏' : '显示' }}坐标轴
          </el-button>
        </div>
        
        <div class="view-presets">
          <label>视角预设:</label>
          <el-button-group size="small">
            <el-button @click="setViewPreset('top')">俯视图</el-button>
            <el-button @click="setViewPreset('side')">侧视图</el-button>
            <el-button @click="setViewPreset('iso')">等距图</el-button>
          </el-button-group>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { Refresh, Aim, Folder, Grid, Coordinate, Location, Close } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useRosbridge } from '../../composables/useRosbridge'

export default {
  name: 'Scene3DController',
  components: {
    Refresh, Aim, Folder, Grid, Coordinate, Location, Close
  },
  emits: [
    'laser-type-change',
    'laser2d-change',
    'pointcloud-change',
    'map-topic-change',
    'map-file-change',
    'odom-topic-change',
    'settings-update',
    'camera-reset',
    'view-preset',
    'navigation-tool-change'
  ],
  setup(props, { emit }) {
    const rosbridge = useRosbridge()
    
    // 引用
    const fileInput = ref(null)
    
    // 激光雷达设置
    const laserType = ref('2d')
    const selectedLaser2D = ref('')
    const selectedPointCloud = ref('')
    const showLaserPoints = ref(true)
    const showLaserLines = ref(true)
    const showIntensity = ref(false)
    const laserPointSize = ref(0.15)  // 2D激光点大小
    const pointSize = ref(0.05)       // 3D点云大小
    const pointOpacity = ref(0.8)
    
    // 地图设置
    const selectedMapTopic = ref('')
    const mapFilePath = ref('')
    const showMap = ref(true)
    const showMapGrid = ref(false)
    const showMapOrigin = ref(true)
    const mapOpacity = ref(0.8)
    
    // 位置信息设置
    const selectedOdomTopic = ref('/odom')
    const showTrajectory = ref(true)
    const trajectoryLength = ref(100)

    // 导航工具设置
    const currentTool = ref('none')
    
    // 全局设置
    const showGrid = ref(true)
    const showAxes = ref(true)
    
    // 可用主题列表
    const availableTopics = ref([])
    const availableLaser2D = computed(() => 
      availableTopics.value.filter(topic => 
        topic.messageType.includes('LaserScan')
      ).map(topic => ({
        name: topic.name,
        label: topic.name.split('/').pop() || topic.name,
        messageType: topic.messageType
      }))
    )
    
    const availablePointClouds = computed(() =>
      availableTopics.value.filter(topic => 
        topic.messageType.includes('PointCloud2')
      ).map(topic => ({
        name: topic.name,
        label: topic.name.split('/').pop() || topic.name,
        messageType: topic.messageType
      }))
    )
    
    const availableMapTopics = computed(() =>
      availableTopics.value.filter(topic => 
        topic.messageType.includes('OccupancyGrid')
      ).map(topic => ({
        name: topic.name,
        label: topic.name.split('/').pop() || topic.name,
        messageType: topic.messageType
      }))
    )
    
    const availableOdomTopics = computed(() =>
      availableTopics.value.filter(topic => 
        topic.messageType.includes('Odometry')
      ).map(topic => ({
        name: topic.name,
        label: topic.name.split('/').pop() || topic.name,
        messageType: topic.messageType
      }))
    )

    // 当前状态
    const currentPose = ref(null)
    const currentVelocity = ref({
      linear: 0,
      angular: 0
    })

    // 方法定义
    const loadAvailableTopics = async () => {
      try {
        const [topicList, topicTypes] = await Promise.all([
          rosbridge.getTopics(),
          rosbridge.getTopicTypes()
        ])

        availableTopics.value = topicList.map(topicInfo => {
          const topicName = typeof topicInfo === 'string' ? topicInfo : topicInfo.name
          return {
            name: topicName,
            messageType: topicTypes[topicName] || 'unknown'
          }
        })

        console.log('加载可用主题:', availableTopics.value)
        
        // 自动选择默认主题
        if (availableLaser2D.value.length > 0 && !selectedLaser2D.value) {
          selectedLaser2D.value = availableLaser2D.value[0].name
        }
        
        if (availablePointClouds.value.length > 0 && !selectedPointCloud.value) {
          selectedPointCloud.value = availablePointClouds.value[0].name
        }
        
        if (availableMapTopics.value.length > 0 && !selectedMapTopic.value) {
          selectedMapTopic.value = availableMapTopics.value[0].name
        }

      } catch (error) {
        console.error('加载主题列表失败:', error)
      }
    }

    // 事件处理
    const onLaserTypeChange = (type) => {
      console.log('激光类型切换:', type)
      emit('laser-type-change', type)
      
      if (type === '2d' && selectedLaser2D.value) {
        emit('laser2d-change', selectedLaser2D.value)
      } else if (type === '3d' && selectedPointCloud.value) {
        emit('pointcloud-change', selectedPointCloud.value)
      }
    }

    const onLaser2DChange = (topic) => {
      console.log('2D激光主题切换:', topic)
      emit('laser2d-change', topic)
    }

    const onPointCloudChange = (topic) => {
      console.log('点云主题切换:', topic)
      emit('pointcloud-change', topic)
    }

    const onMapTopicChange = (topic) => {
      console.log('地图主题切换:', topic)
      emit('map-topic-change', topic)
    }

    const selectMapFile = () => {
      fileInput.value?.click()
    }

    const onFileSelected = (event) => {
      const files = Array.from(event.target.files)
      if (files.length === 0) return

      // 分类文件类型
      const yamlFiles = files.filter(f => f.name.toLowerCase().endsWith('.yaml') || f.name.toLowerCase().endsWith('.yml'))
      const pgmFiles = files.filter(f => f.name.toLowerCase().endsWith('.pgm'))

      if (files.length === 1) {
        // 单文件选择，按原来的逻辑处理
        const file = files[0]
        mapFilePath.value = file.name
        emit('map-file-change', file)
        ElMessage.success(`已选择地图文件: ${file.name}`)
      } else if (yamlFiles.length === 1 && pgmFiles.length === 1) {
        // 同时选择了YAML和PGM文件
        const yamlFile = yamlFiles[0]
        const pgmFile = pgmFiles[0]

        mapFilePath.value = `${yamlFile.name} + ${pgmFile.name}`
        emit('map-files-change', { yamlFile, pgmFile })
        ElMessage.success(`已选择地图文件对: ${yamlFile.name} + ${pgmFile.name}`)
      } else {
        // 多文件但不是正确的组合
        ElMessage.warning('请选择一个YAML文件和一个PGM文件，或单独选择一个文件')
      }
    }

    const onOdomTopicChange = (topic) => {
      console.log('里程计主题切换:', topic)
      emit('odom-topic-change', topic)
      subscribeToOdom(topic)
    }

    const subscribeToOdom = (topic) => {
      console.log('订阅里程计数据:', topic)
      rosbridge.subscribe(topic, 'nav_msgs/msg/Odometry', (message) => {
        updatePoseFromOdom(message)
      })
    }

    const updatePoseFromOdom = (odomMessage) => {
      if (odomMessage.pose && odomMessage.pose.pose) {
        const pose = odomMessage.pose.pose
        const position = pose.position
        const orientation = pose.orientation
        
        // 计算航向角 (yaw)
        const yaw = Math.atan2(
          2 * (orientation.w * orientation.z + orientation.x * orientation.y),
          1 - 2 * (orientation.y * orientation.y + orientation.z * orientation.z)
        ) * 180 / Math.PI

        currentPose.value = {
          position: {
            x: position.x,
            y: position.y,
            z: position.z
          },
          yaw: yaw
        }
      }

      if (odomMessage.twist && odomMessage.twist.twist) {
        const twist = odomMessage.twist.twist
        currentVelocity.value = {
          linear: Math.sqrt(
            twist.linear.x * twist.linear.x +
            twist.linear.y * twist.linear.y +
            twist.linear.z * twist.linear.z
          ),
          angular: twist.angular.z
        }
      }
    }

    // 设置更新
    const updateLaserSettings = () => {
      emit('settings-update', {
        type: 'laser',
        showLaserPoints: showLaserPoints.value,
        showLaserLines: showLaserLines.value,
        showIntensity: showIntensity.value,
        pointSize: laserPointSize.value
      })
    }

    const updatePointCloudSettings = () => {
      emit('settings-update', {
        type: 'pointcloud',
        pointSize: pointSize.value,
        opacity: pointOpacity.value,
        showIntensity: showIntensity.value
      })
    }

    const updateMapSettings = () => {
      emit('settings-update', {
        type: 'map',
        showMap: showMap.value,
        opacity: mapOpacity.value,
        showGrid: showMapGrid.value,
        showOrigin: showMapOrigin.value
      })
    }

    const updatePositionSettings = () => {
      emit('settings-update', {
        type: 'position',
        showTrajectory: showTrajectory.value,
        trajectoryLength: trajectoryLength.value
      })
    }

    const setNavigationTool = (tool) => {
      currentTool.value = tool
      emit('navigation-tool-change', tool)
      console.log('设置导航工具:', tool)
    }

    const updateTrajectorySettings = () => {
      // 统一使用 trajectoryLength 字段名，便于场景侧消费
      emit('settings-update', {
        type: 'trajectory',
        trajectoryLength: Math.max(10, Math.min(100, trajectoryLength.value))
      })
    }

    // 场景控制
    const resetCamera = () => {
      emit('camera-reset')
    }

    const toggleGrid = () => {
      showGrid.value = !showGrid.value
      emit('settings-update', {
        type: 'scene',
        showGrid: showGrid.value
      })
    }

    const toggleAxes = () => {
      showAxes.value = !showAxes.value
      emit('settings-update', {
        type: 'scene',
        showAxes: showAxes.value
      })
    }

    const resetMapView = () => {
      emit('settings-update', { type: 'map', action: 'reset' })
    }

    const centerOnMap = () => {
      emit('settings-update', { type: 'map', action: 'center' })
    }

    const setViewPreset = (preset) => {
      emit('view-preset', preset)
    }

    // 监听器
    watch(() => selectedOdomTopic.value, (newTopic) => {
      if (newTopic) {
        onOdomTopicChange(newTopic)
      }
    }, { immediate: true })

    // 生命周期
    onMounted(async () => {
      await loadAvailableTopics()
    })

    return {
      // 引用
      fileInput,
      
      // 激光设置
      laserType,
      selectedLaser2D,
      selectedPointCloud,
      showLaserPoints,
      showLaserLines,
      showIntensity,
      laserPointSize,
      pointSize,
      pointOpacity,
      
      // 地图设置
      selectedMapTopic,
      mapFilePath,
      showMap,
      showMapGrid,
      showMapOrigin,
      mapOpacity,
      
      // 位置设置
      selectedOdomTopic,
      showTrajectory,
      trajectoryLength,
      currentPose,
      currentVelocity,
      currentTool,
      
      // 全局设置
      showGrid,
      showAxes,
      
      // 可用主题
      availableLaser2D,
      availablePointClouds,
      availableMapTopics,
      availableOdomTopics,
      
      // 方法
      onLaserTypeChange,
      onLaser2DChange,
      onPointCloudChange,
      onMapTopicChange,
      selectMapFile,
      onFileSelected,
      onOdomTopicChange,
      updateLaserSettings,
      updatePointCloudSettings,
      updateMapSettings,
      updatePositionSettings,
      updateTrajectorySettings,
      setNavigationTool,
      resetCamera,
      toggleGrid,
      toggleAxes,
      resetMapView,
      centerOnMap,
      setViewPreset
    }
  }
}
</script>

<style scoped>
.scene3d-controller {
  height: 100%;
  overflow-y: auto;
  padding: 16px;
  background: rgba(15, 23, 42, 0.4);
  border-radius: 8px;
}

.control-section {
  margin-bottom: 24px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  border: 1px solid rgba(148, 163, 184, 0.2);
}

.control-section h4 {
  margin: 0 0 16px 0;
  color: #e2e8f0;
  font-size: 14px;
  font-weight: 600;
  border-bottom: 1px solid rgba(148, 163, 184, 0.2);
  padding-bottom: 8px;
}

.control-item {
  margin-bottom: 16px;
}

.control-item label {
  display: block;
  margin-bottom: 8px;
  color: #cbd5e1;
  font-size: 12px;
  font-weight: 500;
}

.display-options,
.position-display-options,
.map-display-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.laser-settings,
.pointcloud-settings {
  background: rgba(15, 23, 42, 0.3);
  padding: 12px;
  border-radius: 6px;
}

.setting-row {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
  color: #cbd5e1;
  font-size: 12px;
}

.file-controls {
  display: flex;
  gap: 8px;
  align-items: center;
}

.control-buttons {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 12px;
}

.view-presets {
  margin-top: 16px;
}

.view-presets label {
  display: block;
  margin-bottom: 8px;
  color: #cbd5e1;
  font-size: 12px;
}

.tool-hint {
  margin-top: 8px;
  padding: 6px 8px;
  background: rgba(59, 130, 246, 0.1);
  border-radius: 4px;
  border-left: 3px solid #3b82f6;
}

.tool-hint small {
  color: #93c5fd;
  font-size: 11px;
}

.position-info {
  background: rgba(15, 23, 42, 0.3);
  padding: 12px;
  border-radius: 6px;
  margin-top: 12px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.info-row .label {
  color: #94a3b8;
  font-size: 11px;
}

.info-row .value {
  color: #e2e8f0;
  font-size: 11px;
  font-family: monospace;
  font-weight: 600;
}

/* 深色主题覆盖 */
:deep(.el-radio-group) {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

:deep(.el-radio) {
  color: #cbd5e1 !important;
  margin-right: 0;
}

:deep(.el-checkbox) {
  color: #cbd5e1 !important;
  margin-right: 0;
}

:deep(.el-select .el-input__wrapper) {
  background-color: rgba(15, 23, 42, 0.6) !important;
  border-color: rgba(148, 163, 184, 0.3) !important;
}

:deep(.el-input__wrapper) {
  background-color: rgba(15, 23, 42, 0.6) !important;
  border-color: rgba(148, 163, 184, 0.3) !important;
}

:deep(.el-input__inner) {
  color: #e2e8f0 !important;
}

:deep(.el-slider__runway) {
  background-color: rgba(148, 163, 184, 0.3) !important;
}

:deep(.el-slider__bar) {
  background-color: #409eff !important;
}

:deep(.el-button) {
  border-color: rgba(148, 163, 184, 0.3) !important;
}
</style>
