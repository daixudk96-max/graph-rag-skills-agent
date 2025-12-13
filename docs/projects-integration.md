# 三个项目如何整合使用

## 核心思路：每个项目负责一部分

```mermaid
flowchart TB
    subgraph Step1["第1步：内容抓取"]
        A["Skill_Seekers"]
        A1["抓取课程网页"]
        A2["解析PDF讲义"]
        A3["处理视频字幕"]
        A --> A1
        A --> A2
        A --> A3
    end
    
    subgraph Step2["第2步：图谱构建"]
        B["iText2KG / ATOM"]
        B1["实体抽取"]
        B2["实体消歧"]
        B3["构建知识图谱"]
        B --> B1 --> B2 --> B3
    end
    
    subgraph Step3["第3步：智能问答"]
        C["graph-rag-agent"]
        C1["GraphRAG检索"]
        C2["多Agent协作"]
        C3["生成回答"]
        C --> C1 --> C2 --> C3
    end
    
    A3 -->|"scraped_data.json"| B
    B3 -->|"导入Neo4j"| C
    
    style A fill:#87CEEB
    style B fill:#90EE90
    style C fill:#FFD700
```

---

## 具体整合步骤

### 步骤 1：用 Skill_Seekers 抓取课程内容

```bash
# 安装 Skill_Seekers
pip install skill-seekers

# 抓取课程网站
skill-seekers scrape --url https://your-course-site.com --output courses/
```

**输出**：`scraped_data.json`（包含课程文本内容）

---

### 步骤 2：用 iText2KG 构建知识图谱

```python
# 使用 iText2KG 从抓取的内容构建图谱
from itext2kg import ATOM

# 加载抓取的数据
with open("courses/scraped_data.json") as f:
    course_data = json.load(f)

# 初始化 ATOM
atom = ATOM(llm=your_llm, embeddings=your_embeddings)

# 构建知识图谱
kg = atom.build_graph(course_data)

# 导出到 Neo4j 格式
kg.export_to_neo4j("neo4j_import/")
```

**输出**：Neo4j 可导入的图谱数据

---

### 步骤 3：用 graph-rag-agent 提供问答服务

```bash
# 导入图谱到 Neo4j
neo4j-admin import --nodes neo4j_import/nodes.csv --relationships neo4j_import/rels.csv

# 启动 graph-rag-agent 
cd graph-rag-agent
python -m server.main
```

**结果**：可以对课程内容进行智能问答

---

## 数据流动图

```mermaid
flowchart LR
    subgraph Input["原始数据"]
        I1["📄 课程网页"]
        I2["📕 PDF讲义"]
        I3["🎬 视频字幕"]
    end
    
    subgraph Tool1["Skill_Seekers"]
        T1["抓取/解析"]
    end
    
    subgraph Data1["中间数据1"]
        D1["scraped_data.json"]
    end
    
    subgraph Tool2["iText2KG"]
        T2["实体抽取"]
        T3["图谱构建"]
    end
    
    subgraph Data2["中间数据2"]
        D2[("Neo4j图谱")]
    end
    
    subgraph Tool3["graph-rag-agent"]
        T4["GraphRAG检索"]
        T5["Agent问答"]
    end
    
    subgraph Output["最终输出"]
        O1["🤖 智能问答"]
    end
    
    I1 --> T1
    I2 --> T1
    I3 --> T1
    T1 --> D1
    D1 --> T2 --> T3 --> D2
    D2 --> T4 --> T5 --> O1
    
    style T1 fill:#87CEEB
    style T2 fill:#90EE90
    style T3 fill:#90EE90
    style T4 fill:#FFD700
    style T5 fill:#FFD700
```

---

## 或者：只用 graph-rag-agent（更简单）

**实际上 graph-rag-agent 自己就能完成所有步骤**：

```mermaid
flowchart LR
    A["📄 课程文档"] --> B["graph-rag-agent"]
    B --> C["自动抽取实体"]
    C --> D["自动构建图谱"]
    D --> E["提供GraphRAG问答"]
    
    style B fill:#FFD700
```

```bash
# 直接用 graph-rag-agent 处理
python -m graphrag_agent.integrations.build.main --input ./courses/
python -m server.main
```

---

## 两种方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| **三项目组合** | 每个环节更专业 | 集成复杂，需要对接数据格式 |
| **只用 graph-rag-agent** | 开箱即用，无需集成 | 单个项目功能可能不如组合灵活 |

**建议**：先用 graph-rag-agent 快速验证，后续有需要再引入其他项目。
