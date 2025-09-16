#!/usr/bin/env python3
"""
测试点云订阅的简单WebSocket客户端
用于验证前端到后端的订阅是否正常工作
"""

import asyncio
import websockets
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_pointcloud_subscription():
    """测试点云订阅"""

    uri = "ws://localhost:8000/ws"

    try:
        async with websockets.connect(uri) as websocket:
            logger.info("✅ Connected to WebSocket")

            # 订阅点云主题
            topics_to_test = [
                ("/cost_cloud", "sensor_msgs/msg/PointCloud2"),
                ("/fastlio2/world_cloud", "sensor_msgs/msg/PointCloud2")
            ]

            for topic, msg_type in topics_to_test:
                subscribe_msg = {
                    "op": "subscribe",
                    "topic": topic,
                    "type": msg_type
                }

                await websocket.send(json.dumps(subscribe_msg))
                logger.info(f"📡 Sent subscription request for {topic}")

            # 监听消息
            message_count = {}
            timeout = 30  # 30秒超时

            logger.info(f"🔍 Listening for messages (timeout: {timeout}s)...")

            try:
                while True:
                    # 等待消息，设置超时
                    message = await asyncio.wait_for(websocket.recv(), timeout=timeout)
                    data = json.loads(message)

                    if data.get("op") == "publish":
                        topic = data.get("topic")
                        if topic not in message_count:
                            message_count[topic] = 0
                        message_count[topic] += 1

                        logger.info(f"🎉 Received message #{message_count[topic]} from {topic}")

                        # 显示消息的基本信息
                        msg_data = data.get("msg", {})
                        logger.info(f"   - Message keys: {list(msg_data.keys())}")

                        if "width" in msg_data and "height" in msg_data:
                            logger.info(f"   - Point cloud size: {msg_data['width']}x{msg_data['height']}")

                        # 只处理前几条消息作为测试
                        total_messages = sum(message_count.values())
                        if total_messages >= 5:
                            logger.info("✅ Received enough test messages, stopping...")
                            break
                    else:
                        logger.info(f"📨 Other message: {data.get('op', 'unknown')}")

            except asyncio.TimeoutError:
                logger.warning(f"⏰ Timeout after {timeout}s")

                if not message_count:
                    logger.error("❌ No messages received!")
                    logger.error("💡 This suggests the problem is:")
                    logger.error("   1. ROS topics are not publishing data")
                    logger.error("   2. Backend is not forwarding messages to WebSocket clients")
                    logger.error("   3. WebSocket subscription is not working")
                else:
                    logger.info(f"✅ Received some messages: {message_count}")

            # 显示统计
            logger.info("📊 Final statistics:")
            for topic, count in message_count.items():
                logger.info(f"   - {topic}: {count} messages")

            return len(message_count) > 0

    except Exception as e:
        logger.error(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    logger.info("🚀 Starting point cloud subscription test...")
    success = asyncio.run(test_pointcloud_subscription())

    if success:
        logger.info("✅ Test completed successfully - WebSocket subscription is working!")
    else:
        logger.error("❌ Test failed - please check ROS system and backend")