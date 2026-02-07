# 🔗 Rond-API

> 连接 Apple 应用 _[Rond](https://apps.apple.com/app/id1669903815)_ 的 Python API 工具

基于 Python 3.12，用于访问 macOS 应用容器内的数据库，提供 CLI 命令行接口和 MCP 服务器支持。

---

## ✨ 功能特性

- 🐍 Python 3.12
- 🔒 数据库只读访问
- 🧭 支持按时间范围查询
- 📊 支持统计与聚合分析

## ✅ 当前可获取数据

- 每日时间线（到访地点、到达/离开时间）
- 天气（到访时段的小时天气）
- 日记（标题、内容、时间）
- 交通（移动记录 + 交通方式）
- 近期数据（最近 7/30 天）
- 统计（按活动/地点/时间段聚合）

## ⏸ 暂不实现

- 游记/行程
- 健康/体能数据（macOS 不支持 HealthKit）

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

## 📝 License

### MIT