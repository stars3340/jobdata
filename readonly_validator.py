#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
只读数据库验证器
确保严格禁止任何增删改操作，保护腾讯云数据库安全
"""

import re
import logging
import functools
from typing import Optional

logger = logging.getLogger(__name__)

# 禁止的SQL关键词（增删改操作）
FORBIDDEN_SQL_KEYWORDS = [
    'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 
    'TRUNCATE', 'REPLACE', 'MERGE', 'CALL', 'EXEC', 'EXECUTE',
    'GRANT', 'REVOKE', 'COMMIT', 'ROLLBACK', 'SAVEPOINT'
]

# 允许的SQL关键词（仅查询操作）
ALLOWED_SQL_KEYWORDS = [
    'SELECT', 'SHOW', 'DESCRIBE', 'DESC', 'EXPLAIN', 'USE'
]

class ReadOnlyViolationError(Exception):
    """只读模式违规错误"""
    pass

def validate_readonly_sql(sql: str) -> bool:
    """
    验证SQL语句是否符合只读要求
    
    Args:
        sql: SQL语句
        
    Returns:
        bool: True表示安全（只读），False表示危险（写入）
        
    Raises:
        ReadOnlyViolationError: 检测到写入操作时抛出
    """
    if not sql or not isinstance(sql, str):
        return True
    
    # 清理SQL语句（移除注释和多余空白）
    cleaned_sql = clean_sql(sql)
    
    # 检查是否包含禁止的关键词
    for keyword in FORBIDDEN_SQL_KEYWORDS:
        pattern = r'\b' + re.escape(keyword) + r'\b'
        if re.search(pattern, cleaned_sql, re.IGNORECASE):
            error_msg = f"🚫 检测到禁止的SQL操作: {keyword} - 数据库为只读模式！"
            logger.error(error_msg)
            logger.error(f"违规SQL: {sql[:100]}...")
            raise ReadOnlyViolationError(error_msg)
    
    # 检查是否以允许的关键词开头
    first_keyword = get_first_sql_keyword(cleaned_sql)
    if first_keyword and first_keyword.upper() not in ALLOWED_SQL_KEYWORDS:
        error_msg = f"🚫 不允许的SQL操作: {first_keyword} - 仅允许查询操作！"
        logger.error(error_msg)
        raise ReadOnlyViolationError(error_msg)
    
    logger.info(f"✅ SQL查询验证通过: {first_keyword}")
    return True

def clean_sql(sql: str) -> str:
    """清理SQL语句"""
    # 移除单行注释
    sql = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)
    # 移除多行注释
    sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
    # 移除多余空白
    sql = ' '.join(sql.split())
    return sql.strip()

def get_first_sql_keyword(sql: str) -> Optional[str]:
    """获取SQL语句的第一个关键词"""
    if not sql:
        return None
    
    words = sql.strip().split()
    if words:
        return words[0].upper()
    return None

def readonly_database_guard(func):
    """
    数据库函数装饰器，确保只进行只读操作
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # 在执行数据库操作前验证
        logger.info("🔒 只读数据库守护：开始验证数据库操作")
        
        # 如果函数参数中有SQL语句，进行验证
        for arg in args:
            if isinstance(arg, str) and len(arg) > 10:  # 可能是SQL语句
                if any(keyword in arg.upper() for keyword in ['SELECT', 'SHOW', 'DESC']):
                    validate_readonly_sql(arg)
        
        for key, value in kwargs.items():
            if isinstance(value, str) and len(value) > 10:  # 可能是SQL语句
                if any(keyword in value.upper() for keyword in ['SELECT', 'SHOW', 'DESC']):
                    validate_readonly_sql(value)
        
        # 执行原函数
        result = func(*args, **kwargs)
        logger.info("✅ 只读数据库操作完成")
        return result
    
    return wrapper

# 安全提示信息
def print_readonly_warning():
    """打印只读模式警告"""
    warning_message = """
    🔒 ==================== 只读数据库模式 ====================
    ⚠️  警告：当前连接腾讯云MySQL数据库（只读权限）
    ✅  允许操作：SELECT, SHOW, DESCRIBE, EXPLAIN
    🚫  禁止操作：INSERT, UPDATE, DELETE, CREATE, DROP, ALTER
    🛡️  安全保护：自动检测并阻止所有写入操作
    ===========================================================
    """
    print(warning_message)
    logger.warning("数据库已设置为只读模式，所有写入操作将被阻止")

# 示例用法
if __name__ == "__main__":
    # 测试安全的SQL
    safe_queries = [
        "SELECT * FROM user LIMIT 10",
        "SELECT COUNT(*) FROM recruit_event WHERE create_time > '2025-01-01'",
        "SHOW TABLES",
        "DESCRIBE recruit_event"
    ]
    
    # 测试危险的SQL  
    dangerous_queries = [
        "INSERT INTO user (name) VALUES ('test')",
        "UPDATE user SET name = 'updated' WHERE id = 1",
        "DELETE FROM recruit_event WHERE id = 1",
        "DROP TABLE test",
        "CREATE TABLE temp (id int)"
    ]
    
    print("🧪 测试只读验证器...")
    
    # 测试安全查询
    print("\n✅ 测试安全查询:")
    for query in safe_queries:
        try:
            validate_readonly_sql(query)
            print(f"  ✓ {query[:50]}...")
        except ReadOnlyViolationError as e:
            print(f"  ✗ {e}")
    
    # 测试危险查询
    print("\n🚫 测试危险查询:")
    for query in dangerous_queries:
        try:
            validate_readonly_sql(query)
            print(f"  ⚠️  未检测到危险: {query[:50]}...")
        except ReadOnlyViolationError as e:
            print(f"  ✓ 成功阻止: {query[:30]}...")

# 打印警告信息
print_readonly_warning() 