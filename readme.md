# GraphRAG Skills Agent

GraphRAG + Skill Seekers Integration - 智能知识图谱与技能生成系统

本项目结合 **GraphRAG** 知识图谱增强检索与 **Skill Seekers** 技能生成系统，实现从知识图谱到 Claude Skills 的完整工作流。

## 🚀 快速开始

### 环境要求

- Python 3.10+
- Neo4j 5.x (知识图谱存储)
- OpenAI API Key 或 兼容的 LLM API

### 安装步骤

```bash
# 1. 克隆仓库
git clone https://github.com/daixudk96-max/graph-rag-skills-agent.git
cd graph-rag-skills-agent

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入你的 API Keys 和数据库连接信息
```

### 环境变量配置

创建 `.env` 文件并配置以下变量：

```env
# LLM API 配置
OPENAI_API_KEY=your_openai_api_key
OPENAI_BASE_URL=https://api.openai.com/v1  # 或其他兼容API

# Neo4j 数据库配置
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password

# 模型配置
LLM_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
```

## 📦 主要功能

### 1. 知识图谱构建

```bash
# 从文档构建知识图谱
python -m graphrag_agent.integrations.build.main --input-dir ./files
```

### 2. Skill Seekers 集成

使用动态模板系统生成技能文档：

```python
from graphrag_agent.integrations.skill_seekers import (
    TemplateRegistry, TemplateFiller, TemplateEmbedder
)

# 加载模板
registry = TemplateRegistry()
template = registry.get_template("transcript-segmented", "1.0.0")

# 填充内容
filler = TemplateFiller()
content = filler.fill(template, {
    "context": "课程背景...",
    "key_points": ["要点1", "要点2"],
    "summary": "总结内容..."
})

# 嵌入到 SKILL.md
embedder = TemplateEmbedder()
skill_md = embedder.embed_in_skill(skill_content, template)
```

### 3. 可用模板

| 模板 ID | 版本 | 用途 |
|---------|------|------|
| `transcript-segmented` | 1.0.0 | 分段转录（教学视频、讲座） |
| `transcript-interview` | 1.0.0 | 面试记录（问答对话） |
| `transcript-meeting` | 1.0.0 | 会议纪要（会议记录） |

## 📂 项目结构

```
graph-rag-skills-agent/
├── graphrag_agent/              # 核心包
│   ├── agents/                  # Agent 实现
│   ├── community/               # 社区检测与摘要
│   ├── config/                  # 配置管理
│   ├── graph/                   # 图谱构建
│   ├── integrations/            # 集成模块
│   │   ├── build/               # 知识图谱构建
│   │   └── skill_seekers/       # Skill Seekers 集成
│   │       └── templates/       # 动态模板系统
│   ├── search/                  # 搜索模块
│   └── models/                  # 模型管理
├── server/                      # 后端服务
├── frontend/                    # 前端界面
└── docs/                        # 文档
```

## 🔧 工作流

### /skill-seekers-proposal

1. 输入来源（文档/仓库/PDF/转录）
2. 选择动态模板
3. 内容提取与分段
4. 生成 `skill_input.json`

### /skill-seekers-apply

1. 读取 `skill_input.json`
2. 生成 `spec.yaml`
3. 构建 `SKILL.md`
4. 嵌入模板元数据

## 📖 文档

- [动态模板系统文档](./docs/skill_seekers_templates.md)
- [快速开始文档](./assets/start.md)

## 🙏 致谢

- [GraphRAG](https://github.com/microsoft/graphrag)
- [Neo4j](https://neo4j.com/)
- [LangChain](https://www.langchain.com/)

## 📄 License

MIT License
