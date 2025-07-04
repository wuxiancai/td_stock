#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
K线图绘制模块
使用Plotly生成交互式HTML K线图，并添加九转序列标记
"""

import plotly.graph_objects as go
import plotly.offline as pyo
from plotly.subplots import make_subplots
import pandas as pd
import os
import sys
from datetime import datetime

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import get_config
from utils import (
    get_logger, log_execution_time, handle_exceptions, file_cached,
    ChartGenerationException, validate_kline_data, InputSanitizer, PerformanceMonitor
)
class KLineChartPlotter:
    def __init__(self, output_dir=None):
        self.config = get_config()
        self.logger = get_logger('chart_plotter')
        self.sanitizer = InputSanitizer()
        
        # 使用配置中的输出目录或传入的目录
        self.output_dir = output_dir or self.config.CHART_OUTPUT_DIR
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 图表配置
        self.chart_width = getattr(self.config, 'CHART_WIDTH', 1200)
        self.chart_height = getattr(self.config, 'CHART_HEIGHT', 800)
        
        self.logger.info(f"K线图表绘制器初始化完成，输出目录: {self.output_dir}")
        self.logger.debug(f"图表尺寸: {self.chart_width}x{self.chart_height}")
    
    @file_cached(timeout=1800, key_prefix='kline_chart_')
    @log_execution_time
    @handle_exceptions(context='创建K线图表')
    def create_kline_chart(self, stock_code: str, stock_name: str, df: pd.DataFrame, 
                          show_volume: bool = True) -> str:
        """
        创建K线图表
        
        Args:
            stock_code: 股票代码
            stock_name: 股票名称
            df: 包含OHLCV和九转序列数据的DataFrame
            show_volume: 是否显示成交量
        
        Returns:
            str: 生成的HTML文件路径
        """
        if not stock_code or not stock_name:
            raise ChartGenerationException("股票代码和股票名称不能为空", chart_type='kline')
        
        if df is None or df.empty:
            self.logger.warning(f"股票 {stock_code} 的数据为空，跳过图表生成")
            return ""
        
        # 验证和清理输入
        stock_code = self.sanitizer.sanitize_filename(stock_code)
        stock_name = self.sanitizer.sanitize_filename(stock_name)
        df = validate_kline_data(df)
        
        try:
            with PerformanceMonitor(f'生成K线图表-{stock_code}'):
                self.logger.debug(f"开始生成股票 {stock_code} 的K线图表，数据行数: {len(df)}")
                
                # 创建子图
                if show_volume:
                    fig = make_subplots(
                        rows=2, cols=1,
                        shared_xaxes=True,
                        vertical_spacing=0.1,
                        subplot_titles=(f'{stock_code} {stock_name} - K线图', '成交量'),
                        row_width=[0.7, 0.3]
                    )
                else:
                    fig = go.Figure()
                
                # 添加K线图
                candlestick = go.Candlestick(
                    x=df['date'],
                    open=df['open'],
                    high=df['high'],
                    low=df['low'],
                    close=df['close'],
                    name='K线',
                    increasing_line_color='red',
                    decreasing_line_color='green'
                )
                
                if show_volume:
                    fig.add_trace(candlestick, row=1, col=1)
                else:
                    fig.add_trace(candlestick)
                
                # 添加九转序列标记
                self._add_td_signals(fig, df, show_volume)
                
                # 添加成交量图
                if show_volume:
                    self._add_volume_chart(fig, df)
                
                # 设置图表布局
                self._set_chart_layout(fig, stock_code, stock_name, show_volume)
                
                # 保存为HTML文件
                html_file = self._save_chart(fig, stock_code, stock_name)
                
                self.logger.info(f"股票 {stock_code} 的K线图表生成完成: {html_file}")
                return html_file
                
        except Exception as e:
            raise ChartGenerationException(
                f"生成股票 {stock_code} 的K线图表时发生错误: {str(e)}",
                chart_type='kline'
            )
    
    def _add_td_signals(self, fig, df: pd.DataFrame, show_volume: bool):
        """
        添加九转序列信号标记
        
        Args:
            fig: Plotly图表对象
            df: 数据DataFrame
            show_volume: 是否显示成交量
        """
        try:
            # 检查是否有信号列
            if 'setup_signal' not in df.columns:
                self.logger.debug("数据中没有setup_signal列，跳过信号标记")
                return
            
            # 筛选有信号的数据点
            signal_data = df[df['setup_signal'] != 0].copy()
            
            if signal_data.empty:
                self.logger.debug("没有发现TD序列信号")
                return
            
            signal_count = 0
            
            for _, row in signal_data.iterrows():
                try:
                    signal_type = row['setup_signal']
                    position = row.get('signal_position', 'below' if signal_type == 1 else 'above')
                    setup_count = row.get('buy_setup_count', 0) if signal_type == 1 else row.get('sell_setup_count', 0)
                    
                    # 确定标记位置
                    if position == 'above':
                        # 上涨行情，标记在K线上方
                        y_position = row['high'] * 1.02
                        arrow_direction = 'down'
                        color = 'red'
                        symbol_text = f"{setup_count}"
                    else:
                        # 下跌行情，标记在K线下方
                        y_position = row['low'] * 0.98
                        arrow_direction = 'up'
                        color = 'green'
                        symbol_text = f"{setup_count}"
                    
                    # 添加数字标记
                    annotation = dict(
                        x=row['date'],
                        y=y_position,
                        text=symbol_text,
                        showarrow=True,
                        arrowhead=2,
                        arrowsize=1,
                        arrowwidth=2,
                        arrowcolor=color,
                        ax=0,
                        ay=-30 if arrow_direction == 'down' else 30,
                        font=dict(
                            size=14,
                            color=color,
                            family="Arial Black"
                        ),
                        bgcolor="white",
                        bordercolor=color,
                        borderwidth=2,
                        borderpad=4,
                        opacity=0.8
                    )
                    
                    if show_volume:
                        fig.add_annotation(annotation, row=1, col=1)
                    else:
                        fig.add_annotation(annotation)
                    
                    signal_count += 1
                    
                except Exception as e:
                    self.logger.warning(f"添加单个TD序列信号标记时发生错误: {str(e)}")
                    continue
            
            if signal_count > 0:
                self.logger.debug(f"成功添加了 {signal_count} 个TD序列信号标记")
                
        except Exception as e:
            self.logger.error(f"添加TD序列信号标记时发生错误: {str(e)}")
            # 不抛出异常，允许图表继续生成
    
    def _add_volume_chart(self, fig, df: pd.DataFrame):
        """
        添加成交量图表
        
        Args:
            fig: Plotly图表对象
            df: 数据DataFrame
        """
        try:
            if 'volume' not in df.columns:
                self.logger.warning("数据中没有volume列，跳过成交量图表")
                return
            
            # 计算成交量颜色（红涨绿跌）
            colors = []
            for i in range(len(df)):
                if i == 0:
                    colors.append('red')  # 第一天默认红色
                else:
                    if df.iloc[i]['close'] >= df.iloc[i-1]['close']:
                        colors.append('red')  # 涨或平，红色
                    else:
                        colors.append('green')  # 跌，绿色
            
            # 添加成交量柱状图
            volume_trace = go.Bar(
                x=df['date'],
                y=df['volume'],
                name='成交量',
                marker_color=colors,
                opacity=0.7
            )
            
            fig.add_trace(volume_trace, row=2, col=1)
            self.logger.debug("成交量图表添加完成")
            
        except Exception as e:
            self.logger.error(f"添加成交量图表时发生错误: {str(e)}")
            # 不抛出异常，允许图表继续生成
    
    def _set_chart_layout(self, fig, stock_code: str, stock_name: str, show_volume: bool):
        """
        设置图表布局
        
        Args:
            fig: Plotly图表对象
            stock_code: 股票代码
            stock_name: 股票名称
            show_volume: 是否显示成交量
        """
        try:
            title = f"{stock_code} {stock_name} - 九转序列分析"
            
            fig.update_layout(
                title={
                    'text': title,
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 20}
                },
                xaxis_title="日期",
                yaxis_title="价格",
                template="plotly_white",
                showlegend=True,
                height=self.chart_height,
                width=self.chart_width,
                hovermode='x unified'
            )
            
            # 设置x轴格式
            fig.update_xaxes(
                rangeslider_visible=False,
                type='date'
            )
            
            if show_volume:
                # 设置成交量y轴标题
                fig.update_yaxes(title_text="成交量", row=2, col=1)
            
            self.logger.debug(f"图表布局设置完成，尺寸: {self.chart_width}x{self.chart_height}")
            
        except Exception as e:
            self.logger.error(f"设置图表布局时发生错误: {str(e)}")
            raise ChartGenerationException(
                f"设置图表布局失败: {str(e)}",
                chart_type='layout'
            )
            fig.update_yaxes(title_text="成交量", row=2, col=1)
            
            # 隐藏成交量图的x轴标签
            fig.update_xaxes(showticklabels=False, row=1, col=1)
    
    def _save_chart(self, fig, stock_code: str, stock_name: str) -> str:
        """
        保存图表为HTML文件
        
        Args:
            fig: Plotly图表对象
            stock_code: 股票代码
            stock_name: 股票名称
        
        Returns:
            str: HTML文件路径
        """
        try:
            # 生成文件名
            date_str = datetime.now().strftime('%Y%m%d')
            # 清理文件名中的特殊字符
            safe_stock_code = self.sanitizer.sanitize_filename(stock_code)
            safe_stock_name = self.sanitizer.sanitize_filename(stock_name)
            filename = f"{safe_stock_code}_{safe_stock_name}_{date_str}.html"
            filepath = os.path.join(self.output_dir, filename)
            
            # 确保输出目录存在
            os.makedirs(self.output_dir, exist_ok=True)
            
            # 保存为HTML文件
            fig.write_html(
                filepath,
                config={
                    'displayModeBar': True,
                    'displaylogo': False,
                    'modeBarButtonsToRemove': ['pan2d', 'lasso2d'],
                    'responsive': True
                },
                include_plotlyjs='cdn'  # 使用CDN加载plotly.js，减小文件大小
            )
            
            # 验证文件是否成功创建
            if not os.path.exists(filepath):
                raise ChartGenerationException(
                    f"图表文件创建失败: {filepath}",
                    chart_type='save'
                )
            
            file_size = os.path.getsize(filepath)
            self.logger.debug(f"图表文件保存成功: {filepath}, 文件大小: {file_size} bytes")
            
            return filepath
            
        except Exception as e:
            raise ChartGenerationException(
                 f"保存图表文件时发生错误: {str(e)}",
                 chart_type='save'
             )
    
    @file_cached(timeout=1800, key_prefix='summary_chart_')
    @log_execution_time
    @handle_exceptions(context='创建汇总图表')
    def create_summary_chart(self, signal_stocks_df: pd.DataFrame) -> str:
        """
        创建信号股票汇总图表
        
        Args:
            signal_stocks_df: 信号股票DataFrame
        
        Returns:
            str: HTML文件路径
        """
        if signal_stocks_df is None or signal_stocks_df.empty:
            self.logger.warning("信号股票数据为空，跳过汇总图表生成")
            return ""
        
        try:
            with PerformanceMonitor('生成汇总图表'):
                self.logger.debug(f"开始生成汇总图表，信号股票数: {len(signal_stocks_df)}")
                
                # 创建汇总统计图
                buy_count = len(signal_stocks_df[signal_stocks_df['signal_type'] == 'buy'])
                sell_count = len(signal_stocks_df[signal_stocks_df['signal_type'] == 'sell'])
                
                fig = go.Figure()
                
                # 添加柱状图
                fig.add_trace(go.Bar(
                    x=['买入信号', '卖出信号'],
                    y=[buy_count, sell_count],
                    marker_color=['green', 'red'],
                    text=[buy_count, sell_count],
                    textposition='auto'
                ))
                
                fig.update_layout(
                    title={
                        'text': f'九转序列信号汇总 - {datetime.now().strftime("%Y-%m-%d")}',
                        'x': 0.5,
                        'xanchor': 'center',
                        'font': {'size': 20}
                    },
                    xaxis_title="信号类型",
                    yaxis_title="股票数量",
                    template="plotly_white",
                    height=400,
                    width=600
                )
                
                # 保存文件
                date_str = datetime.now().strftime('%Y%m%d')
                filename = f"signal_summary_{date_str}.html"
                filepath = os.path.join(self.output_dir, filename)
                
                # 确保输出目录存在
                os.makedirs(self.output_dir, exist_ok=True)
                
                fig.write_html(
                    filepath,
                    config={
                        'displayModeBar': True,
                        'displaylogo': False,
                        'responsive': True
                    },
                    include_plotlyjs='cdn'
                )
                
                # 验证文件是否成功创建
                if not os.path.exists(filepath):
                    raise ChartGenerationException(
                        f"汇总图表文件创建失败: {filepath}",
                        chart_type='summary'
                    )
                
                file_size = os.path.getsize(filepath)
                self.logger.info(f"汇总图表生成完成: {filepath}, 文件大小: {file_size} bytes")
                self.logger.info(f"信号统计 - 买入: {buy_count}, 卖出: {sell_count}")
                
                return filepath
                
        except Exception as e:
            raise ChartGenerationException(
                f"生成汇总图表时发生错误: {str(e)}",
                chart_type='summary'
            )
    
    @log_execution_time
    @handle_exceptions(context='批量创建图表')
    def batch_create_charts(self, stocks_data: dict, signal_stocks_df: pd.DataFrame) -> list:
        """
        批量创建K线图表
        
        Args:
            stocks_data: {stock_code: (stock_name, kline_dataframe)}
            signal_stocks_df: 信号股票DataFrame
        
        Returns:
            list: 生成的HTML文件路径列表
        """
        if not stocks_data:
            self.logger.warning("股票数据为空，跳过批量图表生成")
            return []
        
        html_files = []
        
        try:
            with PerformanceMonitor('批量生成图表'):
                # 只为有信号的股票创建图表
                signal_codes = signal_stocks_df['stock_code'].tolist() if not signal_stocks_df.empty else []
                
                self.logger.info(f"开始批量生成图表，信号股票数: {len(signal_codes)}")
                
                success_count = 0
                error_count = 0
                
                for stock_code in signal_codes:
                    try:
                        if stock_code in stocks_data:
                            stock_name, kline_data = stocks_data[stock_code]
                            
                            # 验证数据
                            if kline_data is None or kline_data.empty:
                                self.logger.warning(f"股票 {stock_code} 的K线数据为空，跳过")
                                continue
                            
                            html_file = self.create_kline_chart(stock_code, stock_name, kline_data)
                            if html_file:
                                html_files.append(html_file)
                                success_count += 1
                        else:
                            self.logger.warning(f"股票 {stock_code} 的数据不存在，跳过图表生成")
                            
                    except Exception as e:
                        error_count += 1
                        self.logger.error(f"为股票 {stock_code} 生成图表时发生错误: {str(e)}")
                        # 继续处理其他股票，不中断整个批量处理
                        continue
                
                # 创建汇总图表
                try:
                    summary_file = self.create_summary_chart(signal_stocks_df)
                    if summary_file:
                        html_files.append(summary_file)
                        self.logger.info("汇总图表生成成功")
                except Exception as e:
                    self.logger.error(f"生成汇总图表时发生错误: {str(e)}")
                    # 汇总图表失败不影响其他图表
                
                self.logger.info(f"批量图表生成完成 - 成功: {success_count}, 失败: {error_count}, 总文件数: {len(html_files)}")
                
                return html_files
                
        except Exception as e:
            self.logger.error(f"批量生成图表时发生严重错误: {str(e)}")
            # 即使发生错误，也返回已成功生成的文件
            return html_files

if __name__ == "__main__":
    # 测试代码
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
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
    
    # 计算九转序列
    calculator = TDSequentialCalculator()
    test_data_with_td = calculator.calculate_td_setup(test_data)
    
    # 创建图表
    plotter = KLineChartPlotter()
    html_file = plotter.create_kline_chart('TEST001', '测试股票', test_data_with_td)
    
    print(f"测试图表已生成: {html_file}")