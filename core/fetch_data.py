#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据获取模块
使用AkShare获取A股数据
"""

import akshare as ak
import pandas as pd
import os
import sys
from datetime import datetime, timedelta
import time

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import get_config
from utils import (
    get_logger, log_execution_time, handle_exceptions, retry_on_exception,
    cached, DataFetchException, validate_stock_code, clean_kline_data
)
from core.data_sources import DataSourceFactory

class StockDataFetcher:
    """
    股票数据获取器
    支持多种数据源
    """
    
    def __init__(self, data_dir=None, data_source=None):
        self.config = get_config()
        self.logger = get_logger('data_fetcher')
        
        # 使用配置中的目录或传入的目录
        self.data_dir = data_dir or self.config.DATA_DIR
        self.raw_dir = os.path.join(self.data_dir, 'raw')
        self.processed_dir = os.path.join(self.data_dir, "processed")
        
        # 确保目录存在
        os.makedirs(self.raw_dir, exist_ok=True)
        os.makedirs(self.processed_dir, exist_ok=True)
        
        # 初始化数据源
        self.data_source_type = data_source or self.config.DATA_SOURCE
        self.data_source = DataSourceFactory.create_data_source(
            self.data_source_type, 
            self.config
        )
        
        self.logger.info(f"数据获取器初始化完成，数据目录: {self.data_dir}，数据源: {self.data_source_type}")
    
    @cached(timeout=3600, key_prefix='stock_list_')
    @retry_on_exception(max_retries=3, delay=2.0)
    @log_execution_time
    @handle_exceptions(context='获取股票列表')
    def get_stock_list(self):
        """
        获取A股所有股票代码列表
        包括沪深主板、创业板、科创板
        """
        self.logger.info(f"开始获取股票代码列表 (数据源: {self.data_source_type})")
        
        try:
            # 使用配置的数据源获取股票列表
            stock_list = self.data_source.get_stock_list()
            
            if stock_list.empty:
                raise DataFetchException("获取到的股票列表为空")
            
            # 检查必要列是否存在
            if 'code' not in stock_list.columns or 'name' not in stock_list.columns:
                raise DataFetchException("股票列表数据格式异常，缺少必要列")
            
            # 过滤掉ST、*ST等特殊股票
            stock_list = stock_list[~stock_list['name'].str.contains('ST', na=False)]
            
            # 数据清洗和验证
            from utils.validators import data_cleaner
            # 转换字段名以匹配清洗器期望的格式
            stock_records = stock_list.to_dict('records')
            for record in stock_records:
                if 'code' in record:
                    record['stock_code'] = record['code']
                if 'name' in record:
                    record['stock_name'] = record['name']
            
            cleaned_stocks = data_cleaner.clean_stock_list(stock_records)
            
            # 转换回原始字段名格式
            for cleaned_stock in cleaned_stocks:
                if 'stock_code' in cleaned_stock:
                    cleaned_stock['code'] = cleaned_stock['stock_code']
                if 'stock_name' in cleaned_stock:
                    cleaned_stock['name'] = cleaned_stock['stock_name']
            
            stock_list = pd.DataFrame(cleaned_stocks)
            
            self.logger.info(f"获取到 {len(stock_list)} 只有效股票 (数据源: {self.data_source_type})")
            
            # 保存到CSV
            stock_list_file = os.path.join(self.raw_dir, f"stock_list_{datetime.now().strftime('%Y%m%d')}.csv")
            stock_list.to_csv(stock_list_file, index=False, encoding='utf-8-sig')
            
            return stock_list
            
        except Exception as e:
            self.logger.error(f"获取股票列表失败 (数据源: {self.data_source_type}): {str(e)}")
            if isinstance(e, DataFetchException):
                raise
            else:
                raise DataFetchException(f"获取股票列表时发生系统错误: {str(e)}")
    
    @cached(timeout=1800, key_prefix='kline_')
    @retry_on_exception(max_retries=3, delay=1.0, exceptions=(Exception,))
    @log_execution_time
    @handle_exceptions(context='获取K线数据')
    def get_stock_kline(self, stock_code, days=None):
        """
        获取指定股票的历史K线数据
        
        Args:
            stock_code: 股票代码，如 '000001'
            days: 获取天数，默认使用配置值
        
        Returns:
            DataFrame: 包含OHLCV数据
        """
        # 验证股票代码
        stock_code = validate_stock_code(stock_code)
        days = days or self.config.STOCK_DATA_PERIOD
        
        self.logger.debug(f"开始获取 {stock_code} 的K线数据，周期: {days}天 (数据源: {self.data_source_type})")
        
        try:
            # 使用配置的数据源获取K线数据
            kline_data = self.data_source.get_stock_kline(stock_code, days)
            
            if kline_data.empty:
                raise DataFetchException(f"股票 {stock_code} 没有K线数据", stock_code=stock_code)
            
            # 数据验证和清洗
            kline_data = clean_kline_data(kline_data, stock_code)
            
            self.logger.info(f"成功获取股票 {stock_code} 的 {len(kline_data)} 条K线数据 (数据源: {self.data_source_type})")
            
            return kline_data
            
        except Exception as e:
            if isinstance(e, DataFetchException):
                raise
            else:
                raise DataFetchException(
                    f"获取股票 {stock_code} K线数据时发生系统错误: {str(e)}",
                    stock_code=stock_code
                )
    
    @log_execution_time
    @handle_exceptions(context='批量获取股票数据')
    def fetch_all_stocks_data(self, max_stocks=None, delay=None, stock_prefix=None):
        """
        批量获取所有股票的K线数据
        
        Args:
            max_stocks: 最大获取股票数量，None表示获取所有
            delay: 请求间隔时间（秒），默认使用配置值
            stock_prefix: 股票代码前缀过滤（如'0', '2', '3', '6'），None表示不过滤
        
        Returns:
            dict: 包含统计信息的字典
        """
        delay = delay or self.config.RETRY_DELAY
        
        try:
            # 获取股票列表
            stock_list = self.get_stock_list()
            if stock_list.empty:
                raise DataFetchException("没有获取到股票列表")
            
            # 根据股票代码前缀过滤
            if stock_prefix:
                original_count = len(stock_list)
                stock_list = stock_list[stock_list['code'].str.startswith(stock_prefix)]
                self.logger.info(f"按前缀 '{stock_prefix}' 过滤股票: {len(stock_list)}/{original_count}")
                
                if stock_list.empty:
                    raise DataFetchException(f"没有找到以 '{stock_prefix}' 开头的股票")
            
            # 限制股票数量
            if max_stocks:
                stock_list = stock_list.head(max_stocks)
                self.logger.info(f"限制获取股票数量为: {max_stocks}")
            
            self.logger.info(f"开始批量获取 {len(stock_list)} 只股票的K线数据")
            
            success_count = 0
            failed_stocks = []
            all_data = {}
            
            for index, row in stock_list.iterrows():
                stock_code = row.get('code')
                stock_name = row.get('name', '')
                
                self.logger.debug(f"[{index+1}/{len(stock_list)}] 正在获取 {stock_code} {stock_name}")
                
                try:
                    kline_data = self.get_stock_kline(stock_code)
                    if not kline_data.empty:
                        success_count += 1
                        all_data[stock_code] = kline_data
                        
                        # 保存单个股票数据
                        stock_file = os.path.join(self.raw_dir, f"{stock_code}_{datetime.now().strftime('%Y%m%d')}.csv")
                        kline_data.to_csv(stock_file, index=False, encoding='utf-8-sig')
                        
                        self.logger.debug(f"✓ 成功获取 {stock_code} 数据")
                    else:
                        failed_stocks.append((stock_code, "数据为空"))
                        
                except Exception as e:
                    failed_stocks.append((stock_code, str(e)))
                    self.logger.warning(f"✗ 获取 {stock_code} 数据失败: {str(e)}")
                
                # 添加延迟，避免请求过于频繁
                if delay > 0:
                    time.sleep(delay)
            
            # 记录结果统计
            self.logger.info(f"数据获取完成！成功: {success_count}/{len(stock_list)}")
            
            if failed_stocks:
                self.logger.warning(f"失败的股票数量: {len(failed_stocks)}")
                for stock_code, error in failed_stocks[:5]:  # 只记录前5个失败案例
                    self.logger.debug(f"失败股票: {stock_code}, 原因: {error}")
            
            return {
                'total': len(stock_list),
                'success': success_count,
                'failed': len(failed_stocks),
                'failed_stocks': failed_stocks,
                'data': all_data
            }
            
        except Exception as e:
            if isinstance(e, DataFetchException):
                raise
            else:
                raise DataFetchException(f"批量获取数据时发生系统错误: {str(e)}")

if __name__ == "__main__":
    # 测试代码
    fetcher = StockDataFetcher()
    
    # 测试获取股票列表
    stock_list = fetcher.get_stock_list()
    print(f"股票列表样例:\n{stock_list.head()}")
    
    # 测试获取单只股票数据
    if not stock_list.empty:
        test_code = stock_list.iloc[0]['code']
        kline_data = fetcher.get_stock_kline(test_code)
        print(f"\n{test_code} K线数据样例:\n{kline_data.head()}")