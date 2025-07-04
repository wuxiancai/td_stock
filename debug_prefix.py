#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试前缀过滤功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.fetch_data import StockDataFetcher
from core.td_calc import TDSequentialCalculator
from utils.logger import get_logger

def debug_prefix_filtering():
    """调试前缀过滤功能"""
    logger = get_logger('debug_prefix')
    
    try:
        # 1. 测试获取股票列表
        logger.info("=== 步骤1: 获取股票列表 ===")
        fetcher = StockDataFetcher()
        stock_list = fetcher.get_stock_list()
        logger.info(f"获取到股票列表，总数: {len(stock_list)}")
        logger.info(f"股票列表列名: {list(stock_list.columns)}")
        logger.info(f"前5只股票:\n{stock_list.head()}")
        
        # 2. 测试前缀过滤
        logger.info("\n=== 步骤2: 测试前缀过滤 ===")
        prefix_3_stocks = stock_list[stock_list['code'].str.startswith('3')]
        logger.info(f"3开头的股票数量: {len(prefix_3_stocks)}")
        if len(prefix_3_stocks) > 0:
            logger.info(f"前5只3开头股票:\n{prefix_3_stocks.head()}")
        
        # 3. 测试批量获取数据（只获取1只股票）
        logger.info("\n=== 步骤3: 测试批量获取数据 ===")
        fetch_result = fetcher.fetch_all_stocks_data(max_stocks=1, stock_prefix='3')
        logger.info(f"获取结果: {fetch_result}")
        
        if fetch_result and fetch_result.get('data'):
            all_stocks_data = fetch_result['data']
            logger.info(f"获取到的股票数据: {list(all_stocks_data.keys())}")
            
            # 4. 测试九转序列计算
            logger.info("\n=== 步骤4: 测试九转序列计算 ===")
            calculator = TDSequentialCalculator()
            signal_stocks = calculator.get_signal_stocks(all_stocks_data)
            logger.info(f"信号股票数据类型: {type(signal_stocks)}")
            logger.info(f"信号股票数量: {len(signal_stocks)}")
            if not signal_stocks.empty:
                logger.info(f"信号股票列名: {list(signal_stocks.columns)}")
                logger.info(f"信号股票数据:\n{signal_stocks}")
            else:
                logger.info("没有发现信号股票")
        else:
            logger.error("没有获取到股票数据")
            
    except Exception as e:
        logger.error(f"调试过程中发生错误: {e}", exc_info=True)

if __name__ == "__main__":
    debug_prefix_filtering()