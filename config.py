import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Config:
    """应用配置类"""
    
    # 应用配置
    APP_NAME = os.getenv('APP_NAME', '智能招聘数据分析平台')
    APP_HOST = os.getenv('APP_HOST', '0.0.0.0')
    APP_PORT = int(os.getenv('APP_PORT', 8050))
    APP_DEBUG = os.getenv('APP_DEBUG', 'False').lower() == 'true'
    
    # 数据库配置（腾讯云 MySQL - 只读模式）
    DB_CONFIG = {
        'host': os.getenv('DB_HOST', 'bj-cynosdbmysql-grp-5eypnf9y.sql.tencentcdb.com'),
        'port': int(os.getenv('DB_PORT', 26606)),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', 'Gn123456'),
        'database': os.getenv('DB_NAME', 'recruit-db'),
        'charset': os.getenv('DB_CHARSET', 'utf8mb4')
    }
    
    # 安全配置
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # 日志配置
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/app.log')
    
    # 缓存配置
    CACHE_TYPE = os.getenv('CACHE_TYPE', 'simple')
    CACHE_DEFAULT_TIMEOUT = int(os.getenv('CACHE_DEFAULT_TIMEOUT', 300))
    
    @staticmethod
    def get_db_url():
        """获取数据库连接URL"""
        return f"mysql+pymysql://{Config.DB_CONFIG['user']}:{Config.DB_CONFIG['password']}@{Config.DB_CONFIG['host']}:{Config.DB_CONFIG['port']}/{Config.DB_CONFIG['database']}?charset={Config.DB_CONFIG['charset']}" 