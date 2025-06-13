#!/bin/bash

# 智能招聘数据分析平台 - 自动部署脚本

echo "🚀 开始部署智能招聘数据分析平台..."

# 检查必要的工具
echo "📋 检查部署环境..."

# 检查 git
if ! command -v git &> /dev/null; then
    echo "❌ Git 未安装，请先安装 Git"
    exit 1
fi

# 检查 node 和 npm (用于 Vercel CLI)
if ! command -v node &> /dev/null; then
    echo "⚠️  Node.js 未安装，将跳过 Vercel CLI 部署"
    SKIP_VERCEL_CLI=true
else
    echo "✅ Node.js 已安装"
fi

# 创建 .env 文件（如果不存在）
if [ ! -f .env ]; then
    echo "📝 创建环境配置文件..."
    cp env.example .env
    echo "⚠️  请编辑 .env 文件，填入您的数据库配置信息"
    echo "   编辑完成后，按回车键继续..."
    read -p "   " dummy
fi

# 初始化 Git 仓库（如果需要）
if [ ! -d .git ]; then
    echo "🔧 初始化 Git 仓库..."
    git init
    git add .
    git commit -m "Initial commit: 智能招聘数据分析平台"
fi

echo "📦 准备部署文件..."

# 显示部署选项
echo "
🎯 请选择部署方式:
1) GitHub + Vercel Web 界面 (推荐)
2) Vercel CLI 部署
3) 仅准备文件，稍后手动部署
"

read -p "请输入选项 (1-3): " choice

case $choice in
    1)
        echo "
📚 GitHub + Vercel 部署步骤:
1. 将代码推送到 GitHub:
   git remote add origin https://github.com/YOUR_USERNAME/recruitment-dashboard.git
   git branch -M main
   git push -u origin main

2. 访问 https://vercel.com/dashboard
3. 点击 'New Project'
4. 选择您的 GitHub 仓库
5. 在 'Environment Variables' 中配置数据库信息:
   - DB_HOST: 您的数据库主机
   - DB_PORT: 数据库端口
   - DB_USER: 数据库用户名
   - DB_PASSWORD: 数据库密码
   - DB_NAME: 数据库名称
   - DB_CHARSET: utf8mb4
6. 点击 'Deploy'

✨ 部署完成后，您将获得一个可访问的 URL
"
        ;;
    2)
        if [ "$SKIP_VERCEL_CLI" = true ]; then
            echo "❌ Node.js 未安装，无法使用 Vercel CLI"
            echo "请选择其他部署方式"
            exit 1
        fi
        
        echo "🔧 安装 Vercel CLI..."
        npm install -g vercel
        
        echo "🚀 开始 Vercel 部署..."
        echo "⚠️  部署过程中需要配置环境变量，请准备好数据库信息"
        vercel
        ;;
    3)
        echo "✅ 文件准备完成！"
        echo "
📋 手动部署检查清单:
☐ 环境变量配置 (.env 文件)
☐ 数据库连接测试
☐ 代码推送到 Git 仓库
☐ Vercel 项目配置
☐ 环境变量设置
☐ 部署和测试
"
        ;;
    *)
        echo "❌ 无效选项"
        exit 1
        ;;
esac

echo "
🎉 部署准备完成！

📋 部署后测试清单:
☐ 访问部署的 URL
☐ 检查数据加载是否正常
☐ 测试日期筛选功能
☐ 测试用户筛选功能
☐ 测试数据导出功能
☐ 检查移动端适配

🔗 有用的链接:
- Vercel Dashboard: https://vercel.com/dashboard
- 项目文档: README.md
- 问题反馈: GitHub Issues

🆘 如遇问题:
1. 检查环境变量配置
2. 查看 Vercel 部署日志
3. 确认数据库连接正常
4. 参考 README.md 文档
" 