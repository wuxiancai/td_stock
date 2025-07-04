#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
异常处理模块
定义自定义异常类和统一的异常处理机制
"""

import os
import sys
import time
import traceback
from functools import wraps
from typing import Optional, Callable, Any

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import get_logger

class TDAnalysisException(Exception):
    """TD分析系统基础异常类"""
    
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        self.message = message
        self.error_code = error_code or 'UNKNOWN_ERROR'
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            'error_code': self.error_code,
            'message': self.message,
            'details': self.details,
            'exception_type': self.__class__.__name__
        }

class DataFetchException(TDAnalysisException):
    """数据获取异常"""
    
    def __init__(self, message: str, stock_code: str = None, **kwargs):
        super().__init__(message, 'DATA_FETCH_ERROR', {'stock_code': stock_code, **kwargs})

class DataProcessingException(TDAnalysisException):
    """数据处理异常"""
    
    def __init__(self, message: str, data_type: str = None, **kwargs):
        super().__init__(message, 'DATA_PROCESSING_ERROR', {'data_type': data_type, **kwargs})

class TDCalculationException(TDAnalysisException):
    """TD序列计算异常"""
    
    def __init__(self, message: str, calculation_step: str = None, **kwargs):
        super().__init__(message, 'TD_CALCULATION_ERROR', {'calculation_step': calculation_step, **kwargs})

class ChartGenerationException(TDAnalysisException):
    """图表生成异常"""
    
    def __init__(self, message: str, chart_type: str = None, **kwargs):
        super().__init__(message, 'CHART_GENERATION_ERROR', {'chart_type': chart_type, **kwargs})

class WebServiceException(TDAnalysisException):
    """Web服务异常"""
    
    def __init__(self, message: str, endpoint: str = None, **kwargs):
        super().__init__(message, 'WEB_SERVICE_ERROR', {'endpoint': endpoint, **kwargs})

class ConfigurationException(TDAnalysisException):
    """配置异常"""
    
    def __init__(self, message: str, config_key: str = None, **kwargs):
        super().__init__(message, 'CONFIGURATION_ERROR', {'config_key': config_key, **kwargs})

class ValidationException(TDAnalysisException):
    """数据验证异常"""
    
    def __init__(self, message: str, field_name: str = None, **kwargs):
        super().__init__(message, 'VALIDATION_ERROR', {'field_name': field_name, **kwargs})

class RetryableException(TDAnalysisException):
    """可重试异常"""
    
    def __init__(self, message: str, max_retries: int = 3, **kwargs):
        super().__init__(message, 'RETRYABLE_ERROR', {'max_retries': max_retries, **kwargs})
        self.max_retries = max_retries

class ExceptionHandler:
    """异常处理器"""
    
    def __init__(self):
        self.logger = get_logger('exception_handler')
    
    def handle_exception(self, exc: Exception, context: str = None) -> dict:
        """处理异常并返回错误信息"""
        error_info = {
            'success': False,
            'timestamp': time.time(),
            'context': context
        }
        
        if isinstance(exc, TDAnalysisException):
            error_info.update(exc.to_dict())
            self.logger.error(f"业务异常 [{context}]: {exc.message}", extra=exc.details)
        else:
            error_info.update({
                'error_code': 'SYSTEM_ERROR',
                'message': str(exc),
                'exception_type': exc.__class__.__name__
            })
            self.logger.error(f"系统异常 [{context}]: {str(exc)}")
            self.logger.debug(f"异常堆栈: {traceback.format_exc()}")
        
        return error_info
    
    def log_and_reraise(self, exc: Exception, context: str = None):
        """记录异常并重新抛出"""
        self.handle_exception(exc, context)
        raise exc

# 全局异常处理器实例
exception_handler = ExceptionHandler()

def handle_exceptions(context: str = None, reraise: bool = True, default_return: Any = None):
    """异常处理装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_info = exception_handler.handle_exception(e, context or func.__name__)
                
                if reraise:
                    raise
                else:
                    return default_return or error_info
        
        return wrapper
    return decorator

def retry_on_exception(max_retries: int = 3, delay: float = 1.0, 
                      backoff_factor: float = 2.0, 
                      exceptions: tuple = (Exception,)):
    """重试装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger('retry')
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        logger.error(f"{func.__name__} 重试 {max_retries} 次后仍然失败: {str(e)}")
                        raise
                    
                    wait_time = delay * (backoff_factor ** attempt)
                    logger.warning(f"{func.__name__} 第 {attempt + 1} 次尝试失败: {str(e)}, {wait_time:.1f}秒后重试")
                    time.sleep(wait_time)
            
            # 这行代码理论上不会执行到，但为了类型检查
            raise last_exception
        
        return wrapper
    return decorator

def safe_execute(func: Callable, *args, default_return: Any = None, 
                log_errors: bool = True, **kwargs) -> Any:
    """安全执行函数，捕获所有异常"""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if log_errors:
            logger = get_logger('safe_execute')
            logger.error(f"安全执行失败 {func.__name__}: {str(e)}")
        return default_return

class CircuitBreaker:
    """熔断器模式实现"""
    
    def __init__(self, failure_threshold: int = 5, timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
        self.logger = get_logger('circuit_breaker')
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """通过熔断器调用函数"""
        if self.state == 'OPEN':
            if time.time() - self.last_failure_time < self.timeout:
                raise TDAnalysisException("熔断器开启，拒绝调用", 'CIRCUIT_BREAKER_OPEN')
            else:
                self.state = 'HALF_OPEN'
                self.logger.info("熔断器进入半开状态")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        """成功时的处理"""
        self.failure_count = 0
        if self.state == 'HALF_OPEN':
            self.state = 'CLOSED'
            self.logger.info("熔断器关闭")
    
    def _on_failure(self):
        """失败时的处理"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'
            self.logger.warning(f"熔断器开启，失败次数: {self.failure_count}")

def with_circuit_breaker(failure_threshold: int = 5, timeout: float = 60.0):
    """熔断器装饰器"""
    circuit_breaker = CircuitBreaker(failure_threshold, timeout)
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return circuit_breaker.call(func, *args, **kwargs)
        return wrapper
    return decorator

# 便捷函数
def get_exception_handler():
    """获取异常处理器的便捷函数"""
    return exception_handler