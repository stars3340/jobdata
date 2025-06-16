#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库适配器 - 支持多种免费数据库服务
"""

import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class DatabaseConfig:
    """数据库配置管理"""
    
    @staticmethod
    def get_connection_params() -> Dict[str, Any]:
        """获取数据库连接参数"""
        db_type = os.getenv('DB_TYPE', 'mysql').lower()
        
        if db_type == 'postgresql':
            return DatabaseConfig._get_postgresql_params()
        elif db_type == 'mysql':
            return DatabaseConfig._get_mysql_params()
        elif db_type == 'sqlite':
            return DatabaseConfig._get_sqlite_params()
        else:
            raise ValueError(f"不支持的数据库类型: {db_type}")
    
    @staticmethod
    def _get_mysql_params() -> Dict[str, Any]:
        """MySQL/PlanetScale 连接参数"""
        return {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 3306)),
            'user': os.getenv('DB_USER', 'root'),
            'password': os.getenv('DB_PASSWORD', ''),
            'database': os.getenv('DB_NAME', 'recruit_db'),
            'charset': os.getenv('DB_CHARSET', 'utf8mb4'),
            'ssl_disabled': os.getenv('DB_SSL_DISABLED', 'False').lower() == 'true'
        }
    
    @staticmethod
    def _get_postgresql_params() -> Dict[str, Any]:
        """PostgreSQL 连接参数 (ElephantSQL, Supabase等)"""
        return {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 5432)),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', ''),
            'database': os.getenv('DB_NAME', 'recruit_db'),
            'sslmode': os.getenv('DB_SSLMODE', 'require')
        }
    
    @staticmethod
    def _get_sqlite_params() -> Dict[str, Any]:
        """SQLite 连接参数 (本地开发)"""
        return {
            'database': os.getenv('DB_PATH', 'data/recruit.db')
        }

def get_db_connection():
    """获取数据库连接"""
    db_type = os.getenv('DB_TYPE', 'mysql').lower()
    params = DatabaseConfig.get_connection_params()
    
    try:
        if db_type == 'mysql':
            import pymysql
            connection = pymysql.connect(**params)
            logger.info("MySQL 数据库连接成功")
            return connection
            
        elif db_type == 'postgresql':
            logger.error("PostgreSQL 支持已移除，请使用 MySQL 数据库")
            raise ValueError("PostgreSQL 支持已移除，请设置 DB_TYPE=mysql")
            
        elif db_type == 'sqlite':
            import sqlite3
            connection = sqlite3.connect(params['database'])
            logger.info("SQLite 数据库连接成功")
            return connection
            
    except Exception as e:
        logger.error(f"数据库连接失败: {e}")
        raise

def get_sql_dialect() -> str:
    """获取SQL方言"""
    db_type = os.getenv('DB_TYPE', 'mysql').lower()
    return db_type

# 免费数据库服务配置示例
FREE_DB_SERVICES = {
    'planetscale': {
        'type': 'mysql',
        'description': 'MySQL兼容，10GB免费额度',
        'url': 'https://planetscale.com'
    },
    'elephantsql': {
        'type': 'postgresql', 
        'description': 'PostgreSQL，20MB免费额度',
        'url': 'https://www.elephantsql.com'
    },
    'supabase': {
        'type': 'postgresql',
        'description': 'PostgreSQL，500MB免费额度',
        'url': 'https://supabase.com'
    },
    'railway': {
        'type': 'postgresql',
        'description': 'PostgreSQL，100MB免费额度',
        'url': 'https://railway.app'
    }
} 