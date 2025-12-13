# GraphRAG 增量更新流程详解

本文档解释如何将新的教育内容增量更新到现有的 GraphRAG 知识图谱中。

---

## 一、增量更新的核心流程

```mermaid
flowchart TB
    subgraph Input["1️⃣ 新内容输入"]
        A1["📄 新课程文档"]
        A2["🎥 新视频转录"]
    end
    
    subgraph Extract["2️⃣ 实体抽取"]
        B1["LLM 识别实体"]
        B2["LLM 识别关系"]
        B3["生成候选三元组"]
    end
    
    subgraph Resolution["3️⃣ 实体消歧"]
        C1["在现有图谱中搜索"]
        C2["计算相似度"]
        C3{"是否匹配现有实体?"}
        C4["合并到现有节点"]
        C5["创建新节点"]
    end
    
    subgraph Merge["4️⃣ 图谱合并"]
        D1["添加新关系边"]
        D2["更新节点属性"]
        D3["一致性检查"]
    end
    
    subgraph Result["5️⃣ 最终结果"]
        E1[("更新后的图谱")]
    end
    
    A1 --> B1
    A2 --> B1
    B1 --> B2 --> B3
    B3 --> C1 --> C2 --> C3
    C3 -->|"是"| C4
    C3 -->|"否"| C5
    C4 --> D1
    C5 --> D1
    D1 --> D2 --> D3 --> E1
    
    style C3 fill:#FFD700
    style E1 fill:#90EE90
```

---

## 二、graph-rag-agent 中的增量更新实现

根据 `graph-rag-agent` 项目结构，增量更新位于:

```
graphrag_agent/
└── integrations/
    └── build/
        ├── incremental/           # 增量更新子模块
        └── incremental_update.py  # 增量更新管理
```

### 2.1 增量更新的关键步骤

```mermaid
sequenceDiagram
    participant User as 用户
    participant Ingestion as 文档处理器
    participant Extractor as 实体抽取器
    participant Resolver as 消歧模块
    participant Neo4j as 图数据库
    
    User->>Ingestion: 上传新课程文档
    Ingestion->>Ingestion: 文本分块
    Ingestion->>Extractor: 发送文本块
    
    loop 每个文本块
        Extractor->>Extractor: LLM 抽取实体和关系
        Extractor->>Resolver: 候选实体列表
        Resolver->>Neo4j: 查询现有实体
        Neo4j-->>Resolver: 返回相似实体
        
        alt 找到匹配实体
            Resolver->>Neo4j: MERGE 合并节点
        else 无匹配
            Resolver->>Neo4j: CREATE 创建新节点
        end
        
        Resolver->>Neo4j: 添加关系边
    end
    
    Neo4j->>Neo4j: 触发一致性检查
    Neo4j-->>User: 更新完成
```

---

## 三、实体消歧详解（核心去重机制）

这是实现"严格整合"的关键步骤。

### 3.1 三阶段消歧流程

```mermaid
flowchart LR
    subgraph Stage1["阶段1: 字符串召回"]
        A1["候选实体: '生成器'"]
        A2["全文搜索 + 模糊匹配"]
        A3["返回 Top-K 候选"]
    end
    
    subgraph Stage2["阶段2: 向量重排"]
        B1["计算嵌入向量"]
        B2["余弦相似度排序"]
        B3["筛选高相似度候选"]
    end
    
    subgraph Stage3["阶段3: LLM 仲裁"]
        C1["上下文验证"]
        C2["语义等价判断"]
        C3{"最终决策"}
        C4["合并"]
        C5["新建"]
    end
    
    A1 --> A2 --> A3
    A3 --> B1 --> B2 --> B3
    B3 --> C1 --> C2 --> C3
    C3 -->|"等价"| C4
    C3 -->|"不等价"| C5
    
    style C3 fill:#FFD700
```

### 3.2 NIL 检测

当新实体与现有图谱中任何实体都不匹配时：

```mermaid
flowchart TB
    A["新实体: '装饰器模式'"] --> B{"相似度 < 阈值?"}
    B -->|"是"| C["NIL 检测触发"]
    C --> D["创建新的规范实体节点"]
    D --> E["标记来源: 老师A, 课程X"]
    
    B -->|"否"| F["合并到现有节点"]
    F --> G["添加别名"]
    G --> H["保留来源信息"]
    
    style C fill:#87CEEB
    style F fill:#90EE90
```

---

## 四、冲突处理机制

当多位老师的内容存在矛盾时：

### 4.1 冲突检测

```mermaid
flowchart TB
    A["老师A: 递归效率低"] --> C{"属性冲突检测"}
    B["老师B: 递归效率尚可"] --> C
    
    C -->|"检测到冲突"| D["创建视角节点"]
    D --> E["效率视角"]
    D --> F["可读性视角"]
    
    E --> G["链接到概念节点"]
    F --> G
    G --> H[("知识图谱")]
    
    style C fill:#FFD700
    style H fill:#90EE90
```

### 4.2 多视角保留策略

```
(:LearningResource {source: "老师A"})
    -[:TEACHES]->
(:CanonicalConcept {name: "递归"})
    <-[:TEACHES]-
(:LearningResource {source: "老师B"})
```

不同老师的讲解作为独立的 `LearningResource` 节点，都指向同一个 `CanonicalConcept`。

---

## 五、使用 graph-rag-agent 进行增量更新

### 5.1 基本命令

```bash
# 进入项目目录
cd graph-rag-agent

# 执行增量更新
python -m graphrag_agent.integrations.build.incremental_update \
    --input_dir ./new_courses/ \
    --mode incremental
```

### 5.2 增量更新配置

在 `.env` 文件中配置：

```env
# Neo4j 连接
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password

# 增量更新参数
INCREMENTAL_MODE=true
ENTITY_RESOLUTION_THRESHOLD=0.85
```

### 5.3 程序化调用

```python
from graphrag_agent.integrations.build import incremental_update

# 执行增量更新
result = incremental_update.run(
    input_files=["new_course.pdf"],
    mode="incremental",
    entity_resolution_threshold=0.85
)

print(f"新增实体: {result.new_entities}")
print(f"合并实体: {result.merged_entities}")
print(f"新增关系: {result.new_relations}")
```

---

## 六、更新后的验证

### 6.1 一致性检查

```mermaid
flowchart LR
    A["更新完成"] --> B["一致性验证"]
    B --> C{"检测问题?"}
    C -->|"孤岛节点"| D["标记待处理"]
    C -->|"断裂路径"| E["尝试自动修复"]
    C -->|"无问题"| F["更新成功 ✅"]
    
    style F fill:#90EE90
```

### 6.2 验证查询示例

```cypher
// 检查新增的课程内容
MATCH (r:LearningResource)
WHERE r.created_at > datetime() - duration('P1D')
RETURN r.title, r.source, r.instructor

// 检查实体合并情况
MATCH (c:CanonicalConcept)
WHERE size(c.aliases) > 1
RETURN c.name, c.aliases
```

---

## 七、完整更新流程图

```mermaid
flowchart TB
    subgraph Phase1["Phase 1: 准备"]
        A1["收集新课程文档"]
        A2["配置更新参数"]
    end
    
    subgraph Phase2["Phase 2: 处理"]
        B1["文档解析与分块"]
        B2["LLM 实体抽取"]
        B3["实体消歧去重"]
    end
    
    subgraph Phase3["Phase 3: 写入"]
        C1["图谱增量合并"]
        C2["关系链接创建"]
        C3["社区重新检测"]
    end
    
    subgraph Phase4["Phase 4: 验证"]
        D1["一致性检查"]
        D2["质量评估"]
        D3["日志记录"]
    end
    
    subgraph Result["最终结果"]
        E1[("更新后图谱 ✅")]
    end
    
    A1 --> A2 --> B1
    B1 --> B2 --> B3
    B3 --> C1 --> C2 --> C3
    C3 --> D1 --> D2 --> D3
    D3 --> E1
    
    style E1 fill:#90EE90
```

---

## 总结

| 步骤 | 说明 | 关键技术 |
|------|------|----------|
| 1️⃣ 文档处理 | 解析新课程文档 | text_chunker |
| 2️⃣ 实体抽取 | LLM 识别实体和关系 | extraction 模块 |
| 3️⃣ 实体消歧 | 字符串召回 + 向量重排 + NIL检测 | processing 模块 |
| 4️⃣ 图谱合并 | MERGE 操作，保留来源 | Neo4j Cypher |
| 5️⃣ 验证检查 | 一致性校验，质量评估 | evaluation 模块 |

> 💡 关键点：整个流程中最重要的是**实体消歧**步骤，它决定了能否实现"去重但保留多老师视角"的目标。
