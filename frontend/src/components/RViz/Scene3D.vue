<template>
  <div
    ref="containerRef"
    class="scene3d-container"
    tabindex="0"
    @mousedown="onMouseDown"
    @mousemove="onMouseMove"
    @mouseup="onMouseUp"
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
        <small>快捷键: D-调试 | R-重置 | F-适配点云 | G-网格 | M-适配地图 | C-检查订阅 | X-清除全部 | Z-取消订阅</small>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import * as THREE from 'three'
import { ElMessage } from 'element-plus'
import { useRosbridge } from '../../composables/useRosbridge'
import { useConnectionStore } from '../../composables/useConnectionStore'

export default {
  name: 'Scene3D',
  emits: ['object-selected', 'camera-moved'],
  setup(props, { emit }) {
    const rosbridge = useRosbridge()
    const connectionStore = useConnectionStore()
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

    // 持久化设置存储
    const persistentSettings = {
      laser: {
        showLaserPoints: true,
        showLaserLines: true,
        showIntensity: false,
        pointSize: 0.15
      },
      pointcloud: {
        pointSize: 0.05,
        opacity: 0.8,
        showIntensity: false
      },
      map: {
        showMap: true,
        opacity: 0.8,
        showGrid: false,
        showOrigin: true
      },
      position: {
        showTrajectory: true,
        trajectoryLength: 20
      }
    }

    // 地图相关对象
    const mapMesh = ref(null)
    const mapTexture = ref(null)

    // 轨迹记录（用于里程计）
    let trajectoryPoints = []

    // 导航工具状态
    let currentNavigationTool = 'none'
    let isDragging = false
    let dragStartPosition = null
    let dragCurrentPosition = null
    let previewArrow = null

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
        
        // 创建相机 - 设置为俯视XY平面的视角
        const aspect = containerRef.value.clientWidth / containerRef.value.clientHeight
        camera = new THREE.PerspectiveCamera(75, aspect, 0.1, 1000)
        // 默认相机位置，与RViz类似的斜视角
        camera.position.set(10, -10, 10)  // 从右后上方看向原点
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
        
        // 创建网格 - 在XY平面上，Z=0，与RViz一致
        // Three.js的GridHelper默认在XZ平面，需要旋转到XY平面
        gridHelper = new THREE.GridHelper(20, 20, 0x888888, 0x444444)
        gridHelper.position.set(0, 0, 0)  // 网格中心在原点
        gridHelper.rotateX(-Math.PI / 2)  // 旋转90度使网格在XY平面
        scene.add(gridHelper)

        // 创建坐标轴 - 与RViz约定一致：X右(红)，Y前(绿)，Z上(蓝)
        // Three.js默认坐标系：X右，Y上，Z前
        // RViz标准坐标系：X前，Y左，Z上
        // 为了与RViz显示一致，我们不旋转坐标轴，直接使用Three.js的默认方向
        axesHelper = new THREE.AxesHelper(2)
        axesHelper.position.set(0, 0, 0)
        scene.add(axesHelper)

        // 添加坐标系标签
        createCoordinateSystemLabels()

        // 创建机器人模型
        createRobotModel()

        // 订阅位置主题以更新机器人模型
        subscribeToPositionTopics()

        // 窗口大小调整监听
        window.addEventListener('resize', onWindowResize)
        
        // 添加调试快捷键
        window.addEventListener('keydown', onKeyDown)
        
        // 开始渲染循环
        animate()
        
        loading.value = false
        console.log('3D Scene initialized successfully')
        console.log('坐标系设置：')
        console.log('- X轴：向前（红色）')
        console.log('- Y轴：向左（绿色）')
        console.log('- Z轴：向上（蓝色）')
        console.log('机器人模型已创建，等待里程计数据...')
        
      } catch (error) {
        console.error('Failed to initialize 3D scene:', error)
        loading.value = false
      }
    }
    
    /**
     * 创建坐标系标签
     */
    const createCoordinateSystemLabels = () => {
      try {
        // 为每个标签创建独立的canvas
        const createLabelSprite = (text, color, position) => {
          const canvas = document.createElement('canvas')
          const context = canvas.getContext('2d')
          canvas.width = 64
          canvas.height = 64

          context.clearRect(0, 0, 64, 64)
          context.fillStyle = color
          context.font = 'Bold 24px Arial'
          context.textAlign = 'center'
          context.fillText(text, 32, 40)

          const texture = new THREE.CanvasTexture(canvas)
          const material = new THREE.SpriteMaterial({ map: texture })
          const sprite = new THREE.Sprite(material)
          sprite.position.copy(position)
          sprite.scale.set(0.5, 0.5, 1)
          return sprite
        }

        // X轴标签 (红色) - 水平方向
        const xSprite = createLabelSprite('X', '#FF0000', new THREE.Vector3(2.5, 0, 0))
        scene.add(xSprite)

        // Y轴标签 (绿色) - 向上方向
        const ySprite = createLabelSprite('Y', '#00FF00', new THREE.Vector3(0, 2.5, 0))
        scene.add(ySprite)

        // Z轴标签 (蓝色) - 深度方向
        const zSprite = createLabelSprite('Z', '#0000FF', new THREE.Vector3(0, 0, 2.5))
        scene.add(zSprite)

        console.log('坐标系标签已创建')
        console.log('- X轴 (红色): 水平向右')
        console.log('- Y轴 (绿色): 垂直向上')
        console.log('- Z轴 (蓝色): 深度向前')
      } catch (error) {
        console.warn('创建坐标系标签失败:', error)
      }
    }

    /**
     * 创建机器人模型
     */
    let robotModel = null
    const createRobotModel = () => {
      try {
        // 创建机器人组合体
        robotModel = new THREE.Group()

        // 机器人底盘 (长方体)
        const chassisGeometry = new THREE.BoxGeometry(1.0, 0.6, 0.3)
        const chassisMaterial = new THREE.MeshLambertMaterial({ color: 0x4CAF50 })
        const chassis = new THREE.Mesh(chassisGeometry, chassisMaterial)
        chassis.position.set(0, 0, 0.15)
        robotModel.add(chassis)

        // 机器人头部/传感器 (圆柱体)
        const headGeometry = new THREE.CylinderGeometry(0.15, 0.15, 0.2)
        const headMaterial = new THREE.MeshLambertMaterial({ color: 0x2196F3 })
        const head = new THREE.Mesh(headGeometry, headMaterial)
        head.position.set(0.3, 0, 0.4)
        robotModel.add(head)

        // 方向指示箭头
        const arrowGeometry = new THREE.ConeGeometry(0.1, 0.3)
        const arrowMaterial = new THREE.MeshLambertMaterial({ color: 0xFF5722 })
        const arrow = new THREE.Mesh(arrowGeometry, arrowMaterial)
        arrow.position.set(0.6, 0, 0.15)
        arrow.rotation.z = -Math.PI / 2
        robotModel.add(arrow)

        // 轮子 (4个圆柱体)
        const wheelGeometry = new THREE.CylinderGeometry(0.15, 0.15, 0.1)
        const wheelMaterial = new THREE.MeshLambertMaterial({ color: 0x424242 })

        const wheelPositions = [
          { x: 0.35, y: 0.35, z: 0.15 },
          { x: 0.35, y: -0.35, z: 0.15 },
          { x: -0.35, y: 0.35, z: 0.15 },
          { x: -0.35, y: -0.35, z: 0.15 }
        ]

        wheelPositions.forEach(pos => {
          const wheel = new THREE.Mesh(wheelGeometry, wheelMaterial)
          wheel.position.set(pos.x, pos.y, pos.z)
          wheel.rotation.x = Math.PI / 2
          robotModel.add(wheel)
        })

        // 机器人坐标轴 (小一点的轴)
        const robotAxes = new THREE.AxesHelper(0.5)
        robotAxes.position.set(0, 0, 0.3)
        robotModel.add(robotAxes)

        // 初始位置
        robotModel.position.set(0, 0, 0)
        robotModel.userData = {
          type: 'robot',
          lastUpdate: Date.now()
        }

        scene.add(robotModel)
        console.log('机器人模型已创建')

      } catch (error) {
        console.warn('创建机器人模型失败:', error)
      }
    }

    /**
     * 更新机器人位置
     */
    const updateRobotPosition = (position, orientation = null) => {
      if (!robotModel) return

      try {
        // 更新位置 - 确保使用正确的坐标映射，支持下划线前缀
        // X: 水平 (前后), Y: 水平 (左右), Z: 高度
        const x = position.x || position._x || 0
        const y = position.y || position._y || 0
        const z = position.z || position._z || 0

        robotModel.position.set(x, y, z + 0.15)  // 稍微抬高避免与地面重合

        // 更新方向，支持下划线前缀
        if (orientation) {
          robotModel.quaternion.set(
            orientation.x || orientation._x || 0,
            orientation.y || orientation._y || 0,
            orientation.z || orientation._z || 0,
            orientation.w || orientation._w || 1
          )
        }

        robotModel.userData.lastUpdate = Date.now()
        // console.log(`[updateRobotPosition] 机器人位置更新: (${x.toFixed(2)}, ${y.toFixed(2)}, ${z.toFixed(2)})`)

        // 创建轨迹点（基于机器人位置更新）
        if (persistentSettings.position.showTrajectory) {
          const currentPos = new THREE.Vector3(x, y, z)

          // 只在位置变化超过阈值时添加轨迹点
          if (trajectoryPoints.length === 0 ||
              trajectoryPoints[trajectoryPoints.length - 1].distanceTo(currentPos) > 0.1) {
            trajectoryPoints.push(currentPos.clone())
            // console.log(`[Trajectory-Robot] 添加轨迹点 #${trajectoryPoints.length}: (${x.toFixed(2)}, ${y.toFixed(2)}, ${z.toFixed(2)})`)

            // 限制轨迹点数量（由控制面板传入，范围10~100）
            const maxLen = Math.max(10, Math.min(100, persistentSettings.position.trajectoryLength || 100))
            if (trajectoryPoints.length > maxLen) {
              trajectoryPoints.shift()
              // console.log(`[Trajectory-Robot] 轨迹点数量达到上限，移除最早的点`)
            }

            // 创建或更新轨迹线
            if (trajectoryPoints.length > 1) {
              // 清除之前的独立轨迹线
              const existingTrajectory = scene.children.find(child => child.userData?.type === 'global_trajectory')
              if (existingTrajectory) {
                scene.remove(existingTrajectory)
                existingTrajectory.geometry?.dispose()
                existingTrajectory.material?.dispose()
              }

              // 创建新的全局轨迹线
              const globalTrajectoryGeometry = new THREE.BufferGeometry().setFromPoints(trajectoryPoints)
              const globalTrajectoryMaterial = new THREE.LineBasicMaterial({
                color: 0xff0000,  // 红色全局轨迹
                transparent: false,
                linewidth: 6
              })
              const globalTrajectoryLine = new THREE.Line(globalTrajectoryGeometry, globalTrajectoryMaterial)
              globalTrajectoryLine.userData = { type: 'global_trajectory' }
              globalTrajectoryLine.visible = true

              scene.add(globalTrajectoryLine)
              // console.log(`[Trajectory-Robot] 创建全局轨迹线，点数: ${trajectoryPoints.length}`)
            }
          }
        }

      } catch (error) {
        console.warn('更新机器人位置失败:', error)
      }
    }

    /**
     * 订阅位置主题更新机器人位置 (与位置信息面板保持一致)
     */
    const subscribeToPositionTopics = () => {
      console.log('[Scene3D] 开始订阅位置主题以更新机器人模型...')

      // 与位置信息面板完全相同的主题列表
      const positionTopics = [
        { topic: '/odom', type: 'nav_msgs/msg/Odometry' },
        { topic: '/robot_pose', type: 'geometry_msgs/msg/PoseStamped' },
        { topic: '/amcl_pose', type: 'geometry_msgs/msg/PoseWithCovarianceStamped' },
        { topic: '/pose', type: 'geometry_msgs/msg/PoseStamped' },
        { topic: '/localization', type: 'nav_msgs/msg/Odometry' },
        { topic: '/localization_2d', type: 'nav_msgs/msg/Odometry' }
      ]

      positionTopics.forEach(({ topic, type }) => {
        console.log(`[Scene3D] 尝试订阅位置主题: ${topic} (${type})`)

        try {
          rosbridge.subscribe(topic, type, (message) => {
            // console.log(`[Scene3D] 收到${topic}位置数据，更新机器人模型`)

            let position = null
            let orientation = null

            // 根据消息类型解析位置信息 (兼容下划线前缀格式)
            if (type === 'nav_msgs/msg/Odometry') {
              const pose = message.pose || message._pose
              if (pose && (pose.pose || pose._pose)) {
                const poseData = pose.pose || pose._pose || pose
                position = poseData.position || poseData._position
                orientation = poseData.orientation || poseData._orientation
              }
            } else if (type === 'geometry_msgs/msg/PoseStamped') {
              const poseMsg = message.pose || message._pose
              if (poseMsg) {
                position = poseMsg.position || poseMsg._position
                orientation = poseMsg.orientation || poseMsg._orientation
              }
            } else if (type === 'geometry_msgs/msg/PoseWithCovarianceStamped') {
              const pose = message.pose || message._pose
              if (pose && (pose.pose || pose._pose)) {
                const poseData = pose.pose || pose._pose || pose
                position = poseData.position || poseData._position
                orientation = poseData.orientation || poseData._orientation
              }
            }

            // 使用updateRobotPosition函数更新机器人位置
            if (position) {
              updateRobotPosition(position, orientation)
              // 减少频繁的位置更新日志
              // console.debug(`[Scene3D] 机器人位置已更新: (${position.x?.toFixed(3)}, ${position.y?.toFixed(3)}, ${position.z?.toFixed(3)})`)
            } else {
              console.warn(`[Scene3D] 无法从${topic}解析位置信息`, message)
            }
          })

          console.log(`[Scene3D] ✅ 成功订阅位置主题: ${topic}`)
        } catch (error) {
          console.error(`[Scene3D] 订阅${topic}失败:`, error)
        }
      })
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

        // 检查是否使用导航工具
        if (currentNavigationTool !== 'none') {
          // 与地面相交检测（假设地面在z=0平面）
          const groundPlane = new THREE.Plane(new THREE.Vector3(0, 0, 1), 0)
          const intersection = new THREE.Vector3()
          if (raycaster.ray.intersectPlane(groundPlane, intersection)) {
            // 开始拖拽以设置方向
            isDragging = true
            dragStartPosition = intersection.clone()
            dragCurrentPosition = intersection.clone()
            event.preventDefault()
          }
          return
        }

        // 正常的对象选择检测
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
     * 鼠标移动事件
     */
    const onMouseMove = (event) => {
      if (isDragging && currentNavigationTool !== 'none') {
        event.preventDefault()

        const raycaster = new THREE.Raycaster()
        const mouse = new THREE.Vector2()

        const rect = containerRef.value.getBoundingClientRect()
        mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
        mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1

        raycaster.setFromCamera(mouse, camera)

        const groundPlane = new THREE.Plane(new THREE.Vector3(0, 0, 1), 0)
        const intersection = new THREE.Vector3()
        if (raycaster.ray.intersectPlane(groundPlane, intersection)) {
          dragCurrentPosition = intersection.clone()

          // 计算方向并更新预览箭头
          if (dragStartPosition) {
            const direction = new THREE.Vector2(
              dragCurrentPosition.x - dragStartPosition.x,
              dragCurrentPosition.y - dragStartPosition.y
            )

            // 只有在拖拽了足够距离时才显示箭头
            if (direction.length() > 0.1) {
              if (!previewArrow) {
                createPreviewArrow(dragStartPosition, direction)
              } else {
                updatePreviewArrow(dragStartPosition, direction)
              }
            }
          }
        }
      }
    }

    /**
     * 鼠标释放事件
     */
    const onMouseUp = (event) => {
      if (isDragging && currentNavigationTool !== 'none') {
        isDragging = false

        // 清除预览箭头
        clearPreviewArrow()

        if (dragStartPosition && dragCurrentPosition) {
          // 计算方向
          const direction = new THREE.Vector2(
            dragCurrentPosition.x - dragStartPosition.x,
            dragCurrentPosition.y - dragStartPosition.y
          )

          // 只有在拖拽了足够距离时才发布消息
          if (direction.length() > 0.1) {
            // 计算角度（从拖拽方向）
            const yaw = Math.atan2(direction.y, direction.x)

            // 创建四元数
            const orientation = new THREE.Quaternion()
            orientation.setFromAxisAngle(new THREE.Vector3(0, 0, 1), yaw)

            // 发布导航消息
            handleNavigationToolClick(dragStartPosition, {
              x: orientation.x,
              y: orientation.y,
              z: orientation.z,
              w: orientation.w
            })
          } else {
            // 如果拖拽距离太短，使用默认方向
            handleNavigationToolClick(dragStartPosition, { x: 0, y: 0, z: 0, w: 1 })
          }
        }

        dragStartPosition = null
        dragCurrentPosition = null
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
          case 'x':
            // X键：清除所有可视化对象
            clearAllVisualizations()
            break
          case 'z':
            // Z键：取消所有订阅
            unsubscribeAllTopics()
            break
        }
      }
    }
    
    // 公共方法
    const resetCamera = () => {
      if (camera && controls) {
        // 重置为斜上方视角，与RViz类似
        camera.position.set(10, -10, 10)
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
      // console.log(`[Scene3D] 订阅ROS主题: ${topicName}, 类型: ${messageType}`)
      
        // 先清理所有相关的订阅和可视化对象（实现真正的单一主题订阅）
      // console.log(`[Scene3D] 准备订阅新主题: ${topicName}, 当前订阅数: ${rosSubscriptions.size}`)

      // 清理所有旧的订阅和可视化对象
      if (rosSubscriptions.size > 0) {
        // console.log(`[Scene3D] 清理所有旧订阅...`)
        const oldTopics = Array.from(rosSubscriptions.keys())
        oldTopics.forEach(oldTopicName => {
          // console.log(`[Scene3D] 取消订阅: ${oldTopicName}`)
          unsubscribeFromRosTopic(oldTopicName)
        })
      }

      // 清理所有可视化对象
      clearAllVisualizations()
      
      try {
        // 使用rosbridge订阅主题
        // console.log(`[Scene3D] 调用rosbridge.subscribe...`)
        
        const subscription = rosbridge.subscribe(topicName, messageType, (message) => {
          const now = Date.now()
          const subInfo = rosSubscriptions.get(topicName)

          /*
          console.log(`[Scene3D] 📨 收到主题消息: ${topicName}`, {
            messageType: typeof message,
            hasRanges: message?.ranges?.length,
            hasData: message?.data?.length,
            hasPoints: message?.points?.length,
            messageKeys: message ? Object.keys(message) : []
          })
          */

          if (subInfo) {
            subInfo.messageCount = (subInfo.messageCount || 0) + 1
            subInfo.lastMessageTime = now

            // console.log(`[Scene3D] 🎉 收到主题 ${topicName} 的第${subInfo.messageCount}条消息`)

            // 确保消息不为空
            if (message) {
              updateVisualization(topicName, messageType, message)
            } else {
              console.warn(`[Scene3D] 收到空消息: ${topicName}`)
            }
          } else {
            console.warn(`[Scene3D] 收到消息但订阅信息不存在: ${topicName}`)
          }
        })
        
        // console.log(`[Scene3D] rosbridge.subscribe返回:`, subscription)
        
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
          // console.log(`[Scene3D] ✅ 成功订阅主题: ${topicName}, 当前订阅数: ${rosSubscriptions.size}`)
          
          // 设置定时检查，确认是否收到数据
          setTimeout(() => {
            const sub = rosSubscriptions.get(topicName)
            if (sub && sub.messageCount === 0) {
              console.warn(`[Scene3D] ⚠️ 主题 ${topicName} 在 5 秒内没有收到任何消息`)
              ElMessage.warning(`主题 ${topicName} 可能没有数据发布，请检查ROS系统`)
            } else if (sub) {
              // console.log(`[Scene3D] ✅ 主题 ${topicName} 正常，已收到 ${sub.messageCount} 条消息`)
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
          // console.log(`[Scene3D] 取消订阅主题: ${topicName}`)
          rosbridge.unsubscribe(subscription)
          rosSubscriptions.delete(topicName)
          removeVisualization(topicName)
          // console.log(`[Scene3D] 已成功取消订阅主题: ${topicName}`)
        } catch (error) {
          console.error(`[Scene3D] 取消订阅主题 ${topicName} 失败:`, error)
        }
      } else {
        console.warn(`[Scene3D] 试图取消不存在的订阅: ${topicName}`)
        // 仍然尝试清除可视化对象
        removeVisualization(topicName)
      }
    }

    // 取消所有订阅
    const unsubscribeAllTopics = () => {
      // console.log(`[Scene3D] 取消所有订阅, 当前订阅数: ${rosSubscriptions.size}`)

      rosSubscriptions.forEach((subscription, topicName) => {
        unsubscribeFromRosTopic(topicName)
      })

      clearAllVisualizations()
    }
    
    // 添加更新频率控制
    let lastLogTime = 0
    let messageCount = 0

    const updateVisualization = (topic, messageType, message) => {
      messageCount++
      const now = Date.now()

      // 只每5秒记录一次日志，避免刷屏
      if (now - lastLogTime > 5000) {
        console.debug(`[Scene3D] 📡 处理可视化更新 - 主题: ${topic}, 消息类型: ${messageType}, 最近5秒处理了${messageCount}条消息`)
        lastLogTime = now
        messageCount = 0
      }

      // 记录处理前的状态
      const beforeCount = visualizationObjects.size
      
      try {
        // 根据消息类型更新可视化
        switch (messageType) {
          case 'sensor_msgs/msg/PointCloud2':
          case 'sensor_msgs/PointCloud2':
            console.debug(`[Scene3D] 🔄 处理点云消息...`)
            updatePointCloud(topic, message)
            break
          case 'sensor_msgs/msg/LaserScan':
          case 'sensor_msgs/LaserScan':
            console.debug(`[Scene3D] 🔄 处理激光雷达消息...`)
            updateLaserScan(topic, message)
            break
          case 'visualization_msgs/msg/Marker':
          case 'visualization_msgs/Marker':
            console.debug(`[Scene3D] 🔄 处理标记消息...`)
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
          case 'nav_msgs/msg/Odometry':
          case 'nav_msgs/Odometry':
            console.log(`[Scene3D] 🔄 准备处理里程计消息，主题: ${topic}`)
            console.log(`[Scene3D] 🔄 里程计消息内容预览:`, {
              topic,
              hasMessage: !!message,
              hasHeader: !!message?.header,
              hasPose: !!message?.pose,
              hasPosePose: !!message?.pose?.pose,
              hasPosition: !!message?.pose?.pose?.position
            })
            updateOdometry(topic, message)
            break
          case 'geometry_msgs/msg/PoseStamped':
          case 'geometry_msgs/PoseStamped':
            console.log(`[Scene3D] 🔄 处理位置消息...`)
            updatePoseStamped(topic, message)
            break
          case 'geometry_msgs/msg/PoseWithCovarianceStamped':
          case 'geometry_msgs/PoseWithCovarianceStamped':
            console.log(`[Scene3D] 🔄 处理带协方差位置消息...`)
            updatePoseWithCovarianceStamped(topic, message)
            break
          default:
            console.warn(`[Scene3D] ⚠️ 不支持的消息类型: ${messageType}`)
            return
        }
        
        // 只在首次或调试时记录详细信息
        const afterCount = visualizationObjects.size
        if (afterCount > beforeCount && now - lastLogTime <= 1000) {
          console.log(`[Scene3D] ✅ 成功创建可视化对象，新增 ${afterCount - beforeCount} 个对象`)
        }
        
      } catch (error) {
        console.error(`[Scene3D] ❌ 处理可视化消息时发生错误:`, error)
      }
    }
    
    const removeVisualization = (topic) => {
      const object = visualizationObjects.get(topic)
      if (object) {
        // console.log(`[Scene3D] 清除可视化对象: ${topic}`)

        // 递归清理对象和其子对象
        const cleanupObject = (obj) => {
          if (obj.geometry) {
            obj.geometry.dispose()
          }
          if (obj.material) {
            if (Array.isArray(obj.material)) {
              obj.material.forEach(mat => mat.dispose())
            } else {
              obj.material.dispose()
            }
          }
          if (obj.children) {
            obj.children.forEach(child => cleanupObject(child))
          }
        }

        cleanupObject(object)
        scene.remove(object)
        visualizationObjects.delete(topic)

        // console.log(`[Scene3D] 已清除可视化对象: ${topic}, 剩余对象数: ${visualizationObjects.size}`)
      }

      // 同时检查并清除关联的激光连线对象
      const linesObject = visualizationObjects.get(topic + '_lines')
      if (linesObject) {
        // console.log(`[Scene3D] 清除激光连线对象: ${topic}_lines`)
        const cleanupObject = (obj) => {
          if (obj.geometry) {
            obj.geometry.dispose()
          }
          if (obj.material) {
            if (Array.isArray(obj.material)) {
              obj.material.forEach(mat => mat.dispose())
            } else {
              obj.material.dispose()
            }
          }
        }
        cleanupObject(linesObject)
        scene.remove(linesObject)
        visualizationObjects.delete(topic + '_lines')
      }
    }

    // 清除所有可视化对象（但保留地图）
    const clearAllVisualizations = () => {
      // console.log(`[Scene3D] 清除所有可视化对象, 当前数量: ${visualizationObjects.size}`)

      // 需要保留的主题类型（地图相关）
      const preservedTopics = new Set()

      visualizationObjects.forEach((object, topic) => {
        // 检查是否是需要保留的主题类型
        const subscription = rosSubscriptions.get(topic)
        const messageType = subscription?.messageType || ''

        // 只保留PGM加载的地图，不保留主题订阅的地图
        if (topic === 'loaded_map') {
          // console.log(`[Scene3D] 保留PGM加载的地图: ${topic}`)
          preservedTopics.add(topic)
        } else {
          removeVisualization(topic)
        }
      })

      // 清理轨迹点
      trajectoryPoints = []

      // console.log(`[Scene3D] 已清除可视化对象，保留 ${preservedTopics.size} 个地图对象`)
      ElMessage.info(`已清除可视化对象，保留了 ${preservedTopics.size} 个地图`)
    }
    
    const getPerformanceStats = () => {
      return performanceStats.value
    }
    
    // 可视化更新方法
    // 点云更新计数器
    let pointCloudUpdateCount = 0

    const updatePointCloud = (topic, message) => {
      pointCloudUpdateCount++

      // 只在前几次或每100次更新时记录详细信息
      const shouldLog = pointCloudUpdateCount <= 3 || pointCloudUpdateCount % 100 === 0

      if (shouldLog) {
        // console.log(`Updating point cloud for ${topic} (update #${pointCloudUpdateCount})`)
      }
      
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
          if (shouldLog) {
            // console.log('Processing PointCloud2 message')
            console.log('Fields:', message.fields)
            console.log('Width:', message.width, 'Height:', message.height, 'Point step:', message.point_step)
          }
          
          // 如果是 PointCloud2 格式
          if (message.fields && message.data) {
            let dataArray = message.data
            
            // 处理Base64编码的数据（ROSBridge通常这样传输）
            if (typeof message.data === 'string') {
              if (shouldLog) console.log('Decoding Base64 data...')
              try {
                const binaryString = atob(message.data)
                dataArray = new Uint8Array(binaryString.length)
                for (let i = 0; i < binaryString.length; i++) {
                  dataArray[i] = binaryString.charCodeAt(i)
                }
                if (shouldLog) console.log('Decoded data length:', dataArray.length)
              } catch (e) {
                console.error('Base64 decode failed:', e)
                dataArray = []
              }
            }
            
            const width = message.width || 1
            const height = message.height || 1
            const pointStep = message.point_step || 16
            const totalPoints = width * height
            
            if (shouldLog) console.log(`Processing ${totalPoints} points with step ${pointStep}`)

            // 查找XYZ字段的偏移量
            let xOffset = 0, yOffset = 4, zOffset = 8
            if (message.fields && Array.isArray(message.fields)) {
              message.fields.forEach(field => {
                if (shouldLog) console.log(`Field: ${field.name}, offset: ${field.offset}, datatype: ${field.datatype}`)
                if (field.name === 'x') xOffset = field.offset
                else if (field.name === 'y') yOffset = field.offset
                else if (field.name === 'z') zOffset = field.offset
              })
            }

            if (shouldLog) console.log(`Using offsets - X: ${xOffset}, Y: ${yOffset}, Z: ${zOffset}`)
            
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

                    // ROS坐标系转换到Three.js坐标系
                    // ROS: X前，Y左，Z上 -> Three.js: X右，Y上，Z前
                    // 转换：ROS(x,y,z) -> Three.js(x,y,z) 保持不变，因为我们已经旋转了坐标轴
                    positions.push(x, y, z)
                    pointsProcessed++

                    // 根据Z轴高度生成颜色（高程着色）
                    const normalizedZ = Math.max(0, Math.min(1, (z + 2) / 4)) // 假设z范围-2到2
                    const hue = (1 - normalizedZ) * 240 / 360 // 从蓝色(低)到红色(高)
                    const color = new THREE.Color().setHSL(hue, 0.8, 0.6)
                    colors.push(color.r, color.g, color.b)
                  }
                } catch (parseError) {
                  // 忽略单个点的解析错误
                }
              }
            }
            
            if (shouldLog) console.log(`Successfully processed ${pointsProcessed} points out of ${maxPoints}`)
          }
          // 如果是简单的点数组格式
          else if (Array.isArray(message.points)) {
            if (shouldLog) console.log('Processing points array format')
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
          
          // 应用持久化设置创建材质
          // 强度显示优先使用激光设置，如果没有则使用点云设置
          const showIntensity = persistentSettings.laser.showIntensity !== undefined
            ? persistentSettings.laser.showIntensity
            : persistentSettings.pointcloud.showIntensity

          const material = new THREE.PointsMaterial({
            size: persistentSettings.pointcloud.pointSize || Math.max(0.02, size / 500),
            vertexColors: showIntensity,
            sizeAttenuation: true,
            opacity: persistentSettings.pointcloud.opacity || 1.0,
            transparent: (persistentSettings.pointcloud.opacity || 1.0) < 1.0
          })

          const pointCloud = new THREE.Points(geometry, material)
          pointCloud.userData = {
            topic,
            messageType: 'sensor_msgs/msg/PointCloud2',
            pointCount: pointsProcessed,
            originalMessage: message
          }

          // 根据激光设置决定是否显示点云（当作为3D激光时）
          pointCloud.visible = persistentSettings.laser.showLaserPoints !== undefined
            ? persistentSettings.laser.showLaserPoints
            : true

          scene.add(pointCloud)
          visualizationObjects.set(topic, pointCloud)
          
          // 只在首次或特殊情况下调整相机视角，避免频繁变化
          if (pointCloudUpdateCount <= 3) {
            fitCameraToPointCloud(pointCloud)
          }
          
          if (shouldLog) {
            console.log(`✅ Added point cloud with ${pointsProcessed} points`)
            console.log(`Point size: ${material.size}, Bounding box:`, box)
          }

          // 只在首次显示成功消息
          if (pointCloudUpdateCount <= 3) {
            ElMessage.success(`成功显示点云 ${topic}: ${pointsProcessed} 个点`)
          }
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
      // console.log(`[LaserScan] 开始处理激光雷达数据 for ${topic}`)

      // 兼容不同的字段命名格式（有些有下划线前缀）
      let ranges = message.ranges || message._ranges
      const angle_min = message.angle_min || message._angle_min
      const angle_max = message.angle_max || message._angle_max
      const angle_increment = message.angle_increment || message._angle_increment
      const range_min = message.range_min || message._range_min
      const range_max = message.range_max || message._range_max
      const header = message.header || message._header

      // 处理ranges字段 - 可能是字符串格式的Python array
      if (typeof ranges === 'string') {
        // console.log(`[LaserScan] ranges是字符串格式，尝试解析: ${ranges.substring(0, 100)}...`)
        try {
          // 解析Python array格式：array('f', [1.0, 2.0, 3.0, ...])
          const match = ranges.match(/array\('f',\s*\[(.*)\]\)/)
          if (match) {
            const numbersStr = match[1]
            // 分割并解析数字，处理inf和nan
            ranges = numbersStr.split(',').map(str => {
              const trimmed = str.trim()
              if (trimmed === 'inf') return Infinity
              if (trimmed === '-inf') return -Infinity
              if (trimmed === 'nan') return NaN
              return parseFloat(trimmed)
            })
            // 不要在这里过滤无效值！保留所有值以维持角度索引对应关系
            // console.log(`[LaserScan] 成功解析${ranges.length}个ranges值 (包含${ranges.filter(val => !isFinite(val)).length}个无效值)`) 
          } else {
            console.error(`[LaserScan] 无法解析ranges字符串格式: ${ranges}`)
            ranges = []
          }
        } catch (e) {
          console.error(`[LaserScan] 解析ranges字符串失败:`, e)
          ranges = []
        }
      }



      if (angle_min === undefined || angle_max === undefined || angle_increment === undefined) {
        console.error(`[LaserScan] 无效的激光雷达消息: 缺少角度信息`)
        console.error(`[LaserScan] angle_min=${angle_min}, angle_max=${angle_max}, angle_increment=${angle_increment}`)
        return
      }

      // console.log(`[LaserScan] ✅ 消息验证通过，开始处理 ${ranges.length} 个激光点`)

      removeVisualization(topic)

      const geometry = new THREE.BufferGeometry()
      const positions = []
      const colors = []

      try {
        // 解析激光雷达数据
        if (ranges && Array.isArray(ranges) && ranges.length > 0) {
          const angleMin = angle_min || -Math.PI
          const angleMax = angle_max || Math.PI
          const angleIncrement = angle_increment || (angleMax - angleMin) / ranges.length
          const rangeMin = range_min || 0.0
          const rangeMax = range_max || 100.0

          // 只在第一次更新时显示详细信息
          if (!updateLaserScan._firstLogged) {
            console.log(`LaserScan info: ${ranges.length} rays`)
            console.log(`  - 角度范围: ${angleMin.toFixed(3)} 到 ${angleMax.toFixed(3)} 弧度`)
            console.log(`  - 角度范围: ${(angleMin * 180 / Math.PI).toFixed(1)}° 到 ${(angleMax * 180 / Math.PI).toFixed(1)}°`)
            console.log(`  - 角度增量: ${angleIncrement.toFixed(6)} 弧度 (${(angleIncrement * 180 / Math.PI).toFixed(3)}°)`)
            console.log(`  - 距离范围: ${rangeMin} 到 ${rangeMax} 米`)
            console.log(`  - 角度跨度: ${((angleMax - angleMin) * 180 / Math.PI).toFixed(1)}°`)

            // 检查是否是完整的360度扫描
            const totalAngle = angleMax - angleMin
            if (Math.abs(totalAngle - 2 * Math.PI) < 0.1) {
              console.log(`  - 这是360度全方位扫描`)
            } else {
              console.log(`  - 这是${(totalAngle * 180 / Math.PI).toFixed(1)}度扇形扫描`)
            }

            // 计算应该在90度、180度、270度的索引位置
            const index90 = Math.round((Math.PI / 2 - angleMin) / angleIncrement)
            const index180 = Math.round((Math.PI - angleMin) / angleIncrement)
            const index270 = Math.round((3 * Math.PI / 2 - angleMin) / angleIncrement)
            console.log(`  - 关键角度索引: 90°→${index90}, 180°→${index180}, 270°→${index270}`)

            // 检查这些索引是否有有效数据
            if (index90 >= 0 && index90 < ranges.length) {
              const range90 = ranges[index90]
              console.log(`  - 90度方向距离: ${range90} (${isFinite(range90) ? '有效' : '无效'})`)
            }
            if (index180 >= 0 && index180 < ranges.length) {
              const range180 = ranges[index180]
              console.log(`  - 180度方向距离: ${range180} (${isFinite(range180) ? '有效' : '无效'})`)
            }
          }

          let validPoints = 0
          let minX = Infinity, maxX = -Infinity
          let minY = Infinity, maxY = -Infinity
          for (let i = 0; i < ranges.length; i++) {
            const angle = angleMin + i * angleIncrement
            const range = ranges[i]

            // 过滤有效距离值
            if (range >= rangeMin && range <= rangeMax && isFinite(range)) {
              // 极坐标转笛卡尔坐标 - 完全按照flask_ros/map-2d.js的drawLaserScan实现
              // 第730-736行的核心逻辑：
              //
              // const laserAngle = scan.angle_min + index * scan.angle_increment;
              // const worldAngle = this.robotPose.theta + laserAngle;
              // const endX = this.robotPose.x + range * Math.cos(worldAngle);
              // const endY = this.robotPose.y + range * Math.sin(worldAngle);

              // 激光雷达坐标转换 - 修复显示为一条线的问题
              //
              // 问题分析：显示为一条线说明角度计算有问题
              // 让我直接使用标准的极坐标转换，不考虑机器人姿态

              // 极坐标转笛卡尔坐标 - 修复坐标系映射
              // ROS标准：angle_min=-π, angle_max=+π, 0度为前方(+X轴)
              // Three.js坐标系：需要正确映射X/Y/Z轴

              // 方法1：标准ROS坐标系 (先试试这个)
              const x = range * Math.cos(angle)
              const y = range * Math.sin(angle)
              const z = 0

              // 只在第一次更新时输出少量验证数据
              if (!updateLaserScan._firstLogged && validPoints < 3) {
                const angleDeg = angle * 180 / Math.PI
                // console.log(`[LaserScan] 验证点${validPoints}: i=${i}, angle=${angleDeg.toFixed(1)}°, range=${range.toFixed(2)}m`)
              }


              positions.push(x, y, z)

              // 更新边界框
              minX = Math.min(minX, x)
              maxX = Math.max(maxX, x)
              minY = Math.min(minY, y)
              maxY = Math.max(maxY, y)


              // 改进的颜色方案：更明显的颜色，基于距离
              const normalizedRange = Math.min(Math.max((range - rangeMin) / (rangeMax - rangeMin), 0), 1)

              // 方案1：简单的红绿渐变（近红远绿）
              const red = 1.0 - normalizedRange  // 近距离红色
              const green = normalizedRange      // 远距离绿色
              const blue = 0.2                   // 固定蓝色分量

              colors.push(red, green, blue)

              validPoints++
            }
          }

          // console.log(`[LaserScan] 处理结果: ${validPoints}/${ranges.length} 有效点`)

          // 详细统计：分析有效点的分布
          if (!updateLaserScan._firstLogged && validPoints > 0) {
            // console.log(`[LaserScan] 📊 数据分析:`)
            console.log(`  - 总测量点: ${ranges.length}`)
            console.log(`  - 有效点数: ${validPoints}`)
            console.log(`  - 无效点数: ${ranges.length - validPoints}`)
            console.log(`  - 有效率: ${(validPoints / ranges.length * 100).toFixed(1)}%`)
            console.log(`  - 角度范围: ${(angleMin * 180 / Math.PI).toFixed(1)}° ~ ${(angleMax * 180 / Math.PI).toFixed(1)}°`)
            console.log(`  - 距离范围: ${rangeMin}m ~ ${rangeMax}m`)

            // 检查是否真的是360度扫描
            const totalAngleDeg = (angleMax - angleMin) * 180 / Math.PI
            console.log(`  - 扫描角度跨度: ${totalAngleDeg.toFixed(1)}°`)
            console.log(`  - 是否360度扫描: ${Math.abs(totalAngleDeg - 360) < 5 ? '是' : '否'}`)

            // 分析有效点的角度分布
            const validAngles = []
            for (let i = 0; i < ranges.length; i++) {
              const range = ranges[i]
              if (range >= rangeMin && range <= rangeMax && isFinite(range)) {
                const angle = angleMin + i * angleIncrement
                validAngles.push(angle * 180 / Math.PI)
              }
            }
            if (validAngles.length > 0) {
              const minAngle = Math.min(...validAngles)
              const maxAngle = Math.max(...validAngles)
              console.log(`  - 有效点角度分布: ${minAngle.toFixed(1)}° ~ ${maxAngle.toFixed(1)}°`)
              console.log(`  - 角度分布跨度: ${(maxAngle - minAngle).toFixed(1)}°`)
            }
          }

          // 只在第一次更新时显示边界框信息
          if (!updateLaserScan._firstLogged && validPoints > 0) {
            // console.log(`[LaserScan] 点云边界框: X=[${minX.toFixed(2)}, ${maxX.toFixed(2)}], Y=[${minY.toFixed(2)}, ${maxY.toFixed(2)}]`)
            // console.log(`[LaserScan] 点云尺寸: ${(maxX - minX).toFixed(2)}m x ${(maxY - minY).toFixed(2)}m`)
            // console.log(`[LaserScan] X范围: ${(maxX - minX).toFixed(2)}m, Y范围: ${(maxY - minY).toFixed(2)}m`)

            // 如果Y范围太小，说明有问题
            if ((maxY - minY) < 1.0) {
              console.warn(`[LaserScan] ⚠️ Y坐标范围太小 (${(maxY - minY).toFixed(2)}m)，可能存在解析问题`)
            }
          }

          if (validPoints === 0) {
            console.warn('[LaserScan] 没有找到有效的激光雷达点')
            ElMessage.warning(`激光雷达 ${topic} 没有有效数据点`)

            // 创建一个警告指示器
            const warningGeometry = new THREE.SphereGeometry(0.1, 8, 8)
            const warningMaterial = new THREE.MeshBasicMaterial({ color: 0xffff00 })
            const warningSphere = new THREE.Mesh(warningGeometry, warningMaterial)
            warningSphere.position.set(0, 0, 0.5)
            warningSphere.userData = { topic, messageType: 'sensor_msgs/msg/LaserScan', warning: 'no_valid_points' }
            scene.add(warningSphere)
            visualizationObjects.set(topic, warningSphere)
            return
          }
        } else {
          console.error('[LaserScan] 无效的激光雷达消息格式')
          console.error('[LaserScan] 消息内容:', message)
          ElMessage.error(`激光雷达 ${topic} 消息格式无效`)
          return
        }

        geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
        geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3))

        // 创建激光点对象，应用持久化设置
        const pointMaterial = new THREE.PointsMaterial({
          size: persistentSettings.laser.pointSize || 0.15,
          vertexColors: persistentSettings.laser.showIntensity,
          sizeAttenuation: false,  // 不根据距离缩放，保持固定大小
          alphaTest: 0.5
        })

        const laserPoints = new THREE.Points(geometry, pointMaterial)
        laserPoints.userData = {
          topic,
          messageType: 'sensor_msgs/msg/LaserScan',
          type: 'laser_points',
          pointCount: positions.length / 3
        }
        laserPoints.visible = persistentSettings.laser.showLaserPoints

        // 创建激光连线对象
        const lineGeometry = new THREE.BufferGeometry()
        const linePositions = []

        // 创建从原点到每个激光点的连线
        for (let i = 0; i < positions.length; i += 3) {
          // 原点到激光点的线段
          linePositions.push(0, 0, 0)  // 原点
          linePositions.push(positions[i], positions[i + 1], positions[i + 2])  // 激光点
        }

        lineGeometry.setAttribute('position', new THREE.Float32BufferAttribute(linePositions, 3))

        const lineMaterial = new THREE.LineBasicMaterial({
          color: 0x00ff00,
          opacity: 0.3,
          transparent: true
        })

        const laserLines = new THREE.LineSegments(lineGeometry, lineMaterial)
        laserLines.userData = {
          topic,
          messageType: 'sensor_msgs/msg/LaserScan',
          type: 'laser_lines',
          pointCount: positions.length / 3
        }
        laserLines.visible = persistentSettings.laser.showLaserLines

        scene.add(laserPoints)
        scene.add(laserLines)

        // 用点对象作为主要的可视化对象存储
        visualizationObjects.set(topic, laserPoints)
        visualizationObjects.set(topic + '_lines', laserLines)

        // 只在第一次成功时显示详细日志和消息
        if (!updateLaserScan._firstLogged) {
          // console.log(`[LaserScan] 成功添加激光雷达点云: ${positions.length / 3} 个点`)
          ElMessage.success(`激光雷达 ${topic} 显示成功: ${positions.length / 3} 个点`)
          updateLaserScan._firstLogged = true
        }

      } catch (error) {
        console.error('Error updating laser scan:', error)
        ElMessage.error(`激光雷达更新失败: ${error.message}`)
      }
    }
    
    const updateMarker = (topic, message) => {
      // 标记可视化实现
      // console.log(`Updating marker for ${topic}:`, message)
      
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
      // console.log(`Updating marker array for ${topic}:`, message)
      
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
      // console.log(`Updating path for ${topic}:`, message)
      
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
    

    const updateOdometry = (topic, message) => {
      // console.log(`[updateOdometry] ⚙️ 开始处理里程计消息 - 主题: ${topic}`)
      // console.log(`[updateOdometry] 消息内容:`, message)

      try {
        removeVisualization(topic)

        if (!message.pose || !message.pose.pose || !message.pose.pose.position) {
          console.warn('Invalid odometry message format')
          return
        }

        const position = message.pose.pose.position
        const orientation = message.pose.pose.orientation

        // 更新机器人模型位置
        updateRobotPosition(position, orientation)

        // 创建位置指示器（箭头）
        const arrowGeometry = new THREE.ConeGeometry(0.2, 1, 8)
        const arrowMaterial = new THREE.MeshLambertMaterial({ color: 0x00ff00, transparent: true, opacity: 0.8 })
        const arrow = new THREE.Mesh(arrowGeometry, arrowMaterial)

        // 设置位置
        arrow.position.set(position.x, position.y, position.z + 0.5) // 稍微抬高

        // 设置方向（如果有方向信息）
        if (orientation) {
          arrow.quaternion.set(orientation.x, orientation.y, orientation.z, orientation.w)
          // 调整箭头方向，使其指向正前方
          arrow.rotateX(-Math.PI / 2)
        }

        // 创建轨迹线（如果是第一次或距离较远）
        const currentPos = new THREE.Vector3(position.x, position.y, position.z)

        // 只在位置变化超过阈值时添加轨迹点
        if (trajectoryPoints.length === 0 ||
            trajectoryPoints[trajectoryPoints.length - 1].distanceTo(currentPos) > 0.1) {
          trajectoryPoints.push(currentPos.clone())
          // console.log(`[Trajectory] 添加轨迹点 #${trajectoryPoints.length}: (${currentPos.x.toFixed(2)}, ${currentPos.y.toFixed(2)}, ${currentPos.z.toFixed(2)})`)

          // 限制轨迹点数量（由控制面板传入，范围10~100）
          const maxLen = Math.max(10, Math.min(100, persistentSettings.position.trajectoryLength || 100))
          if (trajectoryPoints.length > maxLen) {
            trajectoryPoints.shift()
          }
        }

        // 创建轨迹线
        if (trajectoryPoints.length > 1) {
          const trajectoryGeometry = new THREE.BufferGeometry().setFromPoints(trajectoryPoints)
          const trajectoryMaterial = new THREE.LineBasicMaterial({
            color: 0xff0000,  // 改为红色便于识别
            transparent: false, // 不透明
            linewidth: 5      // 更大的线宽
          })
          const trajectoryLine = new THREE.Line(trajectoryGeometry, trajectoryMaterial)
          trajectoryLine.userData = { type: 'trajectory' }  // 添加类型标识

          // 强制轨迹可见用于调试
          trajectoryLine.visible = true

          // 详细调试信息
          console.log(`[Trajectory] 创建轨迹线详细信息:`)
          console.log(`  - 点数: ${trajectoryPoints.length}`)
          console.log(`  - 几何体顶点数: ${trajectoryGeometry.attributes.position.count}`)
          console.log(`  - 可见性: ${trajectoryLine.visible}`)
          console.log(`  - 设置中的显示轨迹: ${persistentSettings.position.showTrajectory}`)
          console.log(`  - 材质颜色: 0x${trajectoryMaterial.color.getHex().toString(16)}`)
          console.log(`  - 轨迹点坐标:`, trajectoryPoints.map(p => `(${p.x.toFixed(2)}, ${p.y.toFixed(2)}, ${p.z.toFixed(2)})`))

          const group = new THREE.Group()
          group.add(arrow)
          group.add(trajectoryLine)

          // 确保整个组可见
          group.visible = true

          console.log(`[Trajectory] 组对象信息:`)
          console.log(`  - 组可见性: ${group.visible}`)
          console.log(`  - 组内对象数: ${group.children.length}`)
          console.log(`  - 轨迹线在组中: ${group.children.includes(trajectoryLine)}`)
          console.log(`  - 场景添加前场景对象数: ${scene.children.length}`)

          // 额外创建一个独立的轨迹线直接添加到场景，用于调试
          const debugTrajectoryGeometry = new THREE.BufferGeometry().setFromPoints(trajectoryPoints)
          const debugTrajectoryMaterial = new THREE.LineBasicMaterial({
            color: 0x00ff00,  // 绿色调试轨迹
            transparent: false,
            linewidth: 8
          })
          const debugTrajectoryLine = new THREE.Line(debugTrajectoryGeometry, debugTrajectoryMaterial)
          debugTrajectoryLine.position.set(0, 0, 1) // 稍微抬高避免重叠
          scene.add(debugTrajectoryLine)
          console.log(`[Trajectory] 添加了独立的绿色调试轨迹线到场景，位置: (0,0,1)`)

          group.userData = {
            topic,
            messageType: 'nav_msgs/msg/Odometry',
            type: 'robot_pose',  // 添加类型标识
            position: { x: position.x, y: position.y, z: position.z },
            trajectoryLength: trajectoryPoints.length
          }

          scene.add(group)
          visualizationObjects.set(topic, group)
        } else {
          // 只有箭头
          arrow.userData = { topic, messageType: 'nav_msgs/msg/Odometry' }
          scene.add(arrow)
          visualizationObjects.set(topic, arrow)
        }

        // console.log(`Successfully updated odometry at (${position.x.toFixed(2)}, ${position.y.toFixed(2)}, ${position.z.toFixed(2)})`)

      } catch (error) {
        console.error('Error updating odometry:', error)
      }
    }

    const updatePoseStamped = (topic, message) => {
      console.log(`Updating pose stamped for ${topic}:`, message)

      try {
        removeVisualization(topic)

        if (!message.pose || !message.pose.position) {
          console.warn('Invalid pose stamped message format')
          return
        }

        const position = message.pose.position
        const orientation = message.pose.orientation

        // 更新机器人模型位置
        updateRobotPosition(position, orientation)

        // 创建位置指示器（坐标轴）
        const axesHelper = new THREE.AxesHelper(1)
        axesHelper.position.set(position.x, position.y, position.z)

        if (orientation) {
          axesHelper.quaternion.set(orientation.x, orientation.y, orientation.z, orientation.w)
        }

        axesHelper.userData = {
          topic,
          messageType: 'geometry_msgs/msg/PoseStamped',
          position: { x: position.x, y: position.y, z: position.z }
        }

        scene.add(axesHelper)
        visualizationObjects.set(topic, axesHelper)

        // console.log(`Successfully updated pose at (${position.x.toFixed(2)}, ${position.y.toFixed(2)}, ${position.z.toFixed(2)})`)

      } catch (error) {
        console.error('Error updating pose stamped:', error)
      }
    }

    const updatePoseWithCovarianceStamped = (topic, message) => {
      console.log(`Updating pose with covariance for ${topic}:`, message)

      try {
        removeVisualization(topic)

        if (!message.pose || !message.pose.pose || !message.pose.pose.position) {
          console.warn('Invalid pose with covariance message format')
          return
        }

        const position = message.pose.pose.position
        const orientation = message.pose.pose.orientation
        const covariance = message.pose.covariance

        // 创建位置指示器
        const axesHelper = new THREE.AxesHelper(1)
        axesHelper.position.set(position.x, position.y, position.z)

        if (orientation) {
          axesHelper.quaternion.set(orientation.x, orientation.y, orientation.z, orientation.w)
        }

        // 创建协方差椭圆（显示不确定性）
        let uncertaintyEllipse = null
        if (covariance && covariance.length >= 36) {
          // 提取XY平面的协方差
          const cov_xx = covariance[0]   // 第1行第1列
          const cov_yy = covariance[7]   // 第2行第2列
          const cov_xy = covariance[1]   // 第1行第2列

          // 计算椭圆参数
          const trace = cov_xx + cov_yy
          const det = cov_xx * cov_yy - cov_xy * cov_xy

          if (det > 0 && trace > 0) {
            const lambda1 = (trace + Math.sqrt(trace * trace - 4 * det)) / 2
            const lambda2 = (trace - Math.sqrt(trace * trace - 4 * det)) / 2

            const a = Math.sqrt(Math.abs(lambda1)) * 2  // 95%置信间隔
            const b = Math.sqrt(Math.abs(lambda2)) * 2

            // 创建椭圆几何体
            const ellipseGeometry = new THREE.RingGeometry(0, Math.max(a, b), 32)
            const ellipseMaterial = new THREE.MeshBasicMaterial({
              color: 0xff0000,
              transparent: true,
              opacity: 0.3,
              side: THREE.DoubleSide
            })
            uncertaintyEllipse = new THREE.Mesh(ellipseGeometry, ellipseMaterial)
            uncertaintyEllipse.position.set(position.x, position.y, position.z + 0.01)
            uncertaintyEllipse.scale.set(a/Math.max(a,b), b/Math.max(a,b), 1)

            // 旋转椭圆到正确方向
            if (cov_xy !== 0) {
              const angle = 0.5 * Math.atan2(2 * cov_xy, cov_xx - cov_yy)
              uncertaintyEllipse.rotateZ(angle)
            }
          }
        }

        // 组合所有元素
        const group = new THREE.Group()
        group.add(axesHelper)
        if (uncertaintyEllipse) {
          group.add(uncertaintyEllipse)
        }

        group.userData = {
          topic,
          messageType: 'geometry_msgs/msg/PoseWithCovarianceStamped',
          position: { x: position.x, y: position.y, z: position.z },
          hasCovariance: uncertaintyEllipse !== null
        }

        scene.add(group)
        visualizationObjects.set(topic, group)

        // console.log(`Successfully updated pose with covariance at (${position.x.toFixed(2)}, ${position.y.toFixed(2)}, ${position.z.toFixed(2)})`)

      } catch (error) {
        console.error('Error updating pose with covariance:', error)
      }
    }

    // 消息验证相关变量
    let verificationSubscriptions = new Map()

    // 启动消息验证
    const startMessageVerification = () => {
      console.log('[Verification] 启动消息验证系统')

      // 验证/goal_pose话题
      try {
        const goalPoseVerification = rosbridge.subscribe('/goal_pose', 'geometry_msgs/msg/PoseStamped', (message) => {
          console.log('[Verification] ✅ 收到/goal_pose消息:', message)
          ElMessage.success('验证成功：收到发布的目标点消息')
        })

        if (goalPoseVerification) {
          verificationSubscriptions.set('/goal_pose', goalPoseVerification)
          console.log('[Verification] ✅ 成功订阅/goal_pose用于验证')
        }
      } catch (error) {
        console.error('[Verification] 订阅/goal_pose失败:', error)
      }

      // 验证/initialpose话题
      try {
        const initialPoseVerification = rosbridge.subscribe('/initialpose', 'geometry_msgs/msg/PoseWithCovarianceStamped', (message) => {
          console.log('[Verification] ✅ 收到/initialpose消息:', message)
          ElMessage.success('验证成功：收到发布的位置估计消息')
        })

        if (initialPoseVerification) {
          verificationSubscriptions.set('/initialpose', initialPoseVerification)
          console.log('[Verification] ✅ 成功订阅/initialpose用于验证')
        }
      } catch (error) {
        console.error('[Verification] 订阅/initialpose失败:', error)
      }
    }

    // 停止消息验证
    const stopMessageVerification = () => {
      console.log('[Verification] 停止消息验证系统')
      verificationSubscriptions.forEach((subscription, topic) => {
        try {
          rosbridge.unsubscribe(subscription)
          // console.log(`[Verification] 取消订阅验证话题: ${topic}`)
        } catch (error) {
          console.error(`[Verification] 取消订阅${topic}失败:`, error)
        }
      })
      verificationSubscriptions.clear()
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

      // 检查ROS连接状态并启动验证
      if (rosbridge.isConnected) {
        console.log('[Scene3D] ROS已连接，启动消息验证')
        startMessageVerification()
      } else {
        console.log('[Scene3D] ROS未连接，等待连接后启动验证')
        // 定期检查连接状态
        const connectionCheckInterval = setInterval(() => {
          if (rosbridge.isConnected) {
            console.log('[Scene3D] ROS连接成功，启动消息验证')
            startMessageVerification()
            clearInterval(connectionCheckInterval)
          }
        }, 1000)

        // 1分钟后停止检查
        setTimeout(() => {
          clearInterval(connectionCheckInterval)
        }, 60000)
      }
    })
    
    onUnmounted(() => {
      // 清理资源
      if (animationId) {
        cancelAnimationFrame(animationId)
      }

      // 停止消息验证
      stopMessageVerification()
      
      window.removeEventListener('resize', onWindowResize)
      window.removeEventListener('keydown', onKeyDown)
      
      // 清理所有ROS订阅
      rosSubscriptions.forEach((subscription, topicName) => {
        try {
          rosbridge.unsubscribe(subscription)
          // console.log(`清理ROS订阅: ${topicName}`)
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

    const updateRobotTrajectory = () => {
      // 更新所有机器人位姿对象的轨迹线
      visualizationObjects.forEach((object, topic) => {
        if (object.userData?.type === 'robot_pose') {
          // 找到轨迹线并更新
          object.children.forEach(child => {
            if (child.userData?.type === 'trajectory') {
              // 重新创建轨迹几何体
              if (trajectoryPoints.length > 1) {
                child.geometry.dispose()
                child.geometry = new THREE.BufferGeometry().setFromPoints(trajectoryPoints)
              }
            }
          })
        }
      })
    }

    const updateTrajectoryLength = (newLength) => {
      // 限制轨迹点数量
      if (trajectoryPoints.length > newLength) {
        trajectoryPoints.splice(0, trajectoryPoints.length - newLength)
        // 重新创建轨迹线
        updateRobotTrajectory()
      }
    }

    // 导航工具相关方法
    const setNavigationTool = (tool) => {
      currentNavigationTool = tool
      console.log('设置导航工具:', tool)

      // 清除之前的预览箭头
      clearPreviewArrow()

      // 更改鼠标样式
      if (containerRef.value) {
        switch (tool) {
          case '2d_goal':
            containerRef.value.style.cursor = 'crosshair'
            break
          case '2d_pose':
            containerRef.value.style.cursor = 'copy'
            break
          default:
            containerRef.value.style.cursor = 'default'
        }
      }
    }

    const createPreviewArrow = (position, direction) => {
      // 清除之前的箭头
      clearPreviewArrow()

      // 创建箭头几何体
      const arrowGeometry = new THREE.ConeGeometry(0.1, 0.3, 8)
      const arrowMaterial = new THREE.MeshBasicMaterial({
        color: currentNavigationTool === '2d_goal' ? 0xff6b35 : 0x4dabf7,
        transparent: true,
        opacity: 0.8
      })

      const arrowHead = new THREE.Mesh(arrowGeometry, arrowMaterial)

      // 创建箭头杆
      const shaftGeometry = new THREE.CylinderGeometry(0.02, 0.02, 0.4, 8)
      const shaft = new THREE.Mesh(shaftGeometry, arrowMaterial)

      // 组合箭头
      previewArrow = new THREE.Group()
      shaft.position.set(0, -0.2, 0)
      arrowHead.position.set(0, 0, 0)
      previewArrow.add(shaft)
      previewArrow.add(arrowHead)

      // 设置位置和方向
      previewArrow.position.copy(position)
      const angle = Math.atan2(direction.y, direction.x)
      previewArrow.rotation.z = angle - Math.PI / 2 // 调整箭头指向

      scene.add(previewArrow)
    }

    const updatePreviewArrow = (position, direction) => {
      if (previewArrow) {
        previewArrow.position.copy(position)
        const angle = Math.atan2(direction.y, direction.x)
        previewArrow.rotation.z = angle - Math.PI / 2
      }
    }

    const clearPreviewArrow = () => {
      if (previewArrow) {
        scene.remove(previewArrow)
        previewArrow.children.forEach(child => {
          if (child.geometry) child.geometry.dispose()
          if (child.material) child.material.dispose()
        })
        previewArrow = null
      }
    }

    const handleNavigationToolClick = (position, orientation) => {
      switch (currentNavigationTool) {
        case '2d_goal':
          publishGoalPose(position, orientation)
          break
        case '2d_pose':
          publishPoseEstimate(position, orientation)
          break
      }

      // 发布后重置工具
      setNavigationTool('none')
    }

    const publishGoalPose = (position, orientation) => {
      console.log('[Navigation] 开始发布2D目标点')
      console.log('[Navigation] 连接状态检查:', {
        isConnected: rosbridge.isConnected,
        connectionStatus: connectionStore.connectionStatus,
        websocketState: connectionStore.websocket?.readyState
      })

      if (!rosbridge.isConnected) {
        console.error('[Navigation] ❌ ROS Bridge未连接，无法发布消息')
        ElMessage.error('ROS Bridge未连接，请先连接到ROS系统')
        return false
      }

      // RViz兼容的消息格式 - 2D Goal Pose
      const goalMsg = {
        header: {
          stamp: {
            sec: Math.floor(Date.now() / 1000),
            nanosec: (Date.now() % 1000) * 1000000
          },
          frame_id: 'map'  // RViz标准使用map坐标系
        },
        pose: {
          position: {
            x: position.x,
            y: position.y,
            z: 0.0  // 2D导航，z固定为0
          },
          orientation: {
            x: orientation.x,
            y: orientation.y,
            z: orientation.z,
            w: orientation.w
          }
        }
      }

      console.log('[Navigation] 发布2D目标点消息:', JSON.stringify(goalMsg, null, 2))

      try {
        // 发布到标准的goal_pose话题（RViz兼容）
        // console.log('[Navigation] 发布到话题: /goal_pose')
        // console.log('[Navigation] 消息类型: geometry_msgs/msg/PoseStamped')
        const publishResult = rosbridge.publish('/goal_pose', 'geometry_msgs/msg/PoseStamped', goalMsg)
        // console.log('[Navigation] rosbridge.publish返回结果:', publishResult)

        if (publishResult) {
          const yawDegrees = (Math.atan2(2 * (orientation.w * orientation.z + orientation.x * orientation.y),
                                         1 - 2 * (orientation.y * orientation.y + orientation.z * orientation.z)) * 180 / Math.PI).toFixed(1)
          console.log(`[Navigation] ✅ 目标点发布成功: (${position.x.toFixed(2)}, ${position.y.toFixed(2)}) 方向: ${yawDegrees}°`)
          ElMessage.success(`已设置目标点: (${position.x.toFixed(2)}, ${position.y.toFixed(2)}) 方向: ${yawDegrees}°`)

          // 额外验证：订阅目标话题来验证消息是否真的发送了
          console.log('[Navigation] 尝试验证消息发送...')
          return true
        } else {
          throw new Error('发布函数返回false')
        }
      } catch (error) {
        console.error('[Navigation] ❌ 发布目标点失败:', error)
        console.error('[Navigation] 错误堆栈:', error.stack)
        ElMessage.error(`发布目标点失败: ${error.message}`)
        return false
      }
    }

    const publishPoseEstimate = (position, orientation) => {
      console.log('[Navigation] 开始发布2D位置估计')
      console.log('[Navigation] 连接状态检查:', {
        isConnected: rosbridge.isConnected,
        connectionStatus: connectionStore.connectionStatus,
        websocketState: connectionStore.websocket?.readyState
      })

      if (!rosbridge.isConnected) {
        console.error('[Navigation] ❌ ROS Bridge未连接，无法发布消息')
        ElMessage.error('ROS Bridge未连接，请先连接到ROS系统')
        return false
      }

      // RViz兼容的消息格式 - 2D Pose Estimate
      const poseMsg = {
        header: {
          stamp: {
            sec: Math.floor(Date.now() / 1000),
            nanosec: (Date.now() % 1000) * 1000000
          },
          frame_id: 'map'  // RViz标准使用map坐标系
        },
        pose: {
          pose: {
            position: {
              x: position.x,
              y: position.y,
              z: 0.0  // 2D导航，z固定为0
            },
            orientation: {
              x: orientation.x,
              y: orientation.y,
              z: orientation.z,
              w: orientation.w
            }
          },
          // RViz标准协方差矩阵 (6x6 = 36个元素)
          // 表示位置和姿态的不确定性
          covariance: [
            0.25, 0.0, 0.0, 0.0, 0.0, 0.0,   // x的协方差
            0.0, 0.25, 0.0, 0.0, 0.0, 0.0,   // y的协方差
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0,    // z的协方差（2D中不使用）
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0,    // roll的协方差（2D中不使用）
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0,    // pitch的协方差（2D中不使用）
            0.0, 0.0, 0.0, 0.0, 0.0, 0.06853891909  // yaw的协方差
          ]
        }
      }

      console.log('[Navigation] 发布2D位置估计消息:', JSON.stringify(poseMsg, null, 2))

      try {
        // 发布到标准的initialpose话题（RViz兼容）
        // console.log('[Navigation] 发布到话题: /initialpose')
        // console.log('[Navigation] 消息类型: geometry_msgs/msg/PoseWithCovarianceStamped')
        const publishResult = rosbridge.publish('/initialpose', 'geometry_msgs/msg/PoseWithCovarianceStamped', poseMsg)
        // console.log('[Navigation] rosbridge.publish返回结果:', publishResult)

        if (publishResult) {
          const yawDegrees = (Math.atan2(2 * (orientation.w * orientation.z + orientation.x * orientation.y),
                                         1 - 2 * (orientation.y * orientation.y + orientation.z * orientation.z)) * 180 / Math.PI).toFixed(1)
          console.log(`[Navigation] ✅ 位置估计发布成功: (${position.x.toFixed(2)}, ${position.y.toFixed(2)}) 方向: ${yawDegrees}°`)
          ElMessage.success(`已设置位置估计: (${position.x.toFixed(2)}, ${position.y.toFixed(2)}) 方向: ${yawDegrees}°`)
          return true
        } else {
          throw new Error('发布函数返回false')
        }
      } catch (error) {
        console.error('[Navigation] ❌ 发布位置估计失败:', error)
        ElMessage.error(`发布位置估计失败: ${error.message}`)
      }
    }

    const updateSettings = (settings) => {
      console.log('更新3D场景设置:', settings)

      // 首先保存设置到持久化存储
      if (settings.type && persistentSettings[settings.type]) {
        Object.assign(persistentSettings[settings.type], settings)
      }

      switch (settings.type) {
        case 'laser':
          // 更新激光雷达设置
          visualizationObjects.forEach((object, key) => {
            // 2D激光雷达设置
            if (object.userData?.messageType === 'sensor_msgs/msg/LaserScan') {
              // 激光点显示/隐藏
              if (settings.showLaserPoints !== undefined && object.userData?.type === 'laser_points') {
                object.visible = settings.showLaserPoints
              }
              // 激光连线显示/隐藏
              if (settings.showLaserLines !== undefined && object.userData?.type === 'laser_lines') {
                object.visible = settings.showLaserLines
              }
              // 点大小调整
              if (settings.pointSize !== undefined && object.material && object.userData?.type === 'laser_points') {
                object.material.size = settings.pointSize
                object.material.needsUpdate = true
              }
              // 强度显示
              if (settings.showIntensity !== undefined && object.material && object.userData?.type === 'laser_points') {
                // 直接创建新材质以确保vertexColors变化生效
                const oldMaterial = object.material
                const newMaterial = new THREE.PointsMaterial({
                  size: oldMaterial.size,
                  vertexColors: settings.showIntensity,
                  sizeAttenuation: oldMaterial.sizeAttenuation,
                  alphaTest: oldMaterial.alphaTest
                })
                object.material = newMaterial
                oldMaterial.dispose()
              }
            }
            // 3D点云激光设置
            else if (object.userData?.messageType === 'sensor_msgs/msg/PointCloud2') {
              // 激光点显示/隐藏（对3D点云生效）
              if (settings.showLaserPoints !== undefined) {
                object.visible = settings.showLaserPoints
              }
              // 强度显示（对3D点云生效）
              if (settings.showIntensity !== undefined && object.material) {
                // 直接创建新材质以确保vertexColors变化生效
                const oldMaterial = object.material
                const newMaterial = new THREE.PointsMaterial({
                  size: oldMaterial.size,
                  vertexColors: settings.showIntensity,
                  sizeAttenuation: oldMaterial.sizeAttenuation,
                  opacity: oldMaterial.opacity,
                  transparent: oldMaterial.transparent
                })
                object.material = newMaterial
                oldMaterial.dispose()
              }
            }
          })
          console.log('激光雷达设置已更新:', settings)
          break

        case 'pointcloud':
          // 更新点云设置
          visualizationObjects.forEach((object, topic) => {
            if (object.userData?.messageType === 'sensor_msgs/msg/PointCloud2') {
              if (settings.pointSize !== undefined && object.material) {
                object.material.size = settings.pointSize
                object.material.needsUpdate = true
              }
              if (settings.opacity !== undefined && object.material) {
                object.material.opacity = settings.opacity
                object.material.transparent = settings.opacity < 1.0
                object.material.needsUpdate = true
              }
              if (settings.showIntensity !== undefined && object.material) {
                // 直接创建新材质以确保vertexColors变化生效
                const oldMaterial = object.material
                const newMaterial = new THREE.PointsMaterial({
                  size: oldMaterial.size,
                  vertexColors: settings.showIntensity,
                  sizeAttenuation: oldMaterial.sizeAttenuation,
                  opacity: oldMaterial.opacity,
                  transparent: oldMaterial.transparent
                })
                object.material = newMaterial
                oldMaterial.dispose()
              }
            }
          })
          console.log('点云设置已更新:', settings)
          break
          
        case 'map':
          // 更新地图设置
          if (settings.showMap !== undefined && mapMesh.value) {
            mapMesh.value.visible = settings.showMap
          }
          if (settings.opacity !== undefined && mapMesh.value) {
            mapMesh.value.material.opacity = settings.opacity
            mapMesh.value.material.transparent = settings.opacity < 1.0
            mapMesh.value.material.needsUpdate = true
          }
          if (settings.showGrid !== undefined && gridHelper) {
            gridHelper.visible = settings.showGrid
          }
          if (settings.showOrigin !== undefined && axesHelper) {
            axesHelper.visible = settings.showOrigin
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
          console.log('地图设置已更新:', settings)
          break

        case 'position':
          // 更新位置显示设置
          visualizationObjects.forEach((object, topic) => {
            // 轨迹显示
            if (settings.showTrajectory !== undefined) {
              if (object.userData?.type === 'robot_pose') {
                // 查找轨迹线子对象
                object.children.forEach(child => {
                  if (child.userData?.type === 'trajectory') {
                    child.visible = settings.showTrajectory
                  }
                })
              }
            }
          })
          console.log('位置设置已更新:', settings)
          if (settings.trajectoryLength !== undefined) {
            // 更新轨迹长度（夹取到10~100）
            const clamped = Math.max(10, Math.min(100, settings.trajectoryLength))
            updateTrajectoryLength(clamped)
          }
          console.log('位置设置已更新:', settings)
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
          // 更新轨迹长度设置（从控制面板单独通道传入）
          if (settings.trajectoryLength !== undefined) {
            const clamped = Math.max(10, Math.min(100, settings.trajectoryLength))
            persistentSettings.position.trajectoryLength = clamped
            updateTrajectoryLength(clamped)
            console.log('更新轨迹长度:', clamped)
          }
          break
      }
    }

    const setViewPreset = (preset) => {
      console.log('设置视角预设:', preset)
      
      if (!camera) return
      
      const target = new THREE.Vector3(0, 0, 0)
      
      switch (preset) {
        case 'top':
          // 俯视图 - 从正上方看XY平面
          camera.position.set(0, 0, 20)
          camera.lookAt(target)
          break

        case 'side':
          // 侧视图 - 从Y轴侧面看XZ平面
          camera.position.set(0, -20, 5)
          camera.lookAt(target)
          break

        case 'front':
          // 前视图 - 从X轴前方看YZ平面
          camera.position.set(20, 0, 5)
          camera.lookAt(target)
          break

        case 'iso':
          // 等距图 - 从斜上方看，与RViz类似的默认视角
          camera.position.set(10, 10, 10)
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

    const loadMapFiles = async (yamlFile, pgmFile) => {
      console.log(`[Scene3D] 同时加载地图文件: ${yamlFile.name} + ${pgmFile.name}`)

      try {
        // 先加载YAML配置
        const mapConfig = await loadMapYaml(yamlFile)
        console.log(`[Scene3D] YAML配置加载完成:`, mapConfig)

        // 再用配置加载PGM文件
        await loadMapPgmWithConfig(pgmFile, mapConfig)

        ElMessage.success(`地图加载成功: ${yamlFile.name} + ${pgmFile.name}`)

      } catch (error) {
        console.error(`[Scene3D] 地图文件对加载失败:`, error)
        ElMessage.error(`地图文件对加载失败: ${error.message}`)
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
        texture.flipY = true  // 翻转Y轴以匹配ROS坐标系
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
        
        const mesh = new THREE.Mesh(geometry, material)
        mapMesh.value = mesh  // 存储到reactive变量中
        
        // 计算地图在世界坐标系中的真实尺寸
        const mapWidthMeters = width * mapConfig.resolution
        const mapHeightMeters = height * mapConfig.resolution
        
        console.log(`[Scene3D] 地图物理尺寸: ${mapWidthMeters.toFixed(2)}m x ${mapHeightMeters.toFixed(2)}m`)
        
        // 地图位置计算 - 正确应用YAML origin偏移
        //
        // ROS地图约定：
        // - origin是地图像素(0,0)对应的世界坐标，即地图左下角在世界坐标系中的位置
        // - 我们需要让地图的几何中心移动到正确位置，使得坐标原点(0,0)在地图中的正确位置
        //
        // Three.js PlaneGeometry的几何中心默认在原点(0,0,0)
        // 地图左下角应该在世界坐标origin，所以地图中心应该在：
        // mapCenter = origin + (mapSize / 2)

        const mapWidthWorld = width * mapConfig.resolution
        const mapHeightWorld = height * mapConfig.resolution

        // 地图几何中心的世界坐标位置
        // ROS坐标系：X向前(北)，Y向左(西)
        // Three.js坐标系：X向右，Y向上
        // 需要正确处理坐标系转换和origin偏移

        // 确保坐标原点(0,0)在地图中正确显示
        // 如果origin=[-10, -5]，表示地图左下角在世界坐标(-10, -5)
        // 地图中心应该在origin + mapSize/2
        const mapX = mapConfig.origin[0] + mapWidthWorld / 2
        const mapY = mapConfig.origin[1] + mapHeightWorld / 2
        const mapZ = mapConfig.origin[2] || 0.0

        // 验证坐标原点在地图中的位置
        // 坐标原点(0,0)相对于地图左下角的偏移
        const originInMapX = 0 - mapConfig.origin[0]  // 原点X - 地图左下角X
        const originInMapY = 0 - mapConfig.origin[1]  // 原点Y - 地图左下角Y

        console.log(`[Scene3D] 坐标原点(0,0)在地图中的位置检查:`)
        console.log(`[Scene3D] - 原点相对于地图左下角偏移: (${originInMapX.toFixed(2)}, ${originInMapY.toFixed(2)}) 米`)
        console.log(`[Scene3D] - 原点在地图中的百分比位置: (${(originInMapX/mapWidthWorld*100).toFixed(1)}%, ${(originInMapY/mapHeightWorld*100).toFixed(1)}%)`)

        // 如果原点不在地图范围内，给出警告
        if (originInMapX < 0 || originInMapX > mapWidthWorld || originInMapY < 0 || originInMapY > mapHeightWorld) {
          console.warn(`[Scene3D] ⚠️ 坐标原点(0,0)在地图范围外！`)
        }

        console.log(`[Scene3D] 地图世界坐标计算:`)
        console.log(`[Scene3D] - 地图物理尺寸: ${mapWidthWorld.toFixed(2)}m × ${mapHeightWorld.toFixed(2)}m`)
        console.log(`[Scene3D] - YAML origin: [${mapConfig.origin.join(', ')}]`)
        console.log(`[Scene3D] - 计算的地图中心位置: (${mapX.toFixed(3)}, ${mapY.toFixed(3)}, ${mapZ.toFixed(3)})`)

        // 计算坐标原点(0,0)在地图中的相对位置
        const originOffsetX = -mapConfig.origin[0] / mapWidthWorld
        const originOffsetY = -mapConfig.origin[1] / mapHeightWorld
        console.log(`[Scene3D] - 坐标原点(0,0)在地图中的相对位置: (${(originOffsetX*100).toFixed(1)}%, ${(originOffsetY*100).toFixed(1)}%)`)

        mesh.position.set(mapX, mapY, mapZ)

        // 地图旋转 - 测试不同的旋转方案
        // 问题：地图显示悬浮且与坐标系不匹配
        // Three.js的PlaneGeometry默认在XY平面，法线指向+Z
        // 如果地图悬浮，可能是旋转导致的

        // 方案1：不旋转，直接在XY平面
        mesh.rotation.x = 0
        mesh.rotation.y = 0
        mesh.rotation.z = 0

        console.log(`[Scene3D] ✅ 地图加载完成:`)
        console.log(`[Scene3D] - 几何中心位置: (${mapX.toFixed(3)}, ${mapY.toFixed(3)}, ${mapZ.toFixed(3)})`)
        console.log(`[Scene3D] - 原点配置: [${mapConfig.origin.join(', ')}]`)
        console.log(`[Scene3D] - 物理尺寸: ${mapWidthMeters.toFixed(2)}m × ${mapHeightMeters.toFixed(2)}m`)
        console.log(`[Scene3D] - 分辨率: ${mapConfig.resolution}m/pixel`)
        console.log(`[Scene3D] - 像素尺寸: ${width} × ${height}`)

        // 计算地图在世界坐标系中的实际覆盖范围
        const worldMinX = mapConfig.origin[0]
        const worldMinY = mapConfig.origin[1]
        const worldMaxX = mapConfig.origin[0] + width * mapConfig.resolution
        const worldMaxY = mapConfig.origin[1] + height * mapConfig.resolution
        console.log(`[Scene3D] - 世界坐标覆盖范围: X=[${worldMinX.toFixed(2)}, ${worldMaxX.toFixed(2)}], Y=[${worldMinY.toFixed(2)}, ${worldMaxY.toFixed(2)}]`)
        
        // 设置用户数据
        mesh.userData = {
          topic: 'loaded_map',
          messageType: 'loaded_map',
          filename: filename,
          config: mapConfig,
          dimensions: { width, height },
          physicalSize: { width: mapWidthMeters, height: mapHeightMeters },
          worldPosition: { x: mapX, y: mapY, z: mapZ }
        }
        
        // 添加到场景
        scene.add(mesh)
        visualizationObjects.set('loaded_map', mesh)
        
        // 自动调整相机以查看地图
        fitCameraToMap(mesh)
        
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
      onMouseMove,
      onMouseUp,
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
      setNavigationTool,
      loadMapFile,
      loadMapFiles,
      fitCameraToPointCloud,
      fitCameraToMap,
      addDebugInfo,
      checkSubscriptionStatus,
      // 位置信息处理
      updateOdometry,
      updatePoseStamped,
      updatePoseWithCovarianceStamped,
      // 清理方法
      clearAllVisualizations,
      unsubscribeAllTopics
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
  background: transparent;
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
