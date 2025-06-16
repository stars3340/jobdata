#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能招聘数据分析平台 - 极轻量级版本
保持完整功能，最小化依赖
"""

import os
import json
import re
from datetime import datetime, timedelta, date
from flask import Flask, render_template_string, jsonify, request, Response
import pymysql

# 创建Flask应用
app = Flask(__name__)

# 数据库连接配置 - 使用统一配置管理
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config

DB_CONFIG = Config.DB_CONFIG

import contextlib
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def validate_date(date_str):
    """验证日期格式"""
    if not date_str:
        return None
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return date_str
    except ValueError:
        logger.warning(f"无效的日期格式: {date_str}")
        return None

def validate_user_id(user_id):
    """验证用户ID"""
    if not user_id:
        return 'all'
    # 允许 'all' 或者字母数字组合
    if user_id == 'all' or re.match(r'^[a-zA-Z0-9_-]+$', str(user_id)):
        return str(user_id)
    logger.warning(f"无效的用户ID格式: {user_id}")
    return 'all'

def validate_page_params(page, page_size):
    """验证分页参数"""
    try:
        page = max(1, int(page) if page else 1)
        page_size = min(Config.MAX_PAGE_SIZE, max(1, int(page_size) if page_size else 20))
        return page, page_size
    except (ValueError, TypeError):
        logger.warning(f"无效的分页参数: page={page}, page_size={page_size}")
        return 1, 20

def sanitize_search_text(search_text):
    """清理搜索文本"""
    if not search_text:
        return ''
    # 移除潜在的危险字符，保留中文、英文、数字和常用符号
    cleaned = re.sub(r'[^\w\s\u4e00-\u9fff-]', '', str(search_text))
    return cleaned[:50]  # 限制长度

def get_db_connection():
    """获取数据库连接"""
    try:
        # 添加连接参数优化
        config = DB_CONFIG.copy()
        config.update({
            'connect_timeout': 10,
            'read_timeout': 30,
            'write_timeout': 30,
            'autocommit': True
        })
        return pymysql.connect(**config)
    except Exception as e:
        logger.error(f"数据库连接失败: {e}")
        return None

@contextlib.contextmanager
def get_db_cursor():
    """数据库连接上下文管理器"""
    connection = get_db_connection()
    if connection is None:
        yield None
        return
    
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            yield cursor
    except Exception as e:
        logger.error(f"数据库操作失败: {e}")
        raise
    finally:
        connection.close()

def query_data(sql, params=None):
    """执行SQL查询，返回字典列表（使用上下文管理器）"""
    try:
        with get_db_cursor() as cursor:
            if cursor is None:
                logger.warning("数据库连接失败，返回空结果")
                return []
            
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            result = cursor.fetchall()
            return result
    except Exception as e:
        logger.error(f"数据库查询失败: {e}, SQL: {sql[:100]}..., 参数: {params}")
        return []

def get_funnel_data(start_date=None, end_date=None, user_id=None):
    """获取漏斗数据（使用参数化查询）"""
    where_conditions = []
    params = []
    
    if start_date and end_date:
        where_conditions.append("create_time BETWEEN %s AND %s")
        params.extend([start_date, end_date + ' 23:59:59'])
    
    if user_id and user_id != 'all':
        where_conditions.append("uid = %s")
        params.append(user_id)
    
    where_clause = " AND ".join(where_conditions)
    if where_clause:
        where_clause = f"WHERE {where_clause}"
    
    sql = f"""
    SELECT event_type, COUNT(*) as count
    FROM recruit_event {where_clause}
    GROUP BY event_type
    ORDER BY count DESC
    """
    
    result = query_data(sql, params)
    
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
    """获取趋势数据（使用参数化查询）"""
    where_conditions = []
    params = []
    
    if start_date and end_date:
        where_conditions.append("create_time BETWEEN %s AND %s")
        params.extend([start_date, end_date + ' 23:59:59'])
    
    if user_id and user_id != 'all':
        where_conditions.append("uid = %s")
        params.append(user_id)
    
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
    
    result = query_data(sql, params)
    
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
    
    <!-- Chart.js 依赖 -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js"></script>

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
        
        /* 搜索框样式 */
        .search-input {
            padding: 0.5rem;
            border: 1px solid rgba(6, 214, 160, 0.3);
            border-radius: 6px;
            background: rgba(35, 41, 70, 0.8);
            color: #FFFFFF;
            width: 250px;
        }
        
        .search-input:focus {
            outline: none;
            border-color: #06D6A0;
            box-shadow: 0 0 0 3px rgba(6, 214, 160, 0.1);
        }
        
        .search-button {
            margin-left: 0.5rem;
            padding: 0.5rem 1rem;
        }
        
        .page-size-select {
            padding: 0.5rem;
            border: 1px solid rgba(6, 214, 160, 0.3);
            border-radius: 6px;
            background: rgba(35, 41, 70, 0.8);
            color: #FFFFFF;
            margin-right: 1rem;
        }
        
        .page-size-select:focus {
            outline: none;
            border-color: #06D6A0;
            box-shadow: 0 0 0 3px rgba(6, 214, 160, 0.1);
        }
        
        /* 测试按钮样式 */
        .test-button {
            background: #FFD166;
            margin-left: 10px;
        }
        
        .test-button:hover {
            background: #f7ca4d;
        }
        
        /* 错误消息样式 */
        .error-display {
            text-align: center;
            padding: 2rem;
            background: rgba(239, 71, 111, 0.1);
            border: 1px solid rgba(239, 71, 111, 0.3);
            border-radius: 8px;
            margin: 1rem 0;
        }
        
        .error-icon {
            font-size: 2rem;
            margin-bottom: 1rem;
        }
        
        .error-title {
            color: #EF476F;
            font-size: 1.2rem;
            font-weight: 600;
            margin-bottom: 0.5rem;
        }
        
        .error-subtitle {
            color: #CBD5E1;
            font-size: 0.9rem;
            margin-bottom: 1rem;
        }
        
        .reload-button {
            margin-top: 15px;
            padding: 10px 20px;
            background: #06D6A0;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .reload-button:hover {
            background: #05c093;
            transform: translateY(-2px);
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
            
            .search-input {
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
            <button id="refresh-btn" class="btn">🔄 刷新数据</button>
            <button id="test-data-btn" class="btn test-button">🧪 测试数据</button>
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
                    <button class="quick-filter-btn" data-type="today">今天</button>
                    <button class="quick-filter-btn" data-type="yesterday">昨天</button>
                    <button class="quick-filter-btn active" data-type="7days">最近7天</button>
                    <button class="quick-filter-btn" data-type="30days">最近30天</button>
                    <button class="quick-filter-btn" data-type="month">本月</button>
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
                               class="search-input">
                        <button id="search-btn" class="btn search-button">搜索</button>
                        <button id="clear-search-btn" class="btn btn-outline search-button">清除</button>
                    </div>
                    <div class="export-buttons">
                        <select id="page-size" class="page-size-select">
                            <option value="10">10条/页</option>
                            <option value="20" selected>20条/页</option>
                            <option value="50">50条/页</option>
                            <option value="100">100条/页</option>
                        </select>
                        <button id="export-csv-btn" class="btn btn-outline">📄 导出CSV</button>
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
        let searchDebounceTimer = null;
        
        // 表格状态
        let tableState = {
            page: 1,
            pageSize: 20,
            sortField: 'create_time',
            sortOrder: 'DESC',
            searchText: ''
        };
        
        // 防抖函数
        function debounce(func, wait) {
            return function executedFunction(...args) {
                const later = () => {
                    clearTimeout(searchDebounceTimer);
                    func(...args);
                };
                clearTimeout(searchDebounceTimer);
                searchDebounceTimer = setTimeout(later, wait);
            };
        }
        
        // 防抖搜索函数
        const debouncedSearch = debounce(() => {
            const searchText = document.getElementById('table-search').value;
            console.log('🔍 [SEARCH] 执行搜索:', searchText);
            
            tableState.searchText = searchText;
            const loadingText = searchText ? '🔍 搜索数据中...' : '📊 加载数据中...';
            const loadingSubtext = searchText ? `正在搜索包含 "${searchText}" 的记录` : '正在获取全部数据';
            updateData(true, loadingText, loadingSubtext);
        }, 500);
        
        // 加载用户列表
        async function loadUsers() {
            try {
                console.log('👥 [USERS] 开始加载用户列表');
                const response = await fetch('/api/users');
                const users = await response.json();
                const select = document.getElementById('user-select');
                if (select) {
                    select.innerHTML = '';
                    users.forEach(user => {
                        const option = document.createElement('option');
                        option.value = user.value;
                        option.textContent = user.label;
                        select.appendChild(option);
                    });
                    console.log(`✅ [USERS] 用户列表加载完成，共 ${users.length} 个选项`);
                }
            } catch (error) {
                console.error('❌ [USERS] 加载用户列表失败:', error);
            }
        }
        
        // 设置快速日期
        function setQuickDate(type) {
            console.log('🗓️ 设置快速日期:', type);
            const today = new Date();
            let startDate, endDate;
            
            // 移除所有active类
            document.querySelectorAll('.quick-filter-btn').forEach(btn => 
                btn.classList.remove('active'));
            
            // 添加当前按钮的active类
            const buttonTextMap = {
                'today': '今天',
                'yesterday': '昨天', 
                '7days': '最近7天',
                '30days': '最近30天',
                'month': '本月'
            };
            document.querySelectorAll('.quick-filter-btn').forEach(btn => {
                if (btn.textContent === buttonTextMap[type]) {
                    btn.classList.add('active');
                }
            });
            
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
        
        // 搜索功能（立即搜索）
        function searchTable() {
            console.log('🔍 [SEARCH] 立即搜索按钮点击');
            debouncedSearch();
        }
        
        // 实时搜索（输入时触发）
        function handleSearchInput() {
            console.log('🔍 [SEARCH] 输入变化，启动防抖搜索');
            debouncedSearch();
        }
        
        // 清除搜索
        function clearSearch() {
            console.log('🔍 [SEARCH] 清除搜索');
            const searchInput = document.getElementById('table-search');
            if (searchInput) {
                searchInput.value = '';
                tableState.searchText = '';
                updateData(true, '🔄 重置筛选中...', '正在恢复显示全部数据');
            }
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
        
        // 设置事件监听器
        function setupEventListeners() {
            console.log('⚡ [EVENTS] 开始设置事件监听器');
            
            // 刷新和测试按钮
            document.getElementById('refresh-btn').addEventListener('click', refreshData);
            document.getElementById('test-data-btn').addEventListener('click', testDebugData);

            // 快速筛选按钮
            document.querySelectorAll('.quick-filter-btn').forEach(btn => {
                btn.addEventListener('click', () => setQuickDate(btn.dataset.type));
            });

            // 搜索框事件
            const searchInput = document.getElementById('table-search');
            searchInput.addEventListener('keypress', e => e.key === 'Enter' && searchTable());
            searchInput.addEventListener('input', handleSearchInput);

            // 控制按钮
            document.getElementById('search-btn').addEventListener('click', searchTable);
            document.getElementById('clear-search-btn').addEventListener('click', clearSearch);
            document.getElementById('page-size').addEventListener('change', changePageSize);
            document.getElementById('export-csv-btn').addEventListener('click', () => exportData('csv'));

            // 用户选择
            document.getElementById('user-select').addEventListener('change', handleUserChange);

            // 日期选择
            document.getElementById('start-date').addEventListener('change', () => updateData(true, '📅 更新日期范围...', '正在加载指定时间段的数据'));
            document.getElementById('end-date').addEventListener('change', () => updateData(true, '📅 更新日期范围...', '正在加载指定时间段的数据'));
            
            console.log('✅ [EVENTS] 所有事件监听器已设置');
        }
        
        // 更新漏斗图
        function updateFunnelChart(chartData) {
            console.log('📊 更新漏斗图:', chartData);
            
            if (!chartData || !chartData.labels || !chartData.data) {
                console.warn('漏斗图数据无效');
                return;
            }
            
            const canvas = document.getElementById('funnel-chart');
            if (!canvas) {
                console.error('未找到漏斗图canvas元素');
                return;
            }
            
            try {
                // 销毁现有图表
                if (funnelChart) {
                    funnelChart.destroy();
                }
                
                // 创建新的柱状图（代替漏斗图）
                funnelChart = new Chart(canvas, {
                    type: 'bar',
                    data: {
                        labels: chartData.labels,
                        datasets: [{
                            label: '数量',
                            data: chartData.data,
                            backgroundColor: chartData.colors.map(color => color + '80'),
                            borderColor: chartData.colors,
                            borderWidth: 2,
                            borderRadius: 8
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                display: false
                            },
                            tooltip: {
                                backgroundColor: 'rgba(35, 41, 70, 0.95)',
                                titleColor: '#FFFFFF',
                                bodyColor: '#FFFFFF',
                                borderColor: '#06D6A0',
                                borderWidth: 1,
                                callbacks: {
                                    label: function(context) {
                                        const index = context.dataIndex;
                                        const count = chartData.data[index];
                                        const rate = chartData.conversion_rates[index];
                                        return `数量: ${count} (转化率: ${rate}%)`;
                                    }
                                }
                            }
                        },
                        scales: {
                            y: {
                                beginAtZero: true,
                                grid: {
                                    color: 'rgba(255, 255, 255, 0.1)'
                                },
                                ticks: {
                                    color: '#FFFFFF'
                                }
                            },
                            x: {
                                grid: {
                                    color: 'rgba(255, 255, 255, 0.1)'
                                },
                                ticks: {
                                    color: '#FFFFFF',
                                    maxRotation: 45
                                }
                            }
                        }
                    }
                });
                
                console.log('✅ 漏斗图更新成功');
            } catch (error) {
                console.error('❌ 漏斗图更新失败:', error);
            }
        }
        
        // 更新趋势图
        function updateTrendChart(chartData) {
            console.log('📈 更新趋势图:', chartData);
            
            if (!chartData || !chartData.labels || !chartData.datasets) {
                console.warn('趋势图数据无效');
                return;
            }
            
            const canvas = document.getElementById('trend-chart');
            if (!canvas) {
                console.error('未找到趋势图canvas元素');
                return;
            }
            
            try {
                // 销毁现有图表
                if (trendChart) {
                    trendChart.destroy();
                }
                
                // 创建新的折线图
                trendChart = new Chart(canvas, {
                    type: 'line',
                    data: {
                        labels: chartData.labels,
                        datasets: chartData.datasets.map(dataset => ({
                            ...dataset,
                            fill: false,
                            tension: 0.4,
                            pointBackgroundColor: dataset.borderColor,
                            pointBorderColor: '#FFFFFF',
                            pointBorderWidth: 2,
                            pointRadius: 5,
                            pointHoverRadius: 8
                        }))
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        interaction: {
                            intersect: false,
                            mode: 'index'
                        },
                        plugins: {
                            legend: {
                                labels: {
                                    color: '#FFFFFF',
                                    usePointStyle: true,
                                    padding: 20
                                }
                            },
                            tooltip: {
                                backgroundColor: 'rgba(35, 41, 70, 0.95)',
                                titleColor: '#FFFFFF',
                                bodyColor: '#FFFFFF',
                                borderColor: '#06D6A0',
                                borderWidth: 1
                            }
                        },
                        scales: {
                            y: {
                                beginAtZero: true,
                                grid: {
                                    color: 'rgba(255, 255, 255, 0.1)'
                                },
                                ticks: {
                                    color: '#FFFFFF'
                                }
                            },
                            x: {
                                grid: {
                                    color: 'rgba(255, 255, 255, 0.1)'
                                },
                                ticks: {
                                    color: '#FFFFFF',
                                    maxRotation: 45
                                }
                            }
                        }
                    }
                });
                
                console.log('✅ 趋势图更新成功');
            } catch (error) {
                console.error('❌ 趋势图更新失败:', error);
            }
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
        
        // 显示错误信息
        function showError(message) {
            console.error('🚨 错误:', message);
            
            // 创建错误消息元素
            const errorDiv = document.createElement('div');
            errorDiv.className = 'error-display';
            errorDiv.innerHTML = `
                <div class="error-icon">⚠️</div>
                <div class="error-title">操作失败</div>
                <div class="error-subtitle">${message}</div>
                <button class="reload-button" onclick="this.parentElement.remove()">关闭</button>
            `;
            
            // 添加到页面顶部
            const container = document.querySelector('.container');
            if (container) {
                container.insertBefore(errorDiv, container.firstChild);
                
                // 5秒后自动移除
                setTimeout(() => {
                    if (errorDiv.parentElement) {
                        errorDiv.remove();
                    }
                }, 5000);
            } else {
                // 降级到alert
                alert(message);
            }
        }

        // 页面初始化 - 统一初始化入口
        async function initializePage() {
            console.log('🚀 页面初始化开始...');
            
            try {
                // 检查关键元素是否存在
                const requiredElements = {
                    'data-table': '数据表',
                    'table-loading-overlay': '加载遮罩',
                    'data-table-wrapper': '表格包装器',
                    'user-select': '用户选择',
                    'start-date': '开始日期',
                    'end-date': '结束日期',
                    'metrics': '指标区域'
                };
                
                const missingElements = [];
                for (const [id, name] of Object.entries(requiredElements)) {
                    if (!document.getElementById(id)) {
                        missingElements.push(name);
                    }
                }
                
                if (missingElements.length > 0) {
                    throw new Error(`缺少必要元素: ${missingElements.join(', ')}`);
                }
                
                // 1. 加载用户列表
                console.log('👥 加载用户列表...');
                await loadUsers();
                
                // 2. 设置事件监听器
                console.log('🎧 设置事件监听器...');
                setupEventListeners();
                setupAutoRefresh();
                
                // 3. 初始化表格状态
                console.log('📊 初始化表格状态...');
                tableState.page = 1;
                tableState.pageSize = 20;
                tableState.sortField = 'create_time';
                tableState.sortOrder = 'DESC';
                tableState.searchText = '';
                
                // 4. 加载初始数据
                console.log('📈 开始加载数据...');
                await updateData(true, '🎯 正在加载数据...', '首次加载，请稍候');
                
                console.log('🎉 页面初始化完成！');
                
            } catch (error) {
                console.error('❌ 页面初始化失败:', error);
                showInitializationError(error.message);
            }
        }
        
        // 显示初始化错误
        function showInitializationError(message) {
            const dataTableElement = document.getElementById('data-table');
            if (dataTableElement) {
                dataTableElement.innerHTML = 
                    '<div class="table-loading">' +
                        '<div class="error-icon">⚠️</div>' +
                        '<div class="table-loading-text">初始化失败</div>' +
                        '<div class="table-loading-subtext">' + message + '</div>' +
                        '<button onclick="location.reload()" class="reload-button">🔄 刷新页面</button>' +
                    '</div>';
            }
            hideTableLoading();
        }
        
        // 内存清理函数
        function cleanup() {
            console.log('🧹 [CLEANUP] 清理资源');
            
            // 清理定时器
            if (autoRefreshTimer) {
                clearInterval(autoRefreshTimer);
                autoRefreshTimer = null;
                console.log('✅ [CLEANUP] 自动刷新定时器已清理');
            }
            
            if (searchDebounceTimer) {
                clearTimeout(searchDebounceTimer);
                searchDebounceTimer = null;
                console.log('✅ [CLEANUP] 搜索防抖定时器已清理');
            }
            
            // 清理图表
            if (funnelChart) {
                funnelChart.destroy();
                funnelChart = null;
                console.log('✅ [CLEANUP] 漏斗图已清理');
            }
            
            if (trendChart) {
                trendChart.destroy();
                trendChart = null;
                console.log('✅ [CLEANUP] 趋势图已清理');
            }
        }
        
        // 页面卸载时清理资源
        window.addEventListener('beforeunload', cleanup);
        
        // DOM加载完成时统一初始化
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initializePage);
        } else {
            // DOM已经加载完成，直接初始化  
            initializePage();
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

# API路由：健康检查
@app.route('/api/health')
def api_health():
    """健康检查API"""
    try:
        with get_db_cursor() as cursor:
            if cursor is None:
                return jsonify({
                    'status': 'error',
                    'database': 'connection_failed'
                }), 500
            
            cursor.execute("SELECT 1 as test")
            result = cursor.fetchone()
            return jsonify({
                'status': 'healthy',
                'database': 'connected',
                'test_query': 'success',
                'result': result
            })
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return jsonify({
            'status': 'error',
            'database': 'exception',
            'error': str(e)
        }), 500

# API路由：调试数据
@app.route('/api/debug')
def api_debug():
    """调试API - 返回数据库连接和配置信息"""
    debug_info = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'config': {
            'db_host': DB_CONFIG.get('host', 'NOT_SET'),
            'db_port': DB_CONFIG.get('port', 'NOT_SET'),
            'db_user': DB_CONFIG.get('user', 'NOT_SET'),
            'db_name': DB_CONFIG.get('database', 'NOT_SET'),
            'db_charset': DB_CONFIG.get('charset', 'NOT_SET'),
            'db_password_set': 'YES' if DB_CONFIG.get('password') else 'NO'
        },
        'environment_variables': {
            'DB_HOST': 'SET' if os.getenv('DB_HOST') else 'NOT_SET',
            'DB_PORT': 'SET' if os.getenv('DB_PORT') else 'NOT_SET',
            'DB_USER': 'SET' if os.getenv('DB_USER') else 'NOT_SET',
            'DB_PASSWORD': 'SET' if os.getenv('DB_PASSWORD') else 'NOT_SET',
            'DB_NAME': 'SET' if os.getenv('DB_NAME') else 'NOT_SET'
        }
    }
    
    # 测试数据库连接
    try:
        with get_db_cursor() as cursor:
            if cursor is None:
                debug_info['database'] = {
                    'status': 'CONNECTION_FAILED',
                    'error': 'get_db_connection() returned None'
                }
            else:
                cursor.execute("SELECT VERSION() as version")
                version = cursor.fetchone()
                cursor.execute("SELECT COUNT(*) as count FROM recruit_event")
                count_result = cursor.fetchone()
                
                debug_info['database'] = {
                    'status': 'CONNECTED',
                    'version': version['version'] if version else 'UNKNOWN',
                    'recruit_event_count': count_result['count'] if count_result else 0
                }
    except Exception as e:
        logger.error(f"调试API数据库测试失败: {e}")
        debug_info['database'] = {
            'status': 'ERROR',
            'error': str(e)
        }
    
    # 返回简单测试数据以确保API正常工作
    debug_info['test_data'] = [
        {'日期': '2025-06-13', '用户名': '测试用户1', '事件类型': '查看简历', '次数': 10},
        {'日期': '2025-06-12', '用户名': '测试用户2', '事件类型': '简历通过筛选', '次数': 5},
    ]
    
    debug_info['metrics'] = {
        'total_views': 100,
        'passed_screening': 50,
        'boss_chats': 20,
        'contact_exchanges': 10,
        'connection_rate': 20.0,
        'chat_rate': 40.0
    }
    
    debug_info['funnel_chart'] = {
        'labels': ['查看简历', '简历通过筛选', 'Boss上聊天', '交换联系方式'],
        'data': [100, 50, 20, 10],
        'conversion_rates': [100, 50, 40, 50],
        'colors': ['#06D6A0', '#118AB2', '#FFD166', '#EF476F']
    }
    
    debug_info['trend_chart'] = {
        'labels': ['2025-06-11', '2025-06-12', '2025-06-13'],
        'datasets': [
            {
                'label': '查看简历',
                'data': [30, 40, 30],
                'borderColor': '#06D6A0',
                'backgroundColor': '#06D6A020'
            }
        ]
    }
    
    return jsonify(debug_info)

# API路由：获取用户列表
@app.route('/api/users')
def api_users():
    """获取用户列表API"""
    try:
        users = get_user_list()
        if not users or len(users) <= 1:  # 只有"全部用户"选项时返回测试数据
            logger.warning("数据库中无用户数据，返回测试用户列表")
            return jsonify([
                {'label': '全部用户', 'value': 'all'},
                {'label': '用户-demo001 (4条)', 'value': 'demo001'},
                {'label': '用户-demo002 (3条)', 'value': 'demo002'},
                {'label': '用户-demo003 (3条)', 'value': 'demo003'}
            ])
        
        return jsonify(users)
    except Exception as e:
        logger.error(f"获取用户列表失败: {e}")
        return jsonify([
            {'label': '全部用户', 'value': 'all'},
            {'label': '用户-demo001 (4条)', 'value': 'demo001'},
            {'label': '用户-demo002 (3条)', 'value': 'demo002'},
            {'label': '用户-demo003 (3条)', 'value': 'demo003'}
        ])

# API路由：获取主要数据
@app.route('/api/data')
def api_data():
    """获取主要数据API"""
    
    # 验证和清理输入参数
    start_date = validate_date(request.args.get('start_date'))
    end_date = validate_date(request.args.get('end_date'))
    user_id = validate_user_id(request.args.get('user_id', 'all'))
    
    # 获取分页参数
    page, page_size = validate_page_params(
        request.args.get('page', 1),
        request.args.get('page_size', 20)
    )
    
    # 排序参数验证
    allowed_sort_fields = ['create_time', '日期', '用户名', '事件类型', '次数']
    sort_field = request.args.get('sort_field', 'create_time')
    if sort_field not in allowed_sort_fields:
        sort_field = 'create_time'
    
    sort_order = request.args.get('sort_order', 'DESC')
    if sort_order.upper() not in ['ASC', 'DESC']:
        sort_order = 'DESC'
    
    # 搜索文本清理
    search_text = sanitize_search_text(request.args.get('search', ''))
    
    logger.info(f"API数据请求 - 日期: {start_date} 到 {end_date}, 用户: {user_id}, 页面: {page}/{page_size}")
    
    try:
        # 获取漏斗数据
        funnel_data = get_funnel_data(start_date, end_date, user_id) or []
        
        # 计算指标
        metrics = calculate_metrics(funnel_data)
        
        # 生成图表
        funnel_chart = create_funnel_chart(funnel_data)
        
        # 获取趋势数据
        trend_data = get_trend_data(start_date, end_date, user_id) or []
        trend_chart = create_trend_chart(trend_data)
        
        # 获取详细数据表
        table_result = get_table_data(start_date, end_date, user_id, page, page_size, sort_field, sort_order, search_text)
        
        # 如果没有数据，返回测试数据
        if not table_result or not table_result.get('data'):
            logger.info("数据库中没有数据，返回测试数据")
            return return_test_data(start_date, end_date, user_id)
        
        return jsonify({
            'metrics': metrics,
            'funnel_chart': funnel_chart,
            'trend_chart': trend_chart,
            'table_data': table_result['data'],
            'pagination': {
                'total': table_result['total'],
                'page': table_result['page'],
                'page_size': table_result['page_size'],
                'total_pages': table_result['total_pages']
            },
            'debug': {
                'data_source': 'database',
                'start_date': start_date,
                'end_date': end_date,
                'user_id': user_id,
                'funnel_count': len(funnel_data),
                'trend_count': len(trend_data),
                'table_count': len(table_result['data'])
            }
        })
    except Exception as e:
        logger.error(f"API数据处理失败: {e}")
        return return_test_data(start_date, end_date, user_id)

def return_test_data(start_date=None, end_date=None, user_id=None):
    """返回测试数据"""
    test_table_data = [
        {'日期': '2025-06-13', '用户名': '用户-demo001', '事件类型': '查看简历', '次数': 15},
        {'日期': '2025-06-13', '用户名': '用户-demo001', '事件类型': '简历通过筛选', '次数': 8},
        {'日期': '2025-06-13', '用户名': '用户-demo001', '事件类型': 'Boss上聊天', '次数': 3},
        {'日期': '2025-06-13', '用户名': '用户-demo001', '事件类型': '交换联系方式', '次数': 1},
        {'日期': '2025-06-12', '用户名': '用户-demo002', '事件类型': '查看简历', '次数': 12},
        {'日期': '2025-06-12', '用户名': '用户-demo002', '事件类型': '简历通过筛选', '次数': 6},
        {'日期': '2025-06-12', '用户名': '用户-demo002', '事件类型': 'Boss上聊天', '次数': 2},
        {'日期': '2025-06-11', '用户名': '用户-demo003', '事件类型': '查看简历', '次数': 20},
        {'日期': '2025-06-11', '用户名': '用户-demo003', '事件类型': '简历通过筛选', '次数': 10},
        {'日期': '2025-06-11', '用户名': '用户-demo003', '事件类型': 'Boss上聊天', '次数': 4}
    ]
    
    return jsonify({
        'metrics': {
            'total_views': 47,
            'passed_screening': 24,
            'boss_chats': 9,
            'contact_exchanges': 1,
            'connection_rate': 4.2,
            'chat_rate': 37.5
        },
        'funnel_chart': {
            'labels': ['查看简历', '简历通过筛选', 'Boss上聊天', '交换联系方式'],
            'data': [47, 24, 9, 1],
            'conversion_rates': [100, 51.1, 37.5, 11.1],
            'colors': ['#06D6A0', '#118AB2', '#FFD166', '#EF476F']
        },
        'trend_chart': {
            'labels': ['2025-06-11', '2025-06-12', '2025-06-13'],
            'datasets': [
                {
                    'label': '查看简历',
                    'data': [20, 12, 15],
                    'borderColor': '#06D6A0',
                    'backgroundColor': '#06D6A020',
                    'tension': 0.4
                },
                {
                    'label': '简历通过筛选',
                    'data': [10, 6, 8],
                    'borderColor': '#118AB2',
                    'backgroundColor': '#118AB220',
                    'tension': 0.4
                },
                {
                    'label': 'Boss上聊天',
                    'data': [4, 2, 3],
                    'borderColor': '#FFD166',
                    'backgroundColor': '#FFD16620',
                    'tension': 0.4
                },
                {
                    'label': '交换联系方式',
                    'data': [0, 0, 1],
                    'borderColor': '#EF476F',
                    'backgroundColor': '#EF476F20',
                    'tension': 0.4
                }
            ]
        },
        'table_data': test_table_data,
        'pagination': {
            'total': len(test_table_data),
            'page': 1,
            'page_size': 20,
            'total_pages': 1
        },
        'debug': {
            'data_source': 'test_data',
            'message': '数据库连接失败，显示测试数据',
            'start_date': start_date,
            'end_date': end_date,
            'user_id': user_id,
            'note': '请检查Vercel环境变量配置'
        }
    })

# API路由：导出数据
@app.route('/api/export')
def api_export():
    """导出数据API"""
    try:
        # 验证导出格式
        format_type = request.args.get('format', 'csv').lower()
        if format_type not in ['csv', 'excel']:
            return jsonify({'error': '不支持的导出格式，仅支持csv和excel'}), 400
        
        # 验证输入参数
        start_date = validate_date(request.args.get('start_date'))
        end_date = validate_date(request.args.get('end_date'))
        user_id = validate_user_id(request.args.get('user_id', 'all'))
        
        logger.info(f"导出数据请求 - 格式: {format_type}, 日期: {start_date} 到 {end_date}, 用户: {user_id}")
        
        # 获取导出数据
        export_data = get_export_data(start_date, end_date, user_id)
        
        if not export_data:
            logger.warning("导出数据为空")
            return jsonify({'error': '没有可导出的数据'}), 404
        
        if format_type == 'csv':
            return export_csv(export_data)
        else:  # excel格式暂时返回CSV
            return export_csv(export_data)
            
    except Exception as e:
        logger.error(f"导出数据失败: {e}")
        return jsonify({'error': '导出失败，请稍后重试'}), 500

def get_table_data(start_date=None, end_date=None, user_id=None, page=1, page_size=20, sort_field='create_time', sort_order='DESC', search_text=''):
    """获取数据表数据（支持分页、排序、搜索 - 使用参数化查询）"""
    where_conditions = []
    params = []
    
    if start_date and end_date:
        where_conditions.append("create_time BETWEEN %s AND %s")
        params.extend([start_date, end_date + ' 23:59:59'])
    
    if user_id and user_id != 'all':
        where_conditions.append("uid = %s")
        params.append(user_id)
    
    # 搜索功能 - 使用参数化查询
    if search_text:
        search_pattern = f"%{search_text}%"
        search_conditions = [
            "uid LIKE %s",
            "event_type LIKE %s",
            "DATE(create_time) LIKE %s"
        ]
        where_conditions.append(f"({' OR '.join(search_conditions)})")
        params.extend([search_pattern, search_pattern, search_pattern])
    
    where_clause = " AND ".join(where_conditions)
    if where_clause:
        where_clause = f"WHERE {where_clause}"
    
    # 排序映射 - 防止SQL注入
    sort_mapping = {
        '日期': 'DATE(create_time)',
        '用户名': 'uid', 
        '事件类型': 'event_type',
        '次数': 'event_count',
        'create_time': 'create_time'
    }
    
    sort_column = sort_mapping.get(sort_field, 'create_time')
    sort_direction = 'ASC' if sort_order.upper() == 'ASC' else 'DESC'
    
    # 验证分页参数
    page = max(1, int(page))
    page_size = min(100, max(1, int(page_size)))  # 限制最大页面大小
    offset = (page - 1) * page_size
    
    # 获取总数
    count_sql = f"""
    SELECT COUNT(DISTINCT DATE(create_time), uid, event_type) as total
    FROM recruit_event
    {where_clause}
    """
    count_result = query_data(count_sql, params)
    total_count = count_result[0]['total'] if count_result else 0
    
    # 获取分页数据 - 使用参数化查询
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
    LIMIT %s OFFSET %s
    """
    
    # 添加分页参数
    data_params = params + [page_size, offset]
    data = query_data(sql, data_params)
    
    return {
        'data': data,
        'total': total_count,
        'page': page,
        'page_size': page_size,
        'total_pages': (total_count + page_size - 1) // page_size
    }

def get_export_data(start_date=None, end_date=None, user_id=None):
    """获取导出数据（使用参数化查询）"""
    where_conditions = []
    params = []
    
    if start_date and end_date:
        where_conditions.append("re.create_time BETWEEN %s AND %s")
        params.extend([start_date, end_date + ' 23:59:59'])
    
    if user_id and user_id != 'all':
        where_conditions.append("re.uid = %s")
        params.append(user_id)
    
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
    LIMIT %s
    """
    
    # 使用配置中的最大导出记录数
    params.append(Config.MAX_EXPORT_RECORDS)
    return query_data(sql, params)

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

@app.route('/.well-known/appspecific/com.chrome.devtools.json')
def chrome_devtools_config():
    """Chrome开发者工具配置文件 - 避免404错误"""
    return jsonify({
        "name": "智能招聘数据分析平台",
        "description": "Chrome DevTools配置",
        "version": "1.0.0"
    })

@app.route('/test')
def test_page():
    """测试页面 - 用于验证数据加载修复"""
    try:
        with open('test_page.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return '''
        <h1>测试页面未找到</h1>
        <p>请确保 test_page.html 文件存在</p>
        <a href="/">返回主页</a>
        ''', 404

if __name__ == "__main__":
    # 启动前验证配置
    config_issues = Config.validate_config()
    if config_issues:
        logger.warning("配置问题:")
        for issue in config_issues:
            logger.warning(f"  - {issue}")
    
    logger.info("启动智能招聘数据分析平台...")
    logger.info(f"服务地址: http://0.0.0.0:8080")
    logger.info(f"调试模式: {Config.APP_DEBUG}")
    
    app.run(debug=Config.APP_DEBUG, host='0.0.0.0', port=8080) 