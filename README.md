# 体彩竞彩 AI 比分预测网站

自动抓取中国体彩竞彩足球每日开售赛程，调用 GPT、Gemini、DeepSeek、Kimi、豆包五家大模型对每场比赛输出两条比分预测及操盘分析，并根据赛后实际比分对 AI 进行积分排名。

## 主要功能

- 每日定时抓取体彩竞彩足球赛程与赔率
- 五家大模型并发预测，每家输出两条最可能比分
- 展示预测理由与操盘原因分析
- 赛后自动/手动回填比分，对 AI 进行评分与排名
- 响应式 Web 仪表盘

## 目录结构

```
lottery-ai-site/
├── backend/           FastAPI + SQLAlchemy + APScheduler
├── frontend/          React 18 + Vite + TailwindCSS
├── docker-compose.yml
└── README.md
```

## 快速开始（本地开发）

### 1. 后端

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env，填入你的 LLM API Keys
uvicorn app.main:app --reload
```

### 2. 前端

```bash
cd frontend
npm install
npm run dev
```

打开浏览器访问 http://localhost:5173。

## Docker Compose 部署

```bash
cd lottery-ai-site
cp backend/.env.example backend/.env
# 编辑 backend/.env 填入 API Keys
docker-compose up --build -d
```

访问 http://localhost 即可。

## API 说明

- `GET /health` 健康检查
- `GET /dashboard/today` 今日概览与排行榜
- `GET /matches` 比赛列表
- `GET /matches/{match_id}` 比赛详情与预测
- `POST /matches/{match_id}/result?home_score=&away_score=` 回填比分并评分
- `GET /providers/leaderboard` AI 排行榜
- `POST /admin/run-scrape` 手动触发抓取
- `POST /admin/run-predictions` 手动触发预测
- `POST /admin/run-scoring` 手动触发评分

## 申请 LLM API Key

- OpenAI GPT：https://platform.openai.com/
- Google Gemini：https://aistudio.google.com/
- DeepSeek：https://platform.deepseek.com/
- Moonshot Kimi：https://platform.moonshot.cn/
- 豆包/火山方舟：https://www.volcengine.com/product/doubao

## 免责声明

本站所有 AI 预测仅供娱乐与研究，不构成任何投注建议。竞彩足球存在风险，请理性对待。

## 注意事项

1. 体彩官网页面结构可能变化，如爬虫解析失败请检查 `backend/app/services/scraper/parser.py`。
2. 建议控制抓取频率，遵守目标网站的使用条款。
3. 生产环境请妥善保管 `.env` 文件，不要提交到代码仓库。
