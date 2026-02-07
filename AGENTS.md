# Rond-API 项目 AI 开发指南

## 项目概述

Rond-API 是一个连接 Apple 应用 _[Rond](https://apps.apple.com/app/id1669903815)_ 的 API 工具，支持 CLI 命令行调用和 MCP 服务器，基于 `Python 3.12`，运行于 `macOS`。

## 开发规范

### 代码风格

- Python 3.12
- PEP 8，使用 `black` (88 字符) 和 `isort` (profile="black")
- 日志输出使用英文标点 `:` `,` `=` `|`，保持一致性
- 中文注释和文档字符串，英文日志消息

## 环境和工具

### 数据库约束

- 数据库永远只读，API 不允许写入
- 打开数据库时可能有其他应用正在写入
- 生产环境使用 `.env` 中的 `ROND_DB_PATH`
- 开发环境使用 `tests/LifeEasy.sqlite`
- 数据库结构注释 `docs/schema.md`

### 当前范围与限制

- 暂不实现游记/行程（TRIP 系列）
- 暂不实现健康/体能数据（macOS 不支持 HealthKit）

### Python 环境

- Python 3.12.12 pyenv
- requirements.txt
- Shell: macOS zsh

### 代码搜索

`mcp-vector-search` 用于代码搜索，支持语义搜索和关键字搜索。
