# GetJobs — 智能求职自动投递工具

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

一个开源的求职自动投递工具，支持 Boss直聘、猎聘、智联招聘、前程无忧四大平台。

## 功能特性

- **多平台支持**：Boss直聘、猎聘、智联招聘、前程无忧
- **浏览器自动化**：基于 Playwright + Camoufox，模拟真人操作
- **智能过滤**：按关键词、城市、薪资范围筛选职位
- **Web 管理界面**：Next.js 前端，实时查看投递进度
- **数据持久化**：SQLite 本地数据库，记录投递历史
- **跨平台**：支持 Windows、macOS、Linux

## 项目背景

本项目是对 [loks666/get_jobs](https://github.com/loks666/get_jobs) 的 Python 重构版。

原版基于 Kotlin + Chrome 实现，本项目将其重构为 **Python + FastAPI + Camoufox** 技术栈，以获得更好的跨平台支持和反检测能力。

| 维度 | 原版 | 重构版 |
|------|------|--------|
| 后端语言 | Kotlin | Python 3.10+ |
| Web 框架 | — | FastAPI |
| ORM | — | SQLAlchemy 2.0 async |
| 浏览器 | Chrome | Camoufox（反检测） |
| 数据库 | SQLite | SQLite (aiosqlite) |
| 前端 | — | Next.js 16 |

## 系统要求

- Python 3.9+
- Node.js 18+（用于构建前端）
- Chrome/Edge 浏览器（用于 Camoufox）

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/vvvsrx/get_jobs.git
cd getjobs
```

### 2. 一键安装（跨平台）

**Linux / macOS:**
```bash
python3 scripts/setup.py
```

**Windows:**
```cmd
python scripts/setup.py
```

或手动运行：
```bash
pip install -e .
cd frontend && npm install && npm run build
cd .. && python run.py
```

### 3. 访问 Web 界面

打开浏览器访问 http://localhost:8888

## 配置

复制 `.env.example` 为 `.env` 并修改：

```bash
cp .env.example .env
```

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `APP_PORT` | 服务端口 | 8888 |
| `APP_HOST` | 监听地址 | 0.0.0.0 |
| `DATABASE_URL` | 数据库路径 | sqlite+aiosqlite:///db/getjobs.db |
| `API_KEY` | AI 服务密钥（可选） | `""` |
| `BASE_URL` | AI API 基础地址 | `https://api.openai.com` |
| `MODEL` | AI 模型 | `gpt-4o-mini` |

## 项目结构

```
.
├── app/                 # FastAPI 后端
│   ├── main.py          # 应用入口
│   ├── models.py        # SQLAlchemy 数据模型
│   ├── routers/         # API 路由
│   ├── services/        # 业务逻辑
│   └── worker/          # 浏览器自动化 Bot
├── frontend/            # Next.js 前端
├── tests/               # 测试
├── scripts/             # 跨平台构建脚本
├── data/                # 运行时数据
└── db/                  # SQLite 数据库
```

## 技术栈

- **后端**: FastAPI, SQLAlchemy 2.0, Playwright, Camoufox
- **前端**: Next.js 16, React 19, Tailwind CSS, Radix UI
- **数据库**: SQLite (aiosqlite)
- **构建**: pyproject.toml, npm

## 许可证

MIT License — 详见 [LICENSE](LICENSE)
