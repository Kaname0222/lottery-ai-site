#!/bin/bash
set -e

# 生产部署脚本
# 在服务器上项目根目录执行
# 用法：./deploy.sh <邮箱> <域名>
# 示例：./deploy.sh admin@kanamesoccer.site kanamesoccer.site

EMAIL=${1:-admin@kanamesoccer.site}
DOMAIN=${2:-kanamesoccer.site}

echo "=== 1. 拉取最新代码 ==="
git pull origin main 2>/dev/null || echo "未配置 git remote，跳过"

echo "=== 2. 构建前端 ==="
cd frontend
npm install
npm run build
cd ..

echo "=== 3. 检查环境变量 ==="
if [ ! -f backend/.env ]; then
    echo "错误：backend/.env 不存在，请先复制 backend/.env.example 并填写 API Keys"
    exit 1
fi

echo "=== 4. 启动数据库和后端 ==="
docker compose -f docker-compose.prod.yml up -d db backend

echo "=== 5. 初始化数据库 ==="
sleep 5
docker compose -f docker-compose.prod.yml exec -T backend python - <<'PY'
import asyncio
from app.database import init_db
asyncio.run(init_db())
PY

echo "=== 6. 申请/更新 SSL 证书并启动 nginx ==="
chmod +x init-letsencrypt.sh
./init-letsencrypt.sh "$EMAIL" "$DOMAIN"

echo "=== 7. 检查健康状态 ==="
sleep 3
curl -fsS https://$DOMAIN/api/health || echo "健康检查失败，请检查 nginx 和证书"

echo "=== 部署完成：https://$DOMAIN ==="
