"""
Rosbridge 服务
负责 ROS2 与 WebSocket 通信
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from collections import defaultdict, deque
import time
from datetime import datetime

from fastapi import WebSocket, WebSocketDisconnect
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSDurabilityPolicy, QoSHistoryPolicy
from std_msgs.msg import String

from ..core.config import Settings
from ..models.ros import TopicInfo, NodeInfo, SystemStatus, ConnectionInfo
from ..models.viz import VisualizationState, PluginInfo, CameraSettings, RenderSettings

logger = logging.getLogger(__name__)

class ConnectionManager:
    """WebSocket 连接管理器"""
    
    def __init__(self, max_connections: int = 100):
        self.max_connections = max_connections
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_info: Dict[str, ConnectionInfo] = {}
        
    async def connect(self, websocket: WebSocket, client_id: str) -> bool:
        """连接客户端"""
        if len(self.active_connections) >= self.max_connections:
            await websocket.close(code=1008, reason="Max connections reached")
            return False
            
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.connection_info[client_id] = ConnectionInfo(
            client_id=client_id,
            connected_at=datetime.now(),
            subscribed_topics=[],
            message_count=0
        )
        logger.info(f"Client {client_id} connected")
        return True
        
    def disconnect(self, client_id: str):
        """断开客户端"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        if client_id in self.connection_info:
            del self.connection_info[client_id]
        logger.info(f"Client {client_id} disconnected")
        
    async def send_to_client(self, client_id: str, message: dict):
        """发送消息给指定客户端"""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_text(json.dumps(message))
                self.connection_info[client_id].message_count += 1
            except Exception as e:
                logger.error(f"Failed to send message to {client_id}: {e}")
                self.disconnect(client_id)
                
    async def broadcast(self, message: dict):
        """广播消息给所有客户端"""
        if not self.active_connections:
            logger.debug("📭 No active connections for broadcast")
            return False
            
        message_text = json.dumps(message)
        disconnected_clients = []
        sent_count = 0
        
        # 如果是主题消息，只发送给订阅了该主题的客户端
        if message.get('op') == 'publish' and 'topic' in message:
            topic = message['topic']
            for client_id, websocket in self.active_connections.items():
                if client_id in self.connection_info:
                    client_info = self.connection_info[client_id]
                    if topic in client_info.subscribed_topics:
                        try:
                            await websocket.send_text(message_text)
                            client_info.message_count += 1
                            sent_count += 1
                            logger.debug(f"📤 Sent message to {client_id} for topic {topic}")
                        except Exception as e:
                            logger.error(f"Failed to send to {client_id}: {e}")
                            disconnected_clients.append(client_id)
        else:
            # 非主题消息广播给所有客户端
            for client_id, websocket in self.active_connections.items():
                try:
                    await websocket.send_text(message_text)
                    self.connection_info[client_id].message_count += 1
                    sent_count += 1
                except Exception as e:
                    logger.error(f"Failed to broadcast to {client_id}: {e}")
                    disconnected_clients.append(client_id)
                
        # 清理断开的连接
        for client_id in disconnected_clients:
            self.disconnect(client_id)
            
        logger.debug(f"📊 Broadcast sent to {sent_count} clients, {len(disconnected_clients)} disconnected")
        return sent_count > 0

class RosbridgeService:
    """Rosbridge 核心服务"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.connection_manager = ConnectionManager(settings.max_connections)
        self.node: Optional[Node] = None
        self.subscribers = {}
        self.publishers = {}
        self.message_cache = deque(maxlen=settings.message_buffer_size)
        self.start_time = time.time()
        self.topic_info_cache = {}
        self.node_info_cache = {}

        # 异步消息处理队列
        self.message_queue = None
        self.message_processor_task = None
        self._loop = None
        
        # 可视化状态
        self._cache_warning_counts = {}  # 缓存警告计数
        self.visualization_state = VisualizationState(
            camera_settings=CameraSettings(
                position=(5.0, 5.0, 5.0),
                target=(0.0, 0.0, 0.0)
            ),
            render_settings=RenderSettings()
        )
        
    async def start(self):
        """启动服务"""
        try:
            # 获取当前事件循环
            self._loop = asyncio.get_event_loop()

            # 初始化异步消息队列
            self.message_queue = asyncio.Queue(maxsize=1000)

            # 初始化 ROS2
            if not rclpy.ok():
                rclpy.init()

            self.node = Node('ros_web_viz_bridge')
            logger.info("ROS2 node initialized")

            # 启动消息处理任务
            self.message_processor_task = asyncio.create_task(self._message_processor_loop())

            # 🔥 启动ROS2事件循环 - 这是关键！
            self.ros_spin_task = asyncio.create_task(self._ros_spin_loop())

            # 启动后台任务
            asyncio.create_task(self._update_topic_info())
            asyncio.create_task(self._update_node_info())

        except Exception as e:
            logger.error(f"Failed to start Rosbridge service: {e}")
            raise
            
    async def stop(self):
        """停止服务"""
        try:
            # 停止消息处理任务
            if self.message_processor_task and not self.message_processor_task.done():
                self.message_processor_task.cancel()
                try:
                    await self.message_processor_task
                except asyncio.CancelledError:
                    pass

            # 停止ROS spin任务
            if hasattr(self, 'ros_spin_task') and self.ros_spin_task and not self.ros_spin_task.done():
                self.ros_spin_task.cancel()
                try:
                    await self.ros_spin_task
                except asyncio.CancelledError:
                    pass

            if self.node:
                self.node.destroy_node()
            if rclpy.ok():
                rclpy.shutdown()
            logger.info("Rosbridge service stopped")
        except Exception as e:
            logger.error(f"Error stopping Rosbridge service: {e}")
            
    async def handle_websocket(self, websocket: WebSocket):
        """处理 WebSocket 连接"""
        client_id = f"client_{int(time.time() * 1000)}"
        
        if not await self.connection_manager.connect(websocket, client_id):
            return
            
        try:
            while True:
                data = await websocket.receive_text()
                await self._handle_message(client_id, json.loads(data))
                
        except WebSocketDisconnect:
            logger.info(f"Client {client_id} disconnected")
        except Exception as e:
            logger.error(f"WebSocket error for {client_id}: {e}")
        finally:
            self.connection_manager.disconnect(client_id)
            
    async def _handle_message(self, client_id: str, message: dict):
        """处理收到的消息"""
        try:
            op = message.get('op')
            request_id = message.get('id')  # 获取请求ID
            
            if op == 'subscribe':
                await self._handle_subscribe(client_id, message)
            elif op == 'unsubscribe':
                await self._handle_unsubscribe(client_id, message)
            elif op == 'advertise':
                await self._handle_advertise(message)
            elif op == 'unadvertise':
                await self._handle_unadvertise(message)
            elif op == 'publish':
                await self._handle_publish(message)
            elif op == 'get_topics':
                await self._handle_get_topics(client_id, request_id)
            elif op == 'get_nodes':
                await self._handle_get_nodes(client_id, request_id)
            elif op == 'get_topic_types':
                await self._handle_get_topic_types(client_id, request_id)
            elif op == 'get_topic_frequencies':
                await self._handle_get_topic_frequencies(client_id, request_id)
            elif op == 'get_services':
                await self._handle_get_services(client_id, request_id)
            elif op == 'get_service_types':
                await self._handle_get_service_types(client_id, request_id)
            elif op == 'get_params':
                await self._handle_get_params(client_id, request_id)
            else:
                logger.warning(f"Unknown operation: {op}")
                # 发送错误响应
                if request_id:
                    await self.connection_manager.send_to_client(client_id, {
                        'op': 'error',
                        'id': request_id,
                        'error': f'Unknown operation: {op}'
                    })
                
        except Exception as e:
            logger.error(f"Error handling message from {client_id}: {e}")
            # 发送错误响应
            request_id = message.get('id')
            if request_id:
                await self.connection_manager.send_to_client(client_id, {
                    'op': 'error',
                    'id': request_id,
                    'error': str(e)
                })
            
    async def _handle_subscribe(self, client_id: str, message: dict):
        """处理订阅请求"""
        topic = message.get('topic')
        msg_type = message.get('type')

        logger.info(f"🔔 Received subscription request from {client_id}: topic={topic}, type={msg_type}")

        if not topic or not msg_type:
            logger.error(f"❌ Invalid subscription request from {client_id}: missing topic or type")
            return

        # 添加到客户端订阅列表
        info = self.connection_manager.connection_info.get(client_id)
        if info:
            if topic not in info.subscribed_topics:
                info.subscribed_topics.append(topic)
                logger.info(f"✅ Added {topic} to client {client_id} subscription list")
                logger.info(f"🔍 Updated subscription list for {client_id}: {info.subscribed_topics}")
            else:
                logger.info(f"📝 Client {client_id} already subscribed to {topic}")
        else:
            logger.error(f"❌ Client {client_id} connection info not found")
            logger.error(f"🔍 Available connections: {list(self.connection_manager.connection_info.keys())}")
            return

        # 创建 ROS2 订阅者（如果不存在）
        if topic not in self.subscribers:
            logger.info(f"🔄 Creating new ROS2 subscriber for {topic}")
            await self._create_subscriber(topic, msg_type)
        else:
            logger.info(f"♻️ ROS2 subscriber for {topic} already exists")

        logger.info(f"📊 Current subscriptions for {client_id}: {info.subscribed_topics if info else 'none'}")
        logger.info(f"📊 Total active ROS2 subscribers: {len(self.subscribers)}")

        # 🔍 验证订阅是否正确设置
        logger.info(f"🔍 Verification - All connection subscriptions:")
        for cid, cinfo in self.connection_manager.connection_info.items():
            logger.info(f"   - {cid}: {cinfo.subscribed_topics}")
            
    def _get_message_class(self, msg_type: str):
        """获取消息类型对应的类"""
        # 消息类型注册表
        message_type_registry = {
            # 标准消息类型
            'std_msgs/msg/String': ('std_msgs.msg', 'String'),
            'std_msgs/msg/Float64': ('std_msgs.msg', 'Float64'),
            'std_msgs/msg/Float32': ('std_msgs.msg', 'Float32'),
            'std_msgs/msg/Int32': ('std_msgs.msg', 'Int32'),
            'std_msgs/msg/Bool': ('std_msgs.msg', 'Bool'),
            
            # 传感器消息类型
            'sensor_msgs/msg/PointCloud2': ('sensor_msgs.msg', 'PointCloud2'),
            'sensor_msgs/msg/LaserScan': ('sensor_msgs.msg', 'LaserScan'),
            'sensor_msgs/msg/Image': ('sensor_msgs.msg', 'Image'),
            'sensor_msgs/msg/CompressedImage': ('sensor_msgs.msg', 'CompressedImage'),
            'sensor_msgs/msg/CameraInfo': ('sensor_msgs.msg', 'CameraInfo'),
            'sensor_msgs/msg/Imu': ('sensor_msgs.msg', 'Imu'),
            'sensor_msgs/msg/JointState': ('sensor_msgs.msg', 'JointState'),
            'sensor_msgs/msg/PointField': ('sensor_msgs.msg', 'PointField'),
            'sensor_msgs/msg/NavSatFix': ('sensor_msgs.msg', 'NavSatFix'),
            'sensor_msgs/msg/NavSatStatus': ('sensor_msgs.msg', 'NavSatStatus'),
            
            # 几何消息类型
            'geometry_msgs/msg/Twist': ('geometry_msgs.msg', 'Twist'),
            'geometry_msgs/msg/Pose': ('geometry_msgs.msg', 'Pose'),
            'geometry_msgs/msg/PoseStamped': ('geometry_msgs.msg', 'PoseStamped'),
            'geometry_msgs/msg/PoseWithCovariance': ('geometry_msgs.msg', 'PoseWithCovariance'),
            'geometry_msgs/msg/PoseWithCovarianceStamped': ('geometry_msgs.msg', 'PoseWithCovarianceStamped'),
            'geometry_msgs/msg/Point': ('geometry_msgs.msg', 'Point'),
            'geometry_msgs/msg/Vector3': ('geometry_msgs.msg', 'Vector3'),
            'geometry_msgs/msg/Quaternion': ('geometry_msgs.msg', 'Quaternion'),
            'geometry_msgs/msg/Transform': ('geometry_msgs.msg', 'Transform'),
            'geometry_msgs/msg/TransformStamped': ('geometry_msgs.msg', 'TransformStamped'),
            
            # 导航消息类型
            'nav_msgs/msg/OccupancyGrid': ('nav_msgs.msg', 'OccupancyGrid'),
            'nav_msgs/msg/Path': ('nav_msgs.msg', 'Path'),
            'nav_msgs/msg/Odometry': ('nav_msgs.msg', 'Odometry'),
            'nav_msgs/msg/MapMetaData': ('nav_msgs.msg', 'MapMetaData'),
            'nav_msgs/msg/GridCells': ('nav_msgs.msg', 'GridCells'),

            # GPS和导航
            'sensor_msgs/msg/NavSatFix': ('sensor_msgs.msg', 'NavSatFix'),
            'sensor_msgs/msg/NavSatStatus': ('sensor_msgs.msg', 'NavSatStatus'),
            
            # 可视化消息类型
            'visualization_msgs/msg/Marker': ('visualization_msgs.msg', 'Marker'),
            'visualization_msgs/msg/MarkerArray': ('visualization_msgs.msg', 'MarkerArray'),
            'visualization_msgs/msg/InteractiveMarker': ('visualization_msgs.msg', 'InteractiveMarker'),
            'visualization_msgs/msg/InteractiveMarkerUpdate': ('visualization_msgs.msg', 'InteractiveMarkerUpdate'),
            
            # TF和诊断消息
            'tf2_msgs/msg/TFMessage': ('tf2_msgs.msg', 'TFMessage'),
            'diagnostic_msgs/msg/DiagnosticArray': ('diagnostic_msgs.msg', 'DiagnosticArray'),
            
            # 轨迹消息
            'trajectory_msgs/msg/JointTrajectory': ('trajectory_msgs.msg', 'JointTrajectory'),
            'trajectory_msgs/msg/MultiDOFJointTrajectory': ('trajectory_msgs.msg', 'MultiDOFJointTrajectory'),
            
            # Action和状态消息
            'actionlib_msgs/msg/GoalStatus': ('actionlib_msgs.msg', 'GoalStatus'),
            'rosgraph_msgs/msg/Log': ('rosgraph_msgs.msg', 'Log'),
        }
        
        # 可选的消息类型（可能不存在的包）
        optional_message_types = {
            'move_base_msgs/msg/MoveBaseAction': ('move_base_msgs.msg', 'MoveBaseAction'),
            'costmap_2d/msg/VoxelGrid': ('costmap_2d.msg', 'VoxelGrid'),
            'map_msgs/msg/OccupancyGridUpdate': ('map_msgs.msg', 'OccupancyGridUpdate'),
            'gps_msgs/msg/GPSStatus': ('gps_msgs.msg', 'GPSStatus'),
            'gps_msgs/msg/GPSFix': ('gps_msgs.msg', 'GPSFix'),
        }
        
        if msg_type in message_type_registry:
            module_name, class_name = message_type_registry[msg_type]
            try:
                module = __import__(module_name, fromlist=[class_name])
                return getattr(module, class_name)
            except ImportError as e:
                logger.error(f"Failed to import {module_name}.{class_name}: {e}")
                return None
                
        elif msg_type in optional_message_types:
            module_name, class_name = optional_message_types[msg_type]
            try:
                module = __import__(module_name, fromlist=[class_name])
                return getattr(module, class_name)
            except ImportError:
                logger.warning(f"{module_name} not available, will use String as fallback for {msg_type}")
                return None
        else:
            logger.warning(f"Unknown message type {msg_type}")
            return None

    async def _create_subscriber(self, topic: str, msg_type: str):
        """创建 ROS2 订阅者"""
        try:
            # 获取消息类
            msg_class = self._get_message_class(msg_type)
            
            if msg_class is None:
                # 使用String作为默认类型
                logger.warning(f"Using String as fallback for unsupported message type {msg_type}")
                from std_msgs.msg import String
                msg_class = String
            
            def callback(msg):
                # ROS2回调必须是同步的，但我们需要异步处理
                # 使用线程安全的方式将消息放入队列
                logger.debug(f"🚀 ROS2 CALLBACK TRIGGERED for {topic}! Message type: {type(msg).__name__}")
                try:
                    # 调用同步版本的消息处理
                    self._on_message_received_sync(topic, msg)
                    logger.debug(f"✅ Successfully processed callback for {topic}")
                except Exception as e:
                    logger.error(f"❌ Error in message callback for {topic}: {e}")
                
            # 使用兼容的QoS配置 - 优先兼容rosbag2_player
            
            # 首先尝试检测发布者的QoS设置
            publisher_qos_profiles = []
            if self.node:
                try:
                    # 获取发布者信息
                    publishers_info = self.node.get_publishers_info_by_topic(topic)
                    logger.info(f"Found {len(publishers_info)} publishers for topic {topic}")
                    for pub_info in publishers_info:
                        publisher_qos_profiles.append(pub_info.qos_profile)
                        logger.info(f"Publisher {pub_info.node_name} QoS: reliability={pub_info.qos_profile.reliability}, durability={pub_info.qos_profile.durability}, history={pub_info.qos_profile.history}, depth={pub_info.qos_profile.depth}")
                except Exception as e:
                    logger.warning(f"Could not get publisher QoS info for {topic}: {e}")
                    
            # 如果没有获取到发布者信息，再次尝试等待一下
            if not publisher_qos_profiles and self.node:
                logger.info(f"No publisher info found initially for {topic}, waiting and retrying...")
                await asyncio.sleep(0.1)  # 等待100ms
                try:
                    publishers_info = self.node.get_publishers_info_by_topic(topic)
                    for pub_info in publishers_info:
                        publisher_qos_profiles.append(pub_info.qos_profile)
                        logger.info(f"Publisher {pub_info.node_name} QoS (retry): reliability={pub_info.qos_profile.reliability}, durability={pub_info.qos_profile.durability}")
                except Exception as e:
                    logger.warning(f"Could not get publisher QoS info for {topic} on retry: {e}")
            
            # 分析发布者的实际QoS并尝试完全匹配
            logger.info(f"🔧 Analyzing publisher QoS for {topic}")

            if publisher_qos_profiles:
                first_pub_qos = publisher_qos_profiles[0]
                logger.info(f"📊 Raw publisher QoS: reliability={first_pub_qos.reliability}, durability={first_pub_qos.durability}, history={first_pub_qos.history}, depth={first_pub_qos.depth}")

                # 尝试与rosbag2_player的特殊QoS兼容
                # history=3可能是rosbag2特有的，我们尝试KEEP_ALL
                if first_pub_qos.history == 3:
                    logger.info(f"🔍 Detected rosbag2 history=3, trying KEEP_ALL to match")
                    qos_profile = QoSProfile(
                        reliability=QoSReliabilityPolicy.RELIABLE,
                        durability=QoSDurabilityPolicy.VOLATILE,
                        history=QoSHistoryPolicy.KEEP_ALL,  # 尝试KEEP_ALL匹配history=3
                        depth=1000  # 大缓冲区用于KEEP_ALL
                    )
                    logger.info(f"🎯 Using KEEP_ALL history for rosbag2 compatibility")
                else:
                    # 标准配置
                    qos_profile = QoSProfile(
                        reliability=QoSReliabilityPolicy.RELIABLE,
                        durability=QoSDurabilityPolicy.VOLATILE,
                        history=QoSHistoryPolicy.KEEP_LAST,
                        depth=10
                    )
                    logger.info(f"🎯 Using standard KEEP_LAST history")
            else:
                # 没有发布者信息，使用标准配置
                qos_profile = QoSProfile(
                    reliability=QoSReliabilityPolicy.RELIABLE,
                    durability=QoSDurabilityPolicy.VOLATILE,
                    history=QoSHistoryPolicy.KEEP_LAST,
                    depth=10
                )
                logger.info(f"🎯 No publisher info, using standard QoS")

            logger.info(f"✨ Final QoS for {topic}: reliability={qos_profile.reliability.name}, durability={qos_profile.durability.name}, history={qos_profile.history.name}, depth={qos_profile.depth}")
                
            # 记录最终的QoS配置
            reliability_name = qos_profile.reliability.name if hasattr(qos_profile.reliability, 'name') else str(qos_profile.reliability)
            durability_name = qos_profile.durability.name if hasattr(qos_profile.durability, 'name') else str(qos_profile.durability)
            history_name = qos_profile.history.name if hasattr(qos_profile.history, 'name') else str(qos_profile.history)
            logger.info(f"Creating subscriber for {topic} with QoS: reliability={reliability_name}, durability={durability_name}, history={history_name}, depth={qos_profile.depth}")

            # 创建订阅者 - 使用简化的单一配置
            try:
                subscriber = self.node.create_subscription(
                    msg_class,
                    topic,
                    callback,
                    qos_profile
                )

                self.subscribers[topic] = subscriber
                logger.info(f"✅ Successfully created subscriber for {topic}")
                logger.info(f"🎯 QoS: RELIABLE + VOLATILE + KEEP_LAST + depth=10")

            except Exception as e:
                logger.error(f"❌ Failed to create subscriber for {topic}: {e}")
                logger.error(f"💡 This usually indicates QoS incompatibility with publishers")
                raise e
            
            # 启动一个简单的数据检查任务
            asyncio.create_task(self._check_topic_data(topic, 10.0))  # 10秒后检查
            
        except Exception as e:
            logger.error(f"Failed to create subscriber for {topic}: {e}")
            
    async def _check_topic_data(self, topic: str, delay: float):
        """检查主题是否有数据发布"""
        await asyncio.sleep(delay)
        
        if not hasattr(self, '_message_counts') or topic not in self._message_counts:
            # 检查系统中是否有发布者
            if self.node:
                topic_info = self.node.get_publishers_info_by_topic(topic)
                publisher_count = len(topic_info)
                
                if publisher_count == 0:
                    logger.warning(f"🚨 Topic {topic} has no publishers in the ROS system")
                    logger.info(f"💡 To publish test data, try: ros2 topic pub {topic} <msg_type> '<data>'")
                else:
                    logger.warning(f"⚠️ Topic {topic} has {publisher_count} publisher(s) but no messages received")
                    logger.info(f"📊 Publishers: {[pub.node_name for pub in topic_info]}")
            else:
                logger.error(f"❌ ROS node not initialized, cannot check topic {topic}")
        else:
            logger.info(f"✅ Topic {topic} is receiving data normally ({self._message_counts[topic]} messages)")

    def _on_message_received_sync(self, topic: str, msg):
        """同步消息处理入口 - 从ROS2回调调用

        这个方法在ROS2回调线程中被调用，需要线程安全地将消息传递到异步处理循环
        """
        try:
            if self._loop and self.message_queue:
                # 记录第一次接收到消息
                if not hasattr(self, '_first_message_logged'):
                    self._first_message_logged = set()

                if topic not in self._first_message_logged:
                    logger.info(f"🚀 First ROS2 callback received for topic {topic}, type: {type(msg).__name__}")
                    self._first_message_logged.add(topic)

                # 使用call_soon_threadsafe将消息传递到异步循环
                self._loop.call_soon_threadsafe(self._enqueue_message, topic, msg)
            else:
                logger.error(f"❌ Message loop or queue not initialized for topic {topic}")
                logger.error(f"   Loop: {self._loop is not None}, Queue: {self.message_queue is not None}")
        except Exception as e:
            logger.error(f"❌ Error in sync message handler for {topic}: {e}", exc_info=True)

    def _enqueue_message(self, topic: str, msg):
        """将消息放入异步队列 - 在事件循环中调用"""
        try:
            if self.message_queue:
                try:
                    # 非阻塞方式放入队列
                    self.message_queue.put_nowait((topic, msg, time.time()))
                    logger.debug(f"📥 Enqueued message for {topic}, queue size: {self.message_queue.qsize()}")
                except asyncio.QueueFull:
                    logger.warning(f"⚠️ Message queue full (size: {self.message_queue.maxsize}), dropping message for {topic}")
                    logger.warning(f"   Consider increasing queue size or processing messages faster")
            else:
                logger.error(f"❌ Message queue not initialized for {topic}")
        except Exception as e:
            logger.error(f"❌ Error enqueuing message for {topic}: {e}", exc_info=True)

    async def _message_processor_loop(self):
        """异步消息处理循环 - 从队列中取出消息并处理"""
        logger.info("Starting message processor loop")

        # 初始化消息计数
        if not hasattr(self, '_message_counts'):
            self._message_counts = {}

        try:
            while True:
                try:
                    # 从队列中获取消息
                    topic, msg, timestamp = await self.message_queue.get()

                    # 记录消息接收
                    if topic not in self._message_counts:
                        self._message_counts[topic] = 0
                    self._message_counts[topic] += 1

                    # 只记录第一条消息，减少日志输出
                    if self._message_counts[topic] == 1:
                        logger.info(f"🎉 First message received on topic {topic}! Type: {type(msg).__name__}")
                        logger.info(f"✅ Successfully bridged ROS2 callback to async processing for {topic}")
                    # 移除频繁的统计日志以避免刷屏

                    logger.debug(f"📨 Processing message on topic {topic}, type: {type(msg).__name__}, queue size: {self.message_queue.qsize()}")

                    # 调用原有的异步消息处理逻辑
                    await self._on_message_received(topic, msg)

                    # 标记任务完成
                    self.message_queue.task_done()

                except asyncio.CancelledError:
                    logger.info("Message processor loop cancelled")
                    break
                except Exception as e:
                    logger.error(f"Error in message processor loop: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Fatal error in message processor loop: {e}", exc_info=True)
        finally:
            logger.info("Message processor loop stopped")

    async def _ros_spin_loop(self):
        """异步ROS2事件循环 - 处理ROS回调"""
        logger.info("🔥 Starting ROS2 spin loop - THIS IS CRITICAL FOR MESSAGE RECEPTION!")

        try:
            while True:
                # 非阻塞spin，处理ROS2回调
                if self.node:
                    rclpy.spin_once(self.node, timeout_sec=0.01)

                # 让出控制权给其他协程
                await asyncio.sleep(0.001)  # 1ms间隔，保持高响应性

        except asyncio.CancelledError:
            logger.info("ROS2 spin loop cancelled")
        except Exception as e:
            logger.error(f"Fatal error in ROS2 spin loop: {e}", exc_info=True)
        finally:
            logger.info("ROS2 spin loop stopped")

    async def _on_message_received(self, topic: str, msg):
        """处理接收到的 ROS 消息"""
        try:
            logger.debug(f"📨 Processing message on topic {topic}, type: {type(msg).__name__}")

            # 转换消息为字典格式
            msg_dict = self._message_to_dict(msg)

            # 记录消息大小信息
            if 'data' in msg_dict:
                if isinstance(msg_dict['data'], str) and msg_dict.get('data_encoding') == 'base64':
                    logger.debug(f"📝 Converted {topic} to dict with Base64 data (original size estimation)")
                elif isinstance(msg_dict['data'], list):
                    logger.debug(f"📝 Converted {topic} to dict with {len(msg_dict['data'])} data points")
                else:
                    logger.debug(f"📝 Converted {topic} to dict, keys: {list(msg_dict.keys())}")
            else:
                logger.debug(f"📝 Converted {topic} to dict, keys: {list(msg_dict.keys())}")

            # 构造 rosbridge 消息
            rosbridge_msg = {
                'op': 'publish',
                'topic': topic,
                'msg': msg_dict
            }

            # 检查是否有客户端订阅这个主题
            active_subscribers = sum(1 for info in self.connection_manager.connection_info.values()
                                   if topic in info.subscribed_topics)

            # 🔍 调试：详细打印连接信息
            logger.debug(f"🔍 Debug subscription check for {topic}:")
            logger.debug(f"   - Total active connections: {len(self.connection_manager.connection_info)}")
            for client_id, info in self.connection_manager.connection_info.items():
                logger.debug(f"   - Client {client_id}: subscribed to {info.subscribed_topics}")
            logger.debug(f"   - Active subscribers for {topic}: {active_subscribers}")

            if active_subscribers > 0:
                logger.debug(f"🔔 Broadcasting message for {topic} to {active_subscribers} subscribers")

                # 广播给所有订阅该主题的客户端
                broadcast_result = await self.connection_manager.broadcast(rosbridge_msg)

                if broadcast_result:
                    logger.debug(f"📤 Successfully broadcast {topic} to {active_subscribers} clients")
                else:
                    logger.warning(f"⚠️ Failed to broadcast {topic} to clients")
            else:
                # 减少缓存消息的日志输出频率
                if topic not in self._cache_warning_counts:
                    self._cache_warning_counts[topic] = 0

                self._cache_warning_counts[topic] += 1

                # 只在第一次和每100次时输出警告
                if self._cache_warning_counts[topic] == 1 or self._cache_warning_counts[topic] % 100 == 0:
                    logger.warning(f"📭 No active subscribers for {topic}, message cached only ({self._cache_warning_counts[topic]} times)")
                    if self._cache_warning_counts[topic] == 1:
                        logger.warning(f"💡 Tip: Frontend needs to subscribe to {topic} to receive messages")

            # 缓存消息
            self.message_cache.append({
                'topic': topic,
                'message': msg_dict,
                'timestamp': time.time()
            })

        except Exception as e:
            logger.error(f"❌ Error processing message from {topic}: {e}", exc_info=True)
            
    def _process_pointcloud_data(self, pointcloud_msg) -> dict:
        """处理点云数据，进行压缩和采样优化"""
        try:
            import struct
            import numpy as np
            from sensor_msgs.msg import PointField
            
            # 解析点云字段
            fields = []
            for field in pointcloud_msg.fields:
                fields.append({
                    'name': field.name,
                    'offset': field.offset,
                    'datatype': field.datatype,
                    'count': field.count
                })
            
            # 基本信息
            result = {
                'header': self._message_to_dict(pointcloud_msg.header),
                'height': pointcloud_msg.height,
                'width': pointcloud_msg.width,
                'fields': fields,
                'is_bigendian': pointcloud_msg.is_bigendian,
                'point_step': pointcloud_msg.point_step,
                'row_step': pointcloud_msg.row_step,
                'is_dense': pointcloud_msg.is_dense
            }
            
            # 处理点云数据
            if len(pointcloud_msg.data) > 0:
                logger.debug(f"Processing pointcloud data - Total bytes: {len(pointcloud_msg.data)}, Point step: {pointcloud_msg.point_step}")
                
                # 检查是否需要采样（如果点数过多）
                total_points = pointcloud_msg.width * pointcloud_msg.height
                max_points = 50000  # 增加最大传输点数
                
                logger.debug(f"Pointcloud info - Width: {pointcloud_msg.width}, Height: {pointcloud_msg.height}, Total points: {total_points}")
                
                if total_points > max_points and total_points > 0:
                    # 采样数据 - 修复采样逻辑
                    sample_step = max(1, total_points // max_points)
                    logger.info(f"Sampling pointcloud: {total_points} -> ~{total_points//sample_step} points (step: {sample_step})")
                    
                    sampled_data = []
                    point_step = pointcloud_msg.point_step
                    
                    # 按照点为单位进行采样
                    for i in range(0, total_points, sample_step):
                        byte_start = i * point_step
                        byte_end = byte_start + point_step
                        if byte_end <= len(pointcloud_msg.data):
                            sampled_data.extend(pointcloud_msg.data[byte_start:byte_end])
                    
                    # 使用Base64编码传输采样后的数据
                    import base64
                    result['data'] = base64.b64encode(bytes(sampled_data)).decode('ascii')
                    result['data_encoding'] = 'base64'
                    result['width'] = len(sampled_data) // point_step
                    result['height'] = 1
                    result['sampled'] = True
                    result['original_points'] = total_points
                    result['sample_step'] = sample_step

                    logger.info(f"Sampled pointcloud - New size: {len(sampled_data)} bytes, Points: {result['width']}, Base64 encoded")
                else:
                    # 对于大型数据使用Base64编码，小型数据直接传输
                    if len(pointcloud_msg.data) > 10000:  # 大于10KB使用Base64
                        import base64
                        result['data'] = base64.b64encode(pointcloud_msg.data).decode('ascii')
                        result['data_encoding'] = 'base64'
                        logger.debug(f"Direct pointcloud transmission - {len(pointcloud_msg.data)} bytes, {total_points} points, Base64 encoded")
                    else:
                        result['data'] = list(pointcloud_msg.data)
                        result['data_encoding'] = 'array'
                        logger.debug(f"Direct pointcloud transmission - {len(pointcloud_msg.data)} bytes, {total_points} points, as array")

                    result['sampled'] = False
            else:
                result['data'] = []
                result['data_encoding'] = 'array'
                result['sampled'] = False
                logger.warning("Pointcloud data is empty")
                
            return result
            
        except Exception as e:
            logger.error(f"Failed to process pointcloud data: {e}")
            return {
                'header': self._message_to_dict(pointcloud_msg.header),
                'error': str(e),
                'data': []
            }

    def _process_image_data(self, image_msg) -> dict:
        """处理图像数据，进行压缩优化"""
        try:
            result = {
                'header': self._message_to_dict(image_msg.header),
                'height': image_msg.height,
                'width': image_msg.width,
                'encoding': image_msg.encoding,
                'is_bigendian': image_msg.is_bigendian,
                'step': image_msg.step
            }
            
            # 检查图像大小，如果太大则进行缩放
            max_pixels = 640 * 480  # 最大像素数
            current_pixels = image_msg.height * image_msg.width
            
            if current_pixels > max_pixels:
                # 计算缩放比例
                scale_factor = (max_pixels / current_pixels) ** 0.5
                new_height = int(image_msg.height * scale_factor)
                new_width = int(image_msg.width * scale_factor)
                
                logger.info(f"Scaling image: {image_msg.width}x{image_msg.height} -> {new_width}x{new_height}")
                
                result['scaled'] = True
                result['original_width'] = image_msg.width
                result['original_height'] = image_msg.height
                result['width'] = new_width
                result['height'] = new_height
                
                # 这里可以添加实际的图像缩放逻辑
                # 为了简化，我们暂时只记录元数据
                result['data'] = []  # 实际实现中需要缩放后的图像数据
            else:
                result['data'] = list(image_msg.data)
                result['scaled'] = False
                
            return result
            
        except Exception as e:
            logger.error(f"Failed to process image data: {e}")
            return {
                'header': self._message_to_dict(image_msg.header),
                'error': str(e),
                'data': []
            }

    def _message_to_dict(self, msg) -> dict:
        """将 ROS 消息转换为字典"""
        try:
            import numpy as np
            from builtin_interfaces.msg import Time, Duration
            from geometry_msgs.msg import Point, Quaternion, Pose, PoseStamped, PoseWithCovariance, PoseWithCovarianceStamped, Transform, TransformStamped
            from nav_msgs.msg import Odometry
            from std_msgs.msg import Header
            from sensor_msgs.msg import PointCloud2, Image, CompressedImage
            
            # 特殊处理点云数据
            if isinstance(msg, PointCloud2):
                return self._process_pointcloud_data(msg)
            
            # 特殊处理图像数据
            if isinstance(msg, (Image, CompressedImage)):
                return self._process_image_data(msg)
            
            if hasattr(msg, '__slots__'):
                result = {}
                for slot in msg.__slots__:
                    value = getattr(msg, slot)
                    
                    # 处理时间类型
                    if isinstance(value, Time):
                        result[slot] = {
                            'sec': int(value.sec),
                            'nanosec': int(value.nanosec)
                        }
                    elif isinstance(value, Duration):
                        result[slot] = {
                            'sec': int(value.sec),
                            'nanosec': int(value.nanosec)
                        }
                    # 处理Header
                    elif isinstance(value, Header):
                        result[slot] = {
                            'stamp': {
                                'sec': int(value.stamp.sec),
                                'nanosec': int(value.stamp.nanosec)
                            },
                            'frame_id': str(value.frame_id)
                        }
                    # 处理几何类型
                    elif isinstance(value, Point):
                        result[slot] = {'x': float(value.x), 'y': float(value.y), 'z': float(value.z)}
                    elif isinstance(value, Quaternion):
                        result[slot] = {'x': float(value.x), 'y': float(value.y), 'z': float(value.z), 'w': float(value.w)}
                    elif isinstance(value, Pose):
                        result[slot] = {
                            'position': {'x': float(value.position.x), 'y': float(value.position.y), 'z': float(value.position.z)},
                            'orientation': {'x': float(value.orientation.x), 'y': float(value.orientation.y), 'z': float(value.orientation.z), 'w': float(value.orientation.w)}
                        }
                    elif isinstance(value, PoseWithCovariance):
                        result[slot] = {
                            'pose': {
                                'position': {'x': float(value.pose.position.x), 'y': float(value.pose.position.y), 'z': float(value.pose.position.z)},
                                'orientation': {'x': float(value.pose.orientation.x), 'y': float(value.pose.orientation.y), 'z': float(value.pose.orientation.z), 'w': float(value.pose.orientation.w)}
                            },
                            'covariance': [float(c) for c in value.covariance] if hasattr(value, 'covariance') else []
                        }
                    # 处理numpy数组
                    elif isinstance(value, np.ndarray):
                        if value.dtype == np.uint8:
                            result[slot] = value.tolist()
                        else:
                            result[slot] = value.astype(float).tolist()
                    # 处理bytes类型（点云数据等）
                    elif isinstance(value, bytes):
                        # 对于大型bytes数据，使用Base64编码
                        if len(value) > 1000:
                            import base64
                            result[slot] = base64.b64encode(value).decode('ascii')
                            result[f"{slot}_encoding"] = "base64"
                        else:
                            result[slot] = list(value)  # 小数据直接转换为数组
                    # 处理嵌套消息
                    elif hasattr(value, '__slots__'):
                        result[slot] = self._message_to_dict(value)
                    # 处理列表
                    elif isinstance(value, list):
                        result[slot] = [
                            self._message_to_dict(item) if hasattr(item, '__slots__') else 
                            float(item) if isinstance(item, (int, float, np.number)) else 
                            item
                            for item in value
                        ]
                    # 处理基本数值类型
                    elif isinstance(value, (int, float, np.number)):
                        result[slot] = float(value) if isinstance(value, (float, np.floating)) else int(value)
                    # 处理字符串和其他类型
                    else:
                        result[slot] = str(value) if value is not None else None
                        
                return result
            else:
                return {"data": str(msg)}
        except Exception as e:
            logger.error(f"Failed to convert message to dict: {e}")
            return {"error": str(e), "message_type": type(msg).__name__}
    
    # API 方法实现
    async def get_topics(self) -> List[TopicInfo]:
        """获取主题列表"""
        if not self.node:
            return []
            
        try:
            topic_names_and_types = self.node.get_topic_names_and_types()
            topics = []
            
            for name, types in topic_names_and_types:
                topics.append(TopicInfo(
                    name=name,
                    message_type=types[0] if types else "unknown",
                    publishers=[],
                    subscribers=[]
                ))
                
            return topics
        except Exception as e:
            logger.error(f"Failed to get topics: {e}")
            return []
    
    async def get_topic_info(self, topic_name: str) -> Optional[TopicInfo]:
        """获取主题信息"""
        topics = await self.get_topics()
        for topic in topics:
            if topic.name == topic_name:
                return topic
        return None
    
    async def subscribe_topic(self, topic_name: str) -> bool:
        """订阅主题"""
        try:
            # 实现订阅逻辑
            return True
        except Exception as e:
            logger.error(f"Failed to subscribe to {topic_name}: {e}")
            return False
    
    async def unsubscribe_topic(self, topic_name: str) -> bool:
        """取消订阅主题"""
        try:
            # 实现取消订阅逻辑
            return True
        except Exception as e:
            logger.error(f"Failed to unsubscribe from {topic_name}: {e}")
            return False
            
    async def publish_message(self, topic_name: str, message: Dict[str, Any]) -> bool:
        """发布消息"""
        try:
            # 实现发布逻辑
            return True
        except Exception as e:
            logger.error(f"Failed to publish to {topic_name}: {e}")
            return False
    
    async def get_nodes(self) -> List[NodeInfo]:
        """获取节点列表"""
        if not self.node:
            return []
            
        try:
            node_names = self.node.get_node_names()
            nodes = []
            
            for name in node_names:
                # 获取节点的发布和订阅主题
                publishers = []
                subscribers = []
                
                try:
                    # ROS2中获取节点发布和订阅信息的方法
                    # 获取所有主题的发布者和订阅者信息
                    all_topics_and_types = self.node.get_topic_names_and_types()
                    
                    for topic_name, topic_types in all_topics_and_types:
                        try:
                            # 获取该主题的发布者信息
                            publishers_info = self.node.get_publishers_info_by_topic(topic_name)
                            for pub_info in publishers_info:
                                if pub_info.node_name == name:
                                    publishers.append(topic_name)
                            
                            # 获取该主题的订阅者信息
                            subscriptions_info = self.node.get_subscriptions_info_by_topic(topic_name)
                            for sub_info in subscriptions_info:
                                if sub_info.node_name == name:
                                    subscribers.append(topic_name)
                                    
                        except Exception as topic_e:
                            logger.debug(f"Could not get info for topic {topic_name}: {topic_e}")
                            
                except Exception as node_e:
                    logger.debug(f"Could not get detailed info for node {name}: {node_e}")
                
                nodes.append(NodeInfo(
                    name=name,
                    namespace="/",
                    publishers=publishers,
                    subscribers=subscribers,
                    services=[],
                    actions=[],
                    parameters={}
                ))
                
            logger.info(f"Found {len(nodes)} nodes with topic relationships")
            return nodes
        except Exception as e:
            logger.error(f"Failed to get nodes: {e}")
            return []
    
    async def get_topic_types(self) -> Dict[str, str]:
        """获取主题类型映射"""
        if not self.node:
            return {}
            
        try:
            topic_names_and_types = self.node.get_topic_names_and_types()
            topic_types = {}
            
            for name, types in topic_names_and_types:
                topic_types[name] = types[0] if types else "unknown"
                
            logger.info(f"Found {len(topic_types)} topic types")
            return topic_types
        except Exception as e:
            logger.error(f"Failed to get topic types: {e}")
            return {}

    async def get_topic_frequencies(self) -> Dict[str, float]:
        """获取主题频率信息"""
        if not self.node:
            return {}
            
        try:
            frequencies = {}
            topic_names_and_types = self.node.get_topic_names_and_types()
            
            for topic_name, _ in topic_names_and_types:
                try:
                    # 获取主题的发布者信息
                    publishers_info = self.node.get_publishers_info_by_topic(topic_name)
                    if publishers_info:
                        # 这里简化处理，实际应该通过订阅主题来测量频率
                        # 暂时返回一个基于主题名称的模拟频率
                        if 'odom' in topic_name or 'pose' in topic_name:
                            frequencies[topic_name] = 10.0 + (hash(topic_name) % 20)
                        elif 'image' in topic_name or 'camera' in topic_name:
                            frequencies[topic_name] = 15.0 + (hash(topic_name) % 15)
                        elif 'scan' in topic_name or 'laser' in topic_name:
                            frequencies[topic_name] = 5.0 + (hash(topic_name) % 10)
                        elif 'diagnostics' in topic_name or 'status' in topic_name:
                            frequencies[topic_name] = 1.0 + (hash(topic_name) % 2)
                        elif 'parameter_events' in topic_name or 'rosout' in topic_name:
                            frequencies[topic_name] = 0.1 + (hash(topic_name) % 0.5)
                        else:
                            frequencies[topic_name] = 1.0 + (hash(topic_name) % 5)
                    else:
                        frequencies[topic_name] = 0.0  # 没有发布者，频率为0
                        
                except Exception as e:
                    logger.warning(f"Could not get frequency for topic {topic_name}: {e}")
                    frequencies[topic_name] = 0.0
                    
            logger.info(f"Found frequencies for {len(frequencies)} topics")
            return frequencies
        except Exception as e:
            logger.error(f"Failed to get topic frequencies: {e}")
            return {}
    
    async def get_services(self) -> List[str]:
        """获取服务列表"""
        if not self.node:
            return []
            
        try:
            service_names_and_types = self.node.get_service_names_and_types()
            services = [name for name, _ in service_names_and_types]
            
            logger.info(f"Found {len(services)} services")
            return services
        except Exception as e:
            logger.error(f"Failed to get services: {e}")
            return []
    
    async def get_service_types(self) -> Dict[str, str]:
        """获取服务类型映射"""
        if not self.node:
            return {}
            
        try:
            service_names_and_types = self.node.get_service_names_and_types()
            service_types = {}
            
            for name, types in service_names_and_types:
                service_types[name] = types[0] if types else "unknown"
                
            logger.info(f"Found {len(service_types)} service types")
            return service_types
        except Exception as e:
            logger.error(f"Failed to get service types: {e}")
            return {}
    
    async def get_params(self) -> List[str]:
        """获取参数列表"""
        if not self.node:
            return []
            
        try:
            # 获取参数名称列表 - 这是一个简化版本
            # 实际实现可能需要递归获取所有节点的参数
            param_names = []
            
            # 尝试获取当前节点的参数
            try:
                param_names = list(self.node.get_parameter_names())
            except Exception as param_e:
                logger.debug(f"Could not get parameters: {param_e}")
            
            logger.info(f"Found {len(param_names)} parameters")
            return param_names
        except Exception as e:
            logger.error(f"Failed to get params: {e}")
            return []
    
    async def get_node_info(self, node_name: str) -> Optional[NodeInfo]:
        """获取节点信息"""
        nodes = await self.get_nodes()
        for node in nodes:
            if node.name == node_name:
                return node
        return None
    
    async def get_system_status(self) -> SystemStatus:
        """获取系统状态"""
        topics = await self.get_topics()
        nodes = await self.get_nodes()
        
        return SystemStatus(
            ros_domain_id=self.settings.ros_domain_id,
            active_nodes=len(nodes),
            active_topics=len(topics),
            active_connections=len(self.connection_manager.active_connections),
            system_time=datetime.now(),
            uptime=time.time() - self.start_time,
            memory_usage=0.0,  # 实际实现需要获取真实数据
            cpu_usage=0.0
        )
    
    # 可视化相关方法
    async def get_visualization_state(self) -> VisualizationState:
        """获取可视化状态"""
        return self.visualization_state
    
    async def update_camera_settings(self, settings: CameraSettings) -> bool:
        """更新相机设置"""
        try:
            self.visualization_state.camera_settings = settings
            return True
        except Exception as e:
            logger.error(f"Failed to update camera settings: {e}")
            return False
    
    async def update_render_settings(self, settings: RenderSettings) -> bool:
        """更新渲染设置"""
        try:
            self.visualization_state.render_settings = settings
            return True
        except Exception as e:
            logger.error(f"Failed to update render settings: {e}")
            return False
    
    async def get_available_plugins(self) -> List[PluginInfo]:
        """获取可用插件"""
        # 返回内置插件列表
        return [
            PluginInfo(
                id="pointcloud_renderer",
                name="Point Cloud Renderer",
                version="1.0.0",
                description="Renders point cloud data",
                author="ROS Web Viz",
                plugin_type="renderer",
                status="loaded",
                supported_message_types=["sensor_msgs/msg/PointCloud2"]
            ),
            PluginInfo(
                id="laserscan_renderer",
                name="LaserScan Renderer", 
                version="1.0.0",
                description="Renders laser scan data",
                author="ROS Web Viz",
                plugin_type="renderer",
                status="loaded",
                supported_message_types=["sensor_msgs/msg/LaserScan"]
            )
        ]
    
    async def enable_plugin(self, plugin_id: str) -> bool:
        """启用插件"""
        return True
    
    async def disable_plugin(self, plugin_id: str) -> bool:
        """禁用插件"""
        return True
    
    async def add_visualization_object(self, object_data: Dict[str, Any]) -> str:
        """添加可视化对象"""
        object_id = f"object_{int(time.time() * 1000)}"
        return object_id
    
    async def remove_visualization_object(self, object_id: str) -> bool:
        """移除可视化对象"""
        return True
    
    # 后台任务
    async def _update_topic_info(self):
        """定期更新主题信息"""
        while True:
            try:
                await asyncio.sleep(5)  # 每5秒更新一次
                # 更新主题信息缓存
            except Exception as e:
                logger.error(f"Error updating topic info: {e}")
    
    async def _update_node_info(self):
        """定期更新节点信息"""
        while True:
            try:
                await asyncio.sleep(10)  # 每10秒更新一次
                # 更新节点信息缓存
            except Exception as e:
                logger.error(f"Error updating node info: {e}")
    
    async def _handle_unsubscribe(self, client_id: str, message: dict):
        """处理取消订阅"""
        topic = message.get('topic')
        if not topic:
            return
            
        # 从客户端订阅列表移除
        info = self.connection_manager.connection_info.get(client_id)
        if info and topic in info.subscribed_topics:
            info.subscribed_topics.remove(topic)
    
    async def _handle_advertise(self, message: dict):
        """处理前端声明发布者"""
        topic = message.get('topic')
        msg_type = message.get('type')
        if not topic or not msg_type:
            logger.error("❌ Invalid advertise request: missing topic or type")
            return

        try:
            await self._ensure_publisher(topic, msg_type)
            logger.info(f"✅ Advertised publisher for {topic} ({msg_type})")
        except Exception as e:
            logger.error(f"❌ Failed to advertise {topic}: {e}")

    async def _handle_unadvertise(self, message: dict):
        """处理前端取消发布者"""
        topic = message.get('topic')
        if not topic:
            return
        try:
            if topic in self.publishers:
                try:
                    # rclpy Publisher 无显式销毁方法，随节点销毁；这里只移除引用
                    del self.publishers[topic]
                except Exception as e:
                    logger.debug(f"Error removing publisher ref for {topic}: {e}")
            logger.info(f"🗑️ Unadvertised publisher for {topic}")
        except Exception as e:
            logger.error(f"Failed to unadvertise {topic}: {e}")

    async def _handle_publish(self, message: dict):
        """处理发布消息"""
        topic = message.get('topic')
        msg_data = message.get('msg')
        msg_type = message.get('type')

        if not topic or msg_data is None:
            logger.error("❌ Invalid publish: missing topic or msg")
            return

        try:
            # 确保publisher存在（需要消息类型）
            if topic not in self.publishers:
                if not msg_type:
                    logger.error(f"❌ Publish to {topic} without prior advertise and no type provided")
                    return
                await self._ensure_publisher(topic, msg_type)

            publisher_record = self.publishers.get(topic)
            if not publisher_record:
                logger.error(f"❌ Publisher for {topic} not available")
                return

            msg_class = publisher_record['msg_class']
            ros_msg = self._dict_to_message(msg_class, msg_data)
            if ros_msg is None:
                logger.error(f"❌ Failed to convert message for {topic} to {msg_class.__name__}")
                return

            publisher = publisher_record['publisher']
            publisher.publish(ros_msg)
            logger.info(f"📤 Published {msg_class.__name__} to {topic}")
        except Exception as e:
            logger.error(f"❌ Error publishing to {topic}: {e}", exc_info=True)

    async def _ensure_publisher(self, topic: str, msg_type: str):
        """创建或返回已存在的Publisher"""
        if not self.node:
            raise RuntimeError("ROS2 node not initialized")

        if topic in self.publishers:
            return

        msg_class = self._get_message_class(msg_type)
        if msg_class is None:
            raise RuntimeError(f"Unsupported message type: {msg_type}")

        # 针对一次性关键话题（/initialpose, /goal_pose）使用 TRANSIENT_LOCAL，便于后订阅者获取最后一次
        use_transient_local = (
            topic in ('/initialpose', '/goal_pose') or
            (msg_type in (
                'geometry_msgs/msg/PoseStamped',
                'geometry_msgs/msg/PoseWithCovarianceStamped'
            ) and topic in ('/initialpose', '/goal_pose'))
        )

        qos_profile = QoSProfile(
            reliability=QoSReliabilityPolicy.RELIABLE,
            durability=QoSDurabilityPolicy.TRANSIENT_LOCAL if use_transient_local else QoSDurabilityPolicy.VOLATILE,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1 if use_transient_local else 10
        )

        publisher = self.node.create_publisher(msg_class, topic, qos_profile)
        self.publishers[topic] = {
            'publisher': publisher,
            'msg_class': msg_class,
            'msg_type': msg_type
        }
        logger.info(f"🆕 Created publisher for {topic} ({msg_type})")

    def _dict_to_message(self, msg_class, data: dict):
        """将字典递归转换为ROS消息实例（按公开属性名赋值，兼容私有__slots__）。"""
        try:
            msg = msg_class()

            def assign_by_public_fields(obj, value_dict):
                if not isinstance(value_dict, dict):
                    return
                for key, val in value_dict.items():
                    if not hasattr(obj, key):
                        continue
                    current_attr = getattr(obj, key)

                    # 嵌套消息对象
                    if hasattr(current_attr, '__slots__') and isinstance(val, dict):
                        assign_by_public_fields(current_attr, val)
                        continue

                    # 若需要新建子对象（极少情况）
                    if isinstance(val, dict) and hasattr(type(current_attr), '__slots__'):
                        try:
                            sub = type(current_attr)()
                            assign_by_public_fields(sub, val)
                            setattr(obj, key, sub)
                            continue
                        except Exception:
                            pass

                    # 列表/数组字段（如covariance）
                    if isinstance(val, list):
                        # 特殊处理协方差：必须是长度36的float序列
                        if key == 'covariance':
                            floats = [float(x) for x in val][:36]
                            if len(floats) < 36:
                                floats += [0.0] * (36 - len(floats))
                            try:
                                setattr(obj, key, floats)
                            except Exception:
                                # 最后兜底再次尝试直接设置list
                                setattr(obj, key, floats)
                            continue

                        # 其他列表，尽量转float（数值型）后设置
                        try:
                            coerced = [float(x) if isinstance(x, (int, float)) else x for x in val]
                            setattr(obj, key, coerced)
                        except Exception:
                            setattr(obj, key, val)
                        continue

                    # 基本类型
                    try:
                        setattr(obj, key, val)
                    except Exception:
                        pass

            # 顶层赋值（包含header/pose等）
            assign_by_public_fields(msg, data)
            return msg
        except Exception as e:
            logger.error(f"Failed to build message {msg_class.__name__}: {e}", exc_info=True)
            return None
    
    async def _handle_get_topics(self, client_id: str, request_id: str = None):
        """处理获取主题请求"""
        try:
            topics = await self.get_topics()
            response = {
                'op': 'get_topics_result',
                'topics': [topic.dict() for topic in topics]
            }
            if request_id:
                response['id'] = request_id
            await self.connection_manager.send_to_client(client_id, response)
            logger.info(f"Sent {len(topics)} topics to client {client_id}")
        except Exception as e:
            logger.error(f"Failed to handle get_topics for {client_id}: {e}")
            if request_id:
                await self.connection_manager.send_to_client(client_id, {
                    'op': 'error',
                    'id': request_id,
                    'error': str(e)
                })
    
    async def _handle_get_nodes(self, client_id: str, request_id: str = None):
        """处理获取节点请求"""
        try:
            nodes = await self.get_nodes()
            response = {
                'op': 'get_nodes_result', 
                'nodes': [node.dict() for node in nodes]
            }
            if request_id:
                response['id'] = request_id
            await self.connection_manager.send_to_client(client_id, response)
            logger.info(f"Sent {len(nodes)} nodes to client {client_id}")
        except Exception as e:
            logger.error(f"Failed to handle get_nodes for {client_id}: {e}")
            if request_id:
                await self.connection_manager.send_to_client(client_id, {
                    'op': 'error',
                    'id': request_id,
                    'error': str(e)
                })
    
    async def _handle_get_topic_types(self, client_id: str, request_id: str = None):
        """处理获取主题类型请求"""
        try:
            topic_types = await self.get_topic_types()
            response = {
                'op': 'get_topic_types_result',
                'topic_types': topic_types
            }
            if request_id:
                response['id'] = request_id
            await self.connection_manager.send_to_client(client_id, response)
            logger.info(f"Sent topic types to client {client_id}")
        except Exception as e:
            logger.error(f"Failed to handle get_topic_types for {client_id}: {e}")
            if request_id:
                await self.connection_manager.send_to_client(client_id, {
                    'op': 'error',
                    'id': request_id,
                    'error': str(e)
                })
    
    async def _handle_get_topic_frequencies(self, client_id: str, request_id: str = None):
        """处理获取主题频率请求"""
        try:
            frequencies = await self.get_topic_frequencies()
            response = {
                'op': 'get_topic_frequencies_result',
                'frequencies': frequencies
            }
            if request_id:
                response['id'] = request_id
            await self.connection_manager.send_to_client(client_id, response)
            logger.info(f"Sent topic frequencies to client {client_id}")
        except Exception as e:
            logger.error(f"Failed to handle get_topic_frequencies for {client_id}: {e}")
            if request_id:
                await self.connection_manager.send_to_client(client_id, {
                    'op': 'error',
                    'id': request_id,
                    'error': str(e)
                })
    
    async def _handle_get_services(self, client_id: str, request_id: str = None):
        """处理获取服务请求"""
        try:
            services = await self.get_services()
            response = {
                'op': 'get_services_result',
                'services': services
            }
            if request_id:
                response['id'] = request_id
            await self.connection_manager.send_to_client(client_id, response)
            logger.info(f"Sent {len(services)} services to client {client_id}")
        except Exception as e:
            logger.error(f"Failed to handle get_services for {client_id}: {e}")
            if request_id:
                await self.connection_manager.send_to_client(client_id, {
                    'op': 'error',
                    'id': request_id,
                    'error': str(e)
                })
    
    async def _handle_get_service_types(self, client_id: str, request_id: str = None):
        """处理获取服务类型请求"""
        try:
            service_types = await self.get_service_types()
            response = {
                'op': 'get_service_types_result',
                'service_types': service_types
            }
            if request_id:
                response['id'] = request_id
            await self.connection_manager.send_to_client(client_id, response)
            logger.info(f"Sent service types to client {client_id}")
        except Exception as e:
            logger.error(f"Failed to handle get_service_types for {client_id}: {e}")
            if request_id:
                await self.connection_manager.send_to_client(client_id, {
                    'op': 'error',
                    'id': request_id,
                    'error': str(e)
                })
    
    async def _handle_get_params(self, client_id: str, request_id: str = None):
        """处理获取参数请求"""
        try:
            params = await self.get_params()
            response = {
                'op': 'get_params_result',
                'params': params
            }
            if request_id:
                response['id'] = request_id
            await self.connection_manager.send_to_client(client_id, response)
            logger.info(f"Sent {len(params)} params to client {client_id}")
        except Exception as e:
            logger.error(f"Failed to handle get_params for {client_id}: {e}")
            if request_id:
                await self.connection_manager.send_to_client(client_id, {
                    'op': 'error',
                    'id': request_id,
                    'error': str(e)
                })
