# Render 部署指南

本文档说明如何将 GM China 新车舆情监控系统部署到 Render.com。

## 前置条件

- GitHub 账号，已将项目推送到 GitHub 仓库
- Render 账号（注册：https://render.com）
- 注意：Render API (api.render.com) 从中国网络无法访问，部署需通过网页 Dashboard 手动操作

## 部署架构

Render 部署采用三个服务：

1. **Backend (Web Service)** — Flask 后端，Docker 部署，监听 PORT 环境变量
2. **Frontend (Static Site)** — Vue3 前端，静态站点部署
3. **Database (PostgreSQL)** — Render 托管 PostgreSQL

## 步骤一：推送代码到 GitHub

```bash
cd gm-sentiment
git init
git add .
git commit -m "Initial commit: GM China sentiment monitoring system"
git remote add origin https://github.com/你的用户名/gm-sentiment.git
git push -u origin main
```

## 步骤二：创建 PostgreSQL 数据库

1. 登录 Render Dashboard → **New +** → **PostgreSQL**
2. 配置：
   - Name: `gm-sentiment-db`
   - Database: `gm_sentiment`
   - User: `gm_app`
   - Plan: Starter（或 Free 用于测试）
3. 创建后，在数据库详情页复制 **Internal Database URL**（格式：`postgresql://gm_app:xxx@gm-sentiment-db:5432/gm_sentiment`）

## 步骤三：部署后端

1. Dashboard → **New +** → **Web Service**
2. 连接 GitHub 仓库 `gm-sentiment`
3. 配置：
   - Name: `gm-sentiment-backend`
   - Root Directory: `backend`
   - Runtime: **Docker**
   - Plan: Starter
   - Health Check Path: `/api/dashboard/overview`
4. 环境变量（在 Environment 标签页添加）：
   - `FLASK_ENV` = `production`
   - `DATABASE_URL` = 步骤二复制的 Internal Database URL
   - `SECRET_KEY` = 随机字符串（可用 `python -c "import secrets; print(secrets.token_hex(32))"` 生成）
   - `JWT_SECRET_KEY` = 随机字符串
5. 点击 **Create Web Service**，等待构建完成

## 步骤四：部署前端

1. Dashboard → **New +** → **Static Site**
2. 连接同一 GitHub 仓库
3. 配置：
   - Name: `gm-sentiment-frontend`
   - Root Directory: `frontend`
   - Build Command: `npm install && npm run build`
   - Publish Directory: `dist`
4. 环境变量：
   - `VITE_API_BASE_URL` = `https://gm-sentiment-backend.onrender.com/api`（替换为步骤三部署后端的实际URL）
5. 添加路由规则（Rewrites/Routes 标签页）：
   - Source: `/*`
   - Destination: `/index.html`
   - 这是 SPA 单页应用必需的，确保前端路由正常工作
6. 点击 **Create Static Site**

## 步骤五：初始化数据库

后端部署成功后，需要初始化数据库表结构和种子数据。

方法一：通过 Render Shell（推荐）
1. 进入后端服务页 → **Shell** 标签页
2. 执行：
```bash
python seed_data.py
```

方法二：通过 API 触发（如已实现管理接口）

## 步骤六：验证部署

1. 访问前端 URL（如 `https://gm-sentiment-frontend.onrender.com`）
2. 检查 Dashboard 页面是否正常显示品牌卡片和图表
3. 检查 API 是否正常：`https://gm-sentiment-backend.onrender.com/api/dashboard/overview`

## 注意事项

### 网络问题
- Render API (api.render.com) 从中国网络无法访问，部署操作需通过网页 Dashboard 手动完成
- 部署后网站 URL 格式为 `https://服务名.onrender.com`，实际 URL 可能与 Service Name 不同，请在 Dashboard 确认

### 免费套餐限制
- Render Free 套餐服务会在 15 分钟无请求后休眠，首次访问需等待 30-60 秒唤醒
- PostgreSQL Free 套餐 90 天后数据会被清除，生产环境请使用 Starter 或以上套餐
- 建议配置 Uptime Robot 等外部监控服务定时 ping 后端，防止休眠

### 数据库迁移
如需修改数据库模型，使用 Flask-Migrate：
```bash
# 在 Render Shell 中执行
flask db migrate -m "描述变更"
flask db upgrade
```

### 定时抓取任务
后端内置 APScheduler 定时任务，会在每天 8:00/9:00/10:00/20:00/21:00/22:00 自动抓取各数据源。
注意：Render Free 套餐休眠时定时任务不会触发，建议使用 Starter 套餐或外部 Cron 服务。

### 前端 API 地址
前端通过 `VITE_API_BASE_URL` 环境变量指定后端 API 地址。部署后需要：
1. 在后端服务页复制其 URL
2. 在前端服务的环境变量中设置 `VITE_API_BASE_URL`
3. 重新部署前端（Dashboard → Manual Deploy → Deploy latest commit）

## 本地 Docker 部署（备选方案）

如果不使用 Render，也可通过 Docker Compose 在任意服务器部署：

```bash
# 克隆仓库
git clone https://github.com/你的用户名/gm-sentiment.git
cd gm-sentiment

# 启动服务
docker-compose up -d

# 初始化数据
docker-compose exec backend python seed_data.py

# 访问
# 前端: http://localhost
# 后端API: http://localhost:8000/api/
```

## 故障排查

| 问题 | 排查方法 |
|------|---------|
| 后端启动失败 | 查看 Render Logs 标签页的错误日志 |
| 数据库连接失败 | 确认 DATABASE_URL 使用的是 Internal Database URL |
| 前端页面空白 | 检查浏览器控制台错误，确认 VITE_API_BASE_URL 正确 |
| API 返回 404 | 确认后端 Health Check Path 设置为 `/api/dashboard/overview` |
| 中文乱码 | 确认数据库字符集为 UTF-8 (PostgreSQL 默认支持) |
