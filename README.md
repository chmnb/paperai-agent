# 📚 PaperAI — 智能论文精读 AI Agent 系统

基于 LangGraph Agent Loop 与 RAG 的智能论文阅读平台。上传 PDF 论文后，系统自动完成元数据解析、语义切片与向量化存储，支持对论文内容进行自然语言提问，Agent 自主规划检索策略、自省检索质量，并以流式输出生成基于原文的精准回答。

## ✨ 核心特性

- **🧠 Agent Loop 自省机制** — 意图识别分级路由：简单问题快速路径，复杂问题进入 Planner → 检索 → Critic 自省循环，Critic 输出的缺失信息自动改写下一轮检索查询（query rewriting）
- **📄 智能论文解析** — LangGraph 工作流自动提取标题、作者、摘要、关键词与章节结构
- **🔍 高质量 RAG 检索** — RecursiveCharacterTextSplitter 语义边界切分（chunk=500, overlap=100），向量语义检索 + 全文精确检索双工具
- **🛡️ 防幻觉降级** — 三档检索质量分级：充分/部分/无效；无效档不调 LLM 返回诚实回答，部分档自动附加反幻觉约束
- **⚡ 流式输出** — SSE 协议逐 token 推送，首字响应 < 1 秒，支持中途停止，思考过程可视化
- **🚀 异步上传** — 上传 2 秒内返回，LLM 解析与向量化后台执行，前端轮询展示进度
- **🎯 Prompt 工程化** — 全部提示词集中于独立模块，函数封装、few-shot 与模板分离、版本管理

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                   Frontend (Vue 3 + Vite)               │
│   Arco Design UI │ Pinia │ Vue Router │ SSE 流式渲染     │
└────────────────────────┬────────────────────────────────┘
                         │ REST API (JWT) + SSE
┌────────────────────────┴────────────────────────────────┐
│                    Backend (FastAPI)                     │
│                                                          │
│  ┌──────────── Agent Layer (LangGraph) ────────────────┐ │
│  │  论文解析 Agent: 元数据提取 → 章节解析                │ │
│  │  问答 Agent Loop:                                    │ │
│  │    recognize_intent ─┬─ simple → retrieve_once       │ │
│  │                      └─ complex → planner ⇄ critic   │ │
│  │                             ↓          ↓             │ │
│  │                      execute_tool  (vector/full-text)│ │
│  └──────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌──────────── RAG Pipeline ───────────────────────────┐ │
│  │  PDF → pdfplumber → 语义切片 → Embedding             │ │
│  │  → ChromaDB → 相似度检索 → 质量分级 → LLM 生成       │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌──────────── Data Layer ─────────────────────────────┐ │
│  │  PostgreSQL: 用户/论文/章节/问答记录                  │ │
│  │  ChromaDB: 文本向量                                  │ │
│  └──────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

## 🛠️ 技术栈

| 层级 | 技术 |
|------|------|
| Agent 框架 | LangGraph 1.x + LangChain 1.x（StateGraph 工作流编排） |
| 后端 | FastAPI + Uvicorn（异步） |
| LLM | DeepSeek（支持 OpenAI 兼容提供商切换） |
| Embedding | sentence-transformers all-MiniLM-L6-v2（本地，免费） |
| 向量数据库 | ChromaDB |
| 关系数据库 | PostgreSQL + SQLAlchemy Async 2.0 |
| 认证 | JWT + SHA256 |
| PDF 解析 | pdfplumber |
| 流式传输 | SSE (Server-Sent Events) |
| 前端 | Vue 3.5 + TypeScript + Vite |
| UI | Arco Design Vue 2 |
| 状态管理 | Pinia |

## 🚀 快速开始

### 环境要求

- Python 3.13+
- Node.js 20+
- PostgreSQL 16+

### 1. 安装后端

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate   # Windows
# source .venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
```

### 2. 创建数据库

```bash
psql -U postgres -c "CREATE DATABASE paperai;"
```

### 3. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，填入必填项：

```env
# PostgreSQL 连接（必填）
DATABASE_URL=postgresql+asyncpg://postgres:你的密码@localhost:5432/paperai

# DeepSeek LLM（必填，用于论文解析与问答生成）
DEEPSEEK_API_KEY=sk-your-deepseek-api-key
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

> Embedding 使用本地模型，无需 API Key。首次上传会自动下载模型（约 90MB）。

### 4. 安装前端

```bash
cd frontend
npm install
```

### 5. 启动

```bash
# 终端 1 — 后端
cd backend
source .venv/Scripts/activate
uvicorn app.main:app --host 0.0.0.0 --port 8001

# 终端 2 — 前端
cd frontend
npx vite
```

浏览器访问终端输出的地址（默认 `http://localhost:5173`）。

### 6. 使用

1. 登录（任意用户名密码，首次自动注册）
2. 点击"上传论文"选择 PDF — 秒级返回，后台自动解析（列表显示 ⏳ 解析中，自动轮询刷新）
3. 进入论文 → "AI 问答"
4. 提问后查看 Agent 思考过程（意图识别 → 规划 → 检索 → 自省），答案流式生成

## 📁 项目结构

```
├── backend/
│   ├── app/
│   │   ├── agent/                  # LangGraph Agent 工作流
│   │   │   ├── paper_parser/       # 论文解析 Agent（元数据 → 章节）
│   │   │   ├── qa_agent/           # 问答 Agent Loop（意图 → 规划 → 检索 ⇄ 自省）
│   │   │   │   └── tools.py        # 检索工具集（向量/全文/元数据）
│   │   │   └── state.py            # TypedDict 状态定义
│   │   ├── prompts/                # Prompt 工程模块（集中管理）
│   │   │   ├── parser.py           # 论文解析 prompts
│   │   │   ├── qa.py               # 问答 prompts（few-shot 分离）
│   │   │   └── fallbacks.py        # 确定性降级模板
│   │   ├── api/                    # FastAPI 路由
│   │   │   ├── auth.py             # JWT 认证
│   │   │   ├── papers.py           # 论文 CRUD + 异步上传 + SSE 问答
│   │   │   └── notes.py            # 笔记 API
│   │   ├── llm/                    # LLM 客户端（generate / astream）
│   │   ├── models/                 # SQLAlchemy 数据模型
│   │   ├── rag/                    # RAG 知识库（ChromaDB 封装）
│   │   ├── config.py               # Pydantic Settings 配置
│   │   ├── database.py             # 异步数据库连接
│   │   └── main.py                 # 应用入口
│   ├── .env.example
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/                    # Axios + fetch SSE 封装
│   │   ├── router/                 # 路由守卫
│   │   └── views/
│   │       ├── Home.vue            # 首页
│   │       ├── Login.vue           # 登录
│   │       ├── PaperList.vue       # 论文列表（解析状态轮询）
│   │       ├── PaperReader.vue     # 论文阅读
│   │       └── PaperQA.vue         # AI 问答（思考过程可视化 + 流式渲染）
│   └── vite.config.ts
└── README.md
```

## 📄 License

MIT
