#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一日志管理模块
提供结构化的日志记录功能
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from functools import wraps
import traceback

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import get_config

class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # 青色
        'INFO': '\033[32m',     # 绿色
        'WARNING': '\033[33m',  # 黄色
        'ERROR': '\033[31m',    # 红色
        'CRITICAL': '\033[35m', # 紫色
        'RESET': '\033[0m'      # 重置
    }
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        record.levelname = f"{log_color}{record.levelname}{self.COLORS['RESET']}"
        return super().format(record)

class LoggerManager:
    """日志管理器"""
    
    _loggers = {}
    _config = get_config()
    
    @classmethod
    def get_logger(cls, name=None):
        """获取日志记录器"""
        if name is None:
            name = 'td_analysis'
        
        if name not in cls._loggers:
            cls._loggers[name] = cls._create_logger(name)
        
        return cls._loggers[name]
    
    @classmethod
    def _create_logger(cls, name):
        """创建日志记录器"""
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, cls._config.LOG_LEVEL))
        
        # 避免重复添加处理器
        if logger.handlers:
            return logger
        
        # 确保日志目录存在
        os.makedirs(cls._config.LOG_DIR, exist_ok=True)
        
        # 文件处理器
        file_handler = logging.handlers.RotatingFileHandler(
            cls._config.LOG_FILE,
            maxBytes=cls._config.LOG_MAX_BYTES,
            backupCount=cls._config.LOG_BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(cls._config.LOG_FORMAT)
        file_handler.setFormatter(file_formatter)
        
        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, cls._config.LOG_LEVEL))
        console_formatter = ColoredFormatter(cls._config.LOG_FORMAT)
        console_handler.setFormatter(console_formatter)
        
        # 添加处理器
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger

def log_execution_time(func):
    """记录函数执行时间的装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger = LoggerManager.get_logger()
        start_time = datetime.now()
        
        try:
            logger.info(f"开始执行 {func.__name__}")
            result = func(*args, **kwargs)
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            logger.info(f"{func.__name__} 执行完成，耗时: {execution_time:.2f}秒")
            return result
        except Exception as e:
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            logger.error(f"{func.__name__} 执行失败，耗时: {execution_time:.2f}秒，错误: {str(e)}")
            logger.debug(f"详细错误信息: {traceback.format_exc()}")
            raise
    
    return wrapper

def log_exception(func):
    """记录异常的装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger = LoggerManager.get_logger()
        
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"{func.__name__} 发生异常: {str(e)}")
            logger.debug(f"详细错误信息: {traceback.format_exc()}")
            raise
    
    return wrapper

class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, name):
        self.name = name
        self.logger = LoggerManager.get_logger()
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.debug(f"开始监控 {self.name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = datetime.now()
        execution_time = (end_time - self.start_time).total_seconds()
        
        if exc_type is None:
            self.logger.info(f"{self.name} 完成，耗时: {execution_time:.2f}秒")
        else:
            self.logger.error(f"{self.name} 异常结束，耗时: {execution_time:.2f}秒，异常: {exc_val}")

# 便捷函数
def get_logger(name=None):
    """获取日志记录器的便捷函数"""
    return LoggerManager.get_logger(name)