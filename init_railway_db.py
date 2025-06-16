#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Railway PostgreSQL 数据库初始化脚本
运行此脚本来创建必要的数据表和示例数据
"""

import os
import sys
import logging
from datetime import datetime, timedelta
import random

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("❌ psycopg2 未安装，请运行: pip install psycopg2-binary")
    sys.exit(1)

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_db_connection():
    """获取数据库连接"""
    try:
        # 优先使用 DATABASE_URL
        database_url = os.getenv('DATABASE_URL')
        if database_url:
            conn = psycopg2.connect(database_url, sslmode='require')
            logger.info("✅ 使用 DATABASE_URL 连接成功")
            return conn
        
        # 使用单独的环境变量
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            port=int(os.getenv('DB_PORT', 5432)),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME'),
            sslmode='require'
        )
        logger.info("✅ 使用环境变量连接成功")
        return conn
    except Exception as e:
        logger.error(f"❌ 数据库连接失败: {e}")
        raise

def create_tables(conn):
    """创建数据表"""
    cursor = conn.cursor()
    
    # 创建用户表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) NOT NULL UNIQUE,
            email VARCHAR(255),
            full_name VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    logger.info("✅ 用户表创建成功")
    
    # 创建工作表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS job (
            id SERIAL PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            company VARCHAR(255),
            location VARCHAR(255),
            salary_range VARCHAR(100),
            job_type VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    logger.info("✅ 工作表创建成功")
    
    # 创建简历表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resume (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            job_id INTEGER REFERENCES job(id),
            status VARCHAR(50) DEFAULT 'submitted',
            resume_content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    logger.info("✅ 简历表创建成功")
    
    # 创建招聘事件表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recruit_event (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            job_id INTEGER REFERENCES job(id),
            event_type VARCHAR(100) NOT NULL,
            event_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            details TEXT
        )
    """)
    logger.info("✅ 招聘事件表创建成功")
    
    # 创建索引提升性能
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_recruit_event_date ON recruit_event(event_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_recruit_event_type ON recruit_event(event_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON recruit_event(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_job_id ON recruit_event(job_id)")
    logger.info("✅ 索引创建成功")
    
    conn.commit()

def insert_sample_data(conn):
    """插入示例数据"""
    cursor = conn.cursor()
    
    # 插入示例用户
    users_data = [
        ('张三', 'zhangsan@example.com', '张三'),
        ('李四', 'lisi@example.com', '李四'),
        ('王五', 'wangwu@example.com', '王五'),
        ('赵六', 'zhaoliu@example.com', '赵六'),
    ]
    
    for username, email, full_name in users_data:
        cursor.execute("""
            INSERT INTO users (username, email, full_name) 
            VALUES (%s, %s, %s) ON CONFLICT (username) DO NOTHING
        """, (username, email, full_name))
    
    # 插入示例工作
    jobs_data = [
        ('Python开发工程师', '阿里巴巴', '杭州', '20-35K', 'full-time'),
        ('前端开发工程师', '腾讯', '深圳', '18-30K', 'full-time'),
        ('数据分析师', '字节跳动', '北京', '15-25K', 'full-time'),
        ('产品经理', '美团', '北京', '25-40K', 'full-time'),
    ]
    
    for title, company, location, salary, job_type in jobs_data:
        cursor.execute("""
            INSERT INTO job (title, company, location, salary_range, job_type) 
            VALUES (%s, %s, %s, %s, %s)
        """, (title, company, location, salary, job_type))
    
    conn.commit()
    
    # 获取插入的用户和工作ID
    cursor.execute("SELECT id FROM users")
    user_ids = [row[0] for row in cursor.fetchall()]
    
    cursor.execute("SELECT id FROM job")
    job_ids = [row[0] for row in cursor.fetchall()]
    
    # 插入示例简历和事件
    event_types = [
        '查看简历', '简历通过筛选', 'Boss上聊天', '交换联系方式', 
        '安排面试', '面试完成', '发放offer', '入职确认'
    ]
    
    # 生成最近30天的数据
    base_date = datetime.now() - timedelta(days=30)
    
    for i in range(100):  # 生成100条记录
        user_id = random.choice(user_ids)
        job_id = random.choice(job_ids)
        event_type = random.choice(event_types)
        event_date = base_date + timedelta(days=random.randint(0, 30), 
                                         hours=random.randint(0, 23),
                                         minutes=random.randint(0, 59))
        
        cursor.execute("""
            INSERT INTO recruit_event (user_id, job_id, event_type, event_date, details) 
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, job_id, event_type, event_date, f"示例事件: {event_type}"))
    
    conn.commit()
    logger.info("✅ 示例数据插入成功")

def verify_data(conn):
    """验证数据"""
    cursor = conn.cursor()
    
    tables = ['users', 'job', 'resume', 'recruit_event']
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        logger.info(f"📊 {table} 表数据量: {count}")

def main():
    """主函数"""
    logger.info("🚀 开始初始化 Railway PostgreSQL 数据库...")
    
    # 检查环境变量
    required_vars = ['DATABASE_URL'] if os.getenv('DATABASE_URL') else [
        'DB_HOST', 'DB_USER', 'DB_PASSWORD', 'DB_NAME'
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"❌ 缺少环境变量: {missing_vars}")
        logger.error("请在 Railway 中配置数据库环境变量")
        sys.exit(1)
    
    try:
        # 连接数据库
        conn = get_db_connection()
        
        # 创建表
        create_tables(conn)
        
        # 插入示例数据
        insert_sample_data(conn)
        
        # 验证数据
        verify_data(conn)
        
        conn.close()
        logger.info("🎉 数据库初始化完成！")
        logger.info("现在可以访问您的Railway应用了")
        
    except Exception as e:
        logger.error(f"❌ 初始化失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 