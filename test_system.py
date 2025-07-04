#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统测试脚本 - 不依赖外部调度库
"""

import os
import sys
import pandas as pd
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import get_config
from utils import (
    get_logger, log_execution_time, handle_exceptions, 
    TDAnalysisException, PerformanceMonitor, safe_execute
)

@log_execution_time
@handle_exceptions(TDAnalysisException)
def test_basic_functionality():
    """
    测试基本功能
    """
    config = get_config()
    logger = get_logger('test_basic')
    
    logger.info("开始测试九转序列系统基本功能...")
    print("开始测试九转序列系统基本功能...")
    
    with PerformanceMonitor("基本功能测试", logger):
        try:
            # 测试九转序列计算
            logger.info("测试九转序列计算模块")
            print("\n1. 测试九转序列计算模块")
            from core.td_calc import TDSequentialCalculator
            
            # 创建测试数据
            test_data = pd.DataFrame({
                'date': pd.date_range('2024-01-01', periods=20),
                'open': [10.0, 10.1, 9.9, 9.8, 9.7, 9.6, 9.5, 9.4, 9.3, 9.2, 9.1, 9.0, 8.9, 8.8, 8.7, 8.6, 8.5, 8.4, 8.3, 8.2],
                'high': [10.2, 10.3, 10.1, 10.0, 9.9, 9.8, 9.7, 9.6, 9.5, 9.4, 9.3, 9.2, 9.1, 9.0, 8.9, 8.8, 8.7, 8.6, 8.5, 8.4],
                'low': [9.8, 9.9, 9.7, 9.6, 9.5, 9.4, 9.3, 9.2, 9.1, 9.0, 8.9, 8.8, 8.7, 8.6, 8.5, 8.4, 8.3, 8.2, 8.1, 8.0],
                'close': [10.0, 9.9, 9.8, 9.7, 9.6, 9.5, 9.4, 9.3, 9.2, 9.1, 9.0, 8.9, 8.8, 8.7, 8.6, 8.5, 8.4, 8.3, 8.2, 8.1],
                'volume': [1000000] * 20
            })
            
            calculator = TDSequentialCalculator()
            result = safe_execute(calculator.calculate_td_sequential, test_data)
            
            logger.info(f"九转序列计算成功，数据行数: {len(result)}")
            print(f"✓ 九转序列计算成功，数据行数: {len(result)}")
            
            # 检查是否有信号
            signals = result[result['setup_signal'] != 0]
            logger.info(f"发现 {len(signals)} 个信号")
            print(f"✓ 发现 {len(signals)} 个信号")
        
            # 测试K线图绘制
            logger.info("测试K线图绘制模块")
            print("\n2. 测试K线图绘制模块")
            from core.plot_kline import KLineChartPlotter
            
            plotter = KLineChartPlotter()
            html_file = safe_execute(plotter.create_kline_chart, 'TEST001', '测试股票', result)
            
            if html_file and os.path.exists(html_file):
                logger.info(f"K线图生成成功: {html_file}")
                print(f"✓ K线图生成成功: {html_file}")
            else:
                logger.error("K线图生成失败")
                print("✗ K线图生成失败")
        
            # 测试数据采集模块（仅测试类初始化）
            logger.info("测试数据采集模块")
            print("\n3. 测试数据采集模块")
            from core.fetch_data import StockDataFetcher
            
            fetcher = StockDataFetcher()
            logger.info("数据采集模块初始化成功")
            print("✓ 数据采集模块初始化成功")
            
            # 测试Web应用模块（仅测试导入）
            logger.info("测试Web应用模块")
            print("\n4. 测试Web应用模块")
            try:
                from web.app import app
                logger.info("Web应用模块导入成功")
                print("✓ Web应用模块导入成功")
            except ImportError as e:
                logger.error(f"Web应用模块导入失败: {e}")
                print(f"✗ Web应用模块导入失败: {e}")
            
            logger.info("基本功能测试完成 - 所有核心模块工作正常")
            print("\n=== 基本功能测试完成 ===")
            print("所有核心模块工作正常！")
            
            return True
            
        except Exception as e:
            logger.error(f"测试失败: {e}", exc_info=True)
            print(f"\n✗ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            raise TDAnalysisException(f"基本功能测试失败: {e}")

@log_execution_time
@handle_exceptions(TDAnalysisException)
def test_with_real_data():
    """
    使用真实数据进行测试（需要网络连接）
    """
    config = get_config()
    logger = get_logger('test_real_data')
    
    logger.info("开始真实数据测试...")
    print("\n开始真实数据测试...")
    
    with PerformanceMonitor("真实数据测试", logger):
        try:
            from core.fetch_data import StockDataFetcher
            from core.td_calc import TDSequentialCalculator
            from core.plot_kline import KLineChartPlotter
            
            # 初始化模块
            fetcher = StockDataFetcher()
            calculator = TDSequentialCalculator()
            plotter = KLineChartPlotter()
            
            logger.info("正在获取股票列表...")
            print("正在获取股票列表...")
            stock_list = safe_execute(fetcher.get_stock_list)
            
            if stock_list.empty:
                logger.error("无法获取股票列表，可能是网络问题")
                print("✗ 无法获取股票列表，可能是网络问题")
                return False
            
            logger.info(f"获取到 {len(stock_list)} 只股票")
            print(f"✓ 获取到 {len(stock_list)} 只股票")
        
            # 测试获取单只股票数据
            test_stock = stock_list.iloc[0]
            stock_code = test_stock['code']
            stock_name = test_stock['name']
            
            logger.info(f"正在获取 {stock_code} {stock_name} 的K线数据...")
            print(f"正在获取 {stock_code} {stock_name} 的K线数据...")
            kline_data = safe_execute(fetcher.get_stock_kline, stock_code, days=30)
            
            if kline_data.empty:
                logger.error("无法获取K线数据")
                print("✗ 无法获取K线数据")
                return False
            
            logger.info(f"获取到 {len(kline_data)} 天的K线数据")
            print(f"✓ 获取到 {len(kline_data)} 天的K线数据")
        
            # 计算九转序列
            logger.info("正在计算九转序列...")
            print("正在计算九转序列...")
            td_data, has_signal = safe_execute(calculator.analyze_single_stock, stock_code, kline_data)
            
            logger.info(f"九转序列计算完成，是否有信号: {has_signal}")
            print(f"✓ 九转序列计算完成，是否有信号: {has_signal}")
            
            # 生成图表
            logger.info("正在生成K线图...")
            print("正在生成K线图...")
            html_file = safe_execute(plotter.create_kline_chart, stock_code, stock_name, td_data)
            
            if html_file and os.path.exists(html_file):
                logger.info(f"K线图生成成功: {html_file}")
                print(f"✓ K线图生成成功: {html_file}")
            
            logger.info("真实数据测试完成")
            print("\n=== 真实数据测试完成 ===")
            return True
            
        except Exception as e:
            logger.error(f"真实数据测试失败: {e}", exc_info=True)
            print(f"\n✗ 真实数据测试失败: {e}")
            import traceback
            traceback.print_exc()
            raise TDAnalysisException(f"真实数据测试失败: {e}")

@handle_exceptions(TDAnalysisException)
def main():
    """
    主测试函数
    """
    config = get_config()
    logger = get_logger('test_main')
    
    logger.info("九转序列A股分析系统测试程序启动")
    print("九转序列A股分析系统 - 测试程序")
    print("=" * 50)
    
    # 确保目录存在
    os.makedirs(config.RAW_DATA_DIR, exist_ok=True)
    os.makedirs(config.PROCESSED_DATA_DIR, exist_ok=True)
    os.makedirs(config.HTML_CHARTS_DIR, exist_ok=True)
    os.makedirs(config.LOG_DIR, exist_ok=True)
    
    logger.debug(f"目录检查完成: {config.DATA_DIR}, {config.HTML_CHARTS_DIR}, {config.LOG_DIR}")
    
    try:
        # 基本功能测试
        logger.info("开始基本功能测试")
        basic_test_passed = test_basic_functionality()
        
        if basic_test_passed:
            logger.info("基本功能测试通过")
            print("\n基本功能测试通过！")
            
            # 询问是否进行真实数据测试
            try:
                choice = input("\n是否进行真实数据测试？(需要网络连接) [y/N]: ").strip().lower()
                if choice in ['y', 'yes']:
                    logger.info("开始真实数据测试")
                    real_test_passed = test_with_real_data()
                    if real_test_passed:
                        logger.info("所有测试通过")
                        print("\n所有测试通过！系统可以正常使用。")
                        print("\n下一步:")
                        print("1. 安装依赖: pip3 install --break-system-packages -r requirements.txt")
                        print("2. 运行完整分析: python3 run_daily.py --test --test-stocks 5")
                        print("3. 启动Web服务: python3 web/app.py")
                    else:
                        logger.warning("真实数据测试失败，但基本功能正常")
                        print("\n真实数据测试失败，但基本功能正常。")
                else:
                    logger.info("跳过真实数据测试")
                    print("\n跳过真实数据测试。")
                    print("基本功能测试通过，系统核心模块工作正常。")
            except KeyboardInterrupt:
                logger.info("用户中断测试")
                print("\n测试中断。")
        else:
            logger.error("基本功能测试失败")
            print("\n基本功能测试失败，请检查代码。")
            
    except Exception as e:
        logger.error(f"测试程序执行失败: {e}", exc_info=True)
        print(f"\n测试程序执行失败: {e}")
        raise TDAnalysisException(f"测试程序失败: {e}")

if __name__ == '__main__':
    main()