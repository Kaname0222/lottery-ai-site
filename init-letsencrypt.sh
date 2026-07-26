#!/bin/bash

# 申请/续期 Let's Encrypt 证书
# 用法：./init-letsencrypt.sh <邮箱> <域名>
# 示例：./init-letsencrypt.sh admin@kanamesoccer.site kanamesoccer.site

set -e

EMAIL=$1
DOMAIN=$2

if [ -z "$EMAIL" ] || [ -z "$DOMAIN" ]; then
    echo "Usage: $0 <email> <domain>"
    exit 1
fi

# 停止可能占用 80 端口的容器
docker compose -f docker-compose.prod.yml stop nginx 2>/dev/null || true

# 申请证书（standalone 模式，占用 80 端口完成验证）
docker run -it --rm \
    -v lottery-ai-site_certbot_data:/etc/letsencrypt \
    -p 80:80 \
    certbot/certbot certonly \
    --standalone \
    --preferred-challenges http \
    --agree-tos \
    --no-eff-email \
    -m "$EMAIL" \
    -d "$DOMAIN" \
    -d "www.$DOMAIN"

# 启动/重启 nginx 以加载证书
docker compose -f docker-compose.prod.yml up -d nginx
docker compose -f docker-compose.prod.yml restart nginx

echo "SSL certificate initialized for $DOMAIN"
