#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
缓存管理模块
提供内存缓存功能以提升系统性能
"""

import os
import sys
import time
import pickle
import hashlib
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Optional, Callable

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import get_config
from utils.logger import get_logger

class CacheManager:
    """缓存管理器"""
    
    def __init__(self):
        self.config = get_config()
        self.logger = get_logger('cache')
        self._cache = {}
        self._cache_times = {}
        self.enabled = self.config.CACHE_ENABLED
        self.default_timeout = self.config.CACHE_TIMEOUT
    
    def _generate_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """生成缓存键"""
        # 创建参数的哈希值
        params_str = f"{args}_{sorted(kwargs.items())}"
        params_hash = hashlib.md5(params_str.encode()).hexdigest()
        return f"{func_name}_{params_hash}"
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存数据"""
        if not self.enabled:
            return None
        
        if key not in self._cache:
            return None
        
        # 检查是否过期
        cache_time = self._cache_times.get(key)
        if cache_time and datetime.now() - cache_time > timedelta(seconds=self.default_timeout):
            self.delete(key)
            return None
        
        self.logger.debug(f"缓存命中: {key}")
        return self._cache[key]
    
    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> None:
        """设置缓存数据"""
        if not self.enabled:
            return
        
        self._cache[key] = value
        self._cache_times[key] = datetime.now()
        
        self.logger.debug(f"缓存设置: {key}")
    
    def delete(self, key: str) -> None:
        """删除缓存数据"""
        if key in self._cache:
            del self._cache[key]
        if key in self._cache_times:
            del self._cache_times[key]
        
        self.logger.debug(f"缓存删除: {key}")
    
    def clear(self) -> None:
        """清空所有缓存"""
        self._cache.clear()
        self._cache_times.clear()
        self.logger.info("缓存已清空")
    
    def get_stats(self) -> dict:
        """获取缓存统计信息"""
        total_items = len(self._cache)
        expired_items = 0
        
        current_time = datetime.now()
        for cache_time in self._cache_times.values():
            if current_time - cache_time > timedelta(seconds=self.default_timeout):
                expired_items += 1
        
        return {
            'total_items': total_items,
            'expired_items': expired_items,
            'active_items': total_items - expired_items,
            'enabled': self.enabled,
            'default_timeout': self.default_timeout
        }
    
    def cleanup_expired(self) -> int:
        """清理过期缓存"""
        if not self.enabled:
            return 0
        
        current_time = datetime.now()
        expired_keys = []
        
        for key, cache_time in self._cache_times.items():
            if current_time - cache_time > timedelta(seconds=self.default_timeout):
                expired_keys.append(key)
        
        for key in expired_keys:
            self.delete(key)
        
        if expired_keys:
            self.logger.info(f"清理了 {len(expired_keys)} 个过期缓存项")
        
        return len(expired_keys)

# 全局缓存管理器实例
cache_manager = CacheManager()

def cached(timeout: Optional[int] = None, key_prefix: str = ''):
    """缓存装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not cache_manager.enabled:
                return func(*args, **kwargs)
            
            # 生成缓存键
            func_name = f"{key_prefix}{func.__name__}" if key_prefix else func.__name__
            cache_key = cache_manager._generate_key(func_name, args, kwargs)
            
            # 尝试从缓存获取
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result, timeout)
            
            return result
        
        return wrapper
    return decorator

def cache_clear():
    """清空缓存的便捷函数"""
    cache_manager.clear()

def cache_stats():
    """获取缓存统计的便捷函数"""
    return cache_manager.get_stats()

def cache_cleanup():
    """清理过期缓存的便捷函数"""
    return cache_manager.cleanup_expired()

class FileCacheManager:
    """文件缓存管理器"""
    
    def __init__(self, cache_dir: str = None):
        self.config = get_config()
        self.logger = get_logger('file_cache')
        self.cache_dir = cache_dir or os.path.join(self.config.BASE_DIR, '.cache')
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def _get_cache_path(self, key: str) -> str:
        """获取缓存文件路径"""
        safe_key = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{safe_key}.cache")
    
    def get(self, key: str, max_age: int = 3600) -> Optional[Any]:
        """从文件获取缓存数据"""
        cache_path = self._get_cache_path(key)
        
        if not os.path.exists(cache_path):
            return None
        
        # 检查文件年龄
        file_age = time.time() - os.path.getmtime(cache_path)
        if file_age > max_age:
            self.delete(key)
            return None
        
        try:
            with open(cache_path, 'rb') as f:
                data = pickle.load(f)
            self.logger.debug(f"文件缓存命中: {key}")
            return data
        except Exception as e:
            self.logger.error(f"读取文件缓存失败: {key}, 错误: {e}")
            self.delete(key)
            return None
    
    def set(self, key: str, value: Any) -> bool:
        """设置文件缓存数据"""
        cache_path = self._get_cache_path(key)
        
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(value, f)
            self.logger.debug(f"文件缓存设置: {key}")
            return True
        except Exception as e:
            self.logger.error(f"设置文件缓存失败: {key}, 错误: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """删除文件缓存"""
        cache_path = self._get_cache_path(key)
        
        try:
            if os.path.exists(cache_path):
                os.remove(cache_path)
                self.logger.debug(f"文件缓存删除: {key}")
            return True
        except Exception as e:
            self.logger.error(f"删除文件缓存失败: {key}, 错误: {e}")
            return False
    
    def clear(self) -> int:
        """清空所有文件缓存"""
        count = 0
        try:
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.cache'):
                    os.remove(os.path.join(self.cache_dir, filename))
                    count += 1
            self.logger.info(f"清空了 {count} 个文件缓存")
        except Exception as e:
            self.logger.error(f"清空文件缓存失败: {e}")
        
        return count

# 全局文件缓存管理器实例
file_cache_manager = FileCacheManager()

def file_cached(max_age: int = 3600, key_prefix: str = ''):
    """文件缓存装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            func_name = f"{key_prefix}{func.__name__}" if key_prefix else func.__name__
            cache_key = cache_manager._generate_key(func_name, args, kwargs)
            
            # 尝试从文件缓存获取
            cached_result = file_cache_manager.get(cache_key, max_age)
            if cached_result is not None:
                return cached_result
            
            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            file_cache_manager.set(cache_key, result)
            
            return result
        
        return wrapper
    return decorator