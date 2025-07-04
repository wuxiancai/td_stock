#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# 添加项目根目录到路径
sys.path.append('/Users/wuxiancai/td_stock')

from core.plot_kline import KLineChartPlotter
from config import DevelopmentConfig

def generate_300040_test_data():
    """生成300040股票的测试数据，包含涨跌变化和完整TD序列"""
    # 生成30天的测试数据
    dates = [datetime.now() - timedelta(days=i) for i in range(29, -1, -1)]
    
    # 基础价格数据 - 模拟真实的涨跌变化
    base_price = 50.0  # 300040的大概价格区间
    data = []
    
    for i, date in enumerate(dates):
        # 模拟真实的涨跌变化
        if i == 0:
            price_change = 0
        else:
            # 随机涨跌，确保有明显的涨跌变化
            price_change = np.random.uniform(-3.0, 3.0)
        
        base_price += price_change
        base_price = max(base_price, 30.0)  # 防止价格过低
        
        # 生成OHLC数据，确保有涨跌变化
        if i == 0:
            open_price = base_price
        else:
            open_price = data[i-1]['close']  # 开盘价等于前一天收盘价
        
        # 随机生成当日高低点
        high_offset = np.random.uniform(0.5, 2.0)
        low_offset = np.random.uniform(0.5, 2.0)
        
        high_price = max(open_price, base_price) + high_offset
        low_price = min(open_price, base_price) - low_offset
        close_price = base_price
        
        volume = np.random.randint(1000000, 8000000)
        
        data.append({
            'date': date.strftime('%Y-%m-%d'),
            'open': round(open_price, 2),
            'high': round(high_price, 2),
            'low': round(low_price, 2),
            'close': round(close_price, 2),
            'volume': volume
        })
    
    df = pd.DataFrame(data)
    
    # 添加完整的TD序列数据
    # 买入序列（1-9）在前半段
    buy_sequence = [0] * 30
    buy_sequence[3:12] = [1, 2, 3, 4, 5, 6, 7, 8, 9]  # 第4-12天
    
    # 卖出序列（1-7）在后半段
    sell_sequence = [0] * 30
    sell_sequence[18:25] = [1, 2, 3, 4, 5, 6, 7]  # 第19-25天
    
    df['buy_setup_count'] = buy_sequence
    df['sell_setup_count'] = sell_sequence
    
    return df

def main():
    """主函数"""
    try:
        # 初始化配置
        config = DevelopmentConfig()
        
        # 创建图表绘制器
        plotter = KLineChartPlotter(config.HTML_CHARTS_DIR)
        
        # 生成300040测试数据
        test_data = generate_300040_test_data()
        
        print("生成的300040测试数据:")
        print(test_data[['date', 'open', 'close', 'buy_setup_count', 'sell_setup_count']].to_string())
        
        # 打印数据列名进行调试
        print(f"\n传入create_kline_chart的数据列名: {list(test_data.columns)}")
        print(f"数据形状: {test_data.shape}")
        print(f"buy_setup_count列的值: {test_data['buy_setup_count'].tolist()}")
        print(f"sell_setup_count列的值: {test_data['sell_setup_count'].tolist()}")
        
        # 创建图表
        chart_file = plotter.create_kline_chart(
            stock_code='300040',
            stock_name='九洲药业',
            df=test_data,
            show_volume=True
        )
        
        print(f"\n图表已生成: {chart_file}")
        print(f"可通过以下地址查看: http://localhost:8081/chart/300040")
        
        # 验证涨跌变化
        up_days = 0
        down_days = 0
        for i in range(1, len(test_data)):
            if test_data.iloc[i]['close'] > test_data.iloc[i]['open']:
                up_days += 1
            elif test_data.iloc[i]['close'] < test_data.iloc[i]['open']:
                down_days += 1
        
        print(f"\n数据验证:")
        print(f"上涨天数: {up_days}")
        print(f"下跌天数: {down_days}")
        print(f"买入序列: {[i for i, x in enumerate(test_data['buy_setup_count']) if x > 0]}")
        print(f"卖出序列: {[i for i, x in enumerate(test_data['sell_setup_count']) if x > 0]}")
        
    except Exception as e:
        print(f"生成测试图表时发生错误: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()