# 🔗 Rond-API

> 连接 Apple 应用 _[Rond](https://apps.apple.com/app/id1669903815)_ 的 Python API 工具

基于 Python 3.12，用于访问 macOS 应用容器内的数据库，提供 CLI 命令行接口和 MCP 服务器支持。

---

## ✨ 功能特性

- 🐍 Python 3.12

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置数据库路径

在项目根目录创建 `.env` 文件：

```env
ROND_DB_PATH=/Users/你的用户名/Library/Containers/<Rond UUID>/Data/Library/Application Support/Rond/database.sqlite
```

## 📝 License

### MIT