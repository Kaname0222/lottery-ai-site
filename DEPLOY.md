# 生产部署指南

目标：把项目**免费**部署到域名 `kanamesoccer.site`，使用 HTTPS，**不需要国际信用卡**。

---

## 推荐方案 B：Vercel + Render + Supabase + GitHub Actions

### 架构说明

| 组件 | 平台 | 作用 | 费用 |
|------|------|------|------|
| 前端静态站点 | **Vercel** | 托管 React 构建产物 | 免费 |
| 后端 API | **Render** | 运行 FastAPI | 免费（512MB RAM） |
| 数据库 | **Supabase** | PostgreSQL | 免费（长期） |
| 定时爬虫 | **GitHub Actions** | 每天两次抓取赛程/赔率/赛果并评分 | 免费 |

**为什么这样拆分？**

- Render 免费实例只有 **512MB 内存**，跑 **Playwright + Chromium** 会 OOM。因此后端只负责 API。
- GitHub Actions runner 有 **2 核 CPU + 7GB 内存**，跑爬虫很轻松。
- Supabase 免费 PostgreSQL **长期有效**，避免 Render 免费 Postgres 30 天过期删数据的问题。

---

## 前置准备

你需要注册以下账号（都不需要信用卡）：

1. **GitHub**：https://github.com/signup
2. **Render**：https://dashboard.render.com/register（用 GitHub 登录）
3. **Vercel**：https://vercel.com/signup（用 GitHub 登录）
4. **Supabase**：https://supabase.com/（用 GitHub 登录）

然后把本项目代码推送到你的 GitHub 仓库。

---

## 步骤 1：创建 Supabase 数据库

1. 登录 https://supabase.com/dashboard
2. 点击 **New project**
3. 填写 Project name，例如 `lottery-ai`
4. **Region** 建议选择 **Singapore** 或 **Tokyo**（离中国近，延迟低）
5. 等待项目创建完成（约 1-2 分钟）
6. 进入左侧 **Project Settings → Database**
7. 在 **Connection string** 区域选择 **URI** 格式，复制连接串
8. 把连接串中的 `postgresql://` 改成 **`postgresql+asyncpg://`**，例如：

```text
postgresql+asyncpg://postgres.xxxxxxx:xxxxxxxxxxxx@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require
```

这个字符串就是 `DATABASE_URL`，后面会用到。

---

## 步骤 2：配置 GitHub Secrets

爬虫脚本会从 GitHub Secrets 读取数据库地址。

1. 打开 GitHub 仓库 → **Settings → Secrets and variables → Actions**
2. 点击 **New repository secret**
3. 添加：
   - **Name**: `DATABASE_URL`
   - **Secret**: 上面复制好的 Supabase URI（`postgresql+asyncpg://...`）
4. （可选）如果 GitHub Actions 访问体彩网站需要代理，再添加：
   - `HTTP_PROXY`
   - `HTTPS_PROXY`

> 添加后，工作流 `.github/workflows/scraper.yml` 会在每天北京时间 09:00 和 16:00 自动运行爬虫。

---

## 步骤 3：部署后端到 Render

### 通过 Blueprint 一键部署

1. 把代码推送到 GitHub 后，打开 Render Dashboard
2. 点击 **New → Blueprint**
3. 选择你的 GitHub 仓库
4. Render 会自动读取根目录的 [`render.yaml`](render.yaml)
5. 点击 **Apply**
6. 在环境变量确认页面，找到 `DATABASE_URL`，填入 Supabase URI
7. 等待部署完成，记下后端域名，例如：
   ```
   https://lottery-backend-xxxx.onrender.com
   ```

### 如果没有 Blueprint 选项，手动部署

1. Render Dashboard → **New → Web Service**
2. 选择 GitHub 仓库
3. 配置：
   - **Name**: `lottery-backend`
   - **Runtime**: `Docker`
   - **Root Directory**: `backend`
   - **Dockerfile Path**: `./Dockerfile.render`
   - **Branch**: `main`
   - **Instance Type**: `Free`
4. 环境变量：
   - `APP_ENV` = `production`
   - `LOG_LEVEL` = `INFO`
   - `SCHEDULED_PIPELINE_ENABLED` = `false`
   - `DATABASE_URL` = Supabase URI
   - LLM Keys 全部留空（你之前说不用 LLM）
5. 点击 **Create Web Service**

### 验证后端

部署完成后访问：

```text
https://lottery-backend-xxxx.onrender.com/health
```

应返回：

```json
{"status":"ok"}
```

---

## 步骤 4：部署前端到 Vercel

1. 打开 https://vercel.com/new
2. 选择你的 GitHub 仓库
3. 配置：
   - **Framework Preset**: Vite
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. 环境变量：
   - **Name**: `VITE_API_BASE_URL`
   - **Value**: 你的 Render 后端域名，例如 `https://lottery-backend-xxxx.onrender.com`
5. 点击 **Deploy**

---

## 步骤 5：绑定自定义域名 `kanamesoccer.site`

1. 进入 Vercel 项目 → **Settings → Domains**
2. 添加 `kanamesoccer.site`
3. Vercel 会提示你需要添加的 DNS 记录，通常 apex 域名用 **A 记录**，`www` 用 **CNAME**
4. 登录你的域名注册商控制台，按 Vercel 提示添加 DNS 记录
5. 等待 DNS 生效（通常几分钟到几小时）
6. Vercel 会自动申请并续期 HTTPS 证书

> Render 后端不需要绑定自定义域名，前端通过 `VITE_API_BASE_URL` 直接调用 Render 的 `.onrender.com` 域名即可。

---

## 步骤 6：验证完整流程

1. 打开 `https://kanamesoccer.site`，确认页面能加载
2. 打开浏览器开发者工具 → Network，确认前端成功请求了后端 API
3. 在 GitHub 仓库 → **Actions** 标签，手动触发一次 `Scraper Pipeline`，确认爬虫成功写入数据
4. 刷新网站，检查比赛数据是否出现

---

## 文件说明

- [`backend/Dockerfile.render`](backend/Dockerfile.render)：Render 后端使用的轻量 Dockerfile（不安装 Chromium）
- [`render.yaml`](render.yaml)：Render Blueprint 配置文件
- [`frontend/vercel.json`](frontend/vercel.json)：Vercel 构建配置
- [`frontend/.env.example`](frontend/.env.example)：前端环境变量示例
- [`.github/workflows/scraper.yml`](.github/workflows/scraper.yml)：GitHub Actions 定时爬虫
- [`backend/scripts/run_scraper.py`](backend/scripts/run_scraper.py)：爬虫执行脚本

---

## 运维与调试

### 手动触发爬虫

进入 GitHub 仓库 → **Actions → Scraper Pipeline → Run workflow**。

### 查看爬虫日志

在 Actions 运行详情页查看实时日志。

### 查看后端日志

Render Dashboard → 选择 `lottery-backend` → **Logs**。

### 数据库管理

Supabase Dashboard → **Table Editor**，可以直接查看/编辑 `matches`、`predictions` 等表。

### 本地测试后端

```bash
cd backend
cp .env.example .env
# 修改 .env 中的 DATABASE_URL
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 本地测试前端

```bash
cd frontend
cp .env.example .env
# 修改 VITE_API_BASE_URL 为本地后端地址
npm install
npm run dev
```

---

## 备选方案

### 方案 A：全部放在 Render（最简单，但有隐患）

如果你不想用 Vercel + Supabase + GitHub Actions，也可以：

- 前端：Render Static Site
- 后端：Render Web Service
- 数据库：Render PostgreSQL（**30 天后过期，数据会删除**）
- 爬虫：后端内置定时任务（**512MB 内存容易 OOM**）

此方案配置更少，但生产稳定性差，只建议临时测试。

### Oracle Cloud（最稳定，但需要信用卡）

如果你能解决 Visa/Mastercard 信用卡验证，Oracle Cloud 永久免费服务器仍是最佳方案：

- 2 OCPU + 12GB 内存 ARM 实例
- 不休眠、不关机
- 用本项目已有的 `docker-compose.prod.yml` + `deploy.sh` 一键部署

具体步骤见仓库内的 [`docker-compose.prod.yml`](docker-compose.prod.yml)、[`deploy.sh`](deploy.sh) 和 [`nginx/nginx.prod.conf`](nginx/nginx.prod.conf)。

---

## 下一步需要你做的

请完成以下任意一种方式，把账号/仓库授权给我，我来帮你执行剩余部署：

1. **推荐**：把代码推送到你的 GitHub 仓库，加我为协作者（Collaborator），并把 Render / Vercel / Supabase 的登录方式或团队邀请发给我。
2. 你自己按上面步骤操作，遇到报错把日志贴给我，我远程帮你排查。

如果你现在就把仓库链接和平台账号信息发给我，我可以直接开始部署。
