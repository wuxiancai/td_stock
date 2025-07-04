#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
九转序列A股分析系统 - 主任务调度
每日自动执行数据获取、分析和图表生成
"""

import os
import sys
import time
import argparse
from datetime import datetime, timedelta
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import pandas as pd
import logging

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入配置和工具模块
from config import get_config
from utils import (
    get_logger, log_execution_time, handle_exceptions, 
    TDAnalysisException, PerformanceMonitor, safe_execute
)

from core.fetch_data import StockDataFetcher
from core.td_calc import TDSequentialCalculator
from core.plot_kline import KLineChartPlotter

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('td_analysis.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TDSequentialAnalysisSystem:
    def __init__(self, max_stocks=None, test_mode=False):
        """
        初始化分析系统
        
        Args:
            max_stocks: 最大分析股票数量（用于测试）
            test_mode: 测试模式，不启动定时任务
        """
        # 获取配置和初始化日志
        self.config = get_config()
        self.logger = get_logger('td_sequential_analysis')
        
        self.max_stocks = max_stocks
        self.test_mode = test_mode
        
        # 初始化各个模块
        self.fetcher = StockDataFetcher()
        self.calculator = TDSequentialCalculator()
        self.plotter = KLineChartPlotter()
        
        # 数据目录
        self.data_dir = self.config.DATA_DIR
        self.processed_dir = self.config.PROCESSED_DATA_DIR
        self.html_dir = self.config.HTML_CHARTS_DIR
        
        # 确保目录存在
        os.makedirs(self.processed_dir, exist_ok=True)
        os.makedirs(self.html_dir, exist_ok=True)
        
        self.logger.info("TD序列分析系统初始化完成")
        self.logger.debug(f"数据目录: {self.data_dir}, 处理目录: {self.processed_dir}")
    
    @log_execution_time
    @handle_exceptions(TDAnalysisException)
    def run_daily_analysis(self):
        """
        执行每日分析任务
        """
        start_time = datetime.now()
        self.logger.info(f"开始执行每日九转序列分析任务 - {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        with PerformanceMonitor("每日分析任务"):
            try:
                # 步骤1: 获取股票数据
                self.logger.info("步骤1: 获取股票数据")
                all_stocks_data = safe_execute(
                    self.fetcher.fetch_all_stocks_data,
                    max_stocks=self.max_stocks,
                    delay=self.config.REQUEST_DELAY
                )
                
                if not all_stocks_data:
                    raise TDAnalysisException("未获取到任何股票数据")
                
                self.logger.info(f"成功获取 {len(all_stocks_data)} 只股票的数据")
            
                # 步骤2: 计算九转序列并筛选信号股票
                self.logger.info("步骤2: 计算九转序列指标")
                signal_stocks = safe_execute(
                    self.calculator.get_signal_stocks,
                    all_stocks_data
                )
                
                # 保存信号股票数据
                date_str = datetime.now().strftime('%Y%m%d')
                signal_file = os.path.join(self.processed_dir, f"signal_stocks_{date_str}.csv")
                signal_stocks.to_csv(signal_file, index=False, encoding='utf-8-sig')
                
                self.logger.info(f"发现 {len(signal_stocks)} 只信号股票，已保存到 {signal_file}")
            
                # 步骤3: 为信号股票计算完整的九转序列数据
                self.logger.info("步骤3: 计算信号股票的完整九转序列")
                stocks_with_td = {}
                
                for stock_code in signal_stocks['stock_code']:
                    if stock_code in all_stocks_data:
                        kline_data = all_stocks_data[stock_code]
                        td_data, has_signal = safe_execute(
                            self.calculator.analyze_single_stock,
                            stock_code, kline_data
                        )
                        if has_signal and not td_data.empty:
                            # 获取股票名称（这里简化处理，实际可以从股票列表获取）
                            stock_name = f"股票{stock_code}"
                            stocks_with_td[stock_code] = (stock_name, td_data)
                
                self.logger.info(f"完成 {len(stocks_with_td)} 只股票的九转序列计算")
            
                # 步骤4: 生成K线图表
                self.logger.info("步骤4: 生成K线图表")
                html_files = safe_execute(
                    self.plotter.batch_create_charts,
                    stocks_with_td, signal_stocks
                )
                
                self.logger.info(f"生成 {len(html_files)} 个图表文件")
                
                # 步骤5: 生成分析报告
                self._generate_analysis_report(signal_stocks, start_time)
                
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                self.logger.info(f"每日分析任务完成 - 耗时 {duration:.2f} 秒")
                
                return True
                
            except Exception as e:
                self.logger.error(f"每日分析任务执行失败: {e}", exc_info=True)
                raise TDAnalysisException(f"每日分析任务失败: {e}")
    
    def _generate_analysis_report(self, signal_stocks: pd.DataFrame, start_time: datetime):
        """
        生成分析报告
        
        Args:
            signal_stocks: 信号股票DataFrame
            start_time: 任务开始时间
        """
        try:
            # 获取统计信息
            summary = self.calculator.get_signal_summary(signal_stocks)
            
            # 生成报告内容
            report_content = f"""
九转序列分析报告
==================

分析时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}
数据日期: {summary.get('signal_date', 'N/A')}

信号统计:
- 总信号数: {summary['total_signals']}
- 买入信号: {summary['buy_signals']}
- 卖出信号: {summary['sell_signals']}

信号股票列表:
"""
            
            if not signal_stocks.empty:
                for _, row in signal_stocks.iterrows():
                    signal_type_cn = '买入' if row['signal_type'] == 'buy' else '卖出'
                    report_content += f"- {row['stock_code']}: {signal_type_cn}信号, 收盘价 {row['close_price']:.2f}, Setup计数 {row['setup_count']}\n"
            else:
                report_content += "- 暂无信号股票\n"
            
            # 保存报告
            date_str = datetime.now().strftime('%Y%m%d')
            report_file = os.path.join(self.processed_dir, f"analysis_report_{date_str}.txt")
            
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            self.logger.info(f"分析报告已保存: {report_file}")
            
        except Exception as e:
            self.logger.error(f"生成分析报告失败: {e}")
    
    def start_scheduler(self):
        """
        启动定时调度器
        """
        if self.test_mode:
            self.logger.info("测试模式，直接执行一次分析任务")
            self.run_daily_analysis()
            return
        
        scheduler = BlockingScheduler()
        
        # 每天17:00执行任务
        scheduler.add_job(
            func=self.run_daily_analysis,
            trigger=CronTrigger(
                hour=self.config.SCHEDULE_HOUR, 
                minute=self.config.SCHEDULE_MINUTE
            ),
            id='daily_td_analysis',
            name='每日九转序列分析',
            replace_existing=True
        )
        
        self.logger.info(f"定时调度器已启动，每天{self.config.SCHEDULE_HOUR}:{self.config.SCHEDULE_MINUTE:02d}执行分析任务")
        self.logger.info("按 Ctrl+C 停止程序")
        
        try:
            scheduler.start()
        except KeyboardInterrupt:
            self.logger.info("程序已停止")
            scheduler.shutdown()
    
    def run_test(self, max_test_stocks=10):
        """
        运行测试
        
        Args:
            max_test_stocks: 测试股票数量
        """
        self.logger.info(f"开始测试模式，分析 {max_test_stocks} 只股票")
        
        # 临时设置测试参数
        original_max = self.max_stocks
        self.max_stocks = max_test_stocks
        
        # 执行分析
        success = self.run_daily_analysis()
        
        # 恢复原始参数
        self.max_stocks = original_max
        
        if success:
            self.logger.info("测试完成，可以查看生成的文件")
            self.logger.info(f"- 数据文件: {self.processed_dir}")
            self.logger.info(f"- 图表文件: {self.html_dir}")
            self.logger.info("- 启动Web服务: python web/app.py")
        else:
            self.logger.error("测试失败")
        
        return success

@handle_exceptions(TDAnalysisException)
def main():
    """
    主函数
    """
    # 获取配置和初始化日志
    config = get_config()
    logger = get_logger('main')
    
    parser = argparse.ArgumentParser(description='九转序列A股分析系统')
    parser.add_argument('--test', action='store_true', help='测试模式')
    parser.add_argument('--max-stocks', type=int, default=config.MAX_STOCKS, help='最大股票数量')
    parser.add_argument('--test-stocks', type=int, default=config.TEST_STOCKS, help='测试股票数量')
    
    args = parser.parse_args()
    
    logger.info("九转序列A股分析系统启动")
    logger.debug(f"参数: test={args.test}, max_stocks={args.max_stocks}, test_stocks={args.test_stocks}")
    
    try:
        # 创建分析系统
        system = TDSequentialAnalysisSystem(
            max_stocks=args.max_stocks,
            test_mode=args.test
        )
        
        if args.test:
            # 测试模式
            logger.info("运行测试模式")
            success = system.run_test(args.test_stocks)
            if not success:
                logger.error("测试模式执行失败")
                sys.exit(1)
        else:
            # 正常模式，启动定时调度
            logger.info("启动定时调度模式")
            system.start_scheduler()
            
    except KeyboardInterrupt:
        logger.info("用户中断程序")
    except Exception as e:
        logger.error(f"程序执行失败: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()