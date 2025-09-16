"""
自定义异常类模块
"""

from typing import Any, Dict, Optional


class RosWebVizException(Exception):
    """ROS Web 可视化系统基础异常类"""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class ConnectionError(RosWebVizException):
    """连接相关异常"""
    pass


class RosbridgeError(ConnectionError):
    """Rosbridge 连接异常"""
    pass


class WebSocketError(ConnectionError):
    """WebSocket 连接异常"""
    pass


class ValidationError(RosWebVizException):
    """数据验证异常"""
    pass


class TopicError(RosWebVizException):
    """ROS2 主题相关异常"""
    pass


class NodeError(RosWebVizException):
    """ROS2 节点相关异常"""
    pass


class ServiceError(RosWebVizException):
    """ROS2 服务相关异常"""
    pass


class PluginError(RosWebVizException):
    """插件相关异常"""
    pass


class VisualizationError(RosWebVizException):
    """可视化相关异常"""
    pass


class ConfigurationError(RosWebVizException):
    """配置相关异常"""
    pass


class AuthenticationError(RosWebVizException):
    """认证相关异常"""
    pass


class AuthorizationError(RosWebVizException):
    """授权相关异常"""
    pass


class RateLimitError(RosWebVizException):
    """频率限制异常"""
    pass


class ResourceNotFoundError(RosWebVizException):
    """资源未找到异常"""
    pass


class ResourceExistsError(RosWebVizException):
    """资源已存在异常"""
    pass


class SerializationError(RosWebVizException):
    """序列化异常"""
    pass


class DeserializationError(RosWebVizException):
    """反序列化异常"""
    pass


# 错误代码常量
class ErrorCodes:
    """错误代码常量"""
    
    # 通用错误
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    
    # 连接错误
    CONNECTION_FAILED = "CONNECTION_FAILED"
    CONNECTION_TIMEOUT = "CONNECTION_TIMEOUT"
    CONNECTION_LOST = "CONNECTION_LOST"
    WEBSOCKET_ERROR = "WEBSOCKET_ERROR"
    ROSBRIDGE_ERROR = "ROSBRIDGE_ERROR"
    
    # ROS2 相关错误
    TOPIC_NOT_FOUND = "TOPIC_NOT_FOUND"
    TOPIC_TYPE_MISMATCH = "TOPIC_TYPE_MISMATCH"
    NODE_NOT_FOUND = "NODE_NOT_FOUND"
    SERVICE_NOT_FOUND = "SERVICE_NOT_FOUND"
    SERVICE_CALL_FAILED = "SERVICE_CALL_FAILED"
    MESSAGE_SERIALIZATION_ERROR = "MESSAGE_SERIALIZATION_ERROR"
    MESSAGE_DESERIALIZATION_ERROR = "MESSAGE_DESERIALIZATION_ERROR"
    
    # 插件错误
    PLUGIN_NOT_FOUND = "PLUGIN_NOT_FOUND"
    PLUGIN_LOAD_ERROR = "PLUGIN_LOAD_ERROR"
    PLUGIN_EXECUTION_ERROR = "PLUGIN_EXECUTION_ERROR"
    
    # 可视化错误
    RENDER_ERROR = "RENDER_ERROR"
    VISUALIZATION_ERROR = "VISUALIZATION_ERROR"
    
    # 认证和授权错误
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    INVALID_TOKEN = "INVALID_TOKEN"
    AUTHORIZATION_DENIED = "AUTHORIZATION_DENIED"
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
    
    # 资源错误
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_EXISTS = "RESOURCE_EXISTS"
    RESOURCE_LIMIT_EXCEEDED = "RESOURCE_LIMIT_EXCEEDED"
    
    # 速率限制
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"


def create_error_response(exception: RosWebVizException) -> Dict[str, Any]:
    """
    创建标准化的错误响应
    
    Args:
        exception: 异常对象
        
    Returns:
        Dict: 标准化的错误响应
    """
    return {
        "error": {
            "code": exception.error_code or ErrorCodes.UNKNOWN_ERROR,
            "message": exception.message,
            "details": exception.details,
            "type": exception.__class__.__name__
        }
    }
