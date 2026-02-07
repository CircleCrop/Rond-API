# 🔗 Rond-API

> 连接 Apple 应用 _[Rond](https://apps.apple.com/app/id1669903815)_ 的 Python API 工具

基于 Python 3.12，用于访问 macOS 应用容器内的数据库，提供 CLI 命令行接口和 MCP 服务器支持。

---

## ✨ 功能特性

- 🐍 Python 3.12
- 🔒 数据库只读访问
- 🧭 `timeline` 时间线查询（到访 + 交通混排）
- 🧩 分层架构（config/db/repository/service/formatter/cli），便于后续扩展

## ✅ 当前可获取数据

- 指定日期时间线（`today` / `yesterday` / `YYYY-MM-DD`）
- 到访事件：地点、唯一用户分类、标签（Visit+Location 合并）
- 交通事件：交通方式、起止时间、时长、出发/到达地点
- 时间线事件按时间顺序混排输出
- 可读文本输出（默认带 Emoji）与 JSON 输出

## ⏸ 暂不实现

- MCP 接口（本次仅预留代码结构）
- 游记/行程
- 健康/体能数据（macOS 不支持 HealthKit）
- 天气、日记、统计等其他查询能力

---

## 🚀 快速开始

### 1. 安装依赖

```bash
python -m pip install -r requirements.txt
```

### 2. 配置数据库路径

在项目根目录创建 `.env` 文件：

```env
ROND_DB_PATH=/Users/你的用户名/Library/Containers/<Rond UUID>/Data/Library/Application Support/Rond/LifeEasy.sqlite
```

开发环境可将数据库复制保存至 `tests/LifeEasy.sqlite`，避免误修改。

### 3. 运行时间线命令

```bash
rond-api timeline --date today
```

```bash
rond-api timeline --date 2026-01-29 --output both
```

```bash
rond-api timeline --date yesterday --output pretty --no-emoji
```

```bash
rond-api timeline --date today --tree
```

### 4. Python API

```python
from rond_api import get_timeline

timeline = get_timeline(date_expr="2026-01-29", db_path="tests/LifeEasy.sqlite")
print(timeline.query_date, timeline.timezone, len(timeline.events))
```

### 5. tree 装饰线

- CLI: `--tree` 开启，`--no-tree` 关闭
- `.env`: `tree=on|off`（也支持 `TIMELINE_TREE=on|off`）

## 📝 License

### MIT
