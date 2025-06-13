#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能招聘数据分析平台 - Vercel优化版本入口文件
"""

import os
import sys
import warnings
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 过滤警告
warnings.filterwarnings('ignore')

# 导入完整的Dash应用
try:
    from recruitment_dashboard import app
    # 获取Flask应用实例
    server = app.server
    # Vercel需要的应用实例
    application = server
except ImportError as e:
    print(f"导入应用失败: {e}")
    # 创建备用Flask应用
    from flask import Flask
    application = Flask(__name__)
    
    @application.route('/')
    def index():
        return "应用加载中，请稍后刷新..."
    
    @application.route('/health')
    def health():
        return {'status': 'error', 'message': '主应用加载失败'}

# 健康检查路由
@application.route('/api/health')
def api_health():
    return {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '2.0.0'
    }

if __name__ == "__main__":
    application.run(debug=True, host='0.0.0.0', port=8050) 