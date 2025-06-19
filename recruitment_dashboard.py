import dash
from dash import dcc, html, Input, Output, State, callback_context, dash_table
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import pymysql
from datetime import datetime, timedelta, date
import warnings
import time
import io

# 过滤警告
warnings.filterwarnings('ignore')

# 数据库连接配置 - 使用统一配置管理
import os
from config import Config

DB_CONFIG = Config.DB_CONFIG

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
        print(f"数据库连接失败: {e}")
        return None

def query_data(sql):
    """执行SQL查询并返回DataFrame"""
    connection = get_db_connection()
    if connection:
        try:
            df = pd.read_sql(sql, connection)
            return df
        except Exception as e:
            print(f"查询执行失败: {e}")
            return pd.DataFrame()
        finally:
            connection.close()
    return pd.DataFrame()

# 创建Dash应用
app = dash.Dash(__name__, external_stylesheets=['assets/style.css'])
app.title = "智能招聘数据分析平台"

# 定义颜色主题
colors = {
    'primary': '#06D6A0',
    'secondary': '#118AB2',
    'success': '#06D6A0',
    'warning': '#FFD166',
    'danger': '#EF476F',
    'background': '#0A0E1A',
    'text': '#FFFFFF'
}

def create_loading_component():
    """创建加载组件"""
    return html.Div([
        html.Div(className="loading-spinner"),
        html.Span("数据加载中...", style={'marginLeft': '10px', 'color': colors['text']})
    ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'padding': '20px'})

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
    SELECT 
        event_type,
        COUNT(*) as count
    FROM recruit_event 
    {where_clause}
    GROUP BY event_type
    ORDER BY count DESC
    """
    
    df = query_data(sql)
    
    # 事件类型映射（数字到中文）- 根据Prisma schema修正
    event_type_mapping = {
        '1': '浏览简历',        # VIEW_RESUME
        '2': '打招呼',         # SCREEN_PASS  
        '12': '相互沟通',       # BOSS_CHAT
        '13': '建联量'          # PHONE_NUMBER
    }
    
    # 重新定义漏斗顺序
    funnel_mapping = {
        '浏览简历': ('浏览简历', 1),
        '打招呼': ('打招呼', 2), 
        '相互沟通': ('相互沟通', 3),
        '建联量': ('建联量', 4)
    }
    
    funnel_data = []
    for event_num, event_name in event_type_mapping.items():
        count = df[df['event_type'] == event_num]['count'].sum() if not df.empty else 0
        if event_name in funnel_mapping:
            stage_name, order = funnel_mapping[event_name]
            funnel_data.append({
                'stage': stage_name,
                'count': count,
                'order': order
            })
    
    return pd.DataFrame(funnel_data).sort_values('order')

def get_trend_data(start_date=None, end_date=None, user_id=None):
    """获取趋势数据"""
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
    FROM recruit_event 
    {where_clause}
    GROUP BY DATE(create_time), event_type
    ORDER BY date DESC
    LIMIT 100
    """
    
    df = query_data(sql)
    
    # 添加事件类型映射 - 根据Prisma schema修正
    if not df.empty:
        event_type_mapping = {
            '1': '浏览简历',        # VIEW_RESUME
            '2': '打招呼',         # SCREEN_PASS
            '12': '相互沟通',       # BOSS_CHAT
            '13': '建联量'          # PHONE_NUMBER
        }
        df['event_type'] = df['event_type'].map(event_type_mapping).fillna(df['event_type'])
    
    return df

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
    """
    df = query_data(sql)
    
    options = [{'label': '全部用户', 'value': 'all'}]
    
    if not df.empty:
        for _, row in df.iterrows():
            # 显示用户名和事件数量
            options.append({
                'label': f"{row['display_name']} ({row['event_count']}条)",
                'value': str(row['id'])
            })
    
    return options

def get_key_metrics(start_date=None, end_date=None, user_id=None):
    """获取关键指标"""
    funnel_df = get_funnel_data(start_date, end_date, user_id)
    
    if funnel_df.empty:
        return {
            'browse_resumes': 0,
            'greetings': 0, 
            'mutual_communications': 0,
            'connections': 0,
            'greeting_success_rate': 0,
            'communication_success_rate': 0,
            'mutual_communication_rate': 0,
            'resume_screening_rate': 0
        }
    
    # 获取各阶段数据
    views = funnel_df[funnel_df['stage'] == '浏览简历']['count'].iloc[0] if len(funnel_df[funnel_df['stage'] == '浏览简历']) > 0 else 0
    screening = funnel_df[funnel_df['stage'] == '打招呼']['count'].iloc[0] if len(funnel_df[funnel_df['stage'] == '打招呼']) > 0 else 0
    chats = funnel_df[funnel_df['stage'] == '相互沟通']['count'].iloc[0] if len(funnel_df[funnel_df['stage'] == '相互沟通']) > 0 else 0
    contacts = funnel_df[funnel_df['stage'] == '建联量']['count'].iloc[0] if len(funnel_df[funnel_df['stage'] == '建联量']) > 0 else 0
    
    # 计算转化率
    greeting_success_rate = (contacts / screening * 100) if screening > 0 else 0  # 建联量/打招呼数
    communication_success_rate = (contacts / chats * 100) if chats > 0 else 0  # 建联量/相互沟通数
    mutual_communication_rate = (chats / screening * 100) if screening > 0 else 0  # 相互沟通数/打招呼数
    resume_screening_rate = (screening / views * 100) if views > 0 else 0  # 打招呼数/浏览简历
    
    return {
        'browse_resumes': views,          # 浏览简历
        'greetings': screening,           # 打招呼
        'mutual_communications': chats,   # 相互沟通
        'connections': contacts,          # 建联量
        'greeting_success_rate': greeting_success_rate,           # 打招呼成功率
        'communication_success_rate': communication_success_rate, # 沟通成功率
        'mutual_communication_rate': mutual_communication_rate,   # 相互沟通率
        'resume_screening_rate': resume_screening_rate            # 简历过筛率
    }

def create_metric_card(title, value, change=None, format_type='number', icon=None):
    """创建指标卡片"""
    # 根据格式类型处理数值显示
    if format_type == 'percentage':
        display_value = f"{value:.1f}%"
    elif format_type == 'number':
        display_value = f"{value:,}"
    else:
        display_value = str(value)
    
    # 变化指示器
    change_element = html.Div()
    if change is not None:
        change_class = "positive" if change >= 0 else "negative"
        change_text = f"+{change:.1f}%" if change >= 0 else f"{change:.1f}%"
        change_element = html.Div(
            change_text,
            className=f"kpi-change {change_class}"
        )
    
    return html.Div([
        html.H3(title),
        html.Div(display_value, className="kpi-value"),
        change_element
    ], className="card kpi-card")

def create_funnel_chart(funnel_df):
    """创建漏斗图"""
    if funnel_df.empty:
        return go.Figure().add_annotation(
            text="暂无数据",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color=colors['text'])
        )
    
    # 计算转化率
    funnel_df = funnel_df.copy()
    funnel_df['conversion_rate'] = 0
    
    for i in range(1, len(funnel_df)):
        if funnel_df.iloc[i-1]['count'] > 0:
            rate = (funnel_df.iloc[i]['count'] / funnel_df.iloc[i-1]['count']) * 100
            funnel_df.iloc[i, funnel_df.columns.get_loc('conversion_rate')] = rate
    
    # 计算各阶段的文字标签
    stage_texts = []
    total_count = funnel_df.iloc[0]['count'] if not funnel_df.empty else 0
    
    for i, (_, row) in enumerate(funnel_df.iterrows()):
        count = row['count']
        if i == 0:
            # 第一阶段
            stage_texts.append(f"{count}")
        else:
            # 后续阶段计算转化率
            prev_count = funnel_df.iloc[i-1]['count']
            if total_count > 0:
                total_percent = count / total_count * 100
                prev_percent = count / prev_count * 100 if prev_count > 0 else 0
                stage_texts.append(f"{count}<br>总体: {total_percent:.1f}%<br>转化: {prev_percent:.1f}%")
            else:
                stage_texts.append(f"{count}")
    
    # 创建漏斗图
    fig = go.Figure(go.Funnel(
        y=funnel_df['stage'],
        x=funnel_df['count'],
        textinfo="text",
        text=stage_texts,
        textfont=dict(size=14, color='white'),
        marker=dict(
            color=[colors['primary'], colors['secondary'], colors['warning'], colors['success']],
            line=dict(width=2, color='white')
        ),
        connector=dict(line=dict(color=colors['primary'], dash='dot', width=3))
    ))
    
    fig.update_layout(
        title=dict(
            text="<b>招聘漏斗分析</b>",
            font=dict(size=20, color=colors['text']),
            x=0.5
        ),
        font=dict(color=colors['text']),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=80, b=40, l=40, r=40)
    )
    
    return fig

def create_trend_chart(trend_df):
    """创建趋势图"""
    if trend_df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="暂无数据",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color=colors['text'])
        )
    else:
        # 透视数据
        pivot_df = trend_df.pivot_table(
            index='date', 
            columns='event_type', 
            values='count', 
            fill_value=0
        ).reset_index()
        
        fig = go.Figure()
        
        # 定义颜色映射
        color_map = {
            '浏览简历': colors['primary'],
            '打招呼': colors['secondary'], 
            '相互沟通': colors['warning'],
            '建联量': colors['success']
        }
        
        # 添加每个事件类型的线条
        for col in pivot_df.columns[1:]:
            if col in color_map:
                fig.add_trace(go.Scatter(
                    x=pivot_df['date'],
                    y=pivot_df[col],
                    mode='lines+markers',
                    name=col,
                    line=dict(color=color_map[col], width=3),
                    marker=dict(size=8, line=dict(width=2, color='white')),
                    hovertemplate=f'<b>{col}</b><br>日期: %{{x}}<br>数量: %{{y}}<extra></extra>'
                ))
    
    fig.update_layout(
        title=dict(
            text="<b>每日活动趋势</b>",
            font=dict(size=20, color=colors['text']),
            x=0.5
        ),
        xaxis=dict(
            title=dict(text="日期", font=dict(color=colors['text'])),
            tickfont=dict(color=colors['text']),
            gridcolor='rgba(255,255,255,0.1)'
        ),
        yaxis=dict(
            title=dict(text="活动数量", font=dict(color=colors['text'])),
            tickfont=dict(color=colors['text']),
            gridcolor='rgba(255,255,255,0.1)'
        ),
        legend=dict(
            font=dict(color=colors['text']),
            bgcolor='rgba(35, 41, 70, 0.8)',
            bordercolor=colors['primary'],
            borderwidth=1
        ),
        font=dict(color=colors['text']),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=80, b=60, l=60, r=40),
        hovermode='x unified'
    )
    
    return fig

def get_detailed_data(start_date=None, end_date=None, user_id=None):
    """获取详细数据"""
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
        re.id,
        re.event_type as '事件类型',
        CASE 
            WHEN u.name IS NOT NULL AND u.name != '' THEN u.name
            WHEN re.uid IS NOT NULL THEN CONCAT('用户-', LEFT(re.uid, 8))
            ELSE '未知用户'
        END as '用户',
        re.resume_id as '简历ID',
        re.job_id as '职位ID', 
        DATE_FORMAT(re.create_time, '%Y-%m-%d %H:%i:%s') as '创建时间'
    FROM recruit_event re
    LEFT JOIN user u ON re.uid = u.id
    {where_clause}
    ORDER BY re.create_time DESC
    LIMIT 1000
    """
    
    df = query_data(sql)
    
    # 添加事件类型映射 - 根据Prisma schema修正
    if not df.empty:
        event_type_mapping = {
            '1': '浏览简历',        # VIEW_RESUME
            '2': '打招呼',         # SCREEN_PASS
            '12': '相互沟通',       # BOSS_CHAT
            '13': '建联量'          # PHONE_NUMBER
        }
        df['事件类型'] = df['事件类型'].map(event_type_mapping).fillna(df['事件类型'])
    
    return df

# 应用布局
app.layout = html.Div([
    # 隐藏的存储组件用于状态管理
    dcc.Store(id='last-refresh-time'),
    dcc.Store(id='current-data'),
    
    # 头部
    html.Div([
        html.Div([
            html.Div([
                html.H1("🚀 智能招聘数据分析平台"),
                html.P("实时监控 · 数据驱动 · 智能决策")
            ], className="logo-section"),
            
            html.Div([
                html.Span(id="last-update-time", children="数据加载中..."),
                html.Button(
                    "🔄 刷新数据", 
                    id="refresh-btn",
                    className="btn",
                    style={'marginLeft': '15px'}
                )
            ], style={'display': 'flex', 'alignItems': 'center'})
        ], className="header-content")
    ], className="dashboard-header"),
    
    # 控制面板
    html.Div([
        html.Div([
            html.Div([
                html.Label("📅 选择日期范围"),
                dcc.DatePickerRange(
                    id='date-picker-range',
                    start_date=date.today() - timedelta(days=30),
                    end_date=date.today(),
                    display_format='YYYY-MM-DD',
                    style={'width': '100%'}
                )
            ], className="control-group"),
            
            html.Div([
                html.Label("⚡ 快速筛选"),
                html.Div(id="quick-filters", children=[
                    html.Button("今天", id="btn-today", className="quick-filter-btn"),
                    html.Button("昨天", id="btn-yesterday", className="quick-filter-btn"),
                    html.Button("最近7天", id="btn-7days", className="quick-filter-btn active"),
                    html.Button("最近30天", id="btn-30days", className="quick-filter-btn"),
                    html.Button("本月", id="btn-month", className="quick-filter-btn")
                ], className="quick-filters")
            ], className="control-group"),
            
            html.Div([
                html.Label("👤 选择用户"),
                dcc.Dropdown(
                    id='user-dropdown',
                    options=get_user_list(),
                    value='all',
                    clearable=False,
                    style={'minWidth': '200px'}
                )
            ], className="control-group"),
            
            html.Div([
                html.Label("🔄 自动刷新"),
                dcc.Dropdown(
                    id='refresh-interval',
                    options=[
                        {'label': '关闭', 'value': 0},
                        {'label': '30秒', 'value': 30000},
                        {'label': '1分钟', 'value': 60000},
                        {'label': '5分钟', 'value': 300000}
                    ],
                    value=0,
                    clearable=False
                )
            ], className="control-group")
        ], className="control-content")
    ], className="control-panel"),
    
    # 主要内容
    html.Div([
        # KPI指标卡片区域
        html.Div(id="kpi-section", className="kpi-section"),
        
        # 图表区域
        html.Div([
            html.Div([
                html.Div([
                    html.Div([
                        html.H2("📊 招聘漏斗分析", className="card-title"),
                        html.Div(id="funnel-loading", children=create_loading_component())
                    ], className="card-header"),
                    dcc.Graph(id="funnel-chart", style={'display': 'none'})
                ], className="card")
            ], style={'gridColumn': '1'}),
            
            html.Div([
                html.Div([
                    html.Div([
                        html.H2("📈 趋势分析", className="card-title"),
                        html.Div(id="trend-loading", children=create_loading_component())
                    ], className="card-header"),
                    dcc.Graph(id="trend-chart", style={'display': 'none'})
                ], className="card")
            ], style={'gridColumn': '2'})
        ], className="content-grid"),
        
        # 详细数据表格
        html.Div([
            html.Div([
                html.Div([
                    html.H2("📋 详细数据", className="card-title"),
                    html.Div([
                        html.Button("📊 导出Excel", id="export-excel-btn", className="btn btn-outline", style={'marginRight': '10px'}),
                        html.Button("📄 导出CSV", id="export-csv-btn", className="btn btn-outline")
                    ])
                ], className="card-header"),
                html.Div(id="data-table-loading", children=create_loading_component()),
                html.Div(id="data-table-container", style={'display': 'none'})
            ], className="card")
        ], className="data-table-container")
    ], className="main-content"),
    
    # 自动刷新组件
    dcc.Interval(
        id='auto-refresh-interval',
        interval=60000,  # 默认1分钟
        n_intervals=0,
        disabled=True
    ),
    
    # 下载组件
    dcc.Download(id="download-excel"),
    dcc.Download(id="download-csv")
], className="dashboard-container")

# 回调函数：快速日期筛选
@app.callback(
    [Output('date-picker-range', 'start_date'),
     Output('date-picker-range', 'end_date'),
     Output('btn-today', 'className'),
     Output('btn-yesterday', 'className'),
     Output('btn-7days', 'className'),
     Output('btn-30days', 'className'),
     Output('btn-month', 'className')],
    [Input('btn-today', 'n_clicks'),
     Input('btn-yesterday', 'n_clicks'),
     Input('btn-7days', 'n_clicks'),
     Input('btn-30days', 'n_clicks'),
     Input('btn-month', 'n_clicks')]
)
def update_date_range(*args):
    ctx = callback_context
    
    if not ctx.triggered:
        return dash.no_update
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    today = date.today()
    base_class = "quick-filter-btn"
    active_class = "quick-filter-btn active"
    
    classes = [base_class] * 5
    
    if button_id == 'btn-today':
        start_date, end_date = today, today
        classes[0] = active_class
    elif button_id == 'btn-yesterday':
        yesterday = today - timedelta(days=1)
        start_date, end_date = yesterday, yesterday
        classes[1] = active_class
    elif button_id == 'btn-7days':
        start_date = today - timedelta(days=7)
        end_date = today
        classes[2] = active_class
    elif button_id == 'btn-30days':
        start_date = today - timedelta(days=30)
        end_date = today
        classes[3] = active_class
    elif button_id == 'btn-month':
        start_date = today.replace(day=1)
        end_date = today
        classes[4] = active_class
    else:
        return dash.no_update
    
    return start_date, end_date, *classes

# 回调函数：自动刷新设置
@app.callback(
    [Output('auto-refresh-interval', 'interval'),
     Output('auto-refresh-interval', 'disabled')],
    [Input('refresh-interval', 'value')]
)
def update_auto_refresh(interval_value):
    if interval_value == 0:
        return 60000, True
    else:
        return interval_value, False

# 回调函数：更新数据
@app.callback(
    [Output('kpi-section', 'children'),
     Output('funnel-chart', 'figure'),
     Output('funnel-chart', 'style'),
     Output('funnel-loading', 'style'),
     Output('trend-chart', 'figure'),
     Output('trend-chart', 'style'),
     Output('trend-loading', 'style'),
     Output('data-table-container', 'children'),
     Output('data-table-container', 'style'),
     Output('data-table-loading', 'style'),
     Output('last-update-time', 'children'),
     Output('last-refresh-time', 'data')],
    [Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date'),
     Input('user-dropdown', 'value'),
     Input('refresh-btn', 'n_clicks'),
     Input('auto-refresh-interval', 'n_intervals')]
)
def update_dashboard(start_date, end_date, user_id, refresh_clicks, auto_refresh):
    # 显示加载状态
    loading_style = {'display': 'block'}
    hidden_style = {'display': 'none'}
    
    try:
        # 获取数据
        metrics = get_key_metrics(start_date, end_date, user_id)
        funnel_df = get_funnel_data(start_date, end_date, user_id)
        trend_df = get_trend_data(start_date, end_date, user_id)
        detailed_df = get_detailed_data(start_date, end_date, user_id)
        
        # 创建KPI卡片
        kpi_cards = [
            create_metric_card("📊 浏览简历", metrics['browse_resumes'], None, 'number'),
            create_metric_card("✅ 打招呼", metrics['greetings'], None, 'number'),
            create_metric_card("💬 相互沟通", metrics['mutual_communications'], None, 'number'),
            create_metric_card("🤝 建联量", metrics['connections'], None, 'number'),
            create_metric_card("📈 打招呼成功率", metrics['greeting_success_rate'], None, 'percentage'),
            create_metric_card("🎯 沟通成功率", metrics['communication_success_rate'], None, 'percentage'),
            create_metric_card("💡 相互沟通率", metrics['mutual_communication_rate'], None, 'percentage'),
            create_metric_card("📋 简历过筛率", metrics['resume_screening_rate'], None, 'percentage')
        ]
        
        # 创建图表
        funnel_chart = create_funnel_chart(funnel_df)
        trend_chart = create_trend_chart(trend_df)
        
        # 创建数据表格
        if not detailed_df.empty:
            # 移除ID列用于显示
            display_df = detailed_df.drop(columns=['id'] if 'id' in detailed_df.columns else [])
            
            data_table = dash_table.DataTable(
                data=display_df.to_dict('records'),
                columns=[{"name": i, "id": i} for i in display_df.columns],
                page_size=20,
                sort_action="native",
                filter_action="native",
                style_table={'overflowX': 'auto'},
                style_cell={
                    'textAlign': 'left',
                    'padding': '12px',
                    'fontFamily': 'Arial',
                    'fontSize': '14px'
                },
                style_header={
                    'fontWeight': 'bold',
                    'textAlign': 'center'
                },
                style_data_conditional=[
                    {
                        'if': {'row_index': 'odd'},
                        'backgroundColor': 'rgba(30, 39, 73, 0.5)'
                    }
                ]
            )
        else:
            data_table = html.Div("暂无数据", style={
                'textAlign': 'center', 
                'padding': '40px',
                'color': colors['text'],
                'fontSize': '16px'
            })
        
        # 更新时间戳
        update_time = f"最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return (
            kpi_cards,
            funnel_chart, {'display': 'block'}, hidden_style,
            trend_chart, {'display': 'block'}, hidden_style,
            data_table, {'display': 'block'}, hidden_style,
            update_time,
            time.time()
        )
        
    except Exception as e:
        print(f"更新数据时出错: {e}")
        error_msg = html.Div(f"数据加载失败: {str(e)}", style={
            'color': colors['danger'],
            'textAlign': 'center',
            'padding': '20px'
        })
        
        return (
            [error_msg],
            {}, hidden_style, hidden_style,
            {}, hidden_style, hidden_style,
            error_msg, hidden_style, hidden_style,
            f"更新失败: {datetime.now().strftime('%H:%M:%S')}",
            time.time()
        )

# 导出Excel回调
@app.callback(
    Output('download-excel', 'data'),
    [Input('export-excel-btn', 'n_clicks')],
    [State('date-picker-range', 'start_date'),
     State('date-picker-range', 'end_date'),
     State('user-dropdown', 'value')],
    prevent_initial_call=True
)
def export_excel(n_clicks, start_date, end_date, user_id):
    if n_clicks:
        try:
            # 获取详细数据
            df = get_detailed_data(start_date, end_date, user_id)
            if not df.empty:
                # 移除ID列
                if 'id' in df.columns:
                    df = df.drop(columns=['id'])
                
                # 生成文件名
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"招聘数据_{timestamp}.xlsx"
                
                # 创建Excel文件
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='招聘数据', index=False)
                
                output.seek(0)
                
                # 触发下载
                return dcc.send_bytes(output.getvalue(), filename)
        except Exception as e:
            print(f"导出Excel失败: {e}")
    
    return dash.no_update

# 导出CSV回调
@app.callback(
    Output('download-csv', 'data'),
    [Input('export-csv-btn', 'n_clicks')],
    [State('date-picker-range', 'start_date'),
     State('date-picker-range', 'end_date'),
     State('user-dropdown', 'value')],
    prevent_initial_call=True
)
def export_csv(n_clicks, start_date, end_date, user_id):
    if n_clicks:
        try:
            # 获取详细数据
            df = get_detailed_data(start_date, end_date, user_id)
            if not df.empty:
                # 移除ID列
                if 'id' in df.columns:
                    df = df.drop(columns=['id'])
                
                # 生成文件名
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"招聘数据_{timestamp}.csv"
                
                # 生成CSV
                csv_string = df.to_csv(index=False, encoding='utf-8-sig')
                
                # 触发下载
                return dcc.send_string(csv_string, filename)
        except Exception as e:
            print(f"导出CSV失败: {e}")
    
    return dash.no_update

if __name__ == '__main__':
    print("🚀 启动智能招聘数据分析平台...")
    print("📊 访问地址: http://0.0.0.0:8050/")
    print("🌐 局域网访问: http://172.18.202.183:8050/")
    app.run(host='0.0.0.0', port=8050, debug=True) 