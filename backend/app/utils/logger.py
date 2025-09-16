"""
日志工具模块
提供结构化日志记录功能
"""

import logging
import sys
import json
from datetime import datetime
from typing import Any, Dict, Optional
from pathlib import Path


class JsonFormatter(logging.Formatter):
    """JSON 格式化器"""
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录为 JSON 格式"""
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # 添加异常信息
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # 添加额外字段
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
        
        return json.dumps(log_entry, ensure_ascii=False)


class ContextLogger:
    """上下文日志记录器"""
    
    def __init__(self, name: str, extra_fields: Optional[Dict[str, Any]] = None):
        self.logger = logging.getLogger(name)
        self.extra_fields = extra_fields or {}
    
    def _log(self, level: int, message: str, **kwargs):
        """内部日志记录方法"""
        extra_fields = {**self.extra_fields, **kwargs}
        
        # 创建 LogRecord 并添加额外字段
        record = self.logger.makeRecord(
            self.logger.name, level, __file__, 0, message, (), None
        )
        record.extra_fields = extra_fields
        
        self.logger.handle(record)
    
    def debug(self, message: str, **kwargs):
        """记录调试信息"""
        self._log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """记录信息"""
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """记录警告"""
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """记录错误"""
        self._log(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """记录严重错误"""
        self._log(logging.CRITICAL, message, **kwargs)


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    use_json: bool = True
) -> None:
    """
    设置日志配置
    
    Args:
        level: 日志级别
        log_file: 日志文件路径
        use_json: 是否使用 JSON 格式
    """
    # 设置日志级别
    log_level = getattr(logging, level.upper())
    
    # 创建根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # 清除现有的处理器
    root_logger.handlers.clear()
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    if use_json:
        console_formatter = JsonFormatter()
    else:
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # 文件处理器（如果指定了日志文件）
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(log_level)
        file_handler.setFormatter(console_formatter)
        root_logger.addHandler(file_handler)


def get_logger(name: str, **extra_fields) -> ContextLogger:
    """
    获取上下文日志记录器
    
    Args:
        name: 日志器名称
        **extra_fields: 额外的上下文字段
    
    Returns:
        ContextLogger: 上下文日志记录器
    """
    return ContextLogger(name, extra_fields)


# 性能监控装饰器
def log_performance(logger: ContextLogger):
    """性能监控装饰器"""
    def decorator(func):
        import time
        from functools import wraps
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                logger.info(
                    f"Function {func.__name__} executed successfully",
                    function=func.__name__,
                    execution_time=execution_time,
                    status="success"
                )
                
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(
                    f"Function {func.__name__} failed",
                    function=func.__name__,
                    execution_time=execution_time,
                    error=str(e),
                    status="error"
                )
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                logger.info(
                    f"Function {func.__name__} executed successfully",
                    function=func.__name__,
                    execution_time=execution_time,
                    status="success"
                )
                
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(
                    f"Function {func.__name__} failed",
                    function=func.__name__,
                    execution_time=execution_time,
                    error=str(e),
                    status="error"
                )
                raise
        
        # 检查是否为异步函数
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# 默认日志器
default_logger = get_logger("ros_web_viz")
