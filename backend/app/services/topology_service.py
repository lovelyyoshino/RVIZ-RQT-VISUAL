"""
ROS2 拓扑分析服务
负责分析节点间的连接关系和通信拓扑
"""

import rclpy
from rclpy.node import Node
from rclpy.topic_endpoint_info import TopicEndpointInfo
import logging
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict
import asyncio
from datetime import datetime

from ..models.ros import NodeTopology, TopicConnection, SystemTopology
from ..core.config import Settings

logger = logging.getLogger(__name__)


class TopologyAnalyzer:
    """ROS2 拓扑分析器"""
    
    def __init__(self, ros_node: Node):
        self.ros_node = ros_node
        self.topology_cache = {}
        self.last_update = None
        self.cache_duration = 5.0  # 缓存5秒
        
    async def get_system_topology(self, use_cache: bool = True) -> SystemTopology:
        """获取系统拓扑结构"""
        now = datetime.now()
        
        # 检查缓存
        if (use_cache and self.last_update and 
            (now - self.last_update).total_seconds() < self.cache_duration):
            return self.topology_cache
        
        try:
            # 获取节点拓扑信息
            nodes = await self._analyze_node_topology()
            
            # 获取主题连接信息
            topic_connections = await self._analyze_topic_connections()
            
            # 识别孤立节点
            isolated_nodes = self._find_isolated_nodes(nodes, topic_connections)
            
            # 构建系统拓扑
            topology = SystemTopology(
                nodes=nodes,
                topic_connections=topic_connections,
                isolated_nodes=isolated_nodes,
                node_count=len(nodes),
                topic_count=len(topic_connections),
                connection_count=sum(conn.connection_count for conn in topic_connections),
                last_updated=now
            )
            
            # 更新缓存
            self.topology_cache = topology
            self.last_update = now
            
            logger.info(f"Updated topology: {len(nodes)} nodes, "
                       f"{len(topic_connections)} topics, "
                       f"{topology.connection_count} connections")
            
            return topology
            
        except Exception as e:
            logger.error(f"Failed to analyze system topology: {e}")
            # 返回空拓扑
            return SystemTopology()
    
    async def _analyze_node_topology(self) -> List[NodeTopology]:
        """分析节点拓扑"""
        nodes = []
        
        try:
            # 获取所有节点名称
            node_names = self.ros_node.get_node_names()
            
            for node_name in node_names:
                try:
                    # 获取节点的发布和订阅信息
                    published_topics = await self._get_node_publishers(node_name)
                    subscribed_topics = await self._get_node_subscribers(node_name)
                    services = await self._get_node_services(node_name)
                    
                    # 解析命名空间
                    namespace = self._extract_namespace(node_name)
                    
                    node_topology = NodeTopology(
                        node_name=node_name,
                        namespace=namespace,
                        node_type="node",
                        published_topics=published_topics,
                        subscribed_topics=subscribed_topics,
                        services=services,
                        actions=[],  # TODO: 添加action分析
                        is_active=True
                    )
                    
                    nodes.append(node_topology)
                    
                except Exception as e:
                    logger.warning(f"Failed to analyze node {node_name}: {e}")
                    continue
            
            return nodes
            
        except Exception as e:
            logger.error(f"Failed to get node topology: {e}")
            return []
    
    async def _get_node_publishers(self, node_name: str) -> List[str]:
        """获取节点发布的主题"""
        try:
            publishers = []
            topic_names_and_types = self.ros_node.get_topic_names_and_types()
            
            for topic_name, _ in topic_names_and_types:
                try:
                    # 获取主题的发布者信息
                    publisher_info = self.ros_node.get_publishers_info_by_topic(topic_name)
                    
                    # 检查是否有来自指定节点的发布者
                    for info in publisher_info:
                        if info.node_name == node_name:
                            publishers.append(topic_name)
                            break
                            
                except Exception as e:
                    logger.debug(f"Error getting publisher info for {topic_name}: {e}")
                    continue
            
            return publishers
            
        except Exception as e:
            logger.error(f"Failed to get publishers for {node_name}: {e}")
            return []
    
    async def _get_node_subscribers(self, node_name: str) -> List[str]:
        """获取节点订阅的主题"""
        try:
            subscribers = []
            topic_names_and_types = self.ros_node.get_topic_names_and_types()
            
            for topic_name, _ in topic_names_and_types:
                try:
                    # 获取主题的订阅者信息
                    subscriber_info = self.ros_node.get_subscriptions_info_by_topic(topic_name)
                    
                    # 检查是否有来自指定节点的订阅者
                    for info in subscriber_info:
                        if info.node_name == node_name:
                            subscribers.append(topic_name)
                            break
                            
                except Exception as e:
                    logger.debug(f"Error getting subscriber info for {topic_name}: {e}")
                    continue
            
            return subscribers
            
        except Exception as e:
            logger.error(f"Failed to get subscribers for {node_name}: {e}")
            return []
    
    async def _get_node_services(self, node_name: str) -> List[str]:
        """获取节点提供的服务"""
        try:
            services = []
            service_names_and_types = self.ros_node.get_service_names_and_types()
            
            for service_name, _ in service_names_and_types:
                # 简单的启发式方法：如果服务名包含节点名，则认为是该节点提供的
                # 更准确的方法需要使用ROS2的服务发现机制
                if node_name.replace('/', '') in service_name:
                    services.append(service_name)
            
            return services
            
        except Exception as e:
            logger.error(f"Failed to get services for {node_name}: {e}")
            return []
    
    async def _analyze_topic_connections(self) -> List[TopicConnection]:
        """分析主题连接"""
        connections = []
        
        try:
            topic_names_and_types = self.ros_node.get_topic_names_and_types()
            
            for topic_name, topic_types in topic_names_and_types:
                try:
                    message_type = topic_types[0] if topic_types else "unknown"
                    
                    # 获取发布者和订阅者
                    publishers = await self._get_topic_publishers(topic_name)
                    subscribers = await self._get_topic_subscribers(topic_name)
                    
                    connection_count = len(publishers) * len(subscribers)
                    
                    connection = TopicConnection(
                        topic_name=topic_name,
                        message_type=message_type,
                        publishers=publishers,
                        subscribers=subscribers,
                        connection_count=connection_count
                    )
                    
                    connections.append(connection)
                    
                except Exception as e:
                    logger.warning(f"Failed to analyze topic {topic_name}: {e}")
                    continue
            
            return connections
            
        except Exception as e:
            logger.error(f"Failed to analyze topic connections: {e}")
            return []
    
    async def _get_topic_publishers(self, topic_name: str) -> List[str]:
        """获取主题的发布者节点"""
        try:
            publisher_info = self.ros_node.get_publishers_info_by_topic(topic_name)
            return [info.node_name for info in publisher_info]
        except Exception as e:
            logger.debug(f"Error getting publishers for {topic_name}: {e}")
            return []
    
    async def _get_topic_subscribers(self, topic_name: str) -> List[str]:
        """获取主题的订阅者节点"""
        try:
            subscriber_info = self.ros_node.get_subscriptions_info_by_topic(topic_name)
            return [info.node_name for info in subscriber_info]
        except Exception as e:
            logger.debug(f"Error getting subscribers for {topic_name}: {e}")
            return []
    
    def _find_isolated_nodes(self, nodes: List[NodeTopology], 
                           connections: List[TopicConnection]) -> List[str]:
        """找到孤立节点（没有发布或订阅任何主题的节点）"""
        isolated = []
        
        for node in nodes:
            if (not node.published_topics and 
                not node.subscribed_topics and 
                not node.services):
                isolated.append(node.node_name)
        
        return isolated
    
    def _extract_namespace(self, node_name: str) -> str:
        """从节点名称提取命名空间"""
        if not node_name.startswith('/'):
            return '/'
        
        parts = node_name.split('/')
        if len(parts) <= 2:
            return '/'
        
        return '/'.join(parts[:-1])


class TopologyService:
    """拓扑服务主类"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.ros_node: Optional[Node] = None
        self.analyzer: Optional[TopologyAnalyzer] = None
        self.is_running = False
        
    async def start(self):
        """启动拓扑服务"""
        try:
            if not rclpy.ok():
                rclpy.init()
            
            self.ros_node = Node('topology_analyzer')
            self.analyzer = TopologyAnalyzer(self.ros_node)
            self.is_running = True
            
            # 启动后台任务
            asyncio.create_task(self._spin_ros_node())
            
            logger.info("Topology service started")
            
        except Exception as e:
            logger.error(f"Failed to start topology service: {e}")
            raise
    
    async def stop(self):
        """停止拓扑服务"""
        try:
            self.is_running = False
            
            if self.ros_node:
                self.ros_node.destroy_node()
            
            if rclpy.ok():
                rclpy.shutdown()
            
            logger.info("Topology service stopped")
            
        except Exception as e:
            logger.error(f"Error stopping topology service: {e}")
    
    async def _spin_ros_node(self):
        """在后台运行ROS节点"""
        while self.is_running and rclpy.ok():
            try:
                rclpy.spin_once(self.ros_node, timeout_sec=0.1)
                await asyncio.sleep(0.01)
            except Exception as e:
                logger.error(f"Error in ROS node spin: {e}")
                break
    
    async def get_system_topology(self, use_cache: bool = True) -> SystemTopology:
        """获取系统拓扑"""
        if not self.analyzer:
            raise RuntimeError("Topology service not started")
        
        return await self.analyzer.get_system_topology(use_cache)
    
    async def get_node_topology(self, node_name: str) -> Optional[NodeTopology]:
        """获取特定节点的拓扑信息"""
        topology = await self.get_system_topology()
        
        for node in topology.nodes:
            if node.node_name == node_name:
                return node
        
        return None
    
    async def get_topic_connections(self, topic_name: str = None) -> List[TopicConnection]:
        """获取主题连接信息"""
        topology = await self.get_system_topology()
        
        if topic_name:
            return [conn for conn in topology.topic_connections 
                   if conn.topic_name == topic_name]
        
        return topology.topic_connections


# 全局拓扑服务实例
_topology_service: Optional[TopologyService] = None


def get_topology_service(settings: Settings = None) -> TopologyService:
    """获取拓扑服务实例（单例模式）"""
    global _topology_service
    if _topology_service is None and settings:
        _topology_service = TopologyService(settings)
    return _topology_service

