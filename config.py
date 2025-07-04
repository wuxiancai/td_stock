#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统配置文件
集中管理所有配置项，支持不同环境配置
"""

import os
from datetime import time

class Config:
    """基础配置类"""
    
    # 项目根目录
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    # 数据目录
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    RAW_DATA_DIR = os.path.join(DATA_DIR, 'raw')
    PROCESSED_DATA_DIR = os.path.join(DATA_DIR, 'processed')
    
    # 图表目录
    HTML_CHARTS_DIR = os.path.join(BASE_DIR, 'html_charts')
    CHART_OUTPUT_DIR = os.path.join(BASE_DIR, 'charts')
    
    # 日志配置
    LOG_DIR = os.path.join(BASE_DIR, 'logs')
    LOG_FILE = os.path.join(LOG_DIR, 'td_analysis.log')
    LOG_LEVEL = 'INFO'
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5
    
    # 数据获取配置
    STOCK_DATA_PERIOD = 60  # 获取多少天的历史数据
    MAX_RETRY_TIMES = 3  # 最大重试次数
    RETRY_DELAY = 1  # 重试延迟（秒）
    REQUEST_TIMEOUT = 30  # 请求超时时间（秒）
    
    # TD序列配置
    TD_SETUP_THRESHOLD = 3  # Setup信号阈值
    TD_LOOKBACK_PERIOD = 4  # 回看周期
    
    # Web服务配置
    WEB_HOST = '0.0.0.0'
    WEB_PORT = 8080
    WEB_DEBUG = True
    SECRET_KEY = 'td_sequential_stock_analysis_2025'
    
    # 缓存配置
    CACHE_ENABLED = True
    CACHE_TIMEOUT = 300  # 缓存超时时间（秒）
    
    # 安全配置
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    CSRF_ENABLED = True
    
    # 调度配置
    SCHEDULE_TIME = '17:00'  # 每日执行时间
    TIMEZONE = 'Asia/Shanghai'
    
    @classmethod
    def init_directories(cls):
        """初始化必要的目录"""
        directories = [
            cls.DATA_DIR,
            cls.RAW_DATA_DIR,
            cls.PROCESSED_DATA_DIR,
            cls.HTML_CHARTS_DIR,
            cls.CHART_OUTPUT_DIR,
            cls.LOG_DIR
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)

class DevelopmentConfig(Config):
    """开发环境配置"""
    WEB_DEBUG = True
    LOG_LEVEL = 'DEBUG'
    CACHE_TIMEOUT = 60  # 开发环境缓存时间短一些

class ProductionConfig(Config):
    """生产环境配置"""
    WEB_DEBUG = False
    LOG_LEVEL = 'WARNING'
    WEB_HOST = '127.0.0.1'  # 生产环境只监听本地
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'production_secret_key_change_me'
    CACHE_TIMEOUT = 600  # 生产环境缓存时间长一些

class TestingConfig(Config):
    """测试环境配置"""
    WEB_DEBUG = True
    LOG_LEVEL = 'DEBUG'
    STOCK_DATA_PERIOD = 30  # 测试环境获取较少数据
    CACHE_ENABLED = False  # 测试环境禁用缓存

# 配置映射
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config(config_name=None):
    """获取配置对象"""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')
    
    return config.get(config_name, config['default'])