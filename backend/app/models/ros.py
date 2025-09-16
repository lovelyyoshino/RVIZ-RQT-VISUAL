"""
ROS2 数据模型
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class MessageType(str, Enum):
    """消息类型枚举"""
    # 传感器消息
    POINTCLOUD2 = "sensor_msgs/msg/PointCloud2"
    LASERSCAN = "sensor_msgs/msg/LaserScan"
    IMAGE = "sensor_msgs/msg/Image"
    COMPRESSED_IMAGE = "sensor_msgs/msg/CompressedImage"
    CAMERA_INFO = "sensor_msgs/msg/CameraInfo"
    IMU = "sensor_msgs/msg/Imu"
    
    # 可视化消息
    MARKER = "visualization_msgs/msg/Marker"
    MARKER_ARRAY = "visualization_msgs/msg/MarkerArray"
    
    # 几何消息
    TWIST = "geometry_msgs/msg/Twist"
    POSE = "geometry_msgs/msg/Pose"
    POSE_STAMPED = "geometry_msgs/msg/PoseStamped"
    TRANSFORM = "geometry_msgs/msg/Transform"
    TRANSFORM_STAMPED = "geometry_msgs/msg/TransformStamped"
    POINT = "geometry_msgs/msg/Point"
    QUATERNION = "geometry_msgs/msg/Quaternion"
    VECTOR3 = "geometry_msgs/msg/Vector3"
    
    # 导航消息
    ODOMETRY = "nav_msgs/msg/Odometry"
    PATH = "nav_msgs/msg/Path"
    OCCUPANCY_GRID = "nav_msgs/msg/OccupancyGrid"
    
    # 标准消息
    STRING = "std_msgs/msg/String"
    FLOAT64 = "std_msgs/msg/Float64"
    INT32 = "std_msgs/msg/Int32"
    BOOL = "std_msgs/msg/Bool"

class TopicInfo(BaseModel):
    """ROS2 主题信息"""
    name: str = Field(..., description="主题名称")
    message_type: str = Field(..., description="消息类型")
    publishers: List[str] = Field(default_factory=list, description="发布者列表")
    subscribers: List[str] = Field(default_factory=list, description="订阅者列表")
    frequency: Optional[float] = Field(None, description="发布频率 (Hz)")
    last_message_time: Optional[datetime] = Field(None, description="最后消息时间")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class NodeInfo(BaseModel):
    """ROS2 节点信息"""
    name: str = Field(..., description="节点名称")
    namespace: str = Field(..., description="命名空间")
    publishers: List[str] = Field(default_factory=list, description="发布的主题")
    subscribers: List[str] = Field(default_factory=list, description="订阅的主题")
    services: List[str] = Field(default_factory=list, description="提供的服务")
    actions: List[str] = Field(default_factory=list, description="提供的动作")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="节点参数")

class ConnectionInfo(BaseModel):
    """连接信息"""
    client_id: str = Field(..., description="客户端ID")
    connected_at: datetime = Field(..., description="连接时间")
    subscribed_topics: List[str] = Field(default_factory=list, description="订阅的主题")
    message_count: int = Field(default=0, description="消息计数")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class TopicConnection(BaseModel):
    """主题连接信息"""
    topic_name: str = Field(..., description="主题名称")
    message_type: str = Field(..., description="消息类型")
    publishers: List[str] = Field(default_factory=list, description="发布者节点")
    subscribers: List[str] = Field(default_factory=list, description="订阅者节点")
    connection_count: int = Field(default=0, description="连接数")

class NodeTopology(BaseModel):
    """节点拓扑信息"""
    node_name: str = Field(..., description="节点名称")
    namespace: str = Field(default="/", description="命名空间")
    node_type: str = Field(default="node", description="节点类型")
    published_topics: List[str] = Field(default_factory=list, description="发布的主题")
    subscribed_topics: List[str] = Field(default_factory=list, description="订阅的主题")
    services: List[str] = Field(default_factory=list, description="提供的服务")
    actions: List[str] = Field(default_factory=list, description="提供的动作")
    is_active: bool = Field(default=True, description="节点是否活跃")

class SystemTopology(BaseModel):
    """系统拓扑结构"""
    nodes: List[NodeTopology] = Field(default_factory=list, description="节点列表")
    topic_connections: List[TopicConnection] = Field(default_factory=list, description="主题连接")
    isolated_nodes: List[str] = Field(default_factory=list, description="孤立节点")
    node_count: int = Field(default=0, description="节点总数")
    topic_count: int = Field(default=0, description="主题总数")
    connection_count: int = Field(default=0, description="连接总数")
    last_updated: datetime = Field(default_factory=datetime.now, description="最后更新时间")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class SystemStatus(BaseModel):
    """系统状态"""
    ros_domain_id: int = Field(..., description="ROS2 Domain ID")
    active_nodes: int = Field(..., description="活跃节点数")
    active_topics: int = Field(..., description="活跃主题数")
    active_connections: int = Field(..., description="活跃连接数")
    system_time: datetime = Field(..., description="系统时间")
    uptime: float = Field(..., description="运行时间 (秒)")
    memory_usage: float = Field(..., description="内存使用率")
    cpu_usage: float = Field(..., description="CPU 使用率")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class RosMessage(BaseModel):
    """ROS 消息基类"""
    topic: str = Field(..., description="主题名称")
    message_type: str = Field(..., description="消息类型")
    data: Dict[str, Any] = Field(..., description="消息数据")
    timestamp: datetime = Field(..., description="时间戳")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }