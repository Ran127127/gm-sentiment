# GM China 新车舆情监控系统 - 部署指南

## 快速开始（本地开发）

### 环境要求
- Python 3.10+
- Node.js 18+
- MySQL 8.0（可选，开发环境默认用SQLite）

### 后端启动

```bash
cd backend

# 创建虚拟环境
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
# source venv/bin/activate

# 安装依赖（国内镜像加速）
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

# 复制环境配置
cp .env.example .env

# 初始化种子数据（自动创建数据库表 + 生成30天Mock数据）
python seed_data.py

# 启动开发服务器
python wsgi.py
# 后端运行在 http://localhost:5000
```

### 前端启动

```bash
cd frontend

# 安装依赖（淘宝镜像加速）
npm install --registry=https://registry.npmmirror.com

# 启动开发服务器（自动代理API到后端）
npm run dev
# 前端运行在 http://localhost:3000
```

### 访问系统
- 打开浏览器访问 http://localhost:3000
- 默认管理员账号：admin / gm2026

---

## Docker一键部署

```bash
# 在项目根目录执行
docker-compose up -d

# 等待MySQL启动完成后，初始化数据
docker-compose exec backend python seed_data.py
```

访问 http://localhost 即可使用。

---

## 云服务器部署（阿里云/腾讯云）

### 1. 购买服务器
- 推荐：阿里云ECS 2核4G（学生价约99元/年）
- 系统：Ubuntu 22.04

### 2. 环境安装

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 安装Docker Compose
sudo apt install docker-compose-plugin -y

# 安装MySQL客户端（可选，用于调试）
sudo apt install mysql-client -y
```

### 3. 部署项目

```bash
# 上传项目到服务器
scp -r gm-sentiment/ root@your-server:/opt/

# SSH登录服务器
ssh root@your-server

cd /opt/gm-sentiment

# 启动服务
docker compose up -d

# 初始化数据
docker compose exec backend python seed_data.py
```

### 4. 配置域名（可选）

```bash
# 安装Certbot（免费SSL证书）
sudo apt install certbot python3-certbot-nginx -y

# 申请证书
sudo certbot --nginx -d your-domain.cn
```

### 5. ICP备案
- 在中国大陆使用域名访问网站需要ICP备案
- 通过阿里云/腾讯云控制台提交备案申请
- 备案期间可通过IP地址直接访问
- 备案通常需要1-2周

---

## 项目架构

```
gm-sentiment/
├── backend/           # Flask后端
│   ├── app/           # 应用核心
│   │   ├── api/       # REST API接口
│   │   ├── models/    # 数据库模型
│   │   └── utils/     # 工具函数
│   ├── scraper/       # 数据抓取管道
│   ├── sentiment/     # 情感分析引擎
│   ├── seed_data.py   # 种子数据初始化
│   └── wsgi.py        # 应用入口
├── frontend/          # Vue3前端
│   ├── src/
│   │   ├── api/       # API请求模块
│   │   ├── views/     # 页面组件
│   │   └── router/    # 路由配置
│   └── nginx.conf     # Nginx配置
├── docker-compose.yml # Docker编排
└── docs/              # 文档
```

## API接口说明

| 接口 | 方法 | 说明 |
|------|------|------|
| /api/dashboard/overview | GET | 全局概览（三品牌摘要卡片） |
| /api/dashboard/sentiment-trend | GET | 情感趋势折线图 |
| /api/dashboard/source-distribution | GET | 平台数据分布饼图 |
| /api/dashboard/keyword-cloud | GET | 关键词词云 |
| /api/dashboard/model-comparison | GET | 车型维度雷达图 |
| /api/dashboard/hot-articles | GET | 热门文章TOP10 |
| /api/brands | GET | 品牌列表 |
| /api/brands/:id/models | GET | 品牌下车型列表 |
| /api/brands/:id/summary | GET | 品牌舆情摘要 |
| /api/sentiment/articles | GET | 文章列表（分页+筛选） |
| /api/sentiment/articles/:id | GET | 文章详情+评论 |
| /api/sentiment/aspect-analysis | GET | 维度情感分析 |
| /api/recommendations | GET | 智能建议列表 |
| /api/auth/login | POST | 管理员登录 |

## 数据抓取扩展

当前汽车垂直媒体抓取器框架已搭建，实际抓取逻辑需根据目标网站的HTML结构实现：

```python
# scraper/autohome.py
class AutohomeScraper(BaseScraper):
    def scrape(self, **kwargs):
        # 1. 请求搜索API: https://so.autohome.com.cn/article?keyword=别克
        # 2. BeautifulSoup解析结果列表
        # 3. 逐篇获取文章详情
        # 4. 提取评论
        pass
```

社交媒体（微博、小红书、抖音）建议接入第三方数据API（新榜、清博等）。

## 常见问题

**Q: 前端页面空白？**
A: 检查后端是否启动，前端代理配置是否指向正确的后端地址。

**Q: 种子数据运行报错？**
A: 确保已安装所有Python依赖，SQLite开发环境无需额外配置。

**Q: Docker构建失败？**
A: 检查网络连接，pip/npm使用了国内镜像源。
