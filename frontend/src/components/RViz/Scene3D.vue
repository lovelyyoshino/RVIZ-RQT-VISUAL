<template>
  <div 
    ref="containerRef" 
    class="scene3d-container"
    tabindex="0"
    @mousedown="onMouseDown"
    @contextmenu.prevent
  >
    <!-- 加载指示器 -->
    <div v-if="loading" class="loading-overlay">
      <div class="loading-spinner">
        <div class="spinner"></div>
      </div>
      <span>初始化 3D 场景...</span>
    </div>
    
    <!-- 调试快捷键提示 -->
    <div class="debug-hint" v-show="!loading">
      <div class="hint-content">
        <small>快捷键: D-调试 | R-重置 | F-适配点云 | G-网格 | M-适配地图 | C-检查订阅</small>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import * as THREE from 'three'
import { ElMessage } from 'element-plus'
import { useRosbridge } from '../../composables/useRosbridge'

export default {
  name: 'Scene3D',
  emits: ['object-selected', 'camera-moved'],
  setup(props, { emit }) {
    const rosbridge = useRosbridge()
    const containerRef = ref(null)
    const loading = ref(true)
    
    // Three.js 核心对象
    let scene = null
    let camera = null
    let renderer = null
    let controls = null
    let animationId = null
    
    // 场景对象
    let gridHelper = null
    let axesHelper = null
    let ambientLight = null
    let directionalLight = null
    
    // 性能监控
    const performanceStats = ref({
      fps: 0,
      objects: 0,
      vertices: 0
    })
    
    // 可视化对象和ROS订阅管理
    const visualizationObjects = new Map()
    const rosSubscriptions = new Map()
    const plugins = new Map()
    
    // 地图相关对象
    const mapMesh = ref(null)
    const mapTexture = ref(null)
    
    // FPS 计算
    let lastTime = 0
    let frameCount = 0
    let fpsTime = 0
    
    /**
     * 初始化 Three.js 场景
     */
    const initScene = async () => {
      try {
        // 创建场景
        scene = new THREE.Scene()
        scene.background = new THREE.Color(0x2c3e50)
        
        // 创建相机
        const aspect = containerRef.value.clientWidth / containerRef.value.clientHeight
        camera = new THREE.PerspectiveCamera(75, aspect, 0.1, 1000)
        camera.position.set(5, 5, 5)
        camera.lookAt(0, 0, 0)
        
        // 创建渲染器
        renderer = new THREE.WebGLRenderer({ 
          antialias: true,
          alpha: true
        })
        renderer.setSize(containerRef.value.clientWidth, containerRef.value.clientHeight)
        renderer.setPixelRatio(window.devicePixelRatio)
        renderer.shadowMap.enabled = true
        renderer.shadowMap.type = THREE.PCFSoftShadowMap
        containerRef.value.appendChild(renderer.domElement)
        
        // 创建轨道控制器
        const { OrbitControls } = await import('three/examples/jsm/controls/OrbitControls.js')
        controls = new OrbitControls(camera, renderer.domElement)
        controls.enableDamping = true
        controls.dampingFactor = 0.05
        controls.addEventListener('change', onCameraChange)
        
        // 创建光照
        ambientLight = new THREE.AmbientLight(0x404040, 0.6)
        scene.add(ambientLight)
        
        directionalLight = new THREE.DirectionalLight(0xffffff, 0.8)
        directionalLight.position.set(10, 10, 5)
        directionalLight.castShadow = true
        directionalLight.shadow.mapSize.width = 2048
        directionalLight.shadow.mapSize.height = 2048
        scene.add(directionalLight)
        
        // 创建网格
        gridHelper = new THREE.GridHelper(20, 20, 0x888888, 0x444444)
        scene.add(gridHelper)
        
        // 创建坐标轴
        axesHelper = new THREE.AxesHelper(2)
        scene.add(axesHelper)
        
        // 窗口大小调整监听
        window.addEventListener('resize', onWindowResize)
        
        // 添加调试快捷键
        window.addEventListener('keydown', onKeyDown)
        
        // 开始渲染循环
        animate()
        
        loading.value = false
        console.log('3D Scene initialized successfully')
        
      } catch (error) {
        console.error('Failed to initialize 3D scene:', error)
        loading.value = false
      }
    }
    
    /**
     * 渲染循环
     */
    const animate = (currentTime = 0) => {
      animationId = requestAnimationFrame(animate)
      
      // 更新控制器
      if (controls) {
        controls.update()
      }
      
      // 渲染场景
      if (renderer && scene && camera) {
        renderer.render(scene, camera)
      }
      
      // 计算 FPS
      frameCount++
      fpsTime += currentTime - lastTime
      lastTime = currentTime
      
      if (fpsTime >= 1000) {
        performanceStats.value.fps = Math.round((frameCount * 1000) / fpsTime)
        frameCount = 0
        fpsTime = 0
      }
      
      // 更新对象和顶点数
      if (scene) {
        let objectCount = 0
        let vertexCount = 0
        
        scene.traverse((object) => {
          if (object.isMesh) {
            objectCount++
            if (object.geometry) {
              const positionAttribute = object.geometry.getAttribute('position')
              if (positionAttribute) {
                vertexCount += positionAttribute.count
              }
            }
          }
        })
        
        performanceStats.value.objects = objectCount
        performanceStats.value.vertices = vertexCount
      }
    }
    
    /**
     * 窗口大小调整
     */
    const onWindowResize = () => {
      if (!containerRef.value || !camera || !renderer) return
      
      const width = containerRef.value.clientWidth
      const height = containerRef.value.clientHeight
      
      camera.aspect = width / height
      camera.updateProjectionMatrix()
      
      renderer.setSize(width, height)
    }
    
    /**
     * 相机变化事件
     */
    const onCameraChange = () => {
      if (camera) {
        emit('camera-moved', {
          position: camera.position.clone(),
          target: controls.target.clone(),
          zoom: camera.zoom
        })
      }
    }
    
    /**
     * 鼠标点击事件
     */
    const onMouseDown = (event) => {
      if (event.button === 0) { // 左键点击
        // 射线检测
        const raycaster = new THREE.Raycaster()
        const mouse = new THREE.Vector2()
        
        const rect = containerRef.value.getBoundingClientRect()
        mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
        mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1
        
        raycaster.setFromCamera(mouse, camera)
        const intersects = raycaster.intersectObjects(scene.children, true)
        
        if (intersects.length > 0) {
          const object = intersects[0].object
          emit('object-selected', {
            object: object,
            point: intersects[0].point,
            distance: intersects[0].distance
          })
        }
      }
    }
    
    /**
     * 键盘事件处理（调试用）
     */
    const onKeyDown = (event) => {
      // 只在Scene3D容器获得焦点时处理
      if (document.activeElement === containerRef.value || 
          containerRef.value?.contains(document.activeElement)) {
        
        switch (event.key.toLowerCase()) {
          case 'd':
            // D键：显示调试信息
            addDebugInfo()
            break
          case 'r':
            // R键：重置相机
            resetCamera()
            break
          case 'f':
            // F键：自动适配到点云
            if (visualizationObjects.size > 0) {
              for (const [topic, obj] of visualizationObjects) {
                if (obj.userData?.messageType === 'sensor_msgs/msg/PointCloud2') {
                  fitCameraToPointCloud(obj)
                  ElMessage.info(`已适配到点云: ${topic}`)
                  break
                }
              }
            } else {
              ElMessage.warning('没有点云数据可适配')
            }
            break
          case 'g':
            // G键：切换网格
            setGridVisible(!gridHelper?.visible)
            break
          case 'm':
            // M键：适配到地图
            const mapObject = visualizationObjects.get('loaded_map')
            if (mapObject) {
              fitCameraToMap(mapObject)
              ElMessage.info('已适配到地图视图')
            } else {
              ElMessage.warning('没有加载的地图')
            }
            break
          case 'c':
            // C键：检查订阅状态
            checkSubscriptionStatus()
            break
        }
      }
    }
    
    // 公共方法
    const resetCamera = () => {
      if (camera && controls) {
        camera.position.set(5, 5, 5)
        controls.target.set(0, 0, 0)
        controls.update()
      }
    }
    
    const setGridVisible = (visible) => {
      if (gridHelper) {
        gridHelper.visible = visible
      }
    }
    
    const setAxesVisible = (visible) => {
      if (axesHelper) {
        axesHelper.visible = visible
      }
    }
    
    const setBackgroundColor = (color) => {
      console.log('Setting background color to:', color)
      if (scene) {
        try {
          // 支持多种颜色格式
          let threeColor
          if (typeof color === 'string') {
            threeColor = new THREE.Color(color)
          } else if (typeof color === 'number') {
            threeColor = new THREE.Color(color)
          } else if (color && typeof color === 'object' && 'r' in color) {
            threeColor = new THREE.Color(color.r, color.g, color.b)
          } else {
            threeColor = new THREE.Color(color || '#2c3e50')
          }
          
          scene.background = threeColor
          console.log('Background color updated to:', threeColor.getHexString())
        } catch (error) {
          console.error('Failed to set background color:', error)
          // 设置默认颜色
          scene.background = new THREE.Color('#2c3e50')
        }
      } else {
        console.warn('Scene not initialized when trying to set background color')
      }
    }
    
    const updateRenderSettings = (settings) => {
      if (renderer) {
        // 更新渲染设置
        if (settings.shadows !== undefined) {
          renderer.shadowMap.enabled = settings.shadows
        }
        if (settings.antialias !== undefined) {
          // 抗锯齿需要重新创建渲染器
        }
      }
      
      if (scene && settings.backgroundColor) {
        scene.background = new THREE.Color(settings.backgroundColor)
      }
    }
    
    const togglePlugin = (pluginId, enabled) => {
      const plugin = plugins.get(pluginId)
      if (plugin) {
        plugin.enabled = enabled
        // 更新插件状态
      }
    }
    
    const configurePlugin = (pluginId, config) => {
      const plugin = plugins.get(pluginId)
      if (plugin) {
        plugin.config = { ...plugin.config, ...config }
        // 应用配置
      }
    }
    
    // ROS主题订阅方法
    const subscribeToRosTopic = (topicName, messageType) => {
      console.log(`[Scene3D] 订阅ROS主题: ${topicName}, 类型: ${messageType}`)
      
      // 如果已经订阅了这个主题，先取消订阅
      if (rosSubscriptions.has(topicName)) {
        console.log(`[Scene3D] 主题 ${topicName} 已存在，先取消订阅`)
        unsubscribeFromRosTopic(topicName)
      }
      
      try {
        // 使用rosbridge订阅主题
        console.log(`[Scene3D] 调用rosbridge.subscribe...`)
        
        const subscription = rosbridge.subscribe(topicName, messageType, (message) => {
          const now = Date.now()
          const subInfo = rosSubscriptions.get(topicName)
          
          if (subInfo) {
            subInfo.messageCount = (subInfo.messageCount || 0) + 1
            subInfo.lastMessageTime = now
            
            console.log(`[Scene3D] 🎉 收到主题 ${topicName} 的第${subInfo.messageCount}条消息:`, message)
            updateVisualization(topicName, messageType, message)
          }
        })
        
        console.log(`[Scene3D] rosbridge.subscribe返回:`, subscription)
        
        // 检查订阅是否成功
        if (subscription) {
          // 存储订阅引用和统计信息
          const subscriptionInfo = {
            ...subscription,
            subscribeTime: Date.now(),
            lastMessageTime: 0,
            messageCount: 0,
            topicName,
            messageType
          }
          
          rosSubscriptions.set(topicName, subscriptionInfo)
          console.log(`[Scene3D] ✅ 成功订阅主题: ${topicName}, 当前订阅数: ${rosSubscriptions.size}`)
          
          // 设置定时检查，确认是否收到数据
          setTimeout(() => {
            const sub = rosSubscriptions.get(topicName)
            if (sub && sub.messageCount === 0) {
              console.warn(`[Scene3D] ⚠️ 主题 ${topicName} 在 5 秒内没有收到任何消息`)
              ElMessage.warning(`主题 ${topicName} 可能没有数据发布，请检查ROS系统`)
            } else if (sub) {
              console.log(`[Scene3D] ✅ 主题 ${topicName} 正常，已收到 ${sub.messageCount} 条消息`)
            }
          }, 5000)
          
          return true
        } else {
          console.error(`[Scene3D] ❌ rosbridge.subscribe返回null/false`)
          ElMessage.error(`订阅主题 ${topicName} 失败`)
          return false
        }
        
      } catch (error) {
        console.error(`[Scene3D] ❌ 订阅主题 ${topicName} 失败:`, error)
        ElMessage.error(`订阅主题 ${topicName} 异常: ${error.message}`)
        return false
      }
    }
    
    // 取消ROS主题订阅
    const unsubscribeFromRosTopic = (topicName) => {
      const subscription = rosSubscriptions.get(topicName)
      if (subscription) {
        try {
          rosbridge.unsubscribe(subscription)
          rosSubscriptions.delete(topicName)
          removeVisualization(topicName)
          console.log(`已取消订阅主题: ${topicName}`)
        } catch (error) {
          console.error(`取消订阅主题 ${topicName} 失败:`, error)
        }
      }
    }
    
    const updateVisualization = (topic, messageType, message) => {
      console.log(`[Scene3D] 📡 收到可视化更新请求`)
      console.log(`[Scene3D] - 主题: ${topic}`)
      console.log(`[Scene3D] - 消息类型: ${messageType}`)
      console.log(`[Scene3D] - 消息内容:`, message)
      console.log(`[Scene3D] - 消息类型: ${typeof message}`)
      console.log(`[Scene3D] - 消息键值:`, Object.keys(message || {}))
      
      // 记录处理前的状态
      const beforeCount = visualizationObjects.size
      console.log(`[Scene3D] - 处理前可视化对象数: ${beforeCount}`)
      
      try {
        // 根据消息类型更新可视化
        switch (messageType) {
          case 'sensor_msgs/msg/PointCloud2':
          case 'sensor_msgs/PointCloud2':
            console.log(`[Scene3D] 🔄 处理点云消息...`)
            updatePointCloud(topic, message)
            break
          case 'sensor_msgs/msg/LaserScan':
          case 'sensor_msgs/LaserScan':
            console.log(`[Scene3D] 🔄 处理激光雷达消息...`)
            updateLaserScan(topic, message)
            break
          case 'visualization_msgs/msg/Marker':
          case 'visualization_msgs/Marker':
            console.log(`[Scene3D] 🔄 处理标记消息...`)
            updateMarker(topic, message)
            break
          case 'visualization_msgs/msg/MarkerArray':
          case 'visualization_msgs/MarkerArray':
            console.log(`[Scene3D] 🔄 处理标记数组消息...`)
            updateMarkerArray(topic, message)
            break
          case 'nav_msgs/msg/Path':
          case 'nav_msgs/Path':
            console.log(`[Scene3D] 🔄 处理路径消息...`)
            updatePath(topic, message)
            break
          case 'nav_msgs/msg/OccupancyGrid':
          case 'nav_msgs/OccupancyGrid':
            console.log(`[Scene3D] 🔄 处理栅格地图消息...`)
            updateOccupancyGrid(topic, message)
            break
          default:
            console.warn(`[Scene3D] ⚠️ 不支持的消息类型: ${messageType}`)
            return
        }
        
        // 记录处理后的状态
        const afterCount = visualizationObjects.size
        console.log(`[Scene3D] - 处理后可视化对象数: ${afterCount}`)
        
        if (afterCount > beforeCount) {
          console.log(`[Scene3D] ✅ 成功创建可视化对象，新增 ${afterCount - beforeCount} 个对象`)
          
          // 列出所有可视化对象
          visualizationObjects.forEach((obj, topicName) => {
            console.log(`[Scene3D] - 对象: ${topicName}, 类型: ${obj.userData?.messageType}, 可见: ${obj.visible}`)
          })
        } else if (afterCount === beforeCount) {
          console.log(`[Scene3D] ⚠️ 处理完成但没有新增可视化对象`)
        }
        
      } catch (error) {
        console.error(`[Scene3D] ❌ 处理可视化消息时发生错误:`, error)
      }
    }
    
    const removeVisualization = (topic) => {
      const object = visualizationObjects.get(topic)
      if (object) {
        scene.remove(object)
        visualizationObjects.delete(topic)
      }
    }
    
    const getPerformanceStats = () => {
      return performanceStats.value
    }
    
    // 可视化更新方法
    const updatePointCloud = (topic, message) => {
      console.log(`Updating point cloud for ${topic}`)
      console.log('Raw message:', message)
      console.log('Message keys:', Object.keys(message || {}))
      console.log('Message type:', typeof message)
      
      try {
        // 移除旧的点云
        removeVisualization(topic)
        
        // 创建新的点云几何体
        const geometry = new THREE.BufferGeometry()
        const positions = []
        const colors = []
        
        let pointsProcessed = 0
        
        // 解析点云数据
        if (message && typeof message === 'object') {
          console.log('Processing PointCloud2 message')
          console.log('Fields:', message.fields)
          console.log('Width:', message.width)
          console.log('Height:', message.height)
          console.log('Point step:', message.point_step)
          console.log('Data length:', message.data?.length)
          console.log('Data type:', typeof message.data)
          
          // 如果是 PointCloud2 格式
          if (message.fields && message.data) {
            let dataArray = message.data
            
            // 处理Base64编码的数据（ROSBridge通常这样传输）
            if (typeof message.data === 'string') {
              console.log('Decoding Base64 data...')
              try {
                const binaryString = atob(message.data)
                dataArray = new Uint8Array(binaryString.length)
                for (let i = 0; i < binaryString.length; i++) {
                  dataArray[i] = binaryString.charCodeAt(i)
                }
                console.log('Decoded data length:', dataArray.length)
              } catch (e) {
                console.error('Base64 decode failed:', e)
                dataArray = []
              }
            }
            
            const width = message.width || 1
            const height = message.height || 1
            const pointStep = message.point_step || 16
            const totalPoints = width * height
            
            console.log(`Processing ${totalPoints} points with step ${pointStep}`)
            
            // 查找XYZ字段的偏移量
            let xOffset = 0, yOffset = 4, zOffset = 8
            if (message.fields && Array.isArray(message.fields)) {
              message.fields.forEach(field => {
                console.log(`Field: ${field.name}, offset: ${field.offset}, datatype: ${field.datatype}`)
                if (field.name === 'x') xOffset = field.offset
                else if (field.name === 'y') yOffset = field.offset
                else if (field.name === 'z') zOffset = field.offset
              })
            }
            
            console.log(`Using offsets - X: ${xOffset}, Y: ${yOffset}, Z: ${zOffset}`)
            
            // 解析点云数据
            const maxPoints = Math.min(totalPoints, 10000) // 限制最大点数
            for (let i = 0; i < maxPoints; i++) {
              const byteIndex = i * pointStep
              
              if (byteIndex + Math.max(xOffset, yOffset, zOffset) + 4 <= dataArray.length) {
                try {
                  // 创建DataView来正确读取浮点数
                  const buffer = new ArrayBuffer(pointStep)
                  const view = new Uint8Array(buffer)
                  
                  // 复制数据
                  for (let j = 0; j < Math.min(pointStep, dataArray.length - byteIndex); j++) {
                    view[j] = dataArray[byteIndex + j]
                  }
                  
                  const dataView = new DataView(buffer)
                  
                  // 读取XYZ坐标（假设为32位浮点数，小端序）
                  const x = dataView.getFloat32(xOffset, true)
                  const y = dataView.getFloat32(yOffset, true)
                  const z = dataView.getFloat32(zOffset, true)
                  
                  // 验证坐标值
                  if (!isNaN(x) && !isNaN(y) && !isNaN(z) && 
                      isFinite(x) && isFinite(y) && isFinite(z) &&
                      Math.abs(x) < 1000 && Math.abs(y) < 1000 && Math.abs(z) < 1000) {
                    
                    positions.push(x, y, z)
                    pointsProcessed++
                    
                    // 根据高度生成颜色
                    const normalizedZ = Math.max(0, Math.min(1, (z + 2) / 4)) // 假设z范围-2到2
                    const hue = (1 - normalizedZ) * 240 / 360 // 从蓝色到红色
                    const color = new THREE.Color().setHSL(hue, 0.8, 0.6)
                    colors.push(color.r, color.g, color.b)
                  }
                } catch (parseError) {
                  // 忽略单个点的解析错误
                }
              }
            }
            
            console.log(`Successfully processed ${pointsProcessed} points out of ${maxPoints}`)
          }
          // 如果是简单的点数组格式
          else if (Array.isArray(message.points)) {
            console.log('Processing points array format')
            for (let i = 0; i < Math.min(message.points.length, 5000); i++) {
              const point = message.points[i]
              if (point && typeof point === 'object') {
                const x = point.x || 0
                const y = point.y || 0
                const z = point.z || 0
                
                positions.push(x, y, z)
                colors.push(Math.random(), Math.random(), Math.random())
                pointsProcessed++
              }
            }
          }
        }
        
        // 如果没有成功解析出点，创建测试数据以验证渲染
        if (pointsProcessed === 0) {
          console.log('No valid points parsed, creating test point cloud')
          ElMessage.warning(`主题 ${topic} 的点云数据解析失败，显示测试数据`)
          
          for (let i = 0; i < 2000; i++) {
            const angle = (i / 2000) * Math.PI * 4
            const radius = (i / 2000) * 10
            const x = Math.cos(angle) * radius
            const y = Math.sin(angle) * radius
            const z = Math.sin(i / 100) * 2
            
            positions.push(x, y, z)
            
            // 彩色螺旋
            const hue = (i / 2000) % 1
            const color = new THREE.Color().setHSL(hue, 0.8, 0.6)
            colors.push(color.r, color.g, color.b)
          }
          pointsProcessed = 2000
        }
        
        // 创建点云对象
        if (positions.length > 0) {
          geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
          geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3))
          
          // 计算边界框以调整点的大小
          geometry.computeBoundingBox()
          const box = geometry.boundingBox
          const size = Math.max(
            box.max.x - box.min.x,
            box.max.y - box.min.y,
            box.max.z - box.min.z
          )
          
          const material = new THREE.PointsMaterial({
            size: Math.max(0.02, size / 500), // 根据点云尺寸调整点大小
            vertexColors: true,
            sizeAttenuation: true
          })
          
          const pointCloud = new THREE.Points(geometry, material)
          pointCloud.userData = { 
            topic, 
            messageType: 'sensor_msgs/msg/PointCloud2', 
            pointCount: pointsProcessed,
            originalMessage: message
          }
          
          scene.add(pointCloud)
          visualizationObjects.set(topic, pointCloud)
          
          // 自动调整相机视角以查看点云
          fitCameraToPointCloud(pointCloud)
          
          console.log(`✅ Added point cloud with ${pointsProcessed} points`)
          console.log(`Point size: ${material.size}, Bounding box:`, box)
          
          ElMessage.success(`成功显示点云 ${topic}: ${pointsProcessed} 个点`)
        } else {
          console.warn('No positions to create point cloud')
          ElMessage.warning(`点云 ${topic} 没有有效的位置数据`)
        }
        
      } catch (error) {
        console.error('Error updating point cloud:', error)
        ElMessage.error(`点云更新失败: ${error.message}`)
        
        // 创建错误指示器
        const geometry = new THREE.BoxGeometry(2, 2, 2)
        const material = new THREE.MeshBasicMaterial({ 
          color: 0xff0000,
          wireframe: true
        })
        const errorBox = new THREE.Mesh(geometry, material)
        errorBox.userData = { topic, error: true, errorMessage: error.message }
        errorBox.position.set(0, 0, 1)
        
        scene.add(errorBox)
        visualizationObjects.set(topic, errorBox)
        
        console.log('Added error indicator box')
      }
    }
    
    const updateLaserScan = (topic, message) => {
      // 激光雷达可视化实现
      console.log(`Updating laser scan for ${topic}:`, message)
      
      removeVisualization(topic)
      
      const geometry = new THREE.BufferGeometry()
      const positions = []
      
      // 解析激光雷达数据 (简化实现)
      if (message.ranges && message.ranges.length > 0) {
        const angleMin = message.angle_min || -Math.PI
        const angleIncrement = message.angle_increment || (2 * Math.PI) / message.ranges.length
        
        for (let i = 0; i < message.ranges.length; i++) {
          const angle = angleMin + i * angleIncrement
          const range = message.ranges[i]
          
          if (range > 0 && range < 100) {
            const x = range * Math.cos(angle)
            const y = range * Math.sin(angle)
            positions.push(x, y, 0)
          }
        }
      }
      
      geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
      
      const material = new THREE.PointsMaterial({
        size: 0.1,
        color: 0xff0000
      })
      
      const laserScan = new THREE.Points(geometry, material)
      laserScan.userData = { topic, messageType: 'sensor_msgs/msg/LaserScan' }
      
      scene.add(laserScan)
      visualizationObjects.set(topic, laserScan)
    }
    
    const updateMarker = (topic, message) => {
      // 标记可视化实现
      console.log(`Updating marker for ${topic}:`, message)
      
      removeVisualization(topic)
      
      let geometry, material, mesh
      
      switch (message.type) {
        case 1: // CUBE
          geometry = new THREE.BoxGeometry(1, 1, 1)
          break
        case 2: // SPHERE
          geometry = new THREE.SphereGeometry(0.5, 32, 32)
          break
        case 3: // CYLINDER
          geometry = new THREE.CylinderGeometry(0.5, 0.5, 1, 32)
          break
        default:
          geometry = new THREE.BoxGeometry(1, 1, 1)
      }
      
      material = new THREE.MeshLambertMaterial({
        color: new THREE.Color(
          message.color?.r || 1,
          message.color?.g || 0,
          message.color?.b || 0
        ),
        transparent: true,
        opacity: message.color?.a || 1
      })
      
      mesh = new THREE.Mesh(geometry, material)
      
      // 设置位置和旋转
      if (message.pose) {
        mesh.position.set(
          message.pose.position?.x || 0,
          message.pose.position?.y || 0,
          message.pose.position?.z || 0
        )
        
        if (message.pose.orientation) {
          mesh.quaternion.set(
            message.pose.orientation.x || 0,
            message.pose.orientation.y || 0,
            message.pose.orientation.z || 0,
            message.pose.orientation.w || 1
          )
        }
      }
      
      // 设置缩放
      if (message.scale) {
        mesh.scale.set(
          message.scale.x || 1,
          message.scale.y || 1,
          message.scale.z || 1
        )
      }
      
      mesh.userData = { topic, messageType: 'visualization_msgs/msg/Marker' }
      
      scene.add(mesh)
      visualizationObjects.set(topic, mesh)
    }
    
    const updateMarkerArray = (topic, message) => {
      // 标记数组可视化实现
      console.log(`Updating marker array for ${topic}:`, message)
      
      removeVisualization(topic)
      
      const group = new THREE.Group()
      
      if (message.markers && message.markers.length > 0) {
        message.markers.forEach((marker, index) => {
          updateMarker(`${topic}_${index}`, marker)
          const markerObject = visualizationObjects.get(`${topic}_${index}`)
          if (markerObject) {
            group.add(markerObject)
            visualizationObjects.delete(`${topic}_${index}`)
          }
        })
      }
      
      group.userData = { topic, messageType: 'visualization_msgs/msg/MarkerArray' }
      
      scene.add(group)
      visualizationObjects.set(topic, group)
    }
    
    const updatePath = (topic, message) => {
      // 路径可视化实现
      console.log(`Updating path for ${topic}:`, message)
      
      removeVisualization(topic)
      
      const points = []
      
      if (message.poses && message.poses.length > 0) {
        message.poses.forEach(pose => {
          points.push(new THREE.Vector3(
            pose.pose.position?.x || 0,
            pose.pose.position?.y || 0,
            pose.pose.position?.z || 0
          ))
        })
      }
      
      const geometry = new THREE.BufferGeometry().setFromPoints(points)
      const material = new THREE.LineBasicMaterial({ color: 0x00ff00 })
      const path = new THREE.Line(geometry, material)
      
      path.userData = { topic, messageType: 'nav_msgs/msg/Path' }
      
      scene.add(path)
      visualizationObjects.set(topic, path)
    }
    
    const updateOccupancyGrid = (topic, message) => {
      // 栅格地图可视化实现
      console.log(`Updating occupancy grid for ${topic}:`, message)
      
      try {
        removeVisualization(topic)
        
        if (!message.data || !message.info) {
          console.warn('Invalid occupancy grid message')
          return
        }
        
        const info = message.info
        const width = info.width
        const height = info.height
        const resolution = info.resolution
        const origin = info.origin.position
        
        // 创建地图纹理
        const canvas = document.createElement('canvas')
        const ctx = canvas.getContext('2d')
        canvas.width = width
        canvas.height = height
        
        const imageData = ctx.createImageData(width, height)
        const data = imageData.data
        
        // 转换栅格数据到纹理
        for (let i = 0; i < message.data.length; i++) {
          const value = message.data[i]
          const pixelIndex = i * 4
          
          if (value === -1) {
            // 未知区域 - 灰色，半透明
            data[pixelIndex] = 128     // R
            data[pixelIndex + 1] = 128 // G
            data[pixelIndex + 2] = 128 // B
            data[pixelIndex + 3] = 128 // A
          } else if (value === 0) {
            // 自由空间 - 白色，几乎透明
            data[pixelIndex] = 255     // R
            data[pixelIndex + 1] = 255 // G
            data[pixelIndex + 2] = 255 // B
            data[pixelIndex + 3] = 50  // A
          } else {
            // 占用空间 - 黑色，不透明度基于值
            const intensity = Math.min(value / 100 * 255, 255)
            data[pixelIndex] = 0       // R
            data[pixelIndex + 1] = 0   // G
            data[pixelIndex + 2] = 0   // B
            data[pixelIndex + 3] = intensity // A
          }
        }
        
        ctx.putImageData(imageData, 0, 0)
        
        // 创建Three.js纹理
        const texture = new THREE.CanvasTexture(canvas)
        texture.flipY = false
        texture.wrapS = THREE.ClampToEdgeWrapping
        texture.wrapT = THREE.ClampToEdgeWrapping
        
        // 创建地图几何体 - 使用平面几何体
        const geometry = new THREE.PlaneGeometry(
          width * resolution,
          height * resolution
        )
        
        // 创建材质
        const material = new THREE.MeshBasicMaterial({
          map: texture,
          transparent: true,
          opacity: 0.8,
          side: THREE.DoubleSide
        })
        
        // 创建网格
        const mapMesh = new THREE.Mesh(geometry, material)
        
        // 设置位置 - 地图平铺在XY平面上
        mapMesh.position.set(
          origin.x + (width * resolution) / 2,
          origin.y + (height * resolution) / 2,
          0.01 // 稍微抬升避免z-fighting
        )
        
        // 旋转使其水平放置
        mapMesh.rotation.x = 0
        mapMesh.rotation.y = 0
        mapMesh.rotation.z = 0
        
        mapMesh.userData = { 
          topic, 
          messageType: 'nav_msgs/msg/OccupancyGrid',
          mapInfo: info
        }
        
        scene.add(mapMesh)
        visualizationObjects.set(topic, mapMesh)
        
        // 存储地图引用
        if (topic === '/map') {
          mapMesh.value = mapMesh
          mapTexture.value = texture
        }
        
        console.log(`Added occupancy grid map: ${width}x${height}, resolution: ${resolution}m/pixel`)
        
      } catch (error) {
        console.error('Error updating occupancy grid:', error)
        
        // 创建错误指示器
        const geometry = new THREE.BoxGeometry(2, 2, 0.1)
        const material = new THREE.MeshBasicMaterial({ color: 0xff0000 })
        const errorBox = new THREE.Mesh(geometry, material)
        errorBox.userData = { topic, error: true }
        errorBox.position.set(0, 0, 0.05)
        
        scene.add(errorBox)
        visualizationObjects.set(topic, errorBox)
      }
    }
    
    // 生命周期
    onMounted(async () => {
      console.log('Scene3D component mounted')
      await nextTick()
      
      if (containerRef.value) {
        console.log('Container found, initializing scene...')
        console.log('Container size:', containerRef.value.clientWidth, 'x', containerRef.value.clientHeight)
        
        // 确保容器有尺寸后再初始化
        if (containerRef.value.clientWidth > 0 && containerRef.value.clientHeight > 0) {
          await initScene()
        } else {
          console.log('Container has no size, retrying in 100ms')
          setTimeout(async () => {
            if (containerRef.value && containerRef.value.clientWidth > 0) {
              await initScene()
            }
          }, 100)
        }
      } else {
        console.error('Container not found!')
      }
    })
    
    onUnmounted(() => {
      // 清理资源
      if (animationId) {
        cancelAnimationFrame(animationId)
      }
      
      window.removeEventListener('resize', onWindowResize)
      window.removeEventListener('keydown', onKeyDown)
      
      // 清理所有ROS订阅
      rosSubscriptions.forEach((subscription, topicName) => {
        try {
          rosbridge.unsubscribe(subscription)
          console.log(`清理ROS订阅: ${topicName}`)
        } catch (error) {
          console.error(`清理ROS订阅失败: ${topicName}`, error)
        }
      })
      rosSubscriptions.clear()
      
      if (controls) {
        controls.dispose()
      }
      
      if (renderer) {
        renderer.dispose()
      }
      
      // 清理几何体和材质
      visualizationObjects.forEach(object => {
        if (object.geometry) {
          object.geometry.dispose()
        }
        if (object.material) {
          if (Array.isArray(object.material)) {
            object.material.forEach(material => material.dispose())
          } else {
            object.material.dispose()
          }
        }
      })
    })

    // 新增控制方法
    const setLaserType = (type) => {
      console.log('设置激光类型:', type)
      // 在3D场景中切换激光显示方式
    }

    const updateSettings = (settings) => {
      console.log('更新3D场景设置:', settings)
      
      switch (settings.type) {
        case 'pointcloud':
          // 更新点云设置
          if (settings.pointSize !== undefined) {
            // 更新点云大小
          }
          if (settings.opacity !== undefined) {
            // 更新点云透明度
          }
          break
          
        case 'map':
          // 更新地图设置
          if (settings.opacity !== undefined && mapMesh.value) {
            mapMesh.value.material.opacity = settings.opacity
          }
          if (settings.action === 'reset') {
            // 重置地图视图
            resetCamera()
          }
          if (settings.action === 'center') {
            // 居中显示地图
            if (mapMesh.value) {
              const position = mapMesh.value.position
              camera.position.set(position.x, position.y, position.z + 10)
              camera.lookAt(position)
            }
          }
          break
          
        case 'scene':
          // 更新场景设置
          if (settings.showGrid !== undefined) {
            setGridVisible(settings.showGrid)
          }
          if (settings.showAxes !== undefined) {
            setAxesVisible(settings.showAxes)
          }
          break
          
        case 'trajectory':
          // 更新轨迹设置
          console.log('更新轨迹长度:', settings.length)
          break
      }
    }

    const setViewPreset = (preset) => {
      console.log('设置视角预设:', preset)
      
      if (!camera) return
      
      const target = new THREE.Vector3(0, 0, 0)
      
      switch (preset) {
        case 'top':
          // 俯视图
          camera.position.set(0, 0, 20)
          camera.lookAt(target)
          break
          
        case 'side':
          // 侧视图
          camera.position.set(20, 0, 5)
          camera.lookAt(target)
          break
          
        case 'iso':
          // 等距图
          camera.position.set(15, 15, 15)
          camera.lookAt(target)
          break
          
        default:
          resetCamera()
      }
      
      if (controls) {
        controls.target.copy(target)
        controls.update()
      }
    }

    const loadMapFile = async (file) => {
      console.log(`[Scene3D] 加载地图文件: ${file.name}, 大小: ${file.size} bytes`)
      
      try {
        const fileExtension = file.name.toLowerCase().split('.').pop()
        const baseName = file.name.replace(/\.[^/.]+$/, '')
        
        if (fileExtension === 'yaml') {
          const config = await loadMapYaml(file)
          // 存储YAML配置，等待PGM文件
          if (!window.mapConfigs) window.mapConfigs = {}
          window.mapConfigs[baseName] = config
          
          ElMessage.success(`YAML配置已加载: ${file.name}`)
          if (config.image) {
            ElMessage.info(`请选择对应的图像文件: ${config.image}`)
          }
          
        } else if (fileExtension === 'pgm') {
          // 检查是否有对应的YAML配置
          let mapConfig = null
          if (window.mapConfigs && window.mapConfigs[baseName]) {
            mapConfig = window.mapConfigs[baseName]
            console.log(`[Scene3D] 找到对应的YAML配置:`, mapConfig)
          } else {
            console.log(`[Scene3D] 未找到${baseName}.yaml配置，使用默认参数`)
            mapConfig = {
              resolution: 0.05,
              origin: [0, 0, 0],
              occupied_thresh: 0.65,
              free_thresh: 0.196,
              negate: false
            }
          }
          
          await loadMapPgmWithConfig(file, mapConfig)
          
        } else {
          ElMessage.error(`不支持的地图文件格式: ${fileExtension}。支持的格式：YAML, PGM`)
          return
        }
        
      } catch (error) {
        console.error(`[Scene3D] 地图文件加载失败:`, error)
        ElMessage.error(`地图文件加载失败: ${error.message}`)
        
        // 提供更详细的错误信息和建议
        if (error.message.includes('PGM文件格式无效')) {
          ElMessage({
            message: '请确保PGM文件格式正确：支持P5(二进制)和P2(ASCII)格式。请先上传对应的YAML配置文件。',
            type: 'warning',
            duration: 6000
          })
        } else if (error.message.includes('文件读取失败')) {
          ElMessage({
            message: '文件可能已损坏或不完整，请重新选择文件',
            type: 'warning',
            duration: 5000
          })
        }
      }
    }

    const loadMapYaml = async (file) => {
      console.log(`[Scene3D] 解析YAML地图配置文件`)
      
      return new Promise((resolve, reject) => {
        const reader = new FileReader()
        
        reader.onload = (e) => {
          try {
            const yamlContent = e.target.result
            console.log('YAML内容:', yamlContent)
            
            // 简单解析YAML内容（手动解析关键字段）
            const mapConfig = parseMapYaml(yamlContent)
            console.log('解析的地图配置:', mapConfig)
            
            // 如果YAML中指定了图像文件，提示用户也上传PGM文件
            if (mapConfig.image) {
              ElMessage.info(`地图配置已读取，请上传对应的图像文件: ${mapConfig.image}`)
            }
            
            // 存储地图配置用于后续PGM加载
            if (!window.mapConfig) window.mapConfig = {}
            window.mapConfig[file.name] = mapConfig
            
            resolve(mapConfig)
            
          } catch (error) {
            reject(error)
          }
        }
        
        reader.onerror = () => reject(new Error('文件读取失败'))
        reader.readAsText(file)
      })
    }

    const loadMapPgmWithConfig = async (file, mapConfig) => {
      console.log(`[Scene3D] 加载PGM地图图像，使用配置:`, mapConfig)
      
      return new Promise((resolve, reject) => {
        const reader = new FileReader()
        
        reader.onload = (e) => {
          try {
            const arrayBuffer = e.target.result
            const pgmData = parsePgmFile(arrayBuffer)
            
            if (pgmData) {
              createMapFromPgmWithConfig(pgmData, mapConfig, file.name)
              ElMessage.success(`成功加载地图: ${file.name}`)
              resolve(pgmData)
            } else {
              reject(new Error('PGM文件格式无效'))
            }
            
          } catch (error) {
            reject(error)
          }
        }
        
        reader.onerror = () => reject(new Error('文件读取失败'))
        reader.readAsArrayBuffer(file)
      })
    }

    const loadMapPgm = async (file) => {
      console.log(`[Scene3D] 加载PGM地图图像（使用默认配置）`)
      
      const defaultConfig = {
        resolution: 0.05,
        origin: [0, 0, 0],
        occupied_thresh: 0.65,
        free_thresh: 0.196,
        negate: false
      }
      
      return loadMapPgmWithConfig(file, defaultConfig)
    }

    const parseMapYaml = (yamlContent) => {
      const config = {
        resolution: 0.05,
        origin: [0, 0, 0],
        occupied_thresh: 0.65,
        free_thresh: 0.196,
        negate: false,
        image: null
      }
      
      const lines = yamlContent.split('\n')
      for (const line of lines) {
        const trimmed = line.trim()
        if (trimmed.startsWith('#') || !trimmed) continue
        
        const parts = trimmed.split(':')
        if (parts.length >= 2) {
          const key = parts[0].trim()
          const value = parts[1].trim()
          
          switch (key) {
            case 'resolution':
              config.resolution = parseFloat(value)
              break
            case 'origin':
              // 解析数组格式 [x, y, theta]
              const originMatch = value.match(/\[(.*?)\]/)
              if (originMatch) {
                config.origin = originMatch[1].split(',').map(v => parseFloat(v.trim()))
              }
              break
            case 'occupied_thresh':
              config.occupied_thresh = parseFloat(value)
              break
            case 'free_thresh':
              config.free_thresh = parseFloat(value)
              break
            case 'negate':
              config.negate = value === 'true' || value === '1'
              break
            case 'image':
              config.image = value.replace(/['"]/g, '')
              break
          }
        }
      }
      
      return config
    }

    const parsePgmFile = (arrayBuffer) => {
      console.log(`[PGM Parser] 开始解析PGM文件，大小: ${arrayBuffer.byteLength} 字节`)
      
      const uint8Array = new Uint8Array(arrayBuffer)
      let offset = 0
      
      // 读取文本头部，寻找数据开始位置
      let headerLines = []
      let currentLine = ''
      
      // 逐字节读取直到找到完整的头部
      for (let i = 0; i < Math.min(2000, uint8Array.length); i++) {
        const char = String.fromCharCode(uint8Array[i])
        
        if (char === '\n' || char === '\r') {
          if (currentLine.trim()) {
            // 忽略注释行
            if (!currentLine.trim().startsWith('#')) {
              headerLines.push(currentLine.trim())
              console.log(`[PGM Parser] 头部行 ${headerLines.length}: "${currentLine.trim()}"`)
            }
            currentLine = ''
          }
          
          // 检查是否已经有了完整的头部信息
          if (headerLines.length >= 3) {
            // P5 格式需要: 魔数, 宽度高度, 最大值
            offset = i + 1
            // 跳过可能的额外换行符
            while (offset < uint8Array.length && 
                   (uint8Array[offset] === 10 || uint8Array[offset] === 13)) {
              offset++
            }
            break
          }
        } else {
          currentLine += char
        }
      }
      
      console.log(`[PGM Parser] 解析到头部行:`, headerLines)
      console.log(`[PGM Parser] 数据偏移量: ${offset}`)
      
      // 验证头部格式
      if (headerLines.length < 3) {
        console.error('[PGM Parser] 头部信息不完整，至少需要3行')
        return null
      }
      
      // 检查魔数
      const magicNumber = headerLines[0]
      if (magicNumber !== 'P5' && magicNumber !== 'P2') {
        console.error(`[PGM Parser] 不支持的PGM格式: ${magicNumber}，仅支持P5(二进制)和P2(ASCII)`)
        return null
      }
      
      // 解析宽度和高度
      let dimensionLine = headerLines[1]
      let maxValLine = headerLines[2]
      
      // 有些PGM文件可能将宽高分在不同行
      const dimensionParts = dimensionLine.split(/\s+/).filter(p => p)
      let width, height
      
      if (dimensionParts.length >= 2) {
        width = parseInt(dimensionParts[0])
        height = parseInt(dimensionParts[1])
      } else if (dimensionParts.length === 1 && headerLines.length >= 4) {
        // 宽高可能分在两行
        width = parseInt(dimensionParts[0])
        height = parseInt(headerLines[2])
        maxValLine = headerLines[3]
      } else {
        console.error('[PGM Parser] 无法解析图像尺寸')
        return null
      }
      
      const maxVal = parseInt(maxValLine)
      
      if (isNaN(width) || isNaN(height) || isNaN(maxVal)) {
        console.error(`[PGM Parser] 头部参数解析失败: width=${width}, height=${height}, maxVal=${maxVal}`)
        return null
      }
      
      console.log(`[PGM Parser] ✅ PGM图像信息: ${width}x${height}, 最大值: ${maxVal}, 格式: ${magicNumber}`)
      
      // 读取图像数据
      let imageData
      const expectedDataSize = width * height
      
      if (magicNumber === 'P5') {
        // 二进制格式
        imageData = uint8Array.slice(offset)
        if (imageData.length < expectedDataSize) {
          console.error(`[PGM Parser] 二进制数据不完整: 预期 ${expectedDataSize} 字节, 实际 ${imageData.length} 字节`)
          return null
        }
      } else if (magicNumber === 'P2') {
        // ASCII格式 - 需要解析文本数值
        const remainingData = uint8Array.slice(offset)
        const textData = new TextDecoder('ascii').decode(remainingData)
        const values = textData.trim().split(/\s+/).map(v => parseInt(v)).filter(v => !isNaN(v))
        
        if (values.length < expectedDataSize) {
          console.error(`[PGM Parser] ASCII数据不完整: 预期 ${expectedDataSize} 个值, 实际 ${values.length} 个值`)
          return null
        }
        
        imageData = new Uint8Array(values.slice(0, expectedDataSize))
      }
      
      console.log(`[PGM Parser] ✅ 成功解析PGM文件: ${width}x${height}, 数据长度: ${imageData.length}`)
      
      return {
        width,
        height,
        maxVal,
        data: imageData,
        format: magicNumber,
        header: headerLines.join('\n')
      }
    }

    const createMapFromPgmWithConfig = (pgmData, mapConfig, filename) => {
      console.log(`[Scene3D] 创建地图可视化: ${filename}`)
      console.log(`[Scene3D] 使用地图配置:`, mapConfig)
      
      try {
        // 移除旧地图
        removeVisualization('loaded_map')
        
        const { width, height, data, maxVal } = pgmData
        
        console.log(`[Scene3D] PGM数据 - 宽度: ${width}, 高度: ${height}, 最大值: ${maxVal}`)
        console.log(`[Scene3D] 地图配置 - 分辨率: ${mapConfig.resolution}m/pixel, 原点: [${mapConfig.origin.join(', ')}]`)
        
        // 创建Canvas纹理
        const canvas = document.createElement('canvas')
        const ctx = canvas.getContext('2d')
        canvas.width = width
        canvas.height = height
        
        const imageData = ctx.createImageData(width, height)
        const pixels = imageData.data
        
        // 转换PGM数据到RGBA
        for (let i = 0; i < width * height; i++) {
          const pgmValue = data[i]
          const normalizedValue = pgmValue / maxVal
          
          let r, g, b, a
          
          // 根据概率值确定颜色
          if (normalizedValue >= mapConfig.occupied_thresh) {
            // 占用空间 - 黑色
            r = g = b = 0
            a = 255
          } else if (normalizedValue <= mapConfig.free_thresh) {
            // 自由空间 - 白色
            r = g = b = 255
            a = 50  // 半透明
          } else {
            // 未知区域 - 灰色
            r = g = b = 128
            a = 128
          }
          
          // 如果negate为true，反转黑白
          if (mapConfig.negate) {
            if (r === 0 && g === 0 && b === 0) {
              r = g = b = 255
            } else if (r === 255 && g === 255 && b === 255) {
              r = g = b = 0
            }
          }
          
          const pixelIndex = i * 4
          pixels[pixelIndex] = r     // Red
          pixels[pixelIndex + 1] = g // Green
          pixels[pixelIndex + 2] = b // Blue
          pixels[pixelIndex + 3] = a // Alpha
        }
        
        ctx.putImageData(imageData, 0, 0)
        
        // 创建Three.js纹理
        const texture = new THREE.CanvasTexture(canvas)
        texture.flipY = false
        texture.wrapS = THREE.ClampToEdgeWrapping
        texture.wrapT = THREE.ClampToEdgeWrapping
        
        // 创建地图几何体
        const geometry = new THREE.PlaneGeometry(
          width * mapConfig.resolution,
          height * mapConfig.resolution
        )
        
        const material = new THREE.MeshBasicMaterial({
          map: texture,
          transparent: true,
          opacity: 0.8,
          side: THREE.DoubleSide
        })
        
        const mapMesh = new THREE.Mesh(geometry, material)
        
        // 计算地图在世界坐标系中的真实尺寸
        const mapWidthMeters = width * mapConfig.resolution
        const mapHeightMeters = height * mapConfig.resolution
        
        console.log(`[Scene3D] 地图物理尺寸: ${mapWidthMeters.toFixed(2)}m x ${mapHeightMeters.toFixed(2)}m`)
        
        // 设置地图位置 - 确保在XY平面正确放置
        // YAML配置中的origin是地图左下角的位置
        const mapX = mapConfig.origin[0] + mapWidthMeters / 2   // 地图中心X
        const mapY = mapConfig.origin[1] + mapHeightMeters / 2  // 地图中心Y
        const mapZ = 0.01  // 稍微抬升避免与网格重叠
        
        mapMesh.position.set(mapX, mapY, mapZ)
        
        // 确保地图正确朝向（地图应该水平放置在XY平面）
        mapMesh.rotation.x = -Math.PI / 2  // 绕X轴旋转90度，使地图平躺在XY平面
        mapMesh.rotation.y = 0
        mapMesh.rotation.z = 0
        
        // 设置用户数据
        mapMesh.userData = {
          topic: 'loaded_map',
          messageType: 'loaded_map',
          filename: filename,
          config: mapConfig,
          dimensions: { width, height },
          physicalSize: { width: mapWidthMeters, height: mapHeightMeters },
          worldPosition: { x: mapX, y: mapY, z: mapZ }
        }
        
        // 添加到场景
        scene.add(mapMesh)
        visualizationObjects.set('loaded_map', mapMesh)
        
        // 自动调整相机以查看地图
        fitCameraToMap(mapMesh)
        
        console.log(`[Scene3D] ✅ 地图加载成功:`)
        console.log(`[Scene3D] - 像素尺寸: ${width}x${height}`)
        console.log(`[Scene3D] - 物理尺寸: ${mapWidthMeters.toFixed(2)}m x ${mapHeightMeters.toFixed(2)}m`)
        console.log(`[Scene3D] - 分辨率: ${mapConfig.resolution}m/pixel`)
        console.log(`[Scene3D] - 世界位置: (${mapX.toFixed(2)}, ${mapY.toFixed(2)}, ${mapZ.toFixed(2)})`)
        console.log(`[Scene3D] - 原点配置: [${mapConfig.origin.join(', ')}]`)
        
        // 显示成功消息
        ElMessage.success(`地图加载成功！尺寸: ${mapWidthMeters.toFixed(1)}m×${mapHeightMeters.toFixed(1)}m`)
        
      } catch (error) {
        console.error('[Scene3D] 创建地图可视化失败:', error)
        throw error
      }
    }

    const fitCameraToMap = (mapMesh) => {
      if (!camera || !controls || !mapMesh) return
      
      try {
        const box = new THREE.Box3().setFromObject(mapMesh)
        const center = box.getCenter(new THREE.Vector3())
        const size = box.getSize(new THREE.Vector3())
        
        console.log(`[Scene3D] 地图边界框:`, {
          center: { x: center.x.toFixed(2), y: center.y.toFixed(2), z: center.z.toFixed(2) },
          size: { x: size.x.toFixed(2), y: size.y.toFixed(2), z: size.z.toFixed(2) }
        })
        
        // 对于XY平面上的地图，计算合适的俯视距离
        const maxDim = Math.max(size.x, size.y)
        const distance = maxDim * 1.2  // 适当的观察距离
        
        // 从正上方俯视地图（适合XY平面地图）
        const cameraX = center.x
        const cameraY = center.y
        const cameraZ = Math.max(distance, 10)  // 确保有足够的高度
        
        // 设置相机位置
        camera.position.set(cameraX, cameraY, cameraZ)
        
        // 设置相机目标为地图中心
        const targetPoint = new THREE.Vector3(center.x, center.y, 0.01)  // 地图表面
        camera.lookAt(targetPoint)
        
        if (controls) {
          controls.target.copy(targetPoint)
          controls.update()
        }
        
        console.log(`[Scene3D] ✅ 相机已适配到地图:`)
        console.log(`[Scene3D] - 相机位置: (${cameraX.toFixed(2)}, ${cameraY.toFixed(2)}, ${cameraZ.toFixed(2)})`)
        console.log(`[Scene3D] - 观察目标: (${targetPoint.x.toFixed(2)}, ${targetPoint.y.toFixed(2)}, ${targetPoint.z.toFixed(2)})`)
        console.log(`[Scene3D] - 观察距离: ${cameraZ.toFixed(2)}m`)
        console.log(`[Scene3D] - 地图尺寸: ${maxDim.toFixed(2)}m`)
        
      } catch (error) {
        console.error('[Scene3D] 相机适配到地图失败:', error)
      }
    }

    const fitCameraToPointCloud = (pointCloud) => {
      if (!camera || !controls || !pointCloud.geometry) return
      
      try {
        // 确保边界框已计算
        pointCloud.geometry.computeBoundingBox()
        const box = pointCloud.geometry.boundingBox
        
        if (!box) return
        
        // 计算点云的中心和大小
        const center = new THREE.Vector3()
        box.getCenter(center)
        
        const size = new THREE.Vector3()
        box.getSize(size)
        const maxDim = Math.max(size.x, size.y, size.z)
        
        // 计算相机距离（确保能看到整个点云）
        const distance = maxDim * 2
        
        // 设置相机位置（从斜上方观察）
        const cameraPosition = new THREE.Vector3(
          center.x + distance * 0.5,
          center.y + distance * 0.5, 
          center.z + distance * 0.7
        )
        
        camera.position.copy(cameraPosition)
        camera.lookAt(center)
        
        if (controls) {
          controls.target.copy(center)
          controls.update()
        }
        
        console.log(`相机已调整以查看点云 - 中心: (${center.x.toFixed(2)}, ${center.y.toFixed(2)}, ${center.z.toFixed(2)}), 距离: ${distance.toFixed(2)}`)
        
      } catch (error) {
        console.error('调整相机视角失败:', error)
      }
    }

    const addDebugInfo = () => {
      if (!scene) return
      
      // 收集详细的调试信息
      const debugInfo = {
        timestamp: new Date().toISOString(),
        scene: {
          objects: visualizationObjects.size,
          subscriptions: rosSubscriptions.size,
          sceneChildren: scene.children.length,
          camera: camera ? {
            position: {
              x: camera.position.x.toFixed(2),
              y: camera.position.y.toFixed(2),
              z: camera.position.z.toFixed(2)
            },
            target: controls ? {
              x: controls.target.x.toFixed(2),
              y: controls.target.y.toFixed(2),
              z: controls.target.z.toFixed(2)
            } : null
          } : null
        },
        rosbridge: {
          connected: rosbridge?.isConnected ?? false,
          subscriptionCount: rosSubscriptions.size
        },
        performance: {
          fps: performanceStats.value.fps,
          objects: performanceStats.value.objects,
          vertices: performanceStats.value.vertices
        }
      }
      
      console.log('=== 🔍 3D场景详细调试信息 ===')
      console.log('时间戳:', debugInfo.timestamp)
      console.log('--- 场景状态 ---')
      console.log('可视化对象数量:', debugInfo.scene.objects)
      console.log('ROS订阅数量:', debugInfo.scene.subscriptions)
      console.log('Three.js场景子对象数量:', debugInfo.scene.sceneChildren)
      console.log('--- 相机信息 ---')
      console.log('相机位置:', debugInfo.scene.camera?.position)
      console.log('相机目标:', debugInfo.scene.camera?.target)
      console.log('--- ROS连接 ---')
      console.log('ROSBridge连接状态:', debugInfo.rosbridge.connected)
      console.log('--- 性能统计 ---')
      console.log('FPS:', debugInfo.performance.fps)
      console.log('渲染对象数:', debugInfo.performance.objects)
      console.log('顶点数:', debugInfo.performance.vertices)
      
      console.log('--- 可视化对象详情 ---')
      if (visualizationObjects.size === 0) {
        console.log('⚠️ 没有可视化对象')
      } else {
        visualizationObjects.forEach((obj, topic) => {
          console.log(`📊 ${topic}:`, {
            类型: obj.userData?.messageType,
            点数: obj.userData?.pointCount,
            可见: obj.visible,
            位置: `(${obj.position.x.toFixed(2)}, ${obj.position.y.toFixed(2)}, ${obj.position.z.toFixed(2)})`,
            缩放: `(${obj.scale.x.toFixed(2)}, ${obj.scale.y.toFixed(2)}, ${obj.scale.z.toFixed(2)})`,
            用户数据: obj.userData
          })
        })
      }
      
      console.log('--- ROS订阅详情 ---')
      if (rosSubscriptions.size === 0) {
        console.log('⚠️ 没有ROS订阅')
      } else {
        rosSubscriptions.forEach((subscription, topic) => {
          console.log(`📡 ${topic}:`, {
            订阅对象: subscription,
            订阅时间: subscription?.timestamp ? new Date(subscription.timestamp).toLocaleString() : '未知'
          })
        })
      }
      
      console.log('--- Three.js场景对象 ---')
      scene.children.forEach((child, index) => {
        console.log(`🎭 场景对象 ${index}:`, {
          类型: child.type,
          名称: child.name || '未命名',
          可见: child.visible,
          位置: `(${child.position.x.toFixed(2)}, ${child.position.y.toFixed(2)}, ${child.position.z.toFixed(2)})`,
          用户数据: child.userData
        })
      })
      
      console.log('=== 🔍 调试信息结束 ===')
      
      // 显示简化的用户消息
      ElMessage.info(`调试信息已输出到控制台 - 对象:${debugInfo.scene.objects} 订阅:${debugInfo.scene.subscriptions} FPS:${debugInfo.performance.fps}`)
      
      return debugInfo
    }

    const checkSubscriptionStatus = () => {
      console.log('=== 🔍 ROS订阅状态检查 ===')
      
      const now = Date.now()
      let activeSubscriptions = 0
      let inactiveSubscriptions = 0
      let totalMessages = 0
      
      if (rosSubscriptions.size === 0) {
        console.log('⚠️ 没有任何ROS订阅')
        ElMessage.warning('没有任何ROS订阅')
        return
      }
      
      rosSubscriptions.forEach((subscription, topic) => {
        const timeSinceSubscribe = now - (subscription.subscribeTime || 0)
        const timeSinceLastMessage = subscription.lastMessageTime > 0 ? now - subscription.lastMessageTime : -1
        const messageCount = subscription.messageCount || 0
        
        console.log(`📡 ${topic}:`)
        console.log(`  - 订阅时长: ${(timeSinceSubscribe / 1000).toFixed(1)}秒`)
        console.log(`  - 消息数量: ${messageCount}`)
        console.log(`  - 最后消息: ${timeSinceLastMessage > 0 ? (timeSinceLastMessage / 1000).toFixed(1) + '秒前' : '从未收到'}`)
        
        if (messageCount > 0) {
          const avgFreq = messageCount / (timeSinceSubscribe / 1000)
          console.log(`  - 平均频率: ${avgFreq.toFixed(2)} Hz`)
          activeSubscriptions++
        } else {
          console.log(`  - ⚠️ 此主题没有收到任何数据`)
          inactiveSubscriptions++
        }
        
        totalMessages += messageCount
      })
      
      console.log('=== 📊 订阅统计 ===')
      console.log(`总订阅数: ${rosSubscriptions.size}`)
      console.log(`活跃订阅: ${activeSubscriptions}`)
      console.log(`无数据订阅: ${inactiveSubscriptions}`)
      console.log(`总消息数: ${totalMessages}`)
      
      // 用户反馈
      if (inactiveSubscriptions > 0) {
        ElMessage.warning(`有 ${inactiveSubscriptions} 个主题没有数据，请检查ROS系统是否正在发布这些主题`)
      } else if (activeSubscriptions > 0) {
        ElMessage.success(`所有 ${activeSubscriptions} 个订阅都在正常接收数据`)
      }
    }
    
    return {
      containerRef,
      loading,
      mapMesh,
      mapTexture,
      onMouseDown,
      // 暴露给父组件的方法
      resetCamera,
      setGridVisible,
      setAxesVisible,
      setBackgroundColor,
      updateRenderSettings,
      togglePlugin,
      configurePlugin,
      // ROS集成方法
      subscribeToRosTopic,
      unsubscribeFromRosTopic,
      updateVisualization,
      removeVisualization,
      getPerformanceStats,
      // 新增控制方法
      setLaserType,
      updateSettings,
      setViewPreset,
      loadMapFile,
      fitCameraToPointCloud,
      fitCameraToMap,
      addDebugInfo,
      checkSubscriptionStatus
    }
  }
}
</script>

<style scoped>
.scene3d-container {
  width: 100%;
  height: 100%;
  position: relative;
  overflow: hidden;
  background: #000;
  outline: none;
}

.scene3d-container:focus {
  box-shadow: inset 0 0 0 2px rgba(0, 212, 255, 0.5);
}

.loading-overlay {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 15px;
  color: white;
  font-size: 14px;
  z-index: 1000;
}

.loading-spinner {
  display: flex;
  justify-content: center;
  align-items: center;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid rgba(255, 255, 255, 0.3);
  border-top: 3px solid #409eff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.debug-hint {
  position: absolute;
  bottom: 10px;
  right: 10px;
  z-index: 100;
  opacity: 0.7;
  transition: opacity 0.3s;
}

.debug-hint:hover {
  opacity: 1;
}

.hint-content {
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(5px);
  color: rgba(255, 255, 255, 0.8);
  padding: 6px 10px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 11px;
  border: 1px solid rgba(0, 212, 255, 0.3);
}
</style>
