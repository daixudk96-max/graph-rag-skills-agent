# Deploy Graph-RAG-Agent Project

## 概述

按照 `assets/start.md` 指南完成 Graph-RAG-Agent 项目的本地部署，包括基础设施（Docker 容器）、Python 环境、配置和知识图谱构建。

## 用户审核项

> [!IMPORTANT]
> **API Key 配置**：需要用户提供有效的 OpenAI API Key 或者配置第三方 API 代理服务（如 One-API、云雾 API 等）。

> [!WARNING]
> **首次构建时间**：知识图谱的首次全量构建可能需要较长时间，取决于文件数量和内容复杂度。

## 环境现状

| 组件 | 状态 | 说明 |
|------|------|------|
| Docker | ✅ 已安装 | 已有容器运行 |
| Python | ❓ 待确认 | Conda 未在当前 shell 激活 |
| `.env` 配置 | ❌ 缺失 | 需要创建 |
| Neo4j | 📄 配置就绪 | `docker-compose.yaml` 已定义 |
| One-API | ❓ 待确认 | 需确认用户 API 配置方式 |

## 部署方案

### 阶段 1: 基础设施准备

#### 1.1 One-API 或 API 代理配置

**选项 A**: 使用 One-API 本地部署
```bash
docker run --name one-api -d --restart always \
  -p 13000:3000 \
  -e TZ=Asia/Shanghai \
  -v /home/ubuntu/data/one-api:/data \
  justsong/one-api
```

**选项 B**: 使用第三方代理（如云雾 API）

**选项 C**: 直接使用 OpenAI 官方 API

> 用户需提供 API Key 并确认选择的方式。

#### 1.2 Neo4j 数据库启动

```bash
cd graph-rag-agent/
docker compose up -d
```

默认凭据：用户名 `neo4j`，密码 `12345678`

---

### 阶段 2: Python 环境搭建

```bash
# 创建虚拟环境（Conda 或 venv）
conda create -n graphrag python==3.10
conda activate graphrag

# 或使用 venv
python -m venv .venv
.venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# Windows 专用
pip install pywin32>=302
```

---

### 阶段 3: 项目配置

#### 3.1 创建 `.env` 文件

从 `.env.example` 复制并配置必选项：

```env
# 必选配置
OPENAI_API_KEY = 'sk-xxx'
OPENAI_BASE_URL = 'http://localhost:13000/v1'  # 或直接使用 OpenAI URL
OPENAI_EMBEDDINGS_MODEL = 'text-embedding-3-large'
OPENAI_LLM_MODEL = 'gpt-4o'

NEO4J_URI = 'neo4j://localhost:7687'
NEO4J_USERNAME = 'neo4j'
NEO4J_PASSWORD = '12345678'
```

#### 3.2 知识图谱配置

编辑 `graphrag_agent/config/settings.py` 配置实体和关系类型（根据用户数据领域进行调整）。

---

### 阶段 4: 构建与启动

```bash
# 项目初始化
pip install -e .

# 放置知识库文件到 files/ 目录

# 构建知识图谱
python graphrag_agent/integrations/build/main.py

# 启动后端
python server/main.py

# 启动前端（新终端）
streamlit run frontend/app.py
```

## 验证计划

### 自动化验证
1. Docker 容器状态检查：`docker ps | grep neo4j`
2. Neo4j 连接测试：访问 http://localhost:7474
3. Python 依赖验证：`pip check`

### 手动验证
1. 浏览器访问后端 API：http://localhost:8000/docs
2. 浏览器访问前端 UI：http://localhost:8501
3. 执行测试查询验证 RAG 功能
