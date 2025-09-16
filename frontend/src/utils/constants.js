/**
 * 应用常量定义
 */

// 连接状态
export const CONNECTION_STATUS = {
  DISCONNECTED: 'disconnected',
  CONNECTING: 'connecting', 
  CONNECTED: 'connected',
  ERROR: 'error'
}

// ROS2 消息类型
export const ROS_MESSAGE_TYPES = {
  // 传感器消息
  POINT_CLOUD2: 'sensor_msgs/msg/PointCloud2',
  LASER_SCAN: 'sensor_msgs/msg/LaserScan',
  IMAGE: 'sensor_msgs/msg/Image',
  CAMERA_INFO: 'sensor_msgs/msg/CameraInfo',
  IMU: 'sensor_msgs/msg/Imu',
  
  // 几何消息
  TWIST: 'geometry_msgs/msg/Twist',
  POSE: 'geometry_msgs/msg/Pose',
  POSE_STAMPED: 'geometry_msgs/msg/PoseStamped',
  TRANSFORM: 'geometry_msgs/msg/Transform',
  TRANSFORM_STAMPED: 'geometry_msgs/msg/TransformStamped',
  
  // 可视化消息
  MARKER: 'visualization_msgs/msg/Marker',
  MARKER_ARRAY: 'visualization_msgs/msg/MarkerArray',
  
  // 导航消息
  PATH: 'nav_msgs/msg/Path',
  OCCUPANCY_GRID: 'nav_msgs/msg/OccupancyGrid',
  ODOMETRY: 'nav_msgs/msg/Odometry',
  
  // 标准消息
  STRING: 'std_msgs/msg/String',
  BOOL: 'std_msgs/msg/Bool',
  INT32: 'std_msgs/msg/Int32',
  FLOAT32: 'std_msgs/msg/Float32',
  HEADER: 'std_msgs/msg/Header'
}

// 插件类型
export const PLUGIN_TYPES = {
  RENDERER: 'renderer',
  WIDGET: 'widget', 
  TOOL: 'tool',
  FILTER: 'filter'
}

// 插件状态
export const PLUGIN_STATUS = {
  LOADED: 'loaded',
  ENABLED: 'enabled',
  DISABLED: 'disabled',
  ERROR: 'error'
}

// 日志级别
export const LOG_LEVELS = {
  DEBUG: 'DEBUG',
  INFO: 'INFO',
  WARN: 'WARN',
  ERROR: 'ERROR'
}

// 渲染设置
export const RENDER_SETTINGS = {
  QUALITY: {
    LOW: 'low',
    MEDIUM: 'medium',
    HIGH: 'high'
  },
  LOD_LEVELS: {
    LOW: 'low',
    MEDIUM: 'medium', 
    HIGH: 'high'
  }
}

// 默认配置值
export const DEFAULT_CONFIG = {
  // 连接配置
  WS_URL: 'ws://localhost:9090',
  MAX_RECONNECT_ATTEMPTS: 5,
  RECONNECT_INTERVAL: 3000,
  
  // 渲染配置
  MAX_POINT_CLOUD_POINTS: 100000,
  DEFAULT_POINT_SIZE: 1.0,
  DEFAULT_FOV: 75,
  DEFAULT_NEAR: 0.1,
  DEFAULT_FAR: 1000,
  
  // 性能配置
  TARGET_FPS: 60,
  MESSAGE_BUFFER_SIZE: 10000,
  
  // UI 配置
  SIDEBAR_WIDTH: 300,
  TOOLBAR_HEIGHT: 60
}

// 颜色主题
export const COLOR_THEMES = {
  LIGHT: {
    PRIMARY: '#409EFF',
    SUCCESS: '#67C23A',
    WARNING: '#E6A23C',
    DANGER: '#F56C6C',
    INFO: '#909399',
    BACKGROUND: '#FFFFFF',
    SURFACE: '#F5F5F5',
    TEXT_PRIMARY: '#303133',
    TEXT_SECONDARY: '#606266'
  },
  DARK: {
    PRIMARY: '#409EFF',
    SUCCESS: '#67C23A', 
    WARNING: '#E6A23C',
    DANGER: '#F56C6C',
    INFO: '#909399',
    BACKGROUND: '#1A1A1A',
    SURFACE: '#2D2D2D',
    TEXT_PRIMARY: '#E4E7ED',
    TEXT_SECONDARY: '#C0C4CC'
  }
}

// 事件类型
export const EVENT_TYPES = {
  CONNECTION_CHANGED: 'connection:changed',
  TOPIC_SUBSCRIBED: 'topic:subscribed',
  TOPIC_UNSUBSCRIBED: 'topic:unsubscribed',
  MESSAGE_RECEIVED: 'message:received',
  PLUGIN_ENABLED: 'plugin:enabled',
  PLUGIN_DISABLED: 'plugin:disabled',
  CAMERA_MOVED: 'camera:moved',
  OBJECT_SELECTED: 'object:selected'
}

// 键盘快捷键
export const KEYBOARD_SHORTCUTS = {
  RESET_CAMERA: 'KeyR',
  TOGGLE_GRID: 'KeyG', 
  TOGGLE_AXES: 'KeyA',
  TOGGLE_FULLSCREEN: 'F11',
  SAVE_SCREENSHOT: 'KeyS',
  ZOOM_IN: 'Equal',
  ZOOM_OUT: 'Minus'
}

// 文件扩展名
export const FILE_EXTENSIONS = {
  JSON: '.json',
  CSV: '.csv',
  PNG: '.png',
  JPG: '.jpg',
  BAG: '.bag'
}

// API 端点
export const API_ENDPOINTS = {
  TOPICS: '/topics',
  NODES: '/nodes',
  STATUS: '/status',
  PLUGINS: '/visualization/plugins',
  CAMERA: '/visualization/camera',
  RENDER: '/visualization/render'
}

// 错误代码
export const ERROR_CODES = {
  CONNECTION_FAILED: 'CONNECTION_FAILED',
  WEBSOCKET_ERROR: 'WEBSOCKET_ERROR',
  API_ERROR: 'API_ERROR',
  VALIDATION_ERROR: 'VALIDATION_ERROR',
  PLUGIN_ERROR: 'PLUGIN_ERROR',
  RENDER_ERROR: 'RENDER_ERROR'
}
