# 🎨 腾讯云 MySQL + Render 部署指南

> 📊 **专注数据展示** - 连接现有腾讯云 MySQL 数据库，零额外成本部署数据分析平台

## 🚀 部署概览

| 服务类型 | 平台 | 费用 | 权限 |
|---------|------|------|------|
| 应用托管 | Render | 免费 750 小时/月 | 完整控制 |
| 数据库 | 腾讯云 MySQL | 您现有的 | 只读权限 |
| 总成本 | - | **仅 Render 免费** | 专业数据展示 |

## 🎯 功能特色

### ✅ 支持的功能（只读模式）
- 📊 **招聘漏斗分析** - 查看简历→筛选→聊天→联系方式转化
- 📈 **趋势分析** - 每日活动趋势图表
- 🔍 **数据筛选** - 按日期、用户筛选
- 📋 **详细数据表** - 完整事件记录
- 📤 **数据导出** - Excel/CSV 格式导出
- 👥 **用户活动统计** - 个人和团队表现
- 📅 **时间范围分析** - 灵活的日期选择

### ❌ 不支持的功能（只读限制）
- 👤 新用户注册
- 📝 添加招聘事件
- ✏️ 编辑现有数据
- 🗑️ 删除数据

## 📋 详细部署步骤

### 第一步：准备腾讯云数据库信息

您需要准备以下腾讯云 MySQL 连接信息：

```bash
# 腾讯云数据库连接信息
DB_HOST=bj-cynosdbmysql-grp-5eypnf9y.sql.tencentcdb.com
DB_PORT=26606
DB_USER=root
DB_PASSWORD=Gn123456
DB_NAME=recruit-db
```

> 🔒 **安全提示**: 确认数据库用户只有 SELECT 权限，保护数据安全

### 第二步：验证数据库表结构

确保您的腾讯云数据库包含以下必要表结构：

```sql
-- 用户表
CREATE TABLE `user` (
  `id` varchar(50) PRIMARY KEY,
  `name` varchar(255) DEFAULT NULL,
  `email` varchar(255) DEFAULT NULL
);

-- 招聘事件表  
CREATE TABLE `recruit_event` (
  `id` varchar(50) PRIMARY KEY,
  `uid` varchar(50) DEFAULT NULL,
  `event_type` varchar(10) NOT NULL,
  `resume_id` varchar(255) DEFAULT NULL,
  `job_id` varchar(255) DEFAULT NULL,
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  KEY `idx_uid` (`uid`),
  KEY `idx_event_type` (`event_type`),
  KEY `idx_create_time` (`create_time`)
);
```

**事件类型映射**：
- `1` = 查看简历
- `2` = 简历通过筛选  
- `12` = Boss上聊天
- `13` = 交换联系方式

### 第三步：配置 Render Web 服务

1. **访问 Render 并创建服务**
   ```
   🔗 https://render.com/
   ```
   - 使用 GitHub 账户登录
   - 点击 "New +" → "Web Service"

2. **连接 GitHub 仓库**
   - 选择您的项目仓库
   - 点击 "Connect"

3. **配置服务设置**
   ```bash
   # 基本设置
   Name: recruitment-dashboard
   Region: Oregon (US West) 或选择离您最近的
   Branch: main
   
   # 运行时设置  
   Runtime: Python 3
   Build Command: pip install -r requirements.txt
   Start Command: gunicorn --bind 0.0.0.0:$PORT app:application
   
   # 实例类型
   Instance Type: Free
   ```

### 第四步：配置环境变量

在 Render 服务设置中添加以下环境变量：

```bash
# === 数据库配置（腾讯云 MySQL）===
DB_TYPE=mysql
DB_HOST=bj-cynosdbmysql-grp-5eypnf9y.sql.tencentcdb.com
DB_PORT=26606
DB_USER=root
DB_PASSWORD=Gn123456
DB_NAME=recruit-db
DB_CHARSET=utf8mb4

# === 应用配置 ===
APP_NAME=智能招聘数据分析平台
APP_HOST=0.0.0.0
APP_DEBUG=False
SECRET_KEY=gVNzFUEw6JG3UjgXsDQIP8EOhw2VYc8CxhhPIk41VT8

# === 日志配置 ===
LOG_LEVEL=INFO
LOG_FILE=logs/app.log

# === 缓存配置 ===
CACHE_TYPE=simple
CACHE_DEFAULT_TIMEOUT=300
```

> 🔒 **安全提示**: 已配置您的腾讯云数据库信息，**严格只读模式** - 绝不进行增删改操作！

### 第五步：部署验证

1. **启动部署**
   - 配置完成后，点击 "Create Web Service"
   - Render 自动开始构建部署

2. **验证部署成功**
   ```bash
   # 应用访问地址
   https://recruitment-dashboard.onrender.com
   
   # 健康检查端点
   https://recruitment-dashboard.onrender.com/health
   
   # 预期返回
   {
     "status": "healthy",
     "timestamp": "2025-01-27T10:30:00",
     "version": "1.0.0"
   }
   ```

3. **功能验证清单**
   - [ ] 主页面正常加载
   - [ ] 招聘漏斗图正常显示
   - [ ] 趋势图表正常显示  
   - [ ] 数据筛选功能正常
   - [ ] 详细数据表显示
   - [ ] Excel/CSV 导出功能正常

## 🔧 性能优化

### 数据库查询优化

由于是只读数据库，重点优化查询性能：

```python
# 1. 使用索引字段进行筛选
WHERE create_time BETWEEN '2025-01-01' AND '2025-01-31'
WHERE uid = 'specific_user_id'
WHERE event_type IN ('1', '2', '12', '13')

# 2. 限制查询结果数量
LIMIT 1000

# 3. 避免全表扫描
# ❌ 避免
SELECT * FROM recruit_event WHERE resume_id LIKE '%test%'

# ✅ 推荐  
SELECT * FROM recruit_event WHERE uid = 'user123' AND create_time >= '2025-01-01'
```

### 应用层缓存

```python
# 配置缓存（已在环境变量中设置）
CACHE_TYPE=simple
CACHE_DEFAULT_TIMEOUT=300  # 5分钟缓存

# 缓存策略
- 用户列表缓存 10 分钟
- 统计数据缓存 5 分钟  
- 详细数据不缓存（保证实时性）
```

## 🎯 防止自动休眠

Render 免费服务 15 分钟无活动后休眠，使用以下方法保持活跃：

### 方案一：UptimeRobot 监控（推荐）

1. **注册 UptimeRobot**
   ```
   🔗 https://uptimerobot.com/
   ```

2. **创建监控**
   - Monitor Type: HTTP(s)
   - Friendly Name: 招聘数据分析平台
   - URL: `https://recruitment-dashboard.onrender.com/health`
   - Monitoring Interval: 5 minutes

### 方案二：GitHub Actions 定时任务

创建 `.github/workflows/keep-alive.yml`：

```yaml
name: Keep Alive
on:
  schedule:
    - cron: '*/10 * * * *'  # 每10分钟执行
  workflow_dispatch:

jobs:
  keep-alive:
    runs-on: ubuntu-latest
    steps:
      - name: Keep app alive
        run: |
          curl -f https://recruitment-dashboard.onrender.com/health || exit 1
```

## 📊 监控和维护

### 数据库性能监控

定期检查查询性能（在腾讯云控制台）：

```sql
-- 检查慢查询日志
-- 分析最频繁的查询
-- 验证索引使用情况
```

### 应用性能监控

在 Render 控制台监控：

- **Metrics**: CPU、内存使用率
- **Logs**: 应用运行日志  
- **Events**: 部署和重启事件

## 🚨 故障排除

### 常见问题及解决方案

#### 1. 数据库连接失败

**症状**：
```
pymysql.err.OperationalError: (2003, "Can't connect to MySQL server")
```

**解决方案**：
```bash
# 检查项目
1. 验证腾讯云数据库安全组设置
2. 确认 DB_HOST 地址正确
3. 检查用户名密码是否正确
4. 验证数据库名是否存在
```

#### 2. 查询权限不足

**症状**：
```
pymysql.err.ProgrammingError: (1142, "SELECT command denied to user")
```

**解决方案**：
```sql
-- 联系数据库管理员授予 SELECT 权限
GRANT SELECT ON database_name.* TO 'username'@'%';
FLUSH PRIVILEGES;
```

#### 3. 应用加载慢

**症状**：页面加载时间超过 10 秒

**解决方案**：
```python
# 1. 优化查询，添加索引
# 2. 增加缓存时间
# 3. 限制查询数据量
# 4. 使用 UptimeRobot 防止休眠
```

#### 4. 图表不显示数据

**症状**：页面正常但图表为空

**解决方案**：
```python
# 检查数据格式
1. 验证 event_type 字段值（1,2,12,13）
2. 检查 create_time 字段格式
3. 确认表中有数据且时间范围正确
```

## 🎉 部署成功

恭喜！您的智能招聘数据分析平台已成功部署到 Render，并连接到腾讯云 MySQL 数据库。

**访问地址**: `https://recruitment-dashboard.onrender.com`

### 后续操作建议

1. **设置监控**: 配置 UptimeRobot 防止休眠
2. **性能调优**: 根据实际使用情况优化查询
3. **数据备份**: 建议定期备份重要数据（如有权限）
4. **用户培训**: 向团队成员展示如何使用分析功能

**享受您的零成本数据分析平台！** 📊✨ 