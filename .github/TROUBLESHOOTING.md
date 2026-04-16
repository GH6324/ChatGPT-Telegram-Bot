# Troubleshooting: KeyError 'CHAT_TOKEN'

## 问题分析

错误日志显示：
```
KeyError: 'CHAT_TOKEN'
  File "/app/ai/azure.py", line 9, in __init__
    api_key=config["AI"]["CHAT_TOKEN"],
```

这意味着配置文件中的 `AI` 部分缺少 `CHAT_TOKEN` 键，通常有以下原因：

## 🔍 根本原因检查清单

### 1. config.yaml 文件格式问题
```bash
# 在 self-hosted runner 上检查
docker exec chatgpt-telegram-bot cat /app/config.yaml

# 验证 YAML 语法
python -c "import yaml; yaml.load(open('/app/config.yaml'), Loader=yaml.FullLoader); print('✓ YAML 格式正确')"
```

**常见格式错误：**
- ❌ 缩进不一致（混合 tab 和空格）
- ❌ 注释引起的缩进混乱
- ❌ 键值对格式错误

### 2. config.yaml 挂载路径问题
```bash
# 检查容器内是否存在配置文件
docker exec chatgpt-telegram-bot test -f /app/config.yaml && echo "✓ 文件存在" || echo "❌ 文件不存在"

# 检查文件大小是否为 0
docker exec chatgpt-telegram-bot ls -lh /app/config.yaml
```

**常见路径问题：**
- ❌ workflow 中硬编码的路径 `/root/workspace/...` 不存在
- ❌ config.yaml 在工作目录但容器挂载了错误的位置
- ❌ 文件权限问题导致无法读取

### 3. 配置从 Secrets 生成的问题
```bash
# 检查 Secrets 是否正确设置
echo "检查 GitHub Settings → Secrets and variables → Actions 中的 CONFIG_YAML secret"

# 手动验证生成的文件
cat config.yaml | head -20
```

## ✅ 快速修复

### 方法 1：使用正确的工作目录路径（推荐）

已在 workflow 中修复，确保使用：
```yaml
-v $(pwd)/config.yaml:/app/config.yaml:ro
```

或在 start container 步骤中：
```yaml
WORK_DIR=$(pwd)
docker run -d \
  --name chatgpt-telegram-bot \
  --restart unless-stopped \
  -v $WORK_DIR/config.yaml:/app/config.yaml:ro \
  chatgpt-telegram-bot:latest
```

### 方法 2：手动测试配置

在 self-hosted runner 上：

```bash
# 1. 检查 config.yaml 存在且格式正确
cat config.yaml | grep -A 5 "^AI:"

# 2. 创建一个测试容器
docker run --rm \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  chatgpt-telegram-bot:latest \
  python -c "import yaml; config=yaml.load(open('/app/config.yaml'), Loader=yaml.FullLoader); print('✓ 配置加载成功'); print(config['AI'].keys())"

# 3. 如果上面成功，再启动真实容器
```

### 方法 3：清理缓存并重新部署

```bash
# 在 self-hosted runner 上
docker stop chatgpt-telegram-bot || true
docker rm chatgpt-telegram-bot || true
docker rmi chatgpt-telegram-bot:latest || true

# 重新触发 workflow 或手动运行
cd /path/to/repo
git pull origin main
```

## 📋 完整诊断步骤

### 在 GitHub Actions 中查看日志

1. 进入 **Actions** 标签页
2. 点击最新的 workflow run
3. 展开 **Start container** 步骤
4. 查看 `WORK_DIR` 是否正确打印

### 在 Runner 上手动诊断

```bash
#!/bin/bash
set -e

echo "=== 诊断信息 ==="

# 1. 检查工作目录
echo -e "\n1️⃣  当前目录："
pwd

# 2. 检查 config.yaml
echo -e "\n2️⃣  config.yaml 文件状态："
if [ -f config.yaml ]; then
  echo "✓ 文件存在"
  echo "大小: $(du -h config.yaml | cut -f1)"
  echo "内容摘要（前 5 行）："
  head -5 config.yaml
else
  echo "❌ 文件不存在"
  exit 1
fi

# 3. 验证 YAML 格式
echo -e "\n3️⃣  YAML 格式验证："
python3 << 'PYEOF'
import yaml
try:
  with open('config.yaml') as f:
    config = yaml.load(f, Loader=yaml.FullLoader)
  print("✓ YAML 解析成功")
  print(f"✓ AI 部分键: {list(config.get('AI', {}).keys())}")
  if 'CHAT_TOKEN' in config.get('AI', {}):
    print("✓ CHAT_TOKEN 存在")
  else:
    print("❌ CHAT_TOKEN 不存在")
except Exception as e:
  print(f"❌ 错误: {e}")
PYEOF

# 4. 检查容器
echo -e "\n4️⃣  Docker 容器状态："
docker ps -a --filter "name=chatgpt-telegram-bot"

# 5. 查看容器日志
echo -e "\n5️⃣  容器日志（最后 20 行）："
docker logs --tail 20 chatgpt-telegram-bot || echo "❌ 容器不存在或无日志"
```

## 🚀 部署验证

部署后确认：

```bash
# 1. 容器正在运行
docker ps | grep chatgpt-telegram-bot

# 2. 配置文件正确挂载
docker exec chatgpt-telegram-bot test -f /app/config.yaml && echo "✓ 配置文件存在"

# 3. 配置可以被读取
docker exec chatgpt-telegram-bot python3 -c "
import yaml
config = yaml.load(open('/app/config.yaml'), Loader=yaml.FullLoader)
print(f'✓ 配置加载成功，AI 模型: {config[\"AI\"][\"MODEL\"]}')
"

# 4. 应用启动成功
docker logs chatgpt-telegram-bot | grep "Application started"
```

## 🔧 修复总结

已进行的修复：

✅ **修复 1：workflow config.yaml 挂载路径**
- 从硬编码路径改为使用 `$(pwd)/config.yaml`
- 确保容器正确挂载 workflow 生成的配置文件

✅ **修复 2：config.yaml 格式清理**
- 清除了过时的注释代码
- 标准化了 YAML 缩进
- 确保 AI 部分的所有必需键都存在

✅ **修复 3：docker run 改进**
- 使用 `-d` 而不是 `-itd`（后台运行）
- 使用 `--restart unless-stopped` 确保自动重启
- 添加 `:ro` 标记 config.yaml 为只读

## 📞 还有问题？

如果上述步骤都不能解决，收集以下信息：

```bash
# 在 self-hosted runner 上运行收集诊断信息
{
  echo "=== 环境信息 ==="
  pwd
  ls -lh config.yaml
  head -20 config.yaml
  echo ""
  echo "=== Docker 信息 ==="
  docker --version
  docker ps -a | grep chatgpt-telegram-bot
  echo ""
  echo "=== 容器日志 ==="
  docker logs chatgpt-telegram-bot 2>&1 | tail -50
} > diagnostics.txt

# 分享 diagnostics.txt
```

## 参考

- [YAML 规范](https://yaml.org/)
- [Docker Volume 挂载](https://docs.docker.com/storage/volumes/)
- [GitHub Actions 工作流语法](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
