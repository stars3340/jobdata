# 🔺 Vercel + PlanetScale 部署指南

> ⭐ **最推荐的方案** - 项目已配置完整，一键部署

## 🚀 5分钟快速部署

### 第一步：部署到Vercel

1. **访问Vercel**
   ```
   🔗 https://vercel.com/
   ```

2. **导入项目**
   - 点击 "New Project"
   - 选择 `jobdata` GitHub仓库
   - 点击 "Import"

3. **自动检测配置**
   - Vercel会自动检测到 `vercel.json`
   - 自动配置Python运行时
   - 无需手动配置构建命令

### 第二步：配置PlanetScale数据库

1. **注册PlanetScale**
   ```
   🔗 https://planetscale.com/
   ```

2. **创建数据库**
   - 点击 "New database"
   - 数据库名称：`recruitment-db`
   - 区域选择：`AWS us-east-1`（与Vercel同区域）

3. **获取连接字符串**
   - 进入数据库 → "Connect"
   - 选择 "Prisma" 或 "General"
   - 复制连接信息

### 第三步：配置Vercel环境变量

在Vercel项目设置中添加以下环境变量：

```bash
# === 数据库配置 ===
DB_TYPE=mysql
DB_HOST=aws.connect.psdb.cloud
DB_PORT=3306
DB_USER=your-username
DB_PASSWORD=pscale_pw_xxxxx
DB_NAME=recruitment-db
DB_CHARSET=utf8mb4

# === 应用配置 ===
APP_DEBUG=False
SECRET_KEY=your-secret-key
LOG_LEVEL=INFO

# PlanetScale专用
DATABASE_URL=mysql://user:password@host/database?sslaccept=strict
```

## 💰 完全免费额度

### Vercel免费计划
- **函数调用**: 100GB-Hrs/月
- **带宽**: 100GB/月  
- **构建时间**: 6000分钟/月
- **域名**: 免费 .vercel.app 子域名
- **HTTPS**: 自动SSL证书

### PlanetScale免费计划  
- **存储**: 10GB
- **行读取**: 10亿行/月
- **行写入**: 1000万行/月
- **连接数**: 1000个/月

## 🎯 技术优势

### Vercel优势
✅ **全球CDN** - 亚毫秒级响应  
✅ **自动扩展** - 零配置负载均衡  
✅ **Git集成** - 推送即部署  
✅ **预览部署** - 每个PR自动生成预览  

### PlanetScale优势  
✅ **MySQL兼容** - 无需修改现有代码  
✅ **分支功能** - 数据库版本控制  
✅ **自动备份** - 35天数据保护  
✅ **全球分布** - 低延迟访问  

## 🔧 数据库设置

### 创建数据表
```sql
-- 在PlanetScale控制台中执行
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE job (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    company VARCHAR(255),
    location VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE recruit_event (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    job_id INT,
    event_type VARCHAR(100) NOT NULL,
    event_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    details TEXT,
    INDEX idx_event_date (event_date),
    INDEX idx_event_type (event_type)
);
```

## 🚀 部署后验证

### 检查清单
- [ ] Vercel部署成功（绿色状态）
- [ ] 自定义域名可访问（如 `https://your-app.vercel.app`）
- [ ] 健康检查正常（`/health` 端点）
- [ ] PlanetScale数据库连接成功
- [ ] 应用功能正常运行

### 性能监控
- **响应时间**: < 100ms（全球CDN）
- **冷启动**: < 1s（Vercel Functions）
- **数据库查询**: < 50ms（PlanetScale）
- **可用性**: 99.99%（两个平台都有高可用性保证）

## 🛠 故障排除

### 常见问题

1. **Vercel函数超时**
   - 免费计划限制10s执行时间
   - 优化数据查询，添加缓存

2. **PlanetScale连接限制**
   - 检查连接数使用情况
   - 优化连接池配置

3. **环境变量问题**
   - 确认在Vercel设置中配置了所有变量
   - 重新部署以应用新的环境变量

## 🌟 最佳实践

### 性能优化
```python
# 启用连接池
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20

# 查询优化
# 使用索引加速常用查询
# 避免 SELECT * 查询
```

### 安全设置
```python
# 强制HTTPS
FORCE_HTTPS=True

# 安全密钥
SECRET_KEY=使用强随机字符串

# 数据库SSL
DB_SSL=True
```

## 🔗 有用链接

- [Vercel文档](https://vercel.com/docs)
- [PlanetScale文档](https://planetscale.com/docs)
- [MySQL连接指南](https://planetscale.com/docs/tutorials/connect-any-application)

---

## 💡 为什么选择这个方案？

1. **项目已配置** - `vercel.json` 和 `api/index.py` 已就绪
2. **MySQL兼容** - PlanetScale与现有PyMySQL代码完全兼容  
3. **性能最佳** - 全球CDN + 高性能数据库
4. **免费额度充足** - 个人项目完全够用
5. **企业级稳定性** - Vercel和PlanetScale都是知名平台 