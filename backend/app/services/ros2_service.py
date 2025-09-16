"""
ROS2 核心服务
"""
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
import json
import threading
import time
from typing import Dict, List, Any, Optional, Callable
from collections import deque
import logging

# ROS2 消息类型导入
from sensor_msgs.msg import PointCloud2, LaserScan, Image
from geometry_msgs.msg import Pose, Twist, Transform
from visualization_msgs.msg import Marker, MarkerArray
from std_msgs.msg import String

logger = logging.getLogger(__name__)


class ROS2Service(Node):
    """ROS2 核心服务类"""
    
    def __init__(self):
        super().__init__('ros_web_viz_node')
        self.subscribers: Dict[str, Any] = {}
        self.publishers: Dict[str, Any] = {}
        self.message_callbacks: Dict[str, List[Callable]] = {}
        self.message_cache: Dict[str, deque] = {}
        self.is_running = False
        self._lock = threading.Lock()
        
        # 配置 QoS
        self.default_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
            depth=10
        )
        
        logger.info("ROS2Service initialized")
    
    def start(self):
        """启动 ROS2 服务"""
        if not rclpy.ok():
            rclpy.init()
        
        self.is_running = True
        self.spin_thread = threading.Thread(target=self._spin_node)
        self.spin_thread.daemon = True
        self.spin_thread.start()
        
        logger.info("ROS2Service started")
    
    def stop(self):
        """停止 ROS2 服务"""
        self.is_running = False
        if hasattr(self, 'spin_thread'):
            self.spin_thread.join(timeout=1.0)
        
        # 清理订阅者和发布者
        with self._lock:
            for sub in self.subscribers.values():
                if sub:
                    self.destroy_subscription(sub)
            for pub in self.publishers.values():
                if pub:
                    self.destroy_publisher(pub)
            
            self.subscribers.clear()
            self.publishers.clear()
        
        logger.info("ROS2Service stopped")
    
    def _spin_node(self):
        """在单独线程中运行节点"""
        while self.is_running and rclpy.ok():
            try:
                rclpy.spin_once(self, timeout_sec=0.1)
            except Exception as e:
                logger.error(f"Error in spin_node: {e}")
                break    
    def subscribe_topic(self, topic_name: str, message_type: str, callback: Callable = None) -> bool:
        """订阅 ROS2 主题"""
        try:
            with self._lock:
                if topic_name in self.subscribers:
                    logger.warning(f"Topic {topic_name} already subscribed")
                    return True
                
                # 根据消息类型创建订阅者
                msg_class = self._get_message_class(message_type)
                if not msg_class:
                    logger.error(f"Unsupported message type: {message_type}")
                    return False
                
                # 创建消息缓存
                self.message_cache[topic_name] = deque(maxlen=100)
                
                # 创建回调函数
                def topic_callback(msg):
                    try:
                        # 转换消息为字典
                        msg_dict = self._message_to_dict(msg)
                        msg_dict['timestamp'] = time.time()
                        
                        # 缓存消息
                        self.message_cache[topic_name].append(msg_dict)
                        
                        # 调用注册的回调函数
                        if topic_name in self.message_callbacks:
                            for cb in self.message_callbacks[topic_name]:
                                try:
                                    cb(msg_dict)
                                except Exception as e:
                                    logger.error(f"Error in callback for {topic_name}: {e}")
                    
                    except Exception as e:
                        logger.error(f"Error processing message for {topic_name}: {e}")
                
                # 创建订阅者
                subscriber = self.create_subscription(
                    msg_class,
                    topic_name,
                    topic_callback,
                    self.default_qos
                )
                
                self.subscribers[topic_name] = subscriber
                logger.info(f"Subscribed to topic: {topic_name}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to subscribe to {topic_name}: {e}")
            return False
    
    def unsubscribe_topic(self, topic_name: str) -> bool:
        """取消订阅主题"""
        try:
            with self._lock:
                if topic_name in self.subscribers:
                    self.destroy_subscription(self.subscribers[topic_name])
                    del self.subscribers[topic_name]
                    
                    # 清理相关数据
                    if topic_name in self.message_cache:
                        del self.message_cache[topic_name]
                    if topic_name in self.message_callbacks:
                        del self.message_callbacks[topic_name]
                    
                    logger.info(f"Unsubscribed from topic: {topic_name}")
                    return True
                else:
                    logger.warning(f"Topic {topic_name} not subscribed")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to unsubscribe from {topic_name}: {e}")
            return False    
    def register_callback(self, topic_name: str, callback: Callable):
        """注册主题回调函数"""
        with self._lock:
            if topic_name not in self.message_callbacks:
                self.message_callbacks[topic_name] = []
            self.message_callbacks[topic_name].append(callback)
    
    def get_topic_list(self) -> List[str]:
        """获取可用主题列表"""
        try:
            topic_names_and_types = self.get_topic_names_and_types()
            return [name for name, _ in topic_names_and_types]
        except Exception as e:
            logger.error(f"Failed to get topic list: {e}")
            return []
    
    def get_node_list(self) -> List[str]:
        """获取节点列表"""
        try:
            return self.get_node_names()
        except Exception as e:
            logger.error(f"Failed to get node list: {e}")
            return []
    
    def get_latest_message(self, topic_name: str) -> Optional[Dict[str, Any]]:
        """获取主题的最新消息"""
        if topic_name in self.message_cache and self.message_cache[topic_name]:
            return self.message_cache[topic_name][-1]
        return None
    
    def _get_message_class(self, message_type: str):
        """根据消息类型字符串获取消息类"""
        type_mapping = {
            'sensor_msgs/msg/PointCloud2': PointCloud2,
            'sensor_msgs/msg/LaserScan': LaserScan,
            'sensor_msgs/msg/Image': Image,
            'geometry_msgs/msg/Pose': Pose,
            'geometry_msgs/msg/Twist': Twist,
            'geometry_msgs/msg/Transform': Transform,
            'visualization_msgs/msg/Marker': Marker,
            'visualization_msgs/msg/MarkerArray': MarkerArray,
            'std_msgs/msg/String': String,
        }
        return type_mapping.get(message_type)
    
    def _message_to_dict(self, msg) -> Dict[str, Any]:
        """将 ROS2 消息转换为字典"""
        try:
            if hasattr(msg, '__slots__'):
                result = {}
                for slot in msg.__slots__:
                    value = getattr(msg, slot)
                    if hasattr(value, '__slots__'):
                        result[slot] = self._message_to_dict(value)
                    elif isinstance(value, list):
                        result[slot] = [
                            self._message_to_dict(item) if hasattr(item, '__slots__') else item
                            for item in value
                        ]
                    else:
                        result[slot] = value
                return result
            else:
                return {"data": msg}
        except Exception as e:
            logger.error(f"Failed to convert message to dict: {e}")
            return {"error": str(e)}


# 全局 ROS2 服务实例
_ros2_service: Optional[ROS2Service] = None


def get_ros2_service() -> ROS2Service:
    """获取 ROS2 服务实例（单例模式）"""
    global _ros2_service
    if _ros2_service is None:
        _ros2_service = ROS2Service()
    return _ros2_service