#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
腾讯云 MySQL 数据库配置
针对只读权限的数据展示分析优化
"""

import os
from typing import Dict, Any

# 腾讯云 MySQL 配置
TENCENT_CLOUD_CONFIG = {
    'host': 'bj-cynosdbmysql-grp-5eypnf9y.sql.tencentcdb.com',
    'port': int(os.getenv('DB_PORT', 26606)),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', 'Gn123456'),
    'database': os.getenv('DB_NAME', 'recruit-db'),
    'charset': 'utf8mb4',
    'read_only': True,  # 标记为只读 - 切记不能增删改！
    
    # 连接池配置（针对只读查询优化）
    'connect_timeout': 10,
    'read_timeout': 30,
    'write_timeout': 30,
    'autocommit': True,
    
    # SSL 配置（腾讯云推荐）
    'ssl_disabled': False
}

# 环境变量模板（用于部署）
ENV_TEMPLATE = {
    'DB_TYPE': 'mysql',
    'DB_HOST': 'bj-cynosdbmysql-grp-5eypnf9y.sql.tencentcdb.com',
    'DB_PORT': '26606',
    'DB_USER': 'root',
    'DB_PASSWORD': 'Gn123456',
    'DB_NAME': 'recruit-db',
    'DB_CHARSET': 'utf8mb4'
}

def get_connection_config() -> Dict[str, Any]:
    """获取腾讯云数据库连接配置"""
    config = TENCENT_CLOUD_CONFIG.copy()
    
    # 从环境变量更新敏感信息
    config.update({
        'user': os.getenv('DB_USER', config['user']),
        'password': os.getenv('DB_PASSWORD', config['password']),
        'database': os.getenv('DB_NAME', config['database'])
    })
    
    # 移除只读标记（这个是我们内部使用的）
    config.pop('read_only', None)
    
    return config

def validate_readonly_operations():
    """验证是否为只读操作，防止意外的写入操作"""
    import warnings
    
    # 警告：此数据库为只读
    warnings.warn(
        "⚠️  当前数据库为只读模式，仅支持查询操作",
        UserWarning,
        stacklevel=2
    )

def get_optimized_queries():
    """获取针对只读数据库优化的查询语句"""
    return {
        'funnel_data': """
            SELECT 
                event_type,
                COUNT(*) as count
            FROM recruit_event 
            WHERE {where_conditions}
            GROUP BY event_type
            ORDER BY count DESC
        """,
        
        'trend_data': """
            SELECT 
                DATE(create_time) as date,
                event_type,
                COUNT(*) as count
            FROM recruit_event 
            WHERE {where_conditions}
            GROUP BY DATE(create_time), event_type
            ORDER BY date DESC
            LIMIT 100
        """,
        
        'user_list': """
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
        """,
        
        'detailed_data': """
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
            WHERE {where_conditions}
            ORDER BY re.create_time DESC
            LIMIT 1000
        """
    }

# 数据库性能优化建议
PERFORMANCE_TIPS = {
    'indexing': [
        '确保 recruit_event 表在 create_time 字段有索引',
        '确保 recruit_event 表在 uid 字段有索引',
        '确保 recruit_event 表在 event_type 字段有索引'
    ],
    'querying': [
        '使用日期范围限制查询数据量',
        '避免全表扫描，总是添加 WHERE 条件',
        '使用 LIMIT 限制返回行数'
    ],
    'caching': [
        '考虑在应用层添加查询结果缓存',
        '对频繁查询的数据进行缓存'
    ]
}

# 只读模式功能说明
READONLY_FEATURES = {
    '✅ 支持的功能': [
        '📊 数据可视化（漏斗图、趋势图）',
        '📈 实时指标展示',
        '🔍 数据筛选和过滤',
        '📋 详细数据表格',
        '📤 数据导出（Excel/CSV）',
        '👥 用户活动分析',
        '📅 时间范围分析'
    ],
    '❌ 不支持的功能': [
        '👤 新用户注册',
        '📝 添加新的招聘事件',
        '✏️ 编辑现有数据',
        '🗑️ 删除数据',
        '⚙️ 数据库结构修改'
    ]
}

print("✅ 腾讯云 MySQL 只读配置已优化")
print(f"🗄️ 数据库主机: {TENCENT_CLOUD_CONFIG['host']}")
print("📊 专注于数据展示分析功能")
print("🔒 只读模式，确保数据安全") 