"""
可视化数据模型
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum

class PluginType(str, Enum):
    """插件类型"""
    RENDERER = "renderer"
    WIDGET = "widget"
    TOOL = "tool"
    FILTER = "filter"

class PluginStatus(str, Enum):
    """插件状态"""
    LOADED = "loaded"
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"

class PluginInfo(BaseModel):
    """插件信息"""
    id: str = Field(..., description="插件ID")
    name: str = Field(..., description="插件名称")
    version: str = Field(..., description="版本")
    description: str = Field(..., description="描述")
    author: str = Field(..., description="作者")
    plugin_type: PluginType = Field(..., description="插件类型")
    status: PluginStatus = Field(..., description="状态")
    supported_message_types: List[str] = Field(default_factory=list, description="支持的消息类型")
    config: Dict[str, Any] = Field(default_factory=dict, description="配置参数")

class CameraSettings(BaseModel):
    """相机设置"""
    position: Tuple[float, float, float] = Field(..., description="相机位置 (x, y, z)")
    target: Tuple[float, float, float] = Field(..., description="目标位置 (x, y, z)")
    up: Tuple[float, float, float] = Field(default=(0, 0, 1), description="上方向向量")
    fov: float = Field(default=75.0, description="视野角度")
    near: float = Field(default=0.1, description="近裁剪面")
    far: float = Field(default=1000.0, description="远裁剪面")

class RenderSettings(BaseModel):
    """渲染设置"""
    background_color: str = Field(default="#2c3e50", description="背景颜色")
    grid_visible: bool = Field(default=True, description="网格可见性")
    axes_visible: bool = Field(default=True, description="坐标轴可见性")
    lighting_enabled: bool = Field(default=True, description="光照启用")
    shadows_enabled: bool = Field(default=False, description="阴影启用")
    anti_aliasing: bool = Field(default=True, description="抗锯齿")
    max_points: int = Field(default=100000, description="最大点数")
    point_size: float = Field(default=1.0, description="点大小")

class PointCloudData(BaseModel):
    """点云数据"""
    points: List[Tuple[float, float, float]] = Field(..., description="点坐标列表")
    colors: Optional[List[Tuple[float, float, float]]] = Field(None, description="颜色列表")
    intensities: Optional[List[float]] = Field(None, description="强度列表")
    frame_id: str = Field(..., description="坐标系ID")

class MarkerData(BaseModel):
    """标记数据"""
    id: str = Field(..., description="标记ID")
    marker_type: str = Field(..., description="标记类型")
    position: Tuple[float, float, float] = Field(..., description="位置")
    orientation: Tuple[float, float, float, float] = Field(..., description="四元数方向")
    scale: Tuple[float, float, float] = Field(..., description="缩放")
    color: Tuple[float, float, float, float] = Field(..., description="RGBA颜色")
    frame_id: str = Field(..., description="坐标系ID")
    text: Optional[str] = Field(None, description="文本内容")

class VisualizationState(BaseModel):
    """可视化状态"""
    active_plugins: List[str] = Field(default_factory=list, description="活跃插件")
    subscribed_topics: List[str] = Field(default_factory=list, description="订阅的主题")
    camera_settings: CameraSettings = Field(..., description="相机设置")
    render_settings: RenderSettings = Field(..., description="渲染设置")
    objects_count: int = Field(default=0, description="对象数量")
    performance_stats: Dict[str, float] = Field(default_factory=dict, description="性能统计")

class SceneObject(BaseModel):
    """场景对象"""
    id: str = Field(..., description="对象ID")
    object_type: str = Field(..., description="对象类型")
    topic: str = Field(..., description="关联主题")
    visible: bool = Field(default=True, description="可见性")
    transform: Dict[str, Any] = Field(default_factory=dict, description="变换矩阵")
    properties: Dict[str, Any] = Field(default_factory=dict, description="对象属性")