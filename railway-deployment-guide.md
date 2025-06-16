# Railway 部署详细教程

## 🎯 环境变量配置清单

### 必需的环境变量
```bash
# 数据库配置
DB_TYPE=postgresql
DB_HOST=containers-us-west-xxx.railway.app
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your-database-password
DB_NAME=railway
DB_CHARSET=utf8mb4

# 或者直接使用 Railway 提供的 DATABASE_URL
DATABASE_URL=postgresql://postgres:password@host:5432/railway

# 应用配置
APP_HOST=0.0.0.0
APP_PORT=8050
APP_DEBUG=False
SECRET_KEY=your-super-secret-key-change-this

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=logs/app.log

# 缓存配置
CACHE_TYPE=simple
CACHE_DEFAULT_TIMEOUT=300
```

### 可选的环境变量
```bash
# 应用名称
APP_NAME=智能招聘数据分析平台

# SSL 配置（Railway 自动处理，一般不需要设置）
DB_SSLMODE=require
```

## 🔧 部署配置说明

### railway.json 配置解析
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS",
    "buildCommand": "pip install -r requirements-railway.txt"
  },
  "deploy": {
    "startCommand": "gunicorn --bind 0.0.0.0:$PORT app:application",
    "healthcheckPath": "/health"
  }
}
```

### 依赖文件说明
- `requirements-railway.txt` - 包含PostgreSQL支持的完整依赖
- `db_adapter.py` - 支持多种数据库的适配器
- `app.py` - 生产环境入口文件

## 📊 数据库初始化

### 创建数据表结构
```sql
-- 用户表
CREATE TABLE user (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    email VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 工作表
CREATE TABLE job (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    company VARCHAR(255),
    location VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 简历表
CREATE TABLE resume (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES user(id),
    job_id INTEGER REFERENCES job(id),
    status VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 招聘事件表
CREATE TABLE recruit_event (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES user(id),
    job_id INTEGER REFERENCES job(id),
    event_type VARCHAR(100) NOT NULL,
    event_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    details TEXT
);
```

## 🚀 部署流程检查清单

### 部署前检查
- [ ] GitHub代码已推送最新版本
- [ ] `railway.json` 配置文件存在
- [ ] `requirements-railway.txt` 包含所有依赖
- [ ] `db_adapter.py` 支持PostgreSQL

### 部署过程检查
- [ ] Railway项目创建成功
- [ ] PostgreSQL数据库已添加
- [ ] 环境变量配置完整
- [ ] 应用服务部署中

### 部署后验证
- [ ] 访问应用URL正常
- [ ] 健康检查 `/health` 返回200
- [ ] 数据库连接正常
- [ ] 日志无错误信息

## 🔍 故障排除

### 常见问题及解决方案

#### 1. 应用启动失败
```bash
# 检查部署日志
- 访问 Railway项目 → 应用服务 → Deployments
- 查看最新部署的日志输出
- 检查环境变量是否设置正确
```

#### 2. 数据库连接失败
```bash
# 验证数据库配置
- 确认 DB_HOST、DB_PORT、DB_USER、DB_PASSWORD 正确
- 检查 DATABASE_URL 格式是否正确
- 确认数据库服务状态正常
```

#### 3. 依赖安装失败
```bash
# 检查依赖文件
- 确认 requirements-railway.txt 存在
- 检查依赖版本是否兼容
- 查看构建日志中的错误信息
```

#### 4. 端口绑定问题
```bash
# Railway 自动分配端口
- 确保使用 $PORT 环境变量
- startCommand 中使用: --bind 0.0.0.0:$PORT
```

## 📈 性能优化建议

### 1. 数据库优化
```sql
-- 添加索引提升查询性能
CREATE INDEX idx_recruit_event_date ON recruit_event(event_date);
CREATE INDEX idx_recruit_event_type ON recruit_event(event_type);
CREATE INDEX idx_user_id ON recruit_event(user_id);
```

### 2. 缓存配置
```python
# 在应用中启用缓存
CACHE_TYPE=simple
CACHE_DEFAULT_TIMEOUT=300
```

### 3. 日志管理
```python
# 设置合适的日志级别
LOG_LEVEL=INFO  # 生产环境推荐
# LOG_LEVEL=DEBUG  # 开发调试时使用
```

## 💰 Railway 免费额度说明

### 免费计划限制
- **运行时间**: 500小时/月（约21天持续运行）
- **内存**: 512MB RAM
- **CPU**: 共享CPU
- **存储**: 1GB
- **数据库**: PostgreSQL 100MB
- **带宽**: 100GB/月

### 超出免费额度
- **Hobby Plan**: $5/月，无限运行时间
- **Pro Plan**: $20/月，更多资源和功能

## 🔒 安全注意事项

### 1. 环境变量安全
- 使用强密码作为 SECRET_KEY
- 不要在代码中硬编码敏感信息
- 定期更换数据库密码

### 2. 数据库安全
- 启用SSL连接（Railway默认启用）
- 限制数据库访问权限
- 定期备份重要数据

### 3. 应用安全
- 启用HTTPS（Railway自动提供）
- 设置适当的CORS策略
- 实施输入验证和SQL注入防护 