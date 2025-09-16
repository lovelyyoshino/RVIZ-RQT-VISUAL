"""
pytest 配置文件
"""

import pytest
import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import Mock

from fastapi.testclient import TestClient
from app.main import app
from app.core.config import get_settings


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def client() -> TestClient:
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def settings():
    """获取测试设置"""
    return get_settings()


@pytest.fixture
def mock_rosbridge_service():
    """模拟 Rosbridge 服务"""
    mock_service = Mock()
    mock_service.get_topics.return_value = []
    mock_service.get_nodes.return_value = []
    mock_service.get_system_status.return_value = {
        "active_nodes": 0,
        "active_topics": 0,
        "active_connections": 0
    }
    return mock_service


@pytest.fixture
async def async_client() -> AsyncGenerator[TestClient, None]:
    """创建异步测试客户端"""
    async with TestClient(app) as client:
        yield client


# 测试数据
@pytest.fixture
def sample_topic_data():
    """示例主题数据"""
    return {
        "name": "/test_topic",
        "message_type": "std_msgs/msg/String",
        "publishers": ["test_node"],
        "subscribers": []
    }


@pytest.fixture
def sample_node_data():
    """示例节点数据"""
    return {
        "name": "test_node",
        "namespace": "/",
        "publishers": ["/test_topic"],
        "subscribers": [],
        "services": [],
        "actions": [],
        "parameters": {}
    }


@pytest.fixture
def sample_message_data():
    """示例消息数据"""
    return {
        "data": "Hello, ROS2!"
    }
