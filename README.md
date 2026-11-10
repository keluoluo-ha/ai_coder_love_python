# AI 恋爱智能客服助手（ai_coder_love_python）

> 个人独立开发 · 企业级情感 AI 恋爱智能系统 Python 改造版
> 基于 LangChain + FastAPI + 通义千问（qwen-plus）的情感陪伴式智能客服，涵盖对话记忆、RAG 知识库、手写 ReAct Agent、RabbitMQ 异步情感关怀闭环与 RAG 离线评测。

---

## 项目简介

本项目是一个"AI 恋爱客服助手"（苏苏），面向情感咨询场景：用户可以与 AI 进行多轮情感对话，系统会结合**恋爱知识库（RAG）**检索参考内容，由**手写的 ReAct Agent 状态机**自主规划并调用工具（联网搜索、网页抓取、生成 PDF 报告等）回答问题；咨询结束后通过 **RabbitMQ 异步事件链路**完成情感画像更新、回访建立与到点提醒，形成情感关怀闭环。同时内置 **RAG 离线评测框架**（数据集加载 → 指标计算 → 报告生成），可量化检索质量。

## 核心功能

| 模块 | 说明 |
| --- | --- |
| 💬 多轮对话记忆 | `FileChatMemory` / `MySQLChatMemory` 双实现，可切换的会话持久化 |
| 📚 RAG 知识库 | PostgreSQL + pgvector 向量检索，配合查询重写、查询扩展、关键词增强提升召回 |
| 🤖 手写 ReAct Agent | 参考 OpenManus 自研状态机，继承链 `BaseAgent → ReActAgent → ToolCallAgent → SupportAgent`，未使用 LangChain AgentExecutor |
| 🛠️ 工具系统 | 联网搜索、网页抓取、PDF 报告生成、文件读写、终端执行、日期时间、向用户提问（AskHuman）、任务终止等 10+ 工具 |
| ❤️ 情感关怀异步链路 | RabbitMQ 事件驱动：咨询完成 → 情绪画像更新 → 建立回访 → 延迟提醒 → 回访完成自动续环；`event_id` 幂等表 + 发布者确认 + 失败兜底死信队列 |
| 📊 咨询效果评估 | 咨询前后情绪评分差值驱动趋势判定（改善/稳定/下降）与风险分级 |
| 🧪 RAG 离线评测 | 数据集加载、检索命中率等指标计算、评测报告输出（`rag_eval_report.json/txt`） |
| 🌐 Web API | FastAPI 提供 REST 接口，配套 Vue 前端（端口 5173，已配置 CORS） |

## 技术栈

| 类别 | 技术 |
| --- | --- |
| 语言 | Python 3.13 |
| Web 框架 | FastAPI + Uvicorn |
| LLM | LangChain 0.3 + ChatTongyi（通义千问 qwen-plus） |
| Agent | LangGraph 0.2（辅助）+ 自研 ReAct 状态机 |
| 向量库 | PostgreSQL 17 + pgvector |
| 业务数据库 | MySQL 8（SQLAlchemy + PyMySQL） |
| 消息队列 | RabbitMQ（pika） |
| 其他 | Beautiful Soup、ReportLab、python-dotenv |

## 系统架构

```mermaid
flowchart LR
    U[用户 / Vue 前端] --> API[FastAPI /api]
    API --> AGENT[SupportAgent<br/>ReAct 状态机]
    AGENT --> MEM[对话记忆<br/>File / MySQL]
    AGENT --> TOOLS[工具集<br/>搜索/抓取/PDF/RAG检索...]
    TOOLS --> RAG[(pgvector<br/>恋爱知识库)]
    API -- 咨询完成事件 --> MQ[(RabbitMQ)]
    MQ --> PP[情感关怀消费端<br/>评估/画像/回访/提醒]
    PP --> DB[(MySQL 业务库)]
```

## 快速开始

### 1. 环境准备

- Python 3.10+
- MySQL 8.0（业务库 + 对话记忆）
- PostgreSQL 17 + pgvector 扩展（RAG 向量库）
- RabbitMQ（情感关怀异步链路）

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置 `.env`

在项目根目录创建 `.env`（参考 `app/config.py`）：

```env
# 通义千问 API Key
DASHSCOPE_API_KEY=sk-xxxx
LLM_MODEL_NAME=qwen-plus

# MySQL
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=xxxx
MYSQL_DATABASE=supportagent

# PostgreSQL + pgvector
PG_HOST=127.0.0.1
PG_PORT=5432
PG_USER=postgres
PG_PASSWORD=xxxx
PG_DB=ai_agent_support

# 联网搜索 API Key
SEARCH_API_KEY=xxxx

# RabbitMQ
RABBITMQ_URL=amqp://admin:xxxx@127.0.0.1:5672/

# PDF 报告输出目录（可选，默认 pdf_reports）
PDF_SAVE_DIR=pdf_reports
```

### 4. 启动服务

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

启动后访问接口文档：http://127.0.0.1:8000/docs

> 说明：MySQL 为强依赖（启动时自动建表）；RabbitMQ / pgvector 为延迟连接，未启动时仅情感关怀与 RAG 检索相关接口不可用，不影响服务整体启动。

## 目录结构

```
├── app/
│   ├── main.py                 # FastAPI 入口
│   ├── config.py               # 环境变量配置
│   ├── agent/                  # BaseAgent → ReActAgent → ToolCallAgent → SupportAgent
│   ├── tools/                  # 搜索/抓取/PDF/文件/终端/AskHuman 等工具
│   ├── rag/                    # 向量库、查询重写、分块、RAG 离线评测（eval/）
│   ├── chatmemory/             # File / MySQL 对话记忆实现
│   ├── mq/                     # RabbitMQ 事件、发布者、消费者
│   ├── services/               # 情感画像、回访、情感关怀后处理
│   ├── domain/                 # 咨询效果评估
│   ├── controller/             # 路由（对话 / 咨询 / 文件）
│   └── db/                     # SQLAlchemy 模型与会话
├── test/                       # 单元与集成测试（LLM/RAG/工具/Agent/记忆）
├── rag_eval_report.json        # RAG 评测报告（JSON）
├── rag_eval_report.txt         # RAG 评测报告（文本）
└── requirements.txt
```

## 测试

```bash
python -m test.test_llm        # LLM 连通性
python -m test.test_rag        # RAG 检索
python -m test.test_agent      # Agent 推理与工具调用
python -m test.chatMySqlMemoryTest  # MySQL 对话记忆
```

## RAG 离线评测

内置评测框架（`app/rag/eval/`）：数据集加载 → 检索指标计算 → 报告生成，历史评测结果见 `rag_eval_report.json` / `rag_eval_report.txt`。

## 作者

- **克洛洛哈**（[GitHub](https://github.com/keluoluo-ha)）
