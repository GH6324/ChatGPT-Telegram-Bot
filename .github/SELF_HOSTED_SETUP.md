# Self-Hosted Runner Deployment Guide

## 概述

本 GitHub Actions workflow 在 self-hosted runner 上自动构建 Docker 镜像并启动 `chatgpt-telegram-bot` 容器。

## 工作流程

1. **检查代码** - Checkout 最新代码
2. **创建配置文件** - 从 GitHub Secrets 读取 `CONFIG_YAML` 并创建 `config.yaml`
3. **构建镜像** - 使用 `docker build` 构建本地镜像（标签: `chatgpt-telegram-bot:latest`）
4. **停止旧容器** - 如果存在同名容器，先停止并删除
5. **启动新容器** - 启动新容器，挂载 `config.yaml` 配置文件
6. **验证** - 检查容器是否成功运行

## 前置条件

### 1. 配置 Self-Hosted Runner

在你的运行器机器上安装并配置 GitHub Actions self-hosted runner：
- [GitHub Self-Hosted Runner 官方文档](https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/about-self-hosted-runners)

确保 runner 已启动并注册到仓库，runner 标签应为 `self-hosted`。

### 2. 在 GitHub 中配置 Secrets

需要在仓库的 **Settings → Secrets and variables → Actions** 中创建以下 secret：

#### `CONFIG_YAML`
这是完整的 YAML 配置文件内容。示例：

```yaml
BOT:
  TOKEN: "your_telegram_bot_token"
AI:
  CHAT_TOKEN: "your_azure_openai_api_key"
  MODEL: "your_deployment_name"
  CHAT_VERSION: "2024-05-01-preview"
  CHAT_BASE: "https://your-resource.openai.azure.com/"
  IMAGE_TOKEN: "your_image_api_key"
  IMAGE_MODEL: "your_image_deployment_name"
  IMAGE_VERSION: "2025-04-01-preview"
  IMAGE_BASE: "https://your-resource.openai.azure.com/"
  TYPE: "azure"
MYSQL:
  DBHOST: "127.0.0.1"
  DBPORT: 3306
  DBUSER: "root"
  DBPWD: "your_db_password"
  DBNAME: "database_name"
  DBCHAR: "utf8mb4"
RATE_LIMIT:
  0: 10
  1: 30
  2: 300
CONTEXT_COUNT:
  0: 3
  1: 5
  2: 10
MAX_TOKEN:
  0: 256
  1: 1024
  2: 1024
IMAGE_RATE_LIMIT:
  0: 5
  1: 10
  2: 20
TIME_SPAN: 3
DEVELOPER_CHAT_ID: 123456789
```

**设置步骤：**
1. 进入仓库 → Settings
2. 左侧菜单选择 **Secrets and variables** → **Actions**
3. 点击 **New repository secret**
4. 名称填: `CONFIG_YAML`
5. 值填: 完整的 YAML 配置内容
6. 点击 **Add secret**

### 3. Self-Hosted Runner 环境要求

- Docker 已安装并运行
- Docker daemon 可用
- Runner 用户有权限访问 Docker（通常需要加入 docker group）

## 使用方式

### 自动触发
- 每次推送到 `main` 分支时自动运行
- 或在 GitHub UI 中手动触发 **Actions → Deploy ChatGPT Telegram Bot → Run workflow**

### 手动触发
```bash
# 通过 GitHub CLI
gh workflow run deploy-self-hosted.yml --ref main
```

## 监控和调试

### 查看运行日志
1. 进入 **Actions** 标签页
2. 选择 **Deploy ChatGPT Telegram Bot**
3. 点击具体的 workflow run
4. 查看各步骤的日志

### 常见问题排查

#### 容器启动失败
在 self-hosted runner 上手动检查：
```bash
# 查看最后的日志
docker logs chatgpt-telegram-bot

# 检查容器状态
docker ps -a | grep chatgpt-telegram-bot

# 重新启动容器
docker restart chatgpt-telegram-bot
```

#### 镜像构建失败
```bash
# 手动构建测试
docker build -t chatgpt-telegram-bot:latest .

# 查看构建日志中的错误
```

#### config.yaml 问题
```bash
# 检查配置文件是否正确挂载
docker exec chatgpt-telegram-bot cat /app/config.yaml

# 验证 YAML 语法
cat config.yaml | python -m yaml
```

## 高级配置

### 添加 MySQL 服务
如果需要 MySQL，修改 docker-compose.yaml 或在 self-hosted 上预先部署数据库。

### 环境变量
可以通过修改 workflow 中的 `docker run` 命令添加环境变量：

```yaml
docker run -d \
  --name chatgpt-telegram-bot \
  --restart unless-stopped \
  -e SOME_ENV_VAR="value" \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  chatgpt-telegram-bot:latest
```

### 资源限制
为容器设置资源限制：

```yaml
docker run -d \
  --name chatgpt-telegram-bot \
  --restart unless-stopped \
  --memory="512m" \
  --cpus="1" \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  chatgpt-telegram-bot:latest
```

## 更新和维护

### 更新应用代码后
只需 push 到 main 分支，workflow 会自动：
1. 构建新镜像
2. 停止旧容器
3. 启动新容器

### 清理镜像
```bash
# 在 self-hosted 上清理未使用的镜像
docker image prune -f
```

## 安全建议

1. ✅ 使用 GitHub Secrets 存储敏感信息（API keys, 密码等）
2. ✅ config.yaml 以只读模式挂载到容器
3. ✅ 定期更新 Python 和依赖版本
4. ✅ 使用 `--restart unless-stopped` 确保容器持续运行
5. ✅ 定期检查和更新容器镜像

## 相关文件

- **Workflow 配置**: `.github/workflows/deploy-self-hosted.yml`
- **Docker 配置**: `Dockerfile`
- **镜像配置**: `docker-compose.yaml`
- **应用配置**: `config.yaml` (由 Secrets 生成)
