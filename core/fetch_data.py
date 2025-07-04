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

class StockDataFetcher:
    """
    股票数据获取器
    """
    
    def __init__(self, data_dir=None):
        self.config = get_config()
        self.logger = get_logger('data_fetcher')
        
        # 使用配置中的目录或传入的目录
        self.data_dir = data_dir or self.config.DATA_DIR
        self.raw_dir = os.path.join(self.data_dir, 'raw')
        self.processed_dir = os.path.join(self.data_dir, "processed")
        
        # 确保目录存在
        os.makedirs(self.raw_dir, exist_ok=True)
        os.makedirs(self.processed_dir, exist_ok=True)
        
        self.logger.info(f"数据获取器初始化完成，数据目录: {self.data_dir}")
    
    @cached(timeout=3600, key_prefix='stock_list_')
    @retry_on_exception(max_retries=3, delay=2.0)
    @log_execution_time
    @handle_exceptions(context='获取股票列表')
    def get_stock_list(self):
        """
        获取A股所有股票代码列表
        包括沪深主板、创业板、科创板
        """
        self.logger.info("开始获取股票代码列表")
        
        try:
            # 获取沪深A股股票列表
            stock_list = ak.stock_info_a_code_name()
            
            if stock_list.empty:
                raise DataFetchException("获取到的股票列表为空")
            
            # 检查必要列是否存在
            if 'code' not in stock_list.columns or 'name' not in stock_list.columns:
                raise DataFetchException("股票列表数据格式异常，缺少必要列")
            
            # 过滤掉ST、*ST等特殊股票
            stock_list = stock_list[~stock_list['name'].str.contains('ST', na=False)]
            
            # 数据清洗和验证
            from utils.validators import data_cleaner
            cleaned_stocks = data_cleaner.clean_stock_list(stock_list.to_dict('records'))
            stock_list = pd.DataFrame(cleaned_stocks)
            
            self.logger.info(f"获取到 {len(stock_list)} 只有效股票")
            
            # 保存到CSV
            stock_list_file = os.path.join(self.raw_dir, f"stock_list_{datetime.now().strftime('%Y%m%d')}.csv")
            stock_list.to_csv(stock_list_file, index=False, encoding='utf-8-sig')
            
            return stock_list
            
        except Exception as e:
            self.logger.error(f"获取股票列表失败: {str(e)}")
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
        
        self.logger.debug(f"开始获取 {stock_code} 的K线数据，周期: {days}天")
        
        try:
            # 计算开始日期
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=days*2)).strftime('%Y%m%d')  # 多取一些数据以防节假日
            
            # 获取K线数据
            kline_data = ak.stock_zh_a_hist(
                symbol=stock_code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"  # 前复权
            )
            
            if kline_data.empty:
                raise DataFetchException(f"股票 {stock_code} 没有K线数据", stock_code=stock_code)
            
            # 动态处理列名，适应不同的AkShare返回格式
            original_columns = kline_data.columns.tolist()
            self.logger.debug(f"原始列名 [{stock_code}]: {original_columns}")
            
            # 创建列名映射字典
            column_mapping = {}
            required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
            
            # 根据实际列数和常见模式进行映射
            if len(original_columns) >= 6:
                # 标准映射：日期、开盘、最高、最低、收盘、成交量
                for i, col_name in enumerate(required_columns):
                    if i < len(original_columns):
                        column_mapping[original_columns[i]] = col_name
            else:
                raise DataFetchException(
                    f"股票 {stock_code} 数据列数不足: {len(original_columns)}",
                    stock_code=stock_code
                )
            
            # 重命名列
            kline_data = kline_data.rename(columns=column_mapping)
            
            # 只保留需要的列（如果存在）
            available_columns = [col for col in required_columns if col in kline_data.columns]
            kline_data = kline_data[available_columns]
            
            # 转换数据类型
            kline_data['date'] = pd.to_datetime(kline_data['date'])
            for col in ['open', 'high', 'low', 'close', 'volume']:
                kline_data[col] = pd.to_numeric(kline_data[col], errors='coerce')
            
            # 删除包含NaN的行
            original_len = len(kline_data)
            kline_data = kline_data.dropna()
            if len(kline_data) < original_len:
                self.logger.warning(f"股票 {stock_code} 清理了 {original_len - len(kline_data)} 条无效数据")
            
            # 按日期排序
            kline_data = kline_data.sort_values('date').reset_index(drop=True)
            
            # 只取最近的指定天数
            kline_data = kline_data.tail(days)
            
            # 数据验证和清洗
            kline_data = clean_kline_data(kline_data, stock_code)
            
            self.logger.info(f"成功获取股票 {stock_code} 的 {len(kline_data)} 条K线数据")
            
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
    def fetch_all_stocks_data(self, max_stocks=None, delay=None):
        """
        批量获取所有股票的K线数据
        
        Args:
            max_stocks: 最大获取股票数量，None表示获取所有
            delay: 请求间隔时间（秒），默认使用配置值
        
        Returns:
            dict: 包含统计信息的字典
        """
        delay = delay or self.config.RETRY_DELAY
        
        try:
            # 获取股票列表
            stock_list = self.get_stock_list()
            if stock_list.empty:
                raise DataFetchException("没有获取到股票列表")
            
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