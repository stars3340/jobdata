#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能招聘数据分析平台 - 极轻量级版本
保持完整功能，最小化依赖
"""

import os
import json
from datetime import datetime, timedelta, date
from flask import Flask, render_template_string, jsonify, request, Response
import pymysql

# 创建Flask应用
app = Flask(__name__)

# 数据库连接配置
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'bj-cynosdbmysql-grp-5eypnf9y.sql.tencentcdb.com'),
    'port': int(os.getenv('DB_PORT', 26606)),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', 'Gn123456'),
    'database': os.getenv('DB_NAME', 'recruit-db'),
    'charset': os.getenv('DB_CHARSET', 'utf8mb4')
}

def get_db_connection():
    """获取数据库连接"""
    try:
        return pymysql.connect(**DB_CONFIG)
    except Exception as e:
        print(f"数据库连接失败: {e}")
        return None

def query_data(sql):
    """执行SQL查询，返回字典列表（替代pandas）"""
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor(pymysql.cursors.DictCursor)
            cursor.execute(sql)
            result = cursor.fetchall()
            return result
        except Exception as e:
            print(f"查询失败: {e}")
            return []
        finally:
            connection.close()
    return []

def get_funnel_data(start_date=None, end_date=None, user_id=None):
    """获取漏斗数据（无pandas版本）"""
    where_conditions = []
    
    if start_date and end_date:
        where_conditions.append(f"create_time BETWEEN '{start_date}' AND '{end_date} 23:59:59'")
    
    if user_id and user_id != 'all':
        where_conditions.append(f"uid = '{user_id}'")
    
    where_clause = " AND ".join(where_conditions)
    if where_clause:
        where_clause = f"WHERE {where_clause}"
    
    sql = f"""
    SELECT event_type, COUNT(*) as count
    FROM recruit_event {where_clause}
    GROUP BY event_type
    ORDER BY count DESC
    """
    
    result = query_data(sql)
    
    # 事件类型映射
    event_mapping = {
        '1': '查看简历',
        '2': '简历通过筛选',
        '12': 'Boss上聊天', 
        '13': '交换联系方式'
    }
    
    # 构建漏斗数据
    funnel_data = []
    for event_num, event_name in event_mapping.items():
        count = 0
        for row in result:
            if str(row['event_type']) == event_num:
                count = row['count']
                break
        funnel_data.append({
            'stage': event_name,
            'count': count,
            'order': list(event_mapping.keys()).index(event_num) + 1
        })
    
    # 按顺序排序
    return sorted(funnel_data, key=lambda x: x['order'])

def get_trend_data(start_date=None, end_date=None, user_id=None):
    """获取趋势数据（无pandas版本）"""
    where_conditions = []
    
    if start_date and end_date:
        where_conditions.append(f"create_time BETWEEN '{start_date}' AND '{end_date} 23:59:59'")
    
    if user_id and user_id != 'all':
        where_conditions.append(f"uid = '{user_id}'")
    
    where_clause = " AND ".join(where_conditions)
    if where_clause:
        where_clause = f"WHERE {where_clause}"
    
    sql = f"""
    SELECT 
        DATE(create_time) as date,
        event_type,
        COUNT(*) as count
    FROM recruit_event {where_clause}
    GROUP BY DATE(create_time), event_type
    ORDER BY date DESC
    LIMIT 100
    """
    
    result = query_data(sql)
    
    # 事件类型映射
    event_mapping = {
        '1': '查看简历',
        '2': '简历通过筛选',
        '12': 'Boss上聊天',
        '13': '交换联系方式'
    }
    
    # 转换事件类型
    for row in result:
        event_type = str(row['event_type'])
        if event_type in event_mapping:
            row['event_type'] = event_mapping[event_type]
    
    return result

def get_user_list():
    """获取用户列表"""
    sql = """
    SELECT 
        u.id,
        CASE 
            WHEN u.name IS NOT NULL AND u.name != '' THEN u.name
            ELSE CONCAT('用户-', LEFT(u.id, 8))
        END as display_name,
        COUNT(re.id) as event_count
    FROM user u
    LEFT JOIN recruit_event re ON u.id = re.uid
    GROUP BY u.id, u.name
    HAVING event_count > 0
    ORDER BY event_count DESC
    LIMIT 20
    """
    result = query_data(sql)
    
    users = [{'label': '全部用户', 'value': 'all'}]
    for row in result:
        users.append({
            'label': f"{row['display_name']} ({row['event_count']}条)",
            'value': str(row['id'])
        })
    
    return users

def calculate_metrics(funnel_data):
    """计算KPI指标"""
    metrics = {
        'total_views': 0,
        'passed_screening': 0,
        'boss_chats': 0,
        'contact_exchanges': 0,
        'connection_rate': 0,
        'chat_rate': 0
    }
    
    for item in funnel_data:
        if item['stage'] == '查看简历':
            metrics['total_views'] = item['count']
        elif item['stage'] == '简历通过筛选':
            metrics['passed_screening'] = item['count']
        elif item['stage'] == 'Boss上聊天':
            metrics['boss_chats'] = item['count']
        elif item['stage'] == '交换联系方式':
            metrics['contact_exchanges'] = item['count']
    
    # 计算转化率
    if metrics['passed_screening'] > 0:
        metrics['connection_rate'] = (metrics['contact_exchanges'] / metrics['passed_screening']) * 100
        metrics['chat_rate'] = (metrics['boss_chats'] / metrics['passed_screening']) * 100
    
    return metrics

def create_funnel_chart(funnel_data):
    """创建漏斗图数据（Chart.js格式）"""
    if not funnel_data:
        return {}
    
    stages = [item['stage'] for item in funnel_data]
    counts = [item['count'] for item in funnel_data]
    
    # 计算转化率
    conversion_rates = []
    total_count = counts[0] if counts else 0
    
    for i, count in enumerate(counts):
        if i == 0:
            conversion_rates.append(100)
        else:
            if counts[i-1] > 0:
                conversion_rates.append(round((count / counts[i-1]) * 100, 1))
            else:
                conversion_rates.append(0)
    
    return {
        'labels': stages,
        'data': counts,
        'conversion_rates': conversion_rates,
        'colors': ['#06D6A0', '#118AB2', '#FFD166', '#EF476F']
    }

def create_trend_chart(trend_data):
    """创建趋势图数据（Chart.js格式）"""
    if not trend_data:
        return {}
    
    # 使用原生Python进行数据透视
    dates = sorted(list(set([row['date'].strftime('%Y-%m-%d') for row in trend_data])))
    event_types = ['查看简历', '简历通过筛选', 'Boss上聊天', '交换联系方式']
    
    color_map = {
        '查看简历': '#06D6A0',
        '简历通过筛选': '#118AB2',
        'Boss上聊天': '#FFD166', 
        '交换联系方式': '#EF476F'
    }
    
    datasets = []
    
    for event_type in event_types:
        event_data = []
        for date_str in dates:
            count = 0
            for row in trend_data:
                if (row['date'].strftime('%Y-%m-%d') == date_str and 
                    row['event_type'] == event_type):
                    count = row['count']
                    break
            event_data.append(count)
        
        if event_type in color_map:
            datasets.append({
                'label': event_type,
                'data': event_data,
                'borderColor': color_map[event_type],
                'backgroundColor': color_map[event_type] + '20',
                'tension': 0.4
            })
    
    return {
        'labels': dates,
        'datasets': datasets
    }

# 完整的HTML模板（保持原有界面设计）
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🚀 智能招聘数据分析平台</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
            background: linear-gradient(135deg, #0A0E1A 0%, #1a1f3a 100%);
            color: #FFFFFF;
            min-height: 100vh;
        }
        
        .header {
            background: rgba(35, 41, 70, 0.9);
            backdrop-filter: blur(10px);
            padding: 1.5rem 2rem;
            border-bottom: 1px solid rgba(6, 214, 160, 0.3);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .header h1 {
            color: #06D6A0;
            font-size: 2.2rem;
            margin-bottom: 0.5rem;
        }
        
        .header p {
            color: #CBD5E1;
            font-size: 1rem;
        }
        
        .last-update {
            color: #CBD5E1;
            font-size: 0.9rem;
        }
        
        .container {
            max-width: 1400px;
            margin: 2rem auto;
            padding: 0 1rem;
        }
        
        .controls {
            background: rgba(35, 41, 70, 0.6);
            backdrop-filter: blur(10px);
            padding: 1.5rem;
            border-radius: 12px;
            margin-bottom: 2rem;
            border: 1px solid rgba(6, 214, 160, 0.2);
            display: flex;
            flex-wrap: wrap;
            gap: 1rem;
            align-items: end;
        }
        
        .control-group {
            min-width: 200px;
        }
        
        .control-group label {
            display: block;
            margin-bottom: 0.5rem;
            color: #FFFFFF;
            font-weight: 600;
            font-size: 0.9rem;
        }
        
        .control-group input,
        .control-group select,
        .control-group button {
            width: 100%;
            padding: 0.75rem;
            border: 1px solid rgba(6, 214, 160, 0.3);
            border-radius: 8px;
            background: rgba(35, 41, 70, 0.8);
            color: #FFFFFF;
            font-size: 0.9rem;
            transition: all 0.3s ease;
        }
        
        .control-group input:focus,
        .control-group select:focus {
            outline: none;
            border-color: #06D6A0;
            box-shadow: 0 0 0 3px rgba(6, 214, 160, 0.1);
        }
        
        .btn {
            background: linear-gradient(135deg, #06D6A0 0%, #118AB2 100%);
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 8px;
            color: white;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-block;
            text-align: center;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(6, 214, 160, 0.3);
        }
        
        .quick-filters {
            display: flex;
            gap: 0.5rem;
            margin-top: 0.5rem;
        }
        
        .quick-filter-btn {
            padding: 0.5rem 1rem;
            font-size: 0.8rem;
            background: rgba(35, 41, 70, 0.8);
            border: 1px solid rgba(6, 214, 160, 0.3);
            color: #FFFFFF;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .quick-filter-btn:hover,
        .quick-filter-btn.active {
            background: #06D6A0;
            border-color: #06D6A0;
        }
        
        .metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        
        .metric-card {
            background: rgba(35, 41, 70, 0.6);
            backdrop-filter: blur(10px);
            padding: 1.5rem;
            border-radius: 12px;
            border: 1px solid rgba(6, 214, 160, 0.2);
            text-align: center;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }
        
        .metric-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(135deg, #06D6A0 0%, #118AB2 100%);
        }
        
        .metric-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 35px rgba(6, 214, 160, 0.2);
        }
        
        .metric-value {
            font-size: 2.5rem;
            font-weight: bold;
            color: #06D6A0;
            margin-bottom: 0.5rem;
        }
        
        .metric-label {
            color: #FFFFFF;
            font-size: 1rem;
            font-weight: 600;
        }
        
        .charts-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 2rem;
            margin-bottom: 2rem;
        }
        
        .chart-container {
            background: rgba(35, 41, 70, 0.6);
            backdrop-filter: blur(10px);
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px solid rgba(6, 214, 160, 0.2);
        }
        
        .chart-title {
            color: #FFFFFF;
            font-size: 1.3rem;
            font-weight: 600;
            margin-bottom: 1rem;
            text-align: center;
        }
        
        .data-table-section {
            background: rgba(35, 41, 70, 0.6);
            backdrop-filter: blur(10px);
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px solid rgba(6, 214, 160, 0.2);
        }
        
        .table-header {
            margin-bottom: 1rem;
        }
        
        .table-header h3 {
            color: #FFFFFF;
            font-size: 1.3rem;
            font-weight: 600;
            margin-bottom: 1rem;
        }
        
        .table-controls {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
        }
        
        .search-box {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .export-buttons {
            display: flex;
            align-items: center;
            gap: 1rem;
        }
        
        .btn-outline {
            background: transparent;
            border: 1px solid #06D6A0;
            color: #06D6A0;
        }
        
        .btn-outline:hover {
            background: #06D6A0;
            color: white;
        }
        
        .data-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 1rem;
        }
        
        .data-table th,
        .data-table td {
            padding: 0.75rem;
            text-align: left;
            border-bottom: 1px solid rgba(6, 214, 160, 0.2);
            color: #FFFFFF;
        }
        
        .data-table th {
            background: rgba(6, 214, 160, 0.1);
            font-weight: 600;
            color: #06D6A0;
            cursor: pointer;
            user-select: none;
            position: relative;
            transition: background-color 0.3s ease;
        }
        
        .data-table th:hover {
            background: rgba(6, 214, 160, 0.2);
        }
        
        .data-table th.sortable::after {
            content: ' ↕️';
            font-size: 0.8rem;
            opacity: 0.5;
        }
        
        .data-table th.sort-asc::after {
            content: ' ⬆️';
            opacity: 1;
        }
        
        .data-table th.sort-desc::after {
            content: ' ⬇️';
            opacity: 1;
        }
        
        .data-table tr:hover {
            background: rgba(6, 214, 160, 0.05);
        }
        
        .pagination {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 0.5rem;
            margin-top: 1rem;
        }
        
        .pagination button {
            padding: 0.5rem 1rem;
            border: 1px solid rgba(6, 214, 160, 0.3);
            background: rgba(35, 41, 70, 0.8);
            color: #FFFFFF;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .pagination button:hover:not(:disabled) {
            background: #06D6A0;
            border-color: #06D6A0;
        }
        
        .pagination button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        .pagination .current-page {
            background: #06D6A0;
            border-color: #06D6A0;
            font-weight: 600;
        }
        
        .pagination-info {
            color: #CBD5E1;
            font-size: 0.9rem;
            margin: 0 1rem;
        }
        
        .loading {
            text-align: center;
            padding: 3rem;
            color: #CBD5E1;
            font-size: 1.1rem;
        }
        
        .loading-spinner {
            border: 3px solid rgba(6, 214, 160, 0.3);
            border-top: 3px solid #06D6A0;
            border-radius: 50%;
            width: 30px;
            height: 30px;
            animation: spin 1s linear infinite;
            margin: 0 auto 1rem;
        }
        
        .table-loading {
            position: relative;
            min-height: 200px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            background: rgba(35, 41, 70, 0.9);
            border-radius: 8px;
            margin: 1rem 0;
        }
        
        .table-loading-spinner {
            border: 4px solid rgba(6, 214, 160, 0.3);
            border-top: 4px solid #06D6A0;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1.2s linear infinite;
            margin-bottom: 1rem;
        }
        
        .table-loading-text {
            color: #06D6A0;
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 0.5rem;
        }
        
        .table-loading-subtext {
            color: #CBD5E1;
            font-size: 0.9rem;
            opacity: 0.8;
        }
        
        .data-table-wrapper {
            position: relative;
            transition: opacity 0.3s ease;
        }
        
        .data-table-wrapper.loading {
            opacity: 0.5;
            pointer-events: none;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .loading-overlay {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(35, 41, 70, 0.95);
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            z-index: 1000;
            border-radius: 8px;
        }
        
        .refresh-section {
            display: flex;
            align-items: center;
            gap: 1rem;
        }
        
        /* 响应式设计 */
        @media (max-width: 768px) {
            .header {
                flex-direction: column;
                text-align: center;
                gap: 1rem;
            }
            
            .controls {
                flex-direction: column;
            }
            
            .charts-grid {
                grid-template-columns: 1fr;
            }
            
            .table-controls {
                flex-direction: column;
                align-items: stretch;
            }
            
            .search-box {
                flex-direction: column;
                gap: 0.5rem;
            }
            
            .search-box input {
                width: 100% !important;
            }
            
            .export-buttons {
                flex-direction: column;
            }
            
            .pagination {
                flex-wrap: wrap;
                gap: 0.25rem;
            }
            
            .pagination button {
                padding: 0.4rem 0.8rem;
                font-size: 0.9rem;
            }
        }
    </style>
</head>
<body>
    <header class="header">
        <div>
            <h1>🚀 智能招聘数据分析平台</h1>
            <p>实时监控 · 数据驱动 · 智能决策</p>
        </div>
        <div class="refresh-section">
            <span id="last-update" class="last-update">数据加载中...</span>
            <button class="btn" onclick="testDebugData()" style="margin-right: 1rem;">🧪 测试数据</button>
            <button class="btn" onclick="refreshData()">🔄 刷新数据</button>
        </div>
    </header>
    
    <div class="container">
        <!-- 控制面板 -->
        <div class="controls">
            <div class="control-group">
                <label>📅 开始日期</label>
                <input type="date" id="start-date" value="{{ start_date }}">
            </div>
            <div class="control-group">
                <label>📅 结束日期</label>
                <input type="date" id="end-date" value="{{ end_date }}">
            </div>
            <div class="control-group">
                <label>👤 选择用户</label>
                <select id="user-select">
                    <option value="all">全部用户</option>
                </select>
            </div>
            <div class="control-group">
                <label>🔄 自动刷新</label>
                <select id="refresh-interval">
                    <option value="0">关闭</option>
                    <option value="30">30秒</option>
                    <option value="60">1分钟</option>
                    <option value="300">5分钟</option>
                </select>
            </div>
            <div class="control-group">
                <label>⚡ 快速筛选</label>
                <div class="quick-filters">
                    <button class="quick-filter-btn" onclick="setQuickDate('today')">今天</button>
                    <button class="quick-filter-btn" onclick="setQuickDate('yesterday')">昨天</button>
                    <button class="quick-filter-btn active" onclick="setQuickDate('7days')">最近7天</button>
                    <button class="quick-filter-btn" onclick="setQuickDate('30days')">最近30天</button>
                    <button class="quick-filter-btn" onclick="setQuickDate('month')">本月</button>
                </div>
            </div>
        </div>
        
        <!-- KPI指标 -->
        <div class="metrics" id="metrics">
            <div class="loading">
                <div class="loading-spinner"></div>
                数据加载中...
            </div>
        </div>
        
        <!-- 图表区域 -->
        <div class="charts-grid">
            <div class="chart-container">
                <h3 class="chart-title">📊 招聘漏斗分析</h3>
                <div style="height: 450px; position: relative;">
                    <canvas id="funnel-chart"></canvas>
                </div>
            </div>
            
            <div class="chart-container">
                <h3 class="chart-title">📈 每日活动趋势</h3>
                <div style="height: 450px; position: relative;">
                    <canvas id="trend-chart"></canvas>
                </div>
            </div>
        </div>
        
        <!-- 详细数据表 -->
        <div class="data-table-section">
            <div class="table-header">
                <h3>📋 详细数据</h3>
                <div class="table-controls">
                    <div class="search-box">
                        <input type="text" id="table-search" placeholder="🔍 搜索用户、事件类型或日期..." 
                               style="padding: 0.5rem; border: 1px solid rgba(6, 214, 160, 0.3); border-radius: 6px; background: rgba(35, 41, 70, 0.8); color: #FFFFFF; width: 250px;">
                        <button class="btn" onclick="searchTable()" style="margin-left: 0.5rem; padding: 0.5rem 1rem;">搜索</button>
                        <button class="btn btn-outline" onclick="clearSearch()" style="margin-left: 0.5rem; padding: 0.5rem 1rem;">清除</button>
                    </div>
                    <div class="export-buttons">
                        <select id="page-size" onchange="changePageSize()" 
                                style="padding: 0.5rem; border: 1px solid rgba(6, 214, 160, 0.3); border-radius: 6px; background: rgba(35, 41, 70, 0.8); color: #FFFFFF; margin-right: 1rem;">
                            <option value="10">10条/页</option>
                            <option value="20" selected>20条/页</option>
                            <option value="50">50条/页</option>
                            <option value="100">100条/页</option>
                        </select>
                        <button class="btn btn-outline" onclick="exportData('csv')">📄 导出CSV</button>
                    </div>
                </div>
            </div>
            <div class="data-table-wrapper" id="data-table-wrapper">
                <div id="data-table">
                    <div class="table-loading">
                        <div class="table-loading-spinner"></div>
                        <div class="table-loading-text">正在加载数据...</div>
                        <div class="table-loading-subtext">请稍候，系统正在处理您的请求</div>
                    </div>
                </div>
                <div id="table-loading-overlay" class="loading-overlay" style="display: none;">
                    <div class="table-loading-spinner"></div>
                    <div class="table-loading-text">数据处理中...</div>
                    <div class="table-loading-subtext">正在筛选和排序数据</div>
                </div>
            </div>
            <div id="pagination-controls" style="margin-top: 1rem; text-align: center;">
                <!-- 分页控件将在这里动态生成 -->
            </div>
        </div>
    </div>
    
    <script>
        let autoRefreshTimer = null;
        let funnelChart = null;
        let trendChart = null;
        
        // 表格状态
        let tableState = {
            page: 1,
            pageSize: 20,
            sortField: 'create_time',
            sortOrder: 'DESC',
            searchText: ''
        };
        
        // 页面加载完成后初始化
        document.addEventListener('DOMContentLoaded', function() {
            console.log('🚀 页面加载完成，开始初始化...');
            
            // 确保所有元素都存在
            const dataTable = document.getElementById('data-table');
            const overlay = document.getElementById('table-loading-overlay');
            const wrapper = document.getElementById('data-table-wrapper');
            
            console.log('📋 数据表元素:', dataTable ? '✅' : '❌');
            console.log('🎭 遮罩元素:', overlay ? '✅' : '❌');
            console.log('📦 包装元素:', wrapper ? '✅' : '❌');
            
            loadUsers();
            updateData(false, '🚀 初始化中...', '正在加载页面数据');
            setupAutoRefresh();
        });
        
        // 加载用户列表
        async function loadUsers() {
            try {
                const response = await fetch('/api/users');
                const users = await response.json();
                const select = document.getElementById('user-select');
                select.innerHTML = '';
                users.forEach(user => {
                    const option = document.createElement('option');
                    option.value = user.value;
                    option.textContent = user.label;
                    select.appendChild(option);
                });
            } catch (error) {
                console.error('加载用户列表失败:', error);
            }
        }
        
        // 设置快速日期
        function setQuickDate(type) {
            const today = new Date();
            let startDate, endDate;
            
            // 移除所有active类
            document.querySelectorAll('.quick-filter-btn').forEach(btn => 
                btn.classList.remove('active'));
            
            // 添加当前按钮的active类
            event.target.classList.add('active');
            
            switch(type) {
                case 'today':
                    startDate = endDate = today.toISOString().split('T')[0];
                    break;
                case 'yesterday':
                    const yesterday = new Date(today);
                    yesterday.setDate(yesterday.getDate() - 1);
                    startDate = endDate = yesterday.toISOString().split('T')[0];
                    break;
                case '7days':
                    const week = new Date(today);
                    week.setDate(week.getDate() - 7);
                    startDate = week.toISOString().split('T')[0];
                    endDate = today.toISOString().split('T')[0];
                    break;
                case '30days':
                    const month = new Date(today);
                    month.setDate(month.getDate() - 30);
                    startDate = month.toISOString().split('T')[0];
                    endDate = today.toISOString().split('T')[0];
                    break;
                case 'month':
                    startDate = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().split('T')[0];
                    endDate = today.toISOString().split('T')[0];
                    break;
            }
            
            document.getElementById('start-date').value = startDate;
            document.getElementById('end-date').value = endDate;
            updateData(true, '📅 切换日期中...', '正在加载' + getDateRangeText(type) + '的数据');
        }
        
        // 获取日期范围描述文本
        function getDateRangeText(type) {
            switch(type) {
                case 'today': return '今天';
                case 'yesterday': return '昨天';
                case '7days': return '最近7天';
                case '30days': return '最近30天';
                case 'month': return '本月';
                default: return '指定时间段';
            }
        }
        
        // 手动刷新数据
        function refreshData() {
            updateData(false, '🔄 刷新数据中...', '正在获取最新数据');
        }
        
        // 测试调试数据
        async function testDebugData() {
            try {
                showTableLoading('🧪 加载测试数据...', '正在获取调试数据');
                
                const response = await fetch('/api/debug');
                const data = await response.json();
                
                console.log('🧪 调试数据:', data);
                
                if (!response.ok) {
                    throw new Error('调试API请求失败: ' + response.status);
                }
                
                // 更新界面
                if (data.metrics) {
                    updateMetrics(data.metrics);
                }
                
                if (data.funnel_chart) {
                    updateFunnelChart(data.funnel_chart);
                }
                
                updateDataTable(data.table_data, data.pagination);
                
                // 更新最后刷新时间
                document.getElementById('last-update').textContent = 
                    '测试数据加载时间: ' + new Date().toLocaleString();
                
                alert('✅ 测试数据加载成功！如果能看到测试数据，说明前端功能正常。');
                
            } catch (error) {
                console.error('🧪 测试数据失败:', error);
                alert('❌ 测试数据也失败了: ' + error.message);
            } finally {
                hideTableLoading();
            }
        }
        
        // 设置自动刷新
        function setupAutoRefresh() {
            const select = document.getElementById('refresh-interval');
            select.addEventListener('change', function() {
                const interval = parseInt(this.value);
                
                if (autoRefreshTimer) {
                    clearInterval(autoRefreshTimer);
                    autoRefreshTimer = null;
                }
                
                if (interval > 0) {
                    autoRefreshTimer = setInterval(() => {
                        updateData(false, '⏰ 自动刷新中...', '正在更新最新数据');
                    }, interval * 1000);
                }
            });
        }
        
        // 显示加载状态
        function showTableLoading(text = '数据处理中...', subtext = '请稍候') {
            console.log('🔄 显示加载状态:', text);
            
            const overlay = document.getElementById('table-loading-overlay');
            const wrapper = document.getElementById('data-table-wrapper');
            
            if (overlay && wrapper) {
                try {
                    overlay.querySelector('.table-loading-text').textContent = text;
                    overlay.querySelector('.table-loading-subtext').textContent = subtext;
                    overlay.style.display = 'flex';
                    wrapper.classList.add('loading');
                    console.log('✅ 加载状态已显示');
                } catch (error) {
                    console.error('❌ 显示加载状态失败:', error);
                }
            } else {
                console.error('❌ 找不到加载元素');
            }
        }
        
        // 隐藏加载状态
        function hideTableLoading() {
            console.log('⏹️ 隐藏加载状态');
            
            const overlay = document.getElementById('table-loading-overlay');
            const wrapper = document.getElementById('data-table-wrapper');
            
            if (overlay && wrapper) {
                try {
                    overlay.style.display = 'none';
                    wrapper.classList.remove('loading');
                    console.log('✅ 加载状态已隐藏');
                } catch (error) {
                    console.error('❌ 隐藏加载状态失败:', error);
                }
            } else {
                console.error('❌ 找不到加载元素');
            }
        }
        
        // 更新所有数据
        async function updateData(resetPagination = false, loadingText = '数据处理中...', loadingSubtext = '正在获取最新数据') {
            const startDate = document.getElementById('start-date').value;
            const endDate = document.getElementById('end-date').value;
            const userId = document.getElementById('user-select').value;
            
            // 重置分页（搜索或筛选时）
            if (resetPagination) {
                tableState.page = 1;
            }
            
            try {
                // 显示加载动画
                showTableLoading(loadingText, loadingSubtext);
                
                // 更新最后刷新时间
                document.getElementById('last-update').textContent = 
                    '最后更新: ' + new Date().toLocaleString();
                
                // 构建API URL
                const params = new URLSearchParams({
                    start_date: startDate,
                    end_date: endDate,
                    user_id: userId,
                    page: tableState.page,
                    page_size: tableState.pageSize,
                    sort_field: tableState.sortField,
                    sort_order: tableState.sortOrder,
                    search: tableState.searchText
                });
                
                // 获取数据
                const response = await fetch('/api/data?' + params.toString());
                const data = await response.json();
                
                // 调试输出
                console.log('API返回数据:', data);
                
                // 检查响应状态
                if (!response.ok) {
                    throw new Error('API请求失败: ' + response.status);
                }
                
                // 更新KPI指标
                if (data.metrics) {
                    updateMetrics(data.metrics);
                } else {
                    console.error('缺少metrics数据');
                }
                
                // 更新图表
                if (data.funnel_chart && data.funnel_chart.labels) {
                    updateFunnelChart(data.funnel_chart);
                }
                
                if (data.trend_chart && data.trend_chart.labels) {
                    updateTrendChart(data.trend_chart);
                }
                
                // 更新数据表
                console.log('表格数据:', data.table_data);
                console.log('分页信息:', data.pagination);
                console.log('调试信息:', data.debug);
                updateDataTable(data.table_data, data.pagination);
                
            } catch (error) {
                console.error('更新数据失败:', error);
                
                // 显示错误状态
                const dataTableElement = document.getElementById('data-table');
                if (dataTableElement) {
                    dataTableElement.innerHTML = 
                        '<div class="table-loading">' +
                            '<div style="font-size: 2rem; margin-bottom: 1rem;">⚠️</div>' +
                            '<div class="table-loading-text">数据加载失败</div>' +
                            '<div class="table-loading-subtext">请检查网络连接或稍后重试</div>' +
                        '</div>';
                }
                
                // 清空分页控件
                const paginationElement = document.getElementById('pagination-controls');
                if (paginationElement) {
                    paginationElement.innerHTML = '';
                }
                
                showError('数据加载失败，请稍后重试');
            } finally {
                // 确保加载动画被隐藏
                hideTableLoading();
            }
        }
        
        // 更新KPI指标
        function updateMetrics(metrics) {
            const metricsHtml = 
                '<div class="metric-card">' +
                    '<div class="metric-value">' + metrics.total_views.toLocaleString() + '</div>' +
                    '<div class="metric-label">📊 简历查看总数</div>' +
                '</div>' +
                '<div class="metric-card">' +
                    '<div class="metric-value">' + metrics.passed_screening.toLocaleString() + '</div>' +
                    '<div class="metric-label">✅ 通过筛选数量</div>' +
                '</div>' +
                '<div class="metric-card">' +
                    '<div class="metric-value">' + metrics.boss_chats.toLocaleString() + '</div>' +
                    '<div class="metric-label">💬 Boss聊天数量</div>' +
                '</div>' +
                '<div class="metric-card">' +
                    '<div class="metric-value">' + metrics.contact_exchanges.toLocaleString() + '</div>' +
                    '<div class="metric-label">🤝 建联成功数量</div>' +
                '</div>' +
                '<div class="metric-card">' +
                    '<div class="metric-value">' + metrics.connection_rate.toFixed(1) + '%</div>' +
                    '<div class="metric-label">📈 建联转化率</div>' +
                '</div>' +
                '<div class="metric-card">' +
                    '<div class="metric-value">' + metrics.chat_rate.toFixed(1) + '%</div>' +
                    '<div class="metric-label">🎯 聊天转化率</div>' +
                '</div>';
            document.getElementById('metrics').innerHTML = metricsHtml;
        }
        
        // 更新数据表
        function updateDataTable(tableData, pagination) {
            console.log('updateDataTable被调用，数据:', tableData);
            console.log('数据类型:', typeof tableData, '数据长度:', tableData ? tableData.length : 'null');
            console.log('分页信息:', pagination);
            
            const dataTableElement = document.getElementById('data-table');
            const paginationElement = document.getElementById('pagination-controls');
            
            if (!tableData || tableData.length === 0) {
                console.log('数据表为空，显示暂无数据');
                dataTableElement.innerHTML = 
                    '<div class="table-loading">' +
                        '<div style="font-size: 2rem; margin-bottom: 1rem;">📭</div>' +
                        '<div class="table-loading-text">暂无数据</div>' +
                        '<div class="table-loading-subtext">请尝试调整筛选条件或搜索关键词</div>' +
                    '</div>';
                paginationElement.innerHTML = '';
                return;
            }
            
            // 定义显示的列（过滤掉内部字段）
            const displayColumns = ['日期', '用户名', '事件类型', '次数'];
            const sortableColumns = {
                '日期': '日期',
                '用户名': '用户名', 
                '事件类型': '事件类型',
                '次数': '次数'
            };
            
            // 生成表格HTML
            let tableHtml = '<table class="data-table"><thead><tr>';
            
            displayColumns.forEach(header => {
                const isSortable = sortableColumns[header];
                const isCurrentSort = tableState.sortField === header;
                let headerClass = 'sortable';
                
                if (isCurrentSort) {
                    headerClass += tableState.sortOrder === 'ASC' ? ' sort-asc' : ' sort-desc';
                }
                
                tableHtml += '<th class="' + headerClass + '" onclick="sortTable(\'' + header + '\')">' + header + '</th>';
            });
            tableHtml += '</tr></thead><tbody>';
            
            // 显示数据行
            tableData.forEach(row => {
                tableHtml += '<tr>';
                displayColumns.forEach(header => {
                    let value = row[header] || '';
                    // 格式化数值
                    if (header === '次数' && value) {
                        value = parseInt(value).toLocaleString();
                    }
                    tableHtml += '<td>' + value + '</td>';
                });
                tableHtml += '</tr>';
            });
            
            tableHtml += '</tbody></table>';
            
            // 确保清除任何加载状态并显示表格
            dataTableElement.innerHTML = tableHtml;
            console.log('✅ 表格HTML已更新');
            
            // 更新分页控件
            if (pagination) {
                updatePagination(pagination);
                console.log('✅ 分页控件已更新');
            } else {
                paginationElement.innerHTML = '';
                console.log('⚠️ 无分页信息，清空分页控件');
            }
        }
        
        // 导出数据
        async function exportData(format) {
            const startDate = document.getElementById('start-date').value;
            const endDate = document.getElementById('end-date').value;
            const userId = document.getElementById('user-select').value;
            
            try {
                const response = await fetch('/api/export?format=' + format + '&start_date=' + startDate + '&end_date=' + endDate + '&user_id=' + userId);
                
                if (response.ok) {
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = '招聘数据_' + new Date().toISOString().split('T')[0] + '.' + format;
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                } else {
                    showError('导出失败，请稍后重试');
                }
            } catch (error) {
                console.error('导出失败:', error);
                showError('导出失败，请稍后重试');
            }
        }
        
        // 显示错误信息
        function showError(message) {
            // 简单的错误提示，可以后续改进
            alert(message);
        }
        
        // 更新漏斗图
        function updateFunnelChart(chartData) {
            const ctx = document.getElementById('funnel-chart').getContext('2d');
            
            if (funnelChart) {
                funnelChart.destroy();
            }
            
            funnelChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: chartData.labels,
                    datasets: [{
                        data: chartData.data,
                        backgroundColor: chartData.colors,
                        borderColor: chartData.colors,
                        borderWidth: 2
                    }]
                },
                options: {
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        },
                        title: {
                            display: true,
                            text: '招聘漏斗分析',
                            color: '#FFFFFF',
                            font: { size: 18 }
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const value = context.parsed.x;
                                    const rate = chartData.conversion_rates[context.dataIndex];
                                    return '数量: ' + value + ' | 转化率: ' + rate + '%';
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            ticks: { color: '#FFFFFF' },
                            grid: { color: 'rgba(255,255,255,0.1)' }
                        },
                        y: {
                            ticks: { color: '#FFFFFF' },
                            grid: { color: 'rgba(255,255,255,0.1)' }
                        }
                    }
                }
            });
        }
        
        // 更新趋势图
        function updateTrendChart(chartData) {
            const ctx = document.getElementById('trend-chart').getContext('2d');
            
            if (trendChart) {
                trendChart.destroy();
            }
            
            trendChart = new Chart(ctx, {
                type: 'line',
                data: chartData,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            labels: { color: '#FFFFFF' }
                        },
                        title: {
                            display: true,
                            text: '每日活动趋势',
                            color: '#FFFFFF',
                            font: { size: 18 }
                        }
                    },
                    scales: {
                        x: {
                            ticks: { color: '#FFFFFF' },
                            grid: { color: 'rgba(255,255,255,0.1)' }
                        },
                        y: {
                            ticks: { color: '#FFFFFF' },
                            grid: { color: 'rgba(255,255,255,0.1)' }
                        }
                    }
                }
            });
        }
        
        // 搜索功能
        function searchTable() {
            const searchText = document.getElementById('table-search').value;
            tableState.searchText = searchText;
            const loadingText = searchText ? '🔍 搜索数据中...' : '📊 加载数据中...';
            const loadingSubtext = searchText ? '正在搜索包含 "' + searchText + '" 的记录' : '正在获取全部数据';
            updateData(true, loadingText, loadingSubtext); // 重置到第一页
        }
        
        // 清除搜索
        function clearSearch() {
            document.getElementById('table-search').value = '';
            tableState.searchText = '';
            updateData(true, '🔄 重置筛选中...', '正在恢复显示全部数据'); // 重置到第一页
        }
        
        // 改变页面大小
        function changePageSize() {
            const newSize = parseInt(document.getElementById('page-size').value);
            tableState.pageSize = newSize;
            updateData(true, '📄 调整分页中...', '正在切换到每页' + newSize + '条记录'); // 重置到第一页
        }
        
        // 表格排序
        function sortTable(column) {
            let sortDirection;
            if (tableState.sortField === column) {
                // 切换排序方向
                tableState.sortOrder = tableState.sortOrder === 'ASC' ? 'DESC' : 'ASC';
                sortDirection = tableState.sortOrder === 'ASC' ? '升序' : '降序';
            } else {
                // 新列，默认降序
                tableState.sortField = column;
                tableState.sortOrder = 'DESC';
                sortDirection = '降序';
            }
            updateData(false, '↕️ 数据排序中...', '正在按' + column + '进行' + sortDirection + '排序'); // 保持当前页
        }
        
        // 更新分页控件
        function updatePagination(pagination) {
            const { total, page, pageSize, totalPages } = pagination;
            let paginationHtml = '<div class="pagination">';
            
            // 上一页按钮
            const prevDisabled = page <= 1 ? 'disabled' : '';
            paginationHtml += '<button onclick="goToPage(' + (page - 1) + ')" ' + prevDisabled + '>⬅️ 上一页</button>';
            
            // 页码按钮
            const startPage = Math.max(1, page - 2);
            const endPage = Math.min(totalPages, page + 2);
            
            if (startPage > 1) {
                paginationHtml += '<button onclick="goToPage(1)">1</button>';
                if (startPage > 2) {
                    paginationHtml += '<span style="color: #CBD5E1; padding: 0 0.5rem;">...</span>';
                }
            }
            
            for (let i = startPage; i <= endPage; i++) {
                const currentClass = i === page ? 'current-page' : '';
                paginationHtml += '<button class="' + currentClass + '" onclick="goToPage(' + i + ')">' + i + '</button>';
            }
            
            if (endPage < totalPages) {
                if (endPage < totalPages - 1) {
                    paginationHtml += '<span style="color: #CBD5E1; padding: 0 0.5rem;">...</span>';
                }
                paginationHtml += '<button onclick="goToPage(' + totalPages + ')">' + totalPages + '</button>';
            }
            
            // 下一页按钮
            const nextDisabled = page >= totalPages ? 'disabled' : '';
            paginationHtml += '<button onclick="goToPage(' + (page + 1) + ')" ' + nextDisabled + '>下一页 ➡️</button>';
            
            paginationHtml += '</div>';
            
            // 分页信息
            const start = (page - 1) * pageSize + 1;
            const end = Math.min(page * pageSize, total);
            paginationHtml += '<div class="pagination-info">显示第 ' + start + '-' + end + ' 条，共 ' + total + ' 条记录</div>';
            
            document.getElementById('pagination-controls').innerHTML = paginationHtml;
        }
        
        // 跳转到指定页
        function goToPage(page) {
            tableState.page = page;
            updateData(false, '📄 翻页中...', '正在跳转到第' + page + '页');
        }
        
        // 用户筛选功能
        function handleUserChange() {
            const userSelect = document.getElementById('user-select');
            const selectedUser = userSelect.options[userSelect.selectedIndex].text;
            const loadingText = selectedUser.includes('全部') ? '📊 切换到全部用户...' : '👤 筛选用户数据中...';
            const loadingSubtext = selectedUser.includes('全部') ? '正在加载所有用户的数据' : '正在筛选 ' + selectedUser + ' 的数据';
            
            updateData(true, loadingText, loadingSubtext);
        }
        
        // 事件监听器
        document.addEventListener('DOMContentLoaded', function() {
            // 搜索框回车事件
            const searchInput = document.getElementById('table-search');
            if (searchInput) {
                searchInput.addEventListener('keypress', function(e) {
                    if (e.key === 'Enter') {
                        searchTable();
                    }
                });
            }
            
            // 用户选择变更事件
            const userSelect = document.getElementById('user-select');
            if (userSelect) {
                userSelect.addEventListener('change', handleUserChange);
            }
            
            // 日期筛选变更事件  
            const startDateInput = document.getElementById('start-date');
            const endDateInput = document.getElementById('end-date');
            if (startDateInput && endDateInput) {
                startDateInput.addEventListener('change', function() {
                    updateData(true, '📅 更新日期范围...', '正在加载指定时间段的数据');
                });
                endDateInput.addEventListener('change', function() {
                    updateData(true, '📅 更新日期范围...', '正在加载指定时间段的数据');
                });
            }
        });
    </script>
</body>
</html>
'''

# 主页路由
@app.route('/')
def index():
    """主页"""
    # 设置默认日期为最近7天
    today = date.today()
    week_ago = today - timedelta(days=7)
    
    return render_template_string(HTML_TEMPLATE, 
                                start_date=week_ago.strftime('%Y-%m-%d'),
                                end_date=today.strftime('%Y-%m-%d'))

# API路由：健康检查
@app.route('/api/health')
def api_health():
    """健康检查API"""
    try:
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            connection.close()
            return jsonify({
                'status': 'healthy',
                'database': 'connected',
                'test_query': 'success'
            })
        else:
            return jsonify({
                'status': 'error',
                'database': 'connection_failed'
            }), 500
    except Exception as e:
        return jsonify({
            'status': 'error',
            'database': 'exception',
            'error': str(e)
        }), 500

# API路由：调试数据
@app.route('/api/debug')
def api_debug():
    """调试API - 返回简单的测试数据"""
    try:
        # 简单的测试数据
        test_data = [
            {'日期': '2025-06-13', '用户名': '测试用户1', '事件类型': '查看简历', '次数': 10},
            {'日期': '2025-06-12', '用户名': '测试用户2', '事件类型': '简历通过筛选', '次数': 5},
        ]
        
        return jsonify({
            'metrics': {
                'total_views': 100,
                'passed_screening': 50,
                'boss_chats': 20,
                'contact_exchanges': 10,
                'connection_rate': 20.0,
                'chat_rate': 40.0
            },
            'funnel_chart': {
                'labels': ['查看简历', '简历通过筛选', 'Boss上聊天', '交换联系方式'],
                'data': [100, 50, 20, 10],
                'conversion_rates': [100, 50, 40, 50],
                'colors': ['#06D6A0', '#118AB2', '#FFD166', '#EF476F']
            },
            'trend_chart': {
                'labels': ['2025-06-11', '2025-06-12', '2025-06-13'],
                'datasets': []
            },
            'table_data': test_data,
            'pagination': {
                'total': 2,
                'page': 1,
                'page_size': 20,
                'total_pages': 1
            },
            'debug': {
                'message': '这是测试数据',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'message': '调试API也失败了'
        }), 500

# API路由：获取用户列表
@app.route('/api/users')
def api_users():
    """获取用户列表API"""
    try:
        users = get_user_list()
        return jsonify(users)
    except Exception as e:
        print(f"获取用户列表失败: {e}")
        return jsonify([{'label': '全部用户', 'value': 'all'}])

# API路由：获取主要数据
@app.route('/api/data')
def api_data():
    """获取主要数据API"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        user_id = request.args.get('user_id', 'all')
        
        # 获取漏斗数据
        funnel_data = get_funnel_data(start_date, end_date, user_id) or []
        
        # 计算指标
        metrics = calculate_metrics(funnel_data)
        
        # 生成图表
        funnel_chart = create_funnel_chart(funnel_data)
        
        # 获取趋势数据
        trend_data = get_trend_data(start_date, end_date, user_id) or []
        trend_chart = create_trend_chart(trend_data)
        
        # 获取分页参数
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
        sort_field = request.args.get('sort_field', 'create_time')
        sort_order = request.args.get('sort_order', 'DESC')
        search_text = request.args.get('search', '')
        
        # 获取详细数据表
        table_result = get_table_data(start_date, end_date, user_id, page, page_size, sort_field, sort_order, search_text)
        
        return jsonify({
            'metrics': metrics,
            'funnel_chart': funnel_chart,
            'trend_chart': trend_chart,
            'table_data': table_result['data'] if table_result else [],
            'pagination': {
                'total': table_result['total'] if table_result else 0,
                'page': table_result['page'] if table_result else 1,
                'page_size': table_result['page_size'] if table_result else 20,
                'total_pages': table_result['total_pages'] if table_result else 0
            },
            'debug': {
                'start_date': start_date,
                'end_date': end_date,
                'user_id': user_id,
                'funnel_count': len(funnel_data),
                'trend_count': len(trend_data),
                'table_count': len(table_result['data']) if table_result else 0
            }
        })
    except Exception as e:
        print(f"获取数据失败: {e}")
        return jsonify({'error': str(e)}), 500

# API路由：导出数据
@app.route('/api/export')
def api_export():
    """导出数据API"""
    try:
        format_type = request.args.get('format', 'csv')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        user_id = request.args.get('user_id', 'all')
        
        # 获取导出数据
        export_data = get_export_data(start_date, end_date, user_id)
        
        if format_type == 'csv':
            return export_csv(export_data)
        else:
            return jsonify({'error': '不支持的导出格式'}), 400
            
    except Exception as e:
        print(f"导出数据失败: {e}")
        return jsonify({'error': str(e)}), 500

def get_table_data(start_date=None, end_date=None, user_id=None, page=1, page_size=20, sort_field='create_time', sort_order='DESC', search_text=''):
    """获取数据表数据（支持分页、排序、搜索）"""
    where_conditions = []
    
    if start_date and end_date:
        where_conditions.append(f"create_time BETWEEN '{start_date}' AND '{end_date} 23:59:59'")
    
    if user_id and user_id != 'all':
        where_conditions.append(f"uid = '{user_id}'")
    
    # 搜索功能
    if search_text:
        search_conditions = [
            f"uid LIKE '%{search_text}%'",
            f"event_type LIKE '%{search_text}%'",
            f"DATE(create_time) LIKE '%{search_text}%'"
        ]
        where_conditions.append(f"({' OR '.join(search_conditions)})")
    
    where_clause = " AND ".join(where_conditions)
    if where_clause:
        where_clause = f"WHERE {where_clause}"
    
    # 排序映射
    sort_mapping = {
        '日期': 'DATE(create_time)',
        '用户名': 'uid', 
        '事件类型': 'event_type',
        '次数': 'event_count',
        'create_time': 'create_time'
    }
    
    sort_column = sort_mapping.get(sort_field, 'create_time')
    sort_direction = 'ASC' if sort_order.upper() == 'ASC' else 'DESC'
    
    # 计算偏移量
    offset = (page - 1) * page_size
    
    # 获取总数
    count_sql = f"""
    SELECT COUNT(DISTINCT DATE(create_time), uid, event_type) as total
    FROM recruit_event
    {where_clause}
    """
    count_result = query_data(count_sql)
    total_count = count_result[0]['total'] if count_result else 0
    
    # 获取分页数据
    sql = f"""
    SELECT 
        id,
        DATE(create_time) as 日期,
        create_time,
        CONCAT('用户-', LEFT(uid, 8)) as 用户名,
        uid,
        CASE 
            WHEN event_type = 1 THEN '查看简历'
            WHEN event_type = 2 THEN '简历通过筛选'
            WHEN event_type = 12 THEN 'Boss上聊天'
            WHEN event_type = 13 THEN '交换联系方式'
            ELSE CONCAT('事件类型-', event_type)
        END as 事件类型,
        event_type,
        COUNT(*) as 次数
    FROM recruit_event
    {where_clause}
    GROUP BY DATE(create_time), uid, event_type
    ORDER BY {sort_column} {sort_direction}
    LIMIT {page_size} OFFSET {offset}
    """
    
    data = query_data(sql)
    
    return {
        'data': data,
        'total': total_count,
        'page': page,
        'page_size': page_size,
        'total_pages': (total_count + page_size - 1) // page_size
    }

def get_export_data(start_date=None, end_date=None, user_id=None):
    """获取导出数据"""
    where_conditions = []
    
    if start_date and end_date:
        where_conditions.append(f"re.create_time BETWEEN '{start_date}' AND '{end_date} 23:59:59'")
    
    if user_id and user_id != 'all':
        where_conditions.append(f"re.uid = '{user_id}'")
    
    where_clause = " AND ".join(where_conditions)
    if where_clause:
        where_clause = f"WHERE {where_clause}"
    
    sql = f"""
    SELECT 
        re.id as 事件ID,
        re.create_time as 创建时间,
        CASE 
            WHEN u.name IS NOT NULL AND u.name != '' THEN u.name
            ELSE CONCAT('用户-', LEFT(u.id, 8))
        END as 用户名,
        re.uid as 用户ID,
        CASE 
            WHEN re.event_type = 1 THEN '查看简历'
            WHEN re.event_type = 2 THEN '简历通过筛选'
            WHEN re.event_type = 12 THEN 'Boss上聊天'
            WHEN re.event_type = 13 THEN '交换联系方式'
            ELSE CONCAT('事件类型-', re.event_type)
        END as 事件类型,
        re.event_type as 事件类型编码,
        COALESCE(j.name, '未知职位') as 职位名称,
        COALESCE(r.name, '未知简历') as 简历名称
    FROM recruit_event re
    LEFT JOIN user u ON re.uid = u.id
    LEFT JOIN job j ON re.job_id = j.id
    LEFT JOIN resume r ON re.resume_id = r.id
    {where_clause}
    ORDER BY re.create_time DESC
    LIMIT 5000
    """
    
    return query_data(sql)

def export_csv(data):
    """导出CSV格式数据"""
    import io
    
    if not data:
        return Response("暂无数据", mimetype="text/csv")
    
    output = io.StringIO()
    
    # 写入CSV头部
    headers = list(data[0].keys())
    output.write(','.join(headers) + '\n')
    
    # 写入数据行
    for row in data:
        row_data = []
        for header in headers:
            value = row[header]
            if value is None:
                row_data.append('')
            elif isinstance(value, (datetime, date)):
                row_data.append(value.strftime('%Y-%m-%d %H:%M:%S'))
            else:
                # 处理CSV中的特殊字符
                value_str = str(value).replace('"', '""')
                if ',' in value_str or '"' in value_str or '\n' in value_str:
                    value_str = f'"{value_str}"'
                row_data.append(value_str)
        output.write(','.join(row_data) + '\n')
    
    # 创建响应
    response = Response(
        output.getvalue(),
        mimetype="text/csv; charset=utf-8"
    )
    
    # 设置下载文件名
    filename = f"招聘数据_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    
    return response

# Vercel需要的应用实例
application = app

@app.route('/favicon.ico')
def favicon():
    """提供网站图标"""
    # 返回一个简单的SVG作为图标，避免404错误
    return Response(
        (
            b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
            b'<path fill="%2306D6A0" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-1-13h2v6h-2zm0 8h2v2h-2z"/>'
            b'</svg>'
        ),
        mimetype='image/svg+xml'
    )

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=8050) 