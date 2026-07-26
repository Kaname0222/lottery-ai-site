#!/bin/bash
set -e

# 服务器初始化脚本
# 在全新的 Ubuntu 22.04/24.04 服务器上以 root 或 sudo 用户执行

echo "=== 1. 更新系统 ==="
sudo apt-get update
sudo apt-get upgrade -y

echo "=== 2. 安装必要工具 ==="
sudo apt-get install -y curl gnupg ca-certificates lsb-release git

echo "=== 3. 安装 Docker ==="
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

echo "=== 4. 将当前用户加入 docker 组 ==="
sudo usermod -aG docker "$USER" || true

echo "=== 5. 启用 Docker 自启 ==="
sudo systemctl enable docker
sudo systemctl start docker

echo "=== 6. 配置防火墙（Oracle Cloud 安全组也要放行 80/443） ==="
if command -v ufw &> /dev/null; then
    sudo ufw allow 22/tcp
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp
    sudo ufw --force enable
fi

echo "=== 服务器初始化完成 ==="
echo "请重新登录或执行 'newgrp docker' 以应用 docker 组权限"
