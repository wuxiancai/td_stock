#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据验证模块
提供输入数据的验证和清洗功能
"""

import re
import os
import sys
import pandas as pd
from datetime import datetime, date
from typing import Any, List, Dict, Optional, Union

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.exceptions import ValidationException
from utils.logger import get_logger

class DataValidator:
    """数据验证器"""
    
    def __init__(self):
        self.logger = get_logger('validator')
    
    def validate_stock_code(self, stock_code: str) -> str:
        """验证股票代码"""
        if not stock_code:
            raise ValidationException("股票代码不能为空", 'stock_code')
        
        # 清理股票代码
        stock_code = str(stock_code).strip().upper()
        
        # A股股票代码格式验证
        if not re.match(r'^[0-9]{6}$', stock_code):
            raise ValidationException(f"无效的股票代码格式: {stock_code}", 'stock_code')
        
        return stock_code
    
    def validate_date(self, date_value: Union[str, datetime, date], 
                     field_name: str = 'date') -> datetime:
        """验证日期"""
        if not date_value:
            raise ValidationException(f"{field_name}不能为空", field_name)
        
        if isinstance(date_value, str):
            try:
                # 尝试多种日期格式
                for fmt in ['%Y-%m-%d', '%Y%m%d', '%Y/%m/%d', '%Y-%m-%d %H:%M:%S']:
                    try:
                        return datetime.strptime(date_value, fmt)
                    except ValueError:
                        continue
                raise ValueError("无法解析日期格式")
            except ValueError:
                raise ValidationException(f"无效的日期格式: {date_value}", field_name)
        
        elif isinstance(date_value, date):
            if isinstance(date_value, datetime):
                return date_value
            else:
                return datetime.combine(date_value, datetime.min.time())
        
        else:
            raise ValidationException(f"不支持的日期类型: {type(date_value)}", field_name)
    
    def validate_price(self, price: Union[str, int, float], 
                      field_name: str = 'price') -> float:
        """验证价格"""
        if price is None:
            raise ValidationException(f"{field_name}不能为空", field_name)
        
        try:
            price_float = float(price)
            if price_float < 0:
                raise ValidationException(f"{field_name}不能为负数: {price_float}", field_name)
            if price_float > 10000:  # 假设股价不会超过10000元
                raise ValidationException(f"{field_name}超出合理范围: {price_float}", field_name)
            return round(price_float, 2)
        except (ValueError, TypeError):
            raise ValidationException(f"无效的{field_name}格式: {price}", field_name)
    
    def validate_volume(self, volume: Union[str, int, float], 
                       field_name: str = 'volume') -> int:
        """验证成交量"""
        if volume is None:
            raise ValidationException(f"{field_name}不能为空", field_name)
        
        try:
            volume_int = int(float(volume))
            if volume_int < 0:
                raise ValidationException(f"{field_name}不能为负数: {volume_int}", field_name)
            return volume_int
        except (ValueError, TypeError):
            raise ValidationException(f"无效的{field_name}格式: {volume}", field_name)
    
    def validate_dataframe_structure(self, df: pd.DataFrame, 
                                   required_columns: List[str]) -> pd.DataFrame:
        """验证DataFrame结构"""
        if df is None or df.empty:
            raise ValidationException("DataFrame不能为空", 'dataframe')
        
        missing_columns = set(required_columns) - set(df.columns)
        if missing_columns:
            raise ValidationException(
                f"DataFrame缺少必需的列: {missing_columns}", 
                'dataframe_columns'
            )
        
        return df
    
    def validate_kline_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """验证K线数据"""
        required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
        df = self.validate_dataframe_structure(df, required_columns)
        
        # 验证数据类型和范围
        validated_data = []
        
        for index, row in df.iterrows():
            try:
                validated_row = {
                    'date': self.validate_date(row['date']),
                    'open': self.validate_price(row['open'], 'open'),
                    'high': self.validate_price(row['high'], 'high'),
                    'low': self.validate_price(row['low'], 'low'),
                    'close': self.validate_price(row['close'], 'close'),
                    'volume': self.validate_volume(row['volume'])
                }
                
                # 验证价格逻辑关系
                if validated_row['high'] < max(validated_row['open'], validated_row['close']):
                    raise ValidationException(
                        f"最高价不能低于开盘价或收盘价: {validated_row}", 
                        'price_logic'
                    )
                
                if validated_row['low'] > min(validated_row['open'], validated_row['close']):
                    raise ValidationException(
                        f"最低价不能高于开盘价或收盘价: {validated_row}", 
                        'price_logic'
                    )
                
                validated_data.append(validated_row)
                
            except ValidationException as e:
                self.logger.warning(f"第{index}行数据验证失败: {e.message}")
                # 可以选择跳过无效数据或抛出异常
                continue
        
        if not validated_data:
            raise ValidationException("没有有效的K线数据", 'kline_data')
        
        return pd.DataFrame(validated_data)
    
    def validate_td_setup_count(self, setup_count: Union[str, int]) -> int:
        """验证TD Setup计数"""
        try:
            count = int(setup_count)
            if count < 0 or count > 13:  # TD序列通常不超过13
                raise ValidationException(
                    f"TD Setup计数超出范围(0-13): {count}", 
                    'setup_count'
                )
            return count
        except (ValueError, TypeError):
            raise ValidationException(f"无效的Setup计数格式: {setup_count}", 'setup_count')
    
    def validate_signal_type(self, signal_type: str) -> str:
        """验证信号类型"""
        if not signal_type:
            raise ValidationException("信号类型不能为空", 'signal_type')
        
        signal_type = signal_type.lower().strip()
        if signal_type not in ['buy', 'sell']:
            raise ValidationException(f"无效的信号类型: {signal_type}", 'signal_type')
        
        return signal_type

class DataCleaner:
    """数据清洗器"""
    
    def __init__(self):
        self.logger = get_logger('data_cleaner')
        self.validator = DataValidator()
    
    def clean_stock_list(self, stock_list: List[Dict]) -> List[Dict]:
        """清洗股票列表数据"""
        cleaned_data = []
        
        for stock in stock_list:
            try:
                cleaned_stock = {
                    'stock_code': self.validator.validate_stock_code(stock.get('stock_code', '')),
                    'stock_name': str(stock.get('stock_name', '')).strip()
                }
                
                # 过滤ST股票
                if 'ST' in cleaned_stock['stock_name'] or '*ST' in cleaned_stock['stock_name']:
                    self.logger.debug(f"过滤ST股票: {cleaned_stock['stock_code']} {cleaned_stock['stock_name']}")
                    continue
                
                cleaned_data.append(cleaned_stock)
                
            except ValidationException as e:
                self.logger.warning(f"股票数据清洗失败: {e.message}")
                continue
        
        self.logger.info(f"股票列表清洗完成，有效数据: {len(cleaned_data)}")
        return cleaned_data
    
    def clean_kline_data(self, df: pd.DataFrame, stock_code: str = None) -> pd.DataFrame:
        """清洗K线数据"""
        try:
            # 基础验证
            df = self.validator.validate_kline_data(df)
            
            # 去重
            df = df.drop_duplicates(subset=['date'])
            
            # 按日期排序
            df = df.sort_values('date')
            
            # 重置索引
            df = df.reset_index(drop=True)
            
            # 检查数据连续性
            if len(df) < 10:  # 至少需要10天数据
                raise ValidationException(
                    f"K线数据不足，仅有{len(df)}条记录", 
                    'insufficient_data'
                )
            
            self.logger.debug(f"K线数据清洗完成 [{stock_code}]，有效数据: {len(df)}条")
            return df
            
        except Exception as e:
            self.logger.error(f"K线数据清洗失败 [{stock_code}]: {str(e)}")
            raise
    
    def clean_signal_data(self, signals: List[Dict]) -> List[Dict]:
        """清洗信号数据"""
        cleaned_signals = []
        
        for signal in signals:
            try:
                cleaned_signal = {
                    'stock_code': self.validator.validate_stock_code(signal.get('stock_code', '')),
                    'date': self.validator.validate_date(signal.get('date')),
                    'close_price': self.validator.validate_price(signal.get('close_price')),
                    'signal_type': self.validator.validate_signal_type(signal.get('signal_type', '')),
                    'setup_count': self.validator.validate_td_setup_count(signal.get('setup_count', 0))
                }
                
                cleaned_signals.append(cleaned_signal)
                
            except ValidationException as e:
                self.logger.warning(f"信号数据清洗失败: {e.message}")
                continue
        
        self.logger.info(f"信号数据清洗完成，有效信号: {len(cleaned_signals)}")
        return cleaned_signals

class InputSanitizer:
    """输入清理器"""
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """清理文件名，移除危险字符"""
        if not filename:
            return 'default'
        
        # 移除路径分隔符和危险字符
        dangerous_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        for char in dangerous_chars:
            filename = filename.replace(char, '_')
        
        # 限制长度
        filename = filename[:100]
        
        return filename.strip()
    
    @staticmethod
    def sanitize_sql_input(input_str: str) -> str:
        """清理SQL输入，防止注入"""
        if not input_str:
            return ''
        
        # 移除SQL关键字和特殊字符
        dangerous_patterns = [
            r"[';\-\-]",  # SQL注释和语句结束符
            r"\b(DROP|DELETE|INSERT|UPDATE|CREATE|ALTER|EXEC|EXECUTE)\b",  # 危险SQL关键字
            r"[<>\"']",  # XSS相关字符
        ]
        
        cleaned = input_str
        for pattern in dangerous_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        return cleaned.strip()
    
    @staticmethod
    def sanitize_html_input(input_str: str) -> str:
        """清理HTML输入，防止XSS"""
        if not input_str:
            return ''
        
        # 转义HTML特殊字符
        html_escape_table = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#x27;',
            '/': '&#x2F;'
        }
        
        cleaned = input_str
        for char, escape in html_escape_table.items():
            cleaned = cleaned.replace(char, escape)
        
        return cleaned

# 全局实例
data_validator = DataValidator()
data_cleaner = DataCleaner()
input_sanitizer = InputSanitizer()

# 便捷函数
def validate_stock_code(stock_code: str) -> str:
    """验证股票代码的便捷函数"""
    return data_validator.validate_stock_code(stock_code)

def validate_kline_data(df: pd.DataFrame) -> pd.DataFrame:
    """验证K线数据的便捷函数"""
    return data_validator.validate_kline_data(df)

def clean_kline_data(df: pd.DataFrame, stock_code: str = None) -> pd.DataFrame:
    """清洗K线数据的便捷函数"""
    return data_cleaner.clean_kline_data(df, stock_code)

def sanitize_filename(filename: str) -> str:
    """清理文件名的便捷函数"""
    return input_sanitizer.sanitize_filename(filename)