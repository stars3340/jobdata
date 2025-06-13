#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能招聘数据分析平台 - 生产环境入口文件
"""

import sys
import os
import logging
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from recruitment_dashboard import app

def setup_logging():
    """设置日志配置"""
    # 确保日志目录存在
    log_dir = os.path.dirname(Config.LOG_FILE)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 配置日志格式
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # 配置文件日志
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL),
        format=log_format,
        handlers=[
            logging.FileHandler(Config.LOG_FILE, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # 记录启动信息
    logger = logging.getLogger(__name__)
    logger.info(f"启动 {Config.APP_NAME}")
    logger.info(f"配置: Host={Config.APP_HOST}, Port={Config.APP_PORT}, Debug={Config.APP_DEBUG}")
    
    return logger

def create_app():
    """创建并配置应用"""
    # 设置日志
    logger = setup_logging()
    
    # 配置Flask应用
    app.server.config['SECRET_KEY'] = Config.SECRET_KEY
    
    # 添加健康检查路由
    @app.server.route('/health')
    def health_check():
        return {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0'
        }
    
    # 添加应用信息路由
    @app.server.route('/info')
    def app_info():
        return {
            'name': Config.APP_NAME,
            'version': '1.0.0',
            'environment': 'production' if not Config.APP_DEBUG else 'development',
            'database': 'connected'
        }
    
    logger.info("应用配置完成")
    return app

# 创建应用实例
application = create_app()

if __name__ == '__main__':
    application.run_server(
        host=Config.APP_HOST,
        port=Config.APP_PORT,
        debug=Config.APP_DEBUG
    ) 