"""
应用配置管理
"""

from pydantic import Field
from pydantic_settings import BaseSettings

from functools import lru_cache

class Settings(BaseSettings):
    """应用配置"""
    
    # Web 服务配置
    web_host: str = Field(default="0.0.0.0", description="Web 服务主机")
    web_port: int = Field(default=8000, description="Web 服务端口")
    debug: bool = Field(default=False, description="调试模式")
    
    # ROS2 配置
    ros_domain_id: int = Field(default=0, description="ROS2 Domain ID")
    ros_discovery_server: str = Field(default="", description="ROS2 Discovery Server")
    
    # Rosbridge 配置
    rosbridge_host: str = Field(default="0.0.0.0", description="Rosbridge 主机")
    rosbridge_port: int = Field(default=9090, description="Rosbridge 端口")
    max_connections: int = Field(default=100, description="最大连接数")
    message_buffer_size: int = Field(default=10000, description="消息缓冲区大小")
    
    # 安全配置
    secret_key: str = Field(default="ros-web-viz-secret-key", description="JWT 密钥")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings() -> Settings:
    """获取配置实例"""
    return Settings()