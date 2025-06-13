#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能招聘数据分析平台 - Vercel无服务器函数入口
"""

import os
import sys
from flask import Flask

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 导入主应用
from recruitment_dashboard import app

# 获取Flask应用实例
server = app.server

# Vercel需要的应用实例
application = server

# 为Vercel无服务器函数准备的处理器
def handler(event, context):
    """Vercel无服务器函数处理器"""
    return server

# 如果直接运行此文件
if __name__ == "__main__":
    # 开发环境运行
    app.run_server(debug=True, host='0.0.0.0', port=8050) 