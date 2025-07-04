#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
九转序列分析系统 - Web界面

提供Web界面查看分析结果
"""

from flask import Flask, render_template, render_template_string, request, jsonify, send_file, redirect, url_for
import pandas as pd
import os
import sys
from datetime import datetime
import glob
import json

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import get_config
from utils import (
    get_logger, log_execution_time, handle_exceptions, 
    TDAnalysisException, PerformanceMonitor, safe_execute
)

from core.fetch_data import StockDataFetcher
from core.td_calc import TDSequentialCalculator
from core.plot_kline import KLineChartPlotter

app = Flask(__name__)
app.config['SECRET_KEY'] = 'td_sequential_stock_analysis'

# 获取配置和初始化日志
config = get_config()
logger = get_logger('web_app')

# 配置目录
data_dir = config.DATA_DIR
html_dir = config.HTML_CHARTS_DIR
processed_dir = config.PROCESSED_DATA_DIR

class WebStockAnalyzer:
    def __init__(self):
        self.fetcher = StockDataFetcher(data_dir)
        self.calculator = TDSequentialCalculator()
        self.plotter = KLineChartPlotter(html_dir)
        self.signal_stocks_cache = None
        self.last_update = None
    
    def get_latest_signal_stocks(self):
        """
        获取最新的信号股票数据
        """
        try:
            # 查找最新的信号股票文件
            processed_dir = os.path.join(data_dir, 'processed')
            signal_files = glob.glob(os.path.join(processed_dir, 'signal_stocks_*.csv'))
            
            if not signal_files:
                return pd.DataFrame(), None
            
            # 获取最新文件
            latest_file = max(signal_files, key=os.path.getctime)
            
            # 读取数据
            signal_stocks = pd.read_csv(latest_file, encoding='utf-8-sig')
            
            # 获取文件日期
            file_date = os.path.basename(latest_file).split('_')[-1].replace('.csv', '')
            
            return signal_stocks, file_date
            
        except Exception as e:
            print(f"获取信号股票数据失败: {e}")
            return pd.DataFrame(), None
    
    def get_stock_chart_path(self, stock_code):
        """
        获取股票K线图文件路径
        """
        try:
            # 标准化股票代码格式
            if stock_code and len(stock_code) < 6:
                # 如果是短格式（如"2"），补齐为6位
                stock_code = stock_code.zfill(6)
            
            # 查找对应的HTML文件
            chart_files = glob.glob(os.path.join(html_dir, f"{stock_code}_*.html"))
            
            if chart_files:
                return max(chart_files, key=os.path.getctime)
            
            return None
            
        except Exception as e:
            print(f"获取图表文件失败: {e}")
            return None

analyzer = WebStockAnalyzer()

@app.route('/')
@log_execution_time
@handle_exceptions(TDAnalysisException)
def index():
    """
    主页 - 显示信号股票列表
    """
    with PerformanceMonitor("主页加载"):
        try:
            signal_stocks, file_date = analyzer.get_latest_signal_stocks()
            
            if signal_stocks.empty:
                logger.warning("未找到信号股票数据")
                return render_template_string(NO_DATA_TEMPLATE)
            
            # 计算统计信息
            total_signals = len(signal_stocks)
            buy_signals = len(signal_stocks[signal_stocks['signal_type'] == 'buy'])
            sell_signals = len(signal_stocks[signal_stocks['signal_type'] == 'sell'])
            
            logger.info(f"主页数据加载完成: 总信号{total_signals}, 买入{buy_signals}, 卖出{sell_signals}")
            
            # 转换为HTML表格数据
            stocks_data = []
            for _, row in signal_stocks.iterrows():
                stocks_data.append({
                    'stock_code': row['stock_code'],
                    'date': row['date'],
                    'close_price': f"{row['close_price']:.2f}",
                    'signal_type': '买入信号' if row['signal_type'] == 'buy' else '卖出信号',
                    'signal_type_class': 'buy' if row['signal_type'] == 'buy' else 'sell',
                    'setup_count': row['setup_count']
                })
            
            return render_template_string(
                INDEX_TEMPLATE,
                stocks_data=stocks_data,
                total_signals=total_signals,
                buy_signals=buy_signals,
                sell_signals=sell_signals,
                file_date=file_date
            )
            
        except Exception as e:
            logger.error(f"主页加载失败: {e}", exc_info=True)
            return f"<h1>错误</h1><p>加载数据失败: {e}</p>"

@app.route('/chart/<stock_code>')
@log_execution_time
@handle_exceptions(TDAnalysisException)
def show_chart(stock_code):
    """
    显示指定股票的K线图
    """
    with PerformanceMonitor(f"加载图表-{stock_code}"):
        try:
            if not stock_code or not stock_code.strip():
                logger.warning("股票代码为空")
                return "<h1>错误</h1><p>股票代码不能为空</p>"
            
            chart_path = analyzer.get_stock_chart_path(stock_code)
            
            if chart_path and os.path.exists(chart_path):
                logger.info(f"成功加载股票图表: {stock_code}")
                return send_file(chart_path)
            else:
                logger.warning(f"图表文件不存在: {stock_code}")
                return f"<h1>图表不存在</h1><p>股票代码 {stock_code} 的K线图不存在</p>"
                
        except Exception as e:
            logger.error(f"加载图表失败 {stock_code}: {e}", exc_info=True)
            return f"<h1>错误</h1><p>加载图表失败: {e}</p>"

@app.route('/api/stocks')
@log_execution_time
@handle_exceptions(TDAnalysisException)
def api_stocks():
    """
    API接口 - 返回信号股票JSON数据
    """
    with PerformanceMonitor("API获取股票数据"):
        try:
            signal_stocks, file_date = analyzer.get_latest_signal_stocks()
            
            if signal_stocks.empty:
                logger.warning("API请求: 暂无信号股票数据")
                return jsonify({
                    'success': False,
                    'message': '暂无信号股票数据',
                    'data': []
                })
            
            # 转换为JSON格式
            stocks_list = signal_stocks.to_dict('records')
            
            logger.info(f"API成功返回{len(stocks_list)}只信号股票数据")
            
            return jsonify({
                'success': True,
                'message': '获取成功',
                'data': stocks_list,
                'summary': {
                    'total': len(signal_stocks),
                    'buy_signals': len(signal_stocks[signal_stocks['signal_type'] == 'buy']),
                    'sell_signals': len(signal_stocks[signal_stocks['signal_type'] == 'sell']),
                    'date': file_date
                }
            })
            
        except Exception as e:
            logger.error(f"API获取股票数据失败: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'message': f'获取数据失败: {e}',
                'data': []
            })

@app.route('/summary')
@log_execution_time
@handle_exceptions(TDAnalysisException)
def summary():
    """
    汇总页面
    """
    with PerformanceMonitor("加载汇总图表"):
        try:
            # 查找汇总图表文件
            summary_files = glob.glob(os.path.join(html_dir, 'signal_summary_*.html'))
            
            if summary_files:
                latest_summary = max(summary_files, key=os.path.getctime)
                logger.info(f"成功加载汇总图表: {os.path.basename(latest_summary)}")
                return send_file(latest_summary)
            else:
                logger.warning(f"汇总图表文件不存在: {html_dir}")
                return "<h1>汇总图表不存在</h1><p>请先运行数据分析任务</p>"
                
        except Exception as e:
            logger.error(f"加载汇总图表失败: {e}", exc_info=True)
            return f"<h1>错误</h1><p>加载汇总图表失败: {e}</p>"

# HTML模板
INDEX_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>A股九转序列信号 - {{ file_date }}</title>
    <style>
        body {
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #eee;
        }
        .header h1 {
            color: #333;
            margin-bottom: 10px;
        }
        .stats {
            display: flex;
            justify-content: center;
            gap: 30px;
            margin: 20px 0;
        }
        .stat-item {
            text-align: center;
            padding: 15px;
            border-radius: 8px;
            min-width: 100px;
        }
        .stat-total { background-color: #e3f2fd; }
        .stat-buy { background-color: #e8f5e8; }
        .stat-sell { background-color: #ffebee; }
        .stat-number {
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 5px;
        }
        .stat-label {
            font-size: 14px;
            color: #666;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #f8f9fa;
            font-weight: bold;
            color: #333;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        .signal-buy {
            color: #4caf50;
            font-weight: bold;
        }
        .signal-sell {
            color: #f44336;
            font-weight: bold;
        }
        .stock-link {
            color: #1976d2;
            text-decoration: none;
            font-weight: bold;
        }
        .stock-link:hover {
            text-decoration: underline;
        }
        .nav-links {
            text-align: center;
            margin: 20px 0;
        }
        .nav-links a {
            display: inline-block;
            margin: 0 10px;
            padding: 10px 20px;
            background-color: #1976d2;
            color: white;
            text-decoration: none;
            border-radius: 5px;
        }
        .nav-links a:hover {
            background-color: #1565c0;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>A股九转序列信号监控</h1>
            <p>数据日期: {{ file_date }}</p>
            
            <div class="stats">
                <div class="stat-item stat-total">
                    <div class="stat-number">{{ total_signals }}</div>
                    <div class="stat-label">总信号数</div>
                </div>
                <div class="stat-item stat-buy">
                    <div class="stat-number">{{ buy_signals }}</div>
                    <div class="stat-label">买入信号</div>
                </div>
                <div class="stat-item stat-sell">
                    <div class="stat-number">{{ sell_signals }}</div>
                    <div class="stat-label">卖出信号</div>
                </div>
            </div>
            
            <div class="nav-links">
                <a href="/summary">查看汇总图表</a>
                <a href="/api/stocks">API数据</a>
            </div>
        </div>
        
        <table>
            <thead>
                <tr>
                    <th>股票代码</th>
                    <th>日期</th>
                    <th>收盘价</th>
                    <th>信号类型</th>
                    <th>Setup计数</th>
                    <th>操作</th>
                </tr>
            </thead>
            <tbody>
                {% for stock in stocks_data %}
                <tr>
                    <td>{{ stock.stock_code }}</td>
                    <td>{{ stock.date }}</td>
                    <td>{{ stock.close_price }}</td>
                    <td class="signal-{{ stock.signal_type_class }}">{{ stock.signal_type }}</td>
                    <td>{{ stock.setup_count }}</td>
                    <td>
                        <a href="/chart/{{ stock.stock_code }}" class="stock-link" target="_blank">查看K线图</a>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</body>
</html>
"""

NO_DATA_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>A股九转序列信号</title>
    <style>
        body {
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            text-align: center;
        }
        .container {
            max-width: 600px;
            margin: 100px auto;
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            margin-bottom: 20px;
        }
        p {
            color: #666;
            font-size: 16px;
            line-height: 1.6;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>暂无信号数据</h1>
        <p>当前没有九转序列信号股票数据。</p>
        <p>请先运行数据分析任务生成信号数据。</p>
    </div>
</body>
</html>
"""

@handle_exceptions(TDAnalysisException)
def main():
    """
    启动Web应用
    """
    logger.info("九转序列分析系统 Web界面启动")
    logger.info(f"访问地址: http://localhost:{config.WEB_PORT}")
    logger.info("按 Ctrl+C 停止服务")
    
    try:
        app.run(
            host=config.WEB_HOST, 
            port=config.WEB_PORT, 
            debug=config.WEB_DEBUG
        )
    except KeyboardInterrupt:
        logger.info("用户中断Web服务")
    except Exception as e:
        logger.error(f"Web服务启动失败: {e}", exc_info=True)
        raise TDAnalysisException(f"Web服务启动失败: {e}")

if __name__ == '__main__':
    main()