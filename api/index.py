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
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }
        
        .table-header h3 {
            color: #FFFFFF;
            font-size: 1.3rem;
            font-weight: 600;
        }
        
        .export-buttons {
            display: flex;
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
        }
        
        .data-table tr:hover {
            background: rgba(6, 214, 160, 0.05);
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
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
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
            
            .export-buttons {
                flex-direction: column;
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
                <div class="export-buttons">
                    <button class="btn btn-outline" onclick="exportData('csv')">📄 导出CSV</button>
                </div>
            </div>
            <div id="data-table">
                <div class="loading">
                    <div class="loading-spinner"></div>
                    数据加载中...
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let autoRefreshTimer = null;
        let funnelChart = null;
        let trendChart = null;
        
        // 页面加载完成后初始化
        document.addEventListener('DOMContentLoaded', function() {
            loadUsers();
            updateData();
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
            updateData();
        }
        
        // 手动刷新数据
        function refreshData() {
            updateData();
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
                    autoRefreshTimer = setInterval(updateData, interval * 1000);
                }
            });
        }
        
        // 更新所有数据
        async function updateData() {
            const startDate = document.getElementById('start-date').value;
            const endDate = document.getElementById('end-date').value;
            const userId = document.getElementById('user-select').value;
            
            try {
                // 更新最后刷新时间
                document.getElementById('last-update').textContent = 
                    '最后更新: ' + new Date().toLocaleString();
                
                // 获取数据
                const response = await fetch('/api/data?start_date=' + startDate + '&end_date=' + endDate + '&user_id=' + userId);
                const data = await response.json();
                
                // 更新KPI指标
                updateMetrics(data.metrics);
                
                // 更新图表
                if (data.funnel_chart && data.funnel_chart.labels) {
                    updateFunnelChart(data.funnel_chart);
                }
                
                if (data.trend_chart && data.trend_chart.labels) {
                    updateTrendChart(data.trend_chart);
                }
                
                // 更新数据表
                updateDataTable(data.table_data);
                
            } catch (error) {
                console.error('更新数据失败:', error);
                showError('数据加载失败，请稍后重试');
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
        function updateDataTable(tableData) {
            if (!tableData || tableData.length === 0) {
                document.getElementById('data-table').innerHTML = 
                    '<div class="loading">暂无数据</div>';
                return;
            }
            
            // 生成表格HTML
            const headers = Object.keys(tableData[0]);
            let tableHtml = '<table class="data-table"><thead><tr>';
            
            headers.forEach(header => {
                tableHtml += '<th>' + header + '</th>';
            });
            tableHtml += '</tr></thead><tbody>';
            
            // 只显示前100条数据以提高性能
            const displayData = tableData.slice(0, 100);
            displayData.forEach(row => {
                tableHtml += '<tr>';
                headers.forEach(header => {
                    tableHtml += '<td>' + (row[header] || '') + '</td>';
                });
                tableHtml += '</tr>';
            });
            
            tableHtml += '</tbody></table>';
            
            if (tableData.length > 100) {
                tableHtml += '<p style="text-align: center; margin-top: 1rem; color: #CBD5E1;">' +
                    '显示前100条数据，共' + tableData.length + '条记录' +
                '</p>';
            }
            
            document.getElementById('data-table').innerHTML = tableHtml;
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
        funnel_data = get_funnel_data(start_date, end_date, user_id)
        
        # 计算指标
        metrics = calculate_metrics(funnel_data)
        
        # 生成图表
        funnel_chart = create_funnel_chart(funnel_data)
        
        # 获取趋势数据
        trend_data = get_trend_data(start_date, end_date, user_id)
        trend_chart = create_trend_chart(trend_data)
        
        # 获取详细数据表
        table_data = get_table_data(start_date, end_date, user_id)
        
        return jsonify({
            'metrics': metrics,
            'funnel_chart': funnel_chart,
            'trend_chart': trend_chart,
            'table_data': table_data
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

def get_table_data(start_date=None, end_date=None, user_id=None):
    """获取数据表数据"""
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
        DATE(re.create_time) as 日期,
        CASE 
            WHEN u.name IS NOT NULL AND u.name != '' THEN u.name
            ELSE CONCAT('用户-', LEFT(u.id, 8))
        END as 用户名,
        CASE 
            WHEN re.event_type = 1 THEN '查看简历'
            WHEN re.event_type = 2 THEN '简历通过筛选'
            WHEN re.event_type = 12 THEN 'Boss上聊天'
            WHEN re.event_type = 13 THEN '交换联系方式'
            ELSE CONCAT('事件类型-', re.event_type)
        END as 事件类型,
        COUNT(*) as 次数
    FROM recruit_event re
    LEFT JOIN user u ON re.uid = u.id
    {where_clause}
    GROUP BY DATE(re.create_time), re.uid, re.event_type, u.name
    ORDER BY re.create_time DESC
    LIMIT 500
    """
    
    return query_data(sql)

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

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=8050) 