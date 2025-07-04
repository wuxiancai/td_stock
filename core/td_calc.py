#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
九转序列指标计算模块
实现TD Sequential Setup逻辑
"""

import pandas as pd
import numpy as np
from typing import Tuple, List
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import get_config
from utils import (
    get_logger, log_execution_time, handle_exceptions, cached,
    TDCalculationException, validate_kline_data, PerformanceMonitor
)

class TDSequentialCalculator:
    def __init__(self):
        self.config = get_config()
        self.logger = get_logger('td_calculator')
        self.setup_threshold = self.config.TD_SETUP_THRESHOLD
        self.lookback_period = self.config.TD_LOOKBACK_PERIOD
        
        self.logger.info(f"TD序列计算器初始化完成，Setup阈值: {self.setup_threshold}, 回看周期: {self.lookback_period}")
    
    @cached(timeout=600, key_prefix='td_calc_')
    @log_execution_time
    @handle_exceptions(context='计算TD序列')
    def calculate_td_setup(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算九转序列Setup
        
        买入Setup逻辑：当日收盘价 < 4天前收盘价，连续累加
        卖出Setup逻辑：当日收盘价 > 4天前收盘价，连续累加
        
        Args:
            df: 包含OHLCV数据的DataFrame
        
        Returns:
            DataFrame: 添加了Setup相关列的数据
        """
        if df is None or df.empty:
            raise TDCalculationException("输入数据为空")
        
        if len(df) < self.lookback_period + 1:
            raise TDCalculationException(
                f"数据不足，需要至少 {self.lookback_period + 1} 条记录，实际: {len(df)}",
                calculation_step='数据验证'
            )
        
        # 验证数据格式
        df = validate_kline_data(df)
        
        with PerformanceMonitor('TD序列计算'):
            df = df.copy()
            
            # 初始化Setup列
            df['buy_setup'] = 0
            df['sell_setup'] = 0
            df['buy_setup_count'] = 0
            df['sell_setup_count'] = 0
            df['setup_signal'] = 0  # 1为买入信号，-1为卖出信号
            df['signal_position'] = ''  # 标记位置：'above'或'below'
            
            try:
                # 计算买入和卖出条件
                for i in range(self.lookback_period, len(df)):
                    current_close = df.iloc[i]['close']
                    lookback_close = df.iloc[i-self.lookback_period]['close']
                    
                    # 买入Setup：当日收盘价 < 4天前收盘价
                    if current_close < lookback_close:
                        df.iloc[i, df.columns.get_loc('buy_setup')] = 1
                        # 计算连续买入Setup计数
                        if i > self.lookback_period and df.iloc[i-1]['buy_setup'] == 1:
                            df.iloc[i, df.columns.get_loc('buy_setup_count')] = df.iloc[i-1]['buy_setup_count'] + 1
                        else:
                            df.iloc[i, df.columns.get_loc('buy_setup_count')] = 1
                    else:
                        df.iloc[i, df.columns.get_loc('buy_setup_count')] = 0
                    
                    # 卖出Setup：当日收盘价 > 4天前收盘价
                    if current_close > lookback_close:
                        df.iloc[i, df.columns.get_loc('sell_setup')] = 1
                        # 计算连续卖出Setup计数
                        if i > self.lookback_period and df.iloc[i-1]['sell_setup'] == 1:
                            df.iloc[i, df.columns.get_loc('sell_setup_count')] = df.iloc[i-1]['sell_setup_count'] + 1
                        else:
                            df.iloc[i, df.columns.get_loc('sell_setup_count')] = 1
                    else:
                        df.iloc[i, df.columns.get_loc('sell_setup_count')] = 0
                
                # 标记Setup=3的信号点
                df = self._mark_setup_signals(df)
                
                # 验证计算结果
                self._validate_calculation_results(df)
                
                self.logger.debug(f"TD序列计算完成，数据行数: {len(df)}")
                return df
                
            except Exception as e:
                raise TDCalculationException(
                    f"TD序列计算过程中发生错误: {str(e)}",
                    calculation_step='主计算流程'
                )
    
    def _mark_setup_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        标记Setup=3的信号点
        
        Args:
            df: 包含Setup计算结果的DataFrame
        
        Returns:
            DataFrame: 添加了信号标记的数据
        """
        try:
            for i in range(len(df)):
                buy_count = df.iloc[i]['buy_setup_count']
                sell_count = df.iloc[i]['sell_setup_count']
                
                # 买入信号：Setup=3
                if buy_count == self.setup_threshold:
                    df.iloc[i, df.columns.get_loc('setup_signal')] = 1
                    df.iloc[i, df.columns.get_loc('signal_position')] = 'below'  # 下跌行情，标记在K线下方
                
                # 卖出信号：Setup=3
                elif sell_count == self.setup_threshold:
                    df.iloc[i, df.columns.get_loc('setup_signal')] = -1
                    df.iloc[i, df.columns.get_loc('signal_position')] = 'above'  # 上涨行情，标记在K线上方
            
            return df
        except Exception as e:
            raise TDCalculationException(
                f"标记Setup信号失败: {str(e)}",
                calculation_step='信号标记'
            )
    
    def _validate_calculation_results(self, df: pd.DataFrame):
        """
        验证计算结果
        
        Args:
            df: 计算结果DataFrame
        """
        try:
            # 检查必要列是否存在
            required_columns = ['buy_setup_count', 'sell_setup_count', 'setup_signal', 'signal_position']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise TDCalculationException(
                    f"计算结果缺少必要列: {missing_columns}",
                    calculation_step='结果验证'
                )
            
            # 检查Setup计数范围
            max_buy_setup = df['buy_setup_count'].max()
            max_sell_setup = df['sell_setup_count'].max()
            
            if max_buy_setup > 13 or max_sell_setup > 13:  # TD序列通常不超过13
                self.logger.warning(f"Setup计数异常，买入最大值: {max_buy_setup}, 卖出最大值: {max_sell_setup}")
            
            # 统计信号数量
            buy_signals = (df['setup_signal'] == 1).sum()
            sell_signals = (df['setup_signal'] == -1).sum()
            
            self.logger.debug(f"计算结果验证通过，买入信号: {buy_signals}, 卖出信号: {sell_signals}")
            
        except Exception as e:
            raise TDCalculationException(
                f"计算结果验证失败: {str(e)}",
                calculation_step='结果验证'
            )
    
    @log_execution_time
    @handle_exceptions(context='筛选信号股票')
    def get_signal_stocks(self, all_stocks_data: dict) -> pd.DataFrame:
        """
        从所有股票数据中筛选出有Setup=3信号的股票
        
        Args:
            all_stocks_data: {stock_code: kline_dataframe}
        
        Returns:
            DataFrame: 包含信号股票信息的表格
        """
        if not all_stocks_data:
            self.logger.warning("输入的股票数据为空")
            return pd.DataFrame()
        
        signal_stocks = []
        processed_count = 0
        error_count = 0
        
        with PerformanceMonitor('信号股票筛选'):
            for stock_code, kline_data in all_stocks_data.items():
                try:
                    processed_count += 1
                    
                    if kline_data is None or kline_data.empty:
                        self.logger.debug(f"股票 {stock_code} 数据为空，跳过")
                        continue
                    
                    # 计算九转序列
                    df_with_td = self.calculate_td_setup(kline_data)
                    
                    # 检查最新一天是否有信号
                    latest_signal = df_with_td.iloc[-1]['setup_signal']
                    if latest_signal != 0:
                        latest_data = df_with_td.iloc[-1]
                        signal_info = {
                            'stock_code': stock_code,
                            'date': latest_data['date'].strftime('%Y-%m-%d'),
                            'close_price': latest_data['close'],
                            'signal_type': 'buy' if latest_signal == 1 else 'sell',
                            'setup_count': latest_data['buy_setup_count'] if latest_signal == 1 else latest_data['sell_setup_count'],
                            'signal_position': latest_data['signal_position']
                        }
                        signal_stocks.append(signal_info)
                        self.logger.debug(f"发现信号股票: {stock_code}, 信号类型: {signal_info['signal_type']}")
                
                except Exception as e:
                    error_count += 1
                    self.logger.error(f"处理股票 {stock_code} 时发生错误: {str(e)}")
                    continue
        
        result_df = pd.DataFrame(signal_stocks)
        
        self.logger.info(
            f"信号股票筛选完成，处理股票数: {processed_count}, "
            f"发现信号股票: {len(signal_stocks)}, 错误数: {error_count}"
        )
        
        return result_df
    
    @log_execution_time
    @handle_exceptions(context='分析单只股票')
    def analyze_single_stock(self, stock_code: str, kline_data: pd.DataFrame) -> Tuple[pd.DataFrame, bool]:
        """
        分析单只股票的TD序列
        
        Args:
            stock_code: 股票代码
            kline_data: K线数据
            
        Returns:
            Tuple[DataFrame, bool]: (带TD序列的数据, 是否有信号)
        """
        if not stock_code:
            raise TDCalculationException("股票代码不能为空")
        
        if kline_data is None or kline_data.empty:
            self.logger.warning(f"股票 {stock_code} 的K线数据为空")
            return pd.DataFrame(), False
        
        try:
            with PerformanceMonitor(f'分析股票{stock_code}'):
                # 计算TD序列
                df_with_td = self.calculate_td_setup(kline_data)
                
                # 检查是否有信号
                has_signal = (df_with_td['setup_signal'] != 0).any()
                
                # 统计信号信息
                if has_signal:
                    buy_signals = (df_with_td['setup_signal'] == 1).sum()
                    sell_signals = (df_with_td['setup_signal'] == -1).sum()
                    latest_signal_date = df_with_td[df_with_td['setup_signal'] != 0]['date'].iloc[-1]
                    
                    self.logger.debug(
                        f"股票 {stock_code} 分析完成，买入信号: {buy_signals}, "
                        f"卖出信号: {sell_signals}, 最新信号日期: {latest_signal_date}"
                    )
                else:
                    self.logger.debug(f"股票 {stock_code} 分析完成，无信号")
                
                return df_with_td, has_signal
                
        except Exception as e:
            raise TDCalculationException(
                f"分析股票 {stock_code} 时发生错误: {str(e)}",
                calculation_step='单股票分析'
            )
    
    @log_execution_time
    @handle_exceptions(context='生成信号汇总')
    def get_signal_summary(self, signal_stocks_df: pd.DataFrame) -> dict:
        """
        获取信号汇总统计
        
        Args:
            signal_stocks_df: 信号股票数据框
            
        Returns:
            dict: 汇总统计信息
        """
        if signal_stocks_df is None or signal_stocks_df.empty:
            self.logger.info("无信号股票数据，返回空汇总")
            return {
                'total_signals': 0,
                'buy_signals': 0,
                'sell_signals': 0,
                'signal_stocks': [],
                'signal_date': None
            }
        
        try:
            with PerformanceMonitor('信号汇总统计'):
                buy_count = len(signal_stocks_df[signal_stocks_df['signal_type'] == 'buy'])
                sell_count = len(signal_stocks_df[signal_stocks_df['signal_type'] == 'sell'])
                
                # 计算额外统计信息
                avg_setup_count = signal_stocks_df['setup_count'].mean() if 'setup_count' in signal_stocks_df.columns else 0
                unique_dates = signal_stocks_df['date'].nunique() if 'date' in signal_stocks_df.columns else 0
                
                summary = {
                    'total_signals': len(signal_stocks_df),
                    'buy_signals': buy_count,
                    'sell_signals': sell_count,
                    'avg_setup_count': round(avg_setup_count, 2),
                    'unique_signal_dates': unique_dates,
                    'signal_stocks': signal_stocks_df.to_dict('records'),
                    'signal_date': signal_stocks_df.iloc[0]['date'] if len(signal_stocks_df) > 0 else None
                }
                
                self.logger.info(
                    f"信号汇总完成，总信号数: {summary['total_signals']}, "
                    f"买入信号: {buy_count}, 卖出信号: {sell_count}, "
                    f"平均Setup计数: {avg_setup_count:.2f}"
                )
                
                return summary
                
        except Exception as e:
            raise TDCalculationException(
                f"生成信号汇总时发生错误: {str(e)}",
                calculation_step='信号汇总'
            )

if __name__ == "__main__":
    # 测试代码
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from core.fetch_data import StockDataFetcher
    
    # 创建测试数据
    test_data = pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=20),
        'open': [10.0, 10.1, 9.9, 9.8, 9.7, 9.6, 9.5, 9.4, 9.3, 9.2, 9.1, 9.0, 8.9, 8.8, 8.7, 8.6, 8.5, 8.4, 8.3, 8.2],
        'high': [10.2, 10.3, 10.1, 10.0, 9.9, 9.8, 9.7, 9.6, 9.5, 9.4, 9.3, 9.2, 9.1, 9.0, 8.9, 8.8, 8.7, 8.6, 8.5, 8.4],
        'low': [9.8, 9.9, 9.7, 9.6, 9.5, 9.4, 9.3, 9.2, 9.1, 9.0, 8.9, 8.8, 8.7, 8.6, 8.5, 8.4, 8.3, 8.2, 8.1, 8.0],
        'close': [10.0, 9.9, 9.8, 9.7, 9.6, 9.5, 9.4, 9.3, 9.2, 9.1, 9.0, 8.9, 8.8, 8.7, 8.6, 8.5, 8.4, 8.3, 8.2, 8.1],
        'volume': [1000000] * 20
    })
    
    # 测试九转序列计算
    calculator = TDSequentialCalculator()
    result = calculator.calculate_td_setup(test_data)
    
    print("九转序列计算结果:")
    print(result[['date', 'close', 'buy_setup_count', 'sell_setup_count', 'setup_signal', 'signal_position']].tail(10))
    
    # 测试信号统计
    signal_stocks = calculator.get_signal_stocks({'TEST001': result})
    print(f"\n信号股票: {len(signal_stocks)} 只")
    if not signal_stocks.empty:
        print(signal_stocks)
    
    summary = calculator.get_signal_summary(signal_stocks)
    print(f"\n信号统计: {summary}")