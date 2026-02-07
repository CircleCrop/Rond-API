# Rond-API 项目 AI 开发指南

## 项目概述

Rond-API 是一个连接 Apple 应用 _[Rond](https://apps.apple.com/app/id1669903815?platform=iphone)_ 的 API 工具，支持 CLI 命令行调用和 MCP 服务器，基于 `Python 3.12`，运行于 `macOS`。

## 开发规范

### 代码风格

- Python 3.12
- PEP 8，使用 `black` (88 字符) 和 `isort` (profile="black")
- 日志输出使用英文标点 `:` `,` `=` `|`，保持一致性
- 中文注释和文档字符串，英文日志消息

## 环境和工具

### Python 环境

- Python 3.12 pyenv
- requirements.txt
- Shell: macOS zsh

### 代码搜索

`mcp-vector-search` 用于代码搜索，支持语义搜索和关键字搜索。
