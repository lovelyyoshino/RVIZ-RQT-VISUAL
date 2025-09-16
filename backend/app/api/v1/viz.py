"""
可视化相关 API 端点
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
import logging

from ...core.config import get_settings
from ...models.viz import VisualizationState, PluginInfo, CameraSettings, RenderSettings
from ...services.rosbridge import RosbridgeService
from ...services.dependencies import get_rosbridge_service

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/visualization/state", response_model=VisualizationState)
async def get_visualization_state(
    service: RosbridgeService = Depends(get_rosbridge_service)
):
    """获取可视化状态"""
    try:
        state = await service.get_visualization_state()
        return state
    except Exception as e:
        logger.error(f"Failed to get visualization state: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/visualization/camera")
async def update_camera_settings(
    settings: CameraSettings,
    service: RosbridgeService = Depends(get_rosbridge_service)
):
    """更新相机设置"""
    try:
        success = await service.update_camera_settings(settings)
        return {"success": success, "action": "camera_updated"}
    except Exception as e:
        logger.error(f"Failed to update camera settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/visualization/render")
async def update_render_settings(
    settings: RenderSettings,
    service: RosbridgeService = Depends(get_rosbridge_service)
):
    """更新渲染设置"""
    try:
        success = await service.update_render_settings(settings)
        return {"success": success, "action": "render_updated"}
    except Exception as e:
        logger.error(f"Failed to update render settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/visualization/plugins", response_model=List[PluginInfo])
async def get_available_plugins(
    service: RosbridgeService = Depends(get_rosbridge_service)
):
    """获取可用插件列表"""
    try:
        plugins = await service.get_available_plugins()
        return plugins
    except Exception as e:
        logger.error(f"Failed to get plugins: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/visualization/plugins/{plugin_id}/enable")
async def enable_plugin(
    plugin_id: str,
    service: RosbridgeService = Depends(get_rosbridge_service)
):
    """启用插件"""
    try:
        success = await service.enable_plugin(plugin_id)
        return {"success": success, "plugin_id": plugin_id, "action": "enabled"}
    except Exception as e:
        logger.error(f"Failed to enable plugin {plugin_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/visualization/plugins/{plugin_id}/disable")
async def disable_plugin(
    plugin_id: str,
    service: RosbridgeService = Depends(get_rosbridge_service)
):
    """禁用插件"""
    try:
        success = await service.disable_plugin(plugin_id)
        return {"success": success, "plugin_id": plugin_id, "action": "disabled"}
    except Exception as e:
        logger.error(f"Failed to disable plugin {plugin_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/visualization/objects/add")
async def add_visualization_object(
    object_data: Dict[str, Any],
    service: RosbridgeService = Depends(get_rosbridge_service)
):
    """添加可视化对象"""
    try:
        object_id = await service.add_visualization_object(object_data)
        return {"success": True, "object_id": object_id, "action": "object_added"}
    except Exception as e:
        logger.error(f"Failed to add visualization object: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/visualization/objects/{object_id}")
async def remove_visualization_object(
    object_id: str,
    service: RosbridgeService = Depends(get_rosbridge_service)
):
    """移除可视化对象"""
    try:
        success = await service.remove_visualization_object(object_id)
        return {"success": success, "object_id": object_id, "action": "object_removed"}
    except Exception as e:
        logger.error(f"Failed to remove visualization object {object_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
