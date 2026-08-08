# 📚 PaperAI — 智能论文精读 AI Agent

基于 LangGraph + RAG 的智能论文阅读助手，支持 PDF 上传解析、AI 问答交互。

## 核心功能

- **📄 智能解析** — 上传 PDF 论文，LLM 自动提取标题、作者、摘要、关键词、章节结构
- **💬 AI 问答** — 基于 RAG 检索增强生成，针对论文内容精准提问
- **🔍 向量检索** — 本地 embedding 模型，免费不限量
- **📝 笔记管理** — 结构化笔记，分类整理

## 技术架构

```
Frontend (Vue 3 + Vite)          Backend (FastAPI + LangGraph)
┌────────────────────┐           ┌──────────────────────────────┐
│  Arco Design UI    │  REST API │  Paper Parser Agent          │
│  Pinia State       │◄────────►│  QA Agent (Intent → Answer)  │
│  Vue Router        │           │  RAG Pipeline                │
└────────────────────┘           │  ├─ PDF → Text (pdfplumber)  │
                                 │  ├─ Chunks → Embedding       │
                                 │  ├─ ChromaDB Vector Store    │
                                 │  └─ Similarity Search        │
                                 │  LLM Client (DeepSeek)       │
                                 │  PostgreSQL + SQLAlchemy     │
                                 └──────────────────────────────┘
```

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端框架 | Vue 3.5 + TypeScript + Vite 8 |
| UI 组件 | Arco Design Vue 2 |
| 状态管理 | Pinia 4 |
| 后端框架 | FastAPI + Uvicorn |
| Agent 框架 | LangGraph 1.x + LangChain 1.x |
| LLM | DeepSeek (deepseek-v4-flash) |
| Embedding | sentence-transformers (all-MiniLM-L6-v2, 本地) |
| 向量数据库 | ChromaDB |
| 数据库 | PostgreSQL + SQLAlchemy Async |
| 认证 | JWT |

## 快速开始

### 环境要求

- Python 3.13+
- Node.js 20+
- PostgreSQL 16+

### 1. 克隆项目

```bash
git clone https://github.com/你的用户名/PaperAI.git
cd PaperAI
```

### 2. 安装后端

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate  # Windows
# source .venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
```

### 3. 创建数据库

```bash
psql -U postgres -c "CREATE DATABASE paperai;"
```

### 4. 配置环境变量

编辑 `backend/.env`：

```env
# 数据库
DATABASE_URL=postgresql+asyncpg://postgres:你的密码@localhost:5432/paperai

# DeepSeek LLM (聊天)
DEEPSEEK_API_KEY=sk-你的deepseek-api-key
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

> Embedding 使用本地模型，无需配置 API Key。

### 5. 安装前端

```bash
cd frontend
npm install
```

### 6. 启动

```bash
# 终端 1 — 后端
cd backend
source .venv/Scripts/activate
uvicorn app.main:app --host 0.0.0.0 --port 8001

# 终端 2 — 前端
cd frontend
npx vite
```

浏览器访问 `http://localhost:5173`（如果端口被占会自动切换，看终端输出）。

### 7. 使用

1. 打开页面，输入任意用户名和密码登录（首次自动注册）
2. 点击"上传论文"，选择 PDF 文件
3. LLM 自动解析论文元数据和章节结构
4. 点击"问答"，输入问题，AI 基于论文内容回答

## 项目结构

```
├── backend/
│   ├── app/
│   │   ├── agent/              # LangGraph Agent 工作流
│   │   │   ├── paper_parser/   # 论文解析 Agent
│   │   │   ├── qa_agent/       # 问答 Agent
│   │   │   └── state.py        # Agent 状态定义
│   │   ├── api/                # FastAPI 路由
│   │   │   ├── auth.py         # 认证 (JWT)
│   │   │   ├── papers.py       # 论文 CRUD + 上传 + QA
│   │   │   └── notes.py        # 笔记 API
│   │   ├── llm/                # LLM 客户端
│   │   ├── model/              # SQLAlchemy 数据模型
│   │   ├── rag/                # RAG 知识库
│   │   ├── config.py           # 配置管理
│   │   ├── database.py         # 数据库连接
│   │   └── main.py             # 应用入口
│   ├── .env                    # 环境变量
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/                # Axios HTTP 封装
│   │   ├── router/             # Vue Router 路由
│   │   └── views/              # 页面组件
│   │       ├── Home.vue        # 首页
│   │       ├── Login.vue       # 登录
│   │       ├── PaperList.vue   # 论文列表
│   │       ├── PaperReader.vue # 论文阅读
│   │       └── PaperQA.vue     # AI 问答
│   ├── index.html
│   ├── vite.config.ts
│   └── package.json
└── README.md
```

## License

MIT
