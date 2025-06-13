# 🚀 智能招聘数据分析平台

一个基于 Python Dash 构建的全功能招聘数据分析仪表板，专为Vercel云平台优化，提供完整的招聘漏斗分析、趋势监控和数据导出功能。

> 🔐 **安全声明**: 本项目代码和文档中所有的数据库连接信息、密码等均为示例值，不包含任何真实的敏感信息。部署时请使用您自己的数据库配置。

> ⚡ **优化版本**: 为符合Vercel 250MB限制，本项目使用优化的依赖版本（Dash 2.17.1, pandas 2.0.3等），在保持完整功能的同时减少包体积。

## ✨ 功能特色

- 📊 **完整数据分析** - 招聘漏斗分析、趋势图表、关键指标监控
- 🎯 **多维度筛选** - 按日期范围、用户维度进行数据筛选
- 📈 **交互式图表** - 漏斗图、趋势线图、实时数据更新
- 📤 **数据导出** - 支持 Excel 和 CSV 格式导出
- 🔄 **自动刷新** - 可配置的自动数据刷新（30秒/1分钟/5分钟）
- 📱 **响应式设计** - 适配桌面端、平板和移动端
- ⚡ **云优化** - 专为Vercel平台优化的依赖版本

## 🛠️ 技术栈

- **前端**: Dash + Plotly + 现代CSS
- **后端**: Python Flask + Dash框架
- **数据处理**: pandas (优化版本)
- **数据库**: MySQL (通过 PyMySQL)
- **导出功能**: openpyxl (轻量级Excel处理)
- **部署**: Vercel 无服务器函数

## 🚀 快速部署到 Vercel

### 1. 准备工作

```bash
# 克隆项目
git clone https://github.com/stars3340/jobdata.git
cd jobdata

# 安装依赖
pip install -r requirements.txt
```

### 2. 环境配置

复制环境变量模板：
```bash
cp env.example .env
```

编辑 `.env` 文件，填入你的数据库配置：
```env
# 数据库配置 (示例 - 请替换为真实信息)
DB_HOST=your-database-host.example.com
DB_PORT=3306
DB_USER=your-db-username  
DB_PASSWORD=your-secure-password
DB_NAME=your-database-name
DB_CHARSET=utf8mb4
```

### 3. 部署到 Vercel

#### 方式一：通过 Vercel CLI
```bash
# 安装 Vercel CLI
npm i -g vercel

# 登录并部署
vercel login
vercel
```

#### 方式二：通过 GitHub 集成
1. 将代码推送到 GitHub
2. 在 [Vercel Dashboard](https://vercel.com/dashboard) 中导入项目
3. 配置环境变量
4. 部署完成

### 4. 环境变量配置

⚠️ **安全提醒**: 以下为示例值，请替换为您的真实数据库信息

在 Vercel 项目设置中添加以下环境变量：

| 变量名 | 描述 | 示例值 |
|--------|------|--------|
| `DB_HOST` | 数据库主机地址 | `your-database-host.example.com` |
| `DB_PORT` | 数据库端口 | `3306` |
| `DB_USER` | 数据库用户名 | `your-db-username` |
| `DB_PASSWORD` | 数据库密码 | `your-secure-password` |
| `DB_NAME` | 数据库名称 | `your-database-name` |
| `DB_CHARSET` | 字符编码 | `utf8mb4` |

🔐 **重要**: 这些环境变量只应在Vercel控制台中配置，切勿提交到代码仓库！

## 📁 项目结构

```
recruitment-dashboard/
├── api/                    # Vercel 无服务器函数
│   └── index.py           # 应用入口文件
├── assets/                # 静态资源
│   ├── style.css          # 样式文件
│   └── dashboard_enhancements.js  # JavaScript 增强
├── recruitment_dashboard.py    # 主应用文件
├── app.py                 # 本地开发入口
├── config.py              # 配置管理
├── requirements.txt       # Python 依赖
├── vercel.json           # Vercel 配置
├── env.example           # 环境变量模板
├── .gitignore            # Git 忽略文件
└── README.md             # 项目文档
```

## 🏃‍♂️ 本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp env.example .env
# 编辑 .env 文件

# 启动开发服务器
python app.py
```

访问 `http://localhost:8050` 查看应用。

## 📊 数据库要求

项目需要以下数据表：

- `recruit_event` - 招聘事件记录
- `user` - 用户信息
- `job` - 职位信息  
- `resume` - 简历信息

详细的数据库结构请参考项目中的数据分析脚本。

## 🔧 配置说明

### vercel.json 配置
```json
{
  "version": 2,
  "builds": [{"src": "api/index.py", "use": "@vercel/python"}],
  "routes": [{"src": "/(.*)", "dest": "/api/index.py"}]
}
```

### 环境变量说明
- 所有数据库配置都通过环境变量管理
- 支持本地开发和生产环境的不同配置
- 敏感信息不会被提交到代码仓库

## 🚨 注意事项

1. **数据库连接**: 确保数据库允许外网访问
2. **Vercel 限制**: 单个函数执行时间最长 60 秒
3. **🔐 安全考虑**: 
   - 生产环境中请使用强密码和 SSL 连接
   - **切勿在代码中硬编码数据库密码**
   - **不要在README或公开文档中暴露真实的环境变量**
   - 使用Vercel Environment Variables安全地管理敏感信息
4. **性能优化**: 大数据量时建议添加数据缓存

## 📈 功能说明

### 漏斗分析
- 查看简历 → 简历通过筛选 → Boss上聊天 → 交换联系方式
- 显示各阶段转化率和总体转化率

### 趋势分析  
- 按日期展示各类事件的变化趋势
- 支持多事件类型对比

### 数据导出
- Excel 格式：包含完整格式和样式
- CSV 格式：适合数据处理和分析

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## �� 许可证

MIT License 