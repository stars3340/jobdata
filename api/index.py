#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能招聘数据分析平台 - 超轻量级Vercel版本
"""

import os
import json
from datetime import datetime, timedelta, date
from flask import Flask, render_template_string, jsonify, request
import pymysql
import plotly.graph_objects as go
import plotly.utils

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
    """执行SQL查询"""
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
    """获取漏斗数据"""
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
    
    return sorted(funnel_data, key=lambda x: x['order'])

def create_funnel_chart(funnel_data):
    """创建漏斗图"""
    if not funnel_data:
        return {}
    
    stages = [item['stage'] for item in funnel_data]
    counts = [item['count'] for item in funnel_data]
    
    fig = go.Figure(go.Funnel(
        y=stages,
        x=counts,
        textinfo="value+percent initial",
        marker=dict(color=['#06D6A0', '#118AB2', '#FFD166', '#EF476F'])
    ))
    
    fig.update_layout(
        title="招聘漏斗分析",
        font=dict(color='white'),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    return json.loads(plotly.utils.PlotlyJSONEncoder().encode(fig))

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>智能招聘数据分析平台</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            background: linear-gradient(135deg, #0A0E1A 0%, #1a1f3a 100%);
            color: white; margin: 0; padding: 0; 
        }
        .header { 
            background: rgba(35, 41, 70, 0.9); 
            padding: 1rem 2rem; 
            border-bottom: 1px solid #06D6A0; 
        }
        .header h1 { color: #06D6A0; margin: 0; }
        .container { max-width: 1200px; margin: 2rem auto; padding: 0 1rem; }
        .controls { 
            background: rgba(35, 41, 70, 0.6); 
            padding: 1rem; border-radius: 8px; 
            margin-bottom: 2rem; 
        }
        .control-group { 
            display: inline-block; 
            margin-right: 1rem; margin-bottom: 0.5rem; 
        }
        .control-group label { 
            display: block; margin-bottom: 0.5rem; 
            color: #CBD5E1; 
        }
        .control-group input, .control-group select, .control-group button {
            padding: 0.5rem; border: 1px solid #06D6A0;
            border-radius: 4px; background: rgba(35, 41, 70, 0.8);
            color: white;
        }
        .btn {
            background: linear-gradient(135deg, #06D6A0 0%, #118AB2 100%);
            border: none; padding: 0.75rem 1.5rem;
            border-radius: 4px; color: white; cursor: pointer;
        }
        .btn:hover { transform: translateY(-2px); }
        .chart-container {
            background: rgba(35, 41, 70, 0.6);
            border-radius: 8px; padding: 1rem; margin-bottom: 2rem;
        }
        .metrics {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem; margin-bottom: 2rem;
        }
        .metric-card {
            background: rgba(35, 41, 70, 0.6); padding: 1rem;
            border-radius: 8px; text-align: center;
        }
        .metric-value { font-size: 2rem; font-weight: bold; color: #06D6A0; }
        .metric-label { color: #CBD5E1; margin-top: 0.5rem; }
        .loading { text-align: center; padding: 2rem; color: #CBD5E1; }
    </style>
</head>
<body>
    <header class="header">
        <h1>🚀 智能招聘数据分析平台</h1>
        <p>实时监控 · 数据驱动 · 智能决策</p>
    </header>
    
    <div class="container">
        <div class="controls">
            <div class="control-group">
                <label>开始日期:</label>
                <input type="date" id="start-date" value="{{ start_date }}">
            </div>
            <div class="control-group">
                <label>结束日期:</label>
                <input type="date" id="end-date" value="{{ end_date }}">
            </div>
            <div class="control-group">
                <label>用户:</label>
                <select id="user-select">
                    <option value="all">全部用户</option>
                </select>
            </div>
            <div class="control-group">
                <button class="btn" onclick="updateData()">🔄 更新数据</button>
            </div>
        </div>
        
        <div class="metrics" id="metrics">
            <div class="loading">数据加载中...</div>
        </div>
        
        <div class="chart-container">
            <div id="funnel-chart" style="height: 500px;">
                <div class="loading">图表加载中...</div>
            </div>
        </div>
    </div>
    
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            loadUsers();
            updateData();
        });
        
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
        
        async function updateData() {
            const startDate = document.getElementById('start-date').value;
            const endDate = document.getElementById('end-date').value;
            const userId = document.getElementById('user-select').value;
            
            try {
                const response = await fetch(`/api/funnel?start_date=${startDate}&end_date=${endDate}&user_id=${userId}`);
                const data = await response.json();
                
                updateMetrics(data.metrics);
                
                if (data.chart) {
                    Plotly.newPlot('funnel-chart', data.chart.data, data.chart.layout);
                }
            } catch (error) {
                console.error('更新数据失败:', error);
                document.getElementById('metrics').innerHTML = '<div class="loading">数据加载失败</div>';
                document.getElementById('funnel-chart').innerHTML = '<div class="loading">图表加载失败</div>';
            }
        }
        
        function updateMetrics(metrics) {
            const metricsHtml = `
                <div class="metric-card">
                    <div class="metric-value">${metrics.total_views}</div>
                    <div class="metric-label">查看简历</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">${metrics.passed_screening}</div>
                    <div class="metric-label">通过筛选</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">${metrics.boss_chats}</div>
                    <div class="metric-label">Boss聊天</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">${metrics.contact_exchanges}</div>
                    <div class="metric-label">交换联系方式</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">${metrics.connection_rate.toFixed(1)}%</div>
                    <div class="metric-label">联系转化率</div>
                </div>
            `;
            document.getElementById('metrics').innerHTML = metricsHtml;
        }
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    """主页"""
    today = date.today()
    start_date = (today - timedelta(days=7)).strftime('%Y-%m-%d')
    end_date = today.strftime('%Y-%m-%d')
    return render_template_string(HTML_TEMPLATE, start_date=start_date, end_date=end_date)

@app.route('/api/users')
def api_users():
    """获取用户列表"""
    sql = """
    SELECT u.id,
           CASE WHEN u.name IS NOT NULL AND u.name != '' 
                THEN u.name
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
    
    return jsonify(users)

@app.route('/api/funnel')
def api_funnel():
    """获取漏斗数据"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    user_id = request.args.get('user_id')
    
    funnel_data = get_funnel_data(start_date, end_date, user_id)
    
    # 计算指标
    metrics = {
        'total_views': 0,
        'passed_screening': 0,
        'boss_chats': 0,
        'contact_exchanges': 0,
        'connection_rate': 0
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
    
    if metrics['passed_screening'] > 0:
        metrics['connection_rate'] = (metrics['contact_exchanges'] / metrics['passed_screening']) * 100
    
    chart = create_funnel_chart(funnel_data)
    
    return jsonify({
        'metrics': metrics,
        'chart': chart,
        'data': funnel_data
    })

@app.route('/health')
def health():
    """健康检查"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

# Vercel需要的应用实例
application = app

if __name__ == "__main__":
    app.run(debug=True) 