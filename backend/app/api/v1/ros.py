"""
ROS2 相关 API 端点
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
import logging

from ...core.config import get_settings
from ...models.ros import (
    TopicInfo, NodeInfo, SystemStatus, 
    SystemTopology, NodeTopology, TopicConnection
)
from ...services.rosbridge import RosbridgeService
from ...services.topology_service import TopologyService
from ...services.dependencies import get_rosbridge_service, get_topology_service

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/topics", response_model=List[TopicInfo])
async def get_topics(
    service: RosbridgeService = Depends(get_rosbridge_service)
):
    """获取所有 ROS2 主题列表"""
    try:
        topics = await service.get_topics()
        return topics
    except Exception as e:
        logger.error(f"Failed to get topics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/topics/{topic_name}", response_model=TopicInfo)
async def get_topic_info(
    topic_name: str,
    service: RosbridgeService = Depends(get_rosbridge_service)
):
    """获取特定主题信息"""
    try:
        topic_info = await service.get_topic_info(topic_name)
        if not topic_info:
            raise HTTPException(status_code=404, detail=f"Topic {topic_name} not found")
        return topic_info
    except Exception as e:
        logger.error(f"Failed to get topic info for {topic_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/topics/frequencies", response_model=Dict[str, float])
async def get_topic_frequencies(
    service: RosbridgeService = Depends(get_rosbridge_service)
):
    """获取所有主题的频率信息"""
    try:
        frequencies = await service.get_topic_frequencies()
        return frequencies
    except Exception as e:
        logger.error(f"Failed to get topic frequencies: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/topics/{topic_name}/subscribe")
async def subscribe_topic(
    topic_name: str,
    service: RosbridgeService = Depends(get_rosbridge_service)
):
    """订阅主题"""
    try:
        success = await service.subscribe_topic(topic_name)
        return {"success": success, "topic": topic_name, "action": "subscribed"}
    except Exception as e:
        logger.error(f"Failed to subscribe to {topic_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/topics/{topic_name}/unsubscribe")
async def unsubscribe_topic(
    topic_name: str,
    service: RosbridgeService = Depends(get_rosbridge_service)
):
    """取消订阅主题"""
    try:
        success = await service.unsubscribe_topic(topic_name)
        return {"success": success, "topic": topic_name, "action": "unsubscribed"}
    except Exception as e:
        logger.error(f"Failed to unsubscribe from {topic_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/topics/{topic_name}/publish")
async def publish_message(
    topic_name: str,
    message: Dict[str, Any],
    service: RosbridgeService = Depends(get_rosbridge_service)
):
    """发布消息到主题"""
    try:
        success = await service.publish_message(topic_name, message)
        return {"success": success, "topic": topic_name, "action": "published"}
    except Exception as e:
        logger.error(f"Failed to publish to {topic_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/nodes", response_model=List[NodeInfo])
async def get_nodes(
    service: RosbridgeService = Depends(get_rosbridge_service)
):
    """获取所有 ROS2 节点列表"""
    try:
        nodes = await service.get_nodes()
        return nodes
    except Exception as e:
        logger.error(f"Failed to get nodes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/nodes/{node_name}", response_model=NodeInfo)
async def get_node_info(
    node_name: str,
    service: RosbridgeService = Depends(get_rosbridge_service)
):
    """获取特定节点信息"""
    try:
        node_info = await service.get_node_info(node_name)
        if not node_info:
            raise HTTPException(status_code=404, detail=f"Node {node_name} not found")
        return node_info
    except Exception as e:
        logger.error(f"Failed to get node info for {node_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status", response_model=SystemStatus)
async def get_system_status(
    service: RosbridgeService = Depends(get_rosbridge_service)
):
    """获取系统状态"""
    try:
        status = await service.get_system_status()
        return status
    except Exception as e:
        logger.error(f"Failed to get system status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/topology", response_model=SystemTopology)
async def get_system_topology(
    use_cache: bool = True,
    topology_service: TopologyService = Depends(get_topology_service)
):
    """获取系统拓扑结构"""
    try:
        topology = await topology_service.get_system_topology(use_cache)
        return topology
    except Exception as e:
        logger.error(f"Failed to get system topology: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/topology/nodes/{node_name}", response_model=NodeTopology)
async def get_node_topology(
    node_name: str,
    topology_service: TopologyService = Depends(get_topology_service)
):
    """获取特定节点的拓扑信息"""
    try:
        node_topology = await topology_service.get_node_topology(node_name)
        if not node_topology:
            raise HTTPException(status_code=404, detail=f"Node {node_name} not found")
        return node_topology
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get topology for node {node_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/topology/topics", response_model=List[TopicConnection])
async def get_topic_connections(
    topic_name: Optional[str] = None,
    topology_service: TopologyService = Depends(get_topology_service)
):
    """获取主题连接信息"""
    try:
        connections = await topology_service.get_topic_connections(topic_name)
        return connections
    except Exception as e:
        logger.error(f"Failed to get topic connections: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/topology/topics/{topic_name}/connections", response_model=List[TopicConnection])
async def get_topic_connection_details(
    topic_name: str,
    topology_service: TopologyService = Depends(get_topology_service)
):
    """获取特定主题的连接详情"""
    try:
        connections = await topology_service.get_topic_connections(topic_name)
        if not connections:
            raise HTTPException(status_code=404, detail=f"Topic {topic_name} not found")
        return connections
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get connections for topic {topic_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
