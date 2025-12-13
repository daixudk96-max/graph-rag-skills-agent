# graph-rag-agent vs Graphiti：全方位对比分析

## 一、项目概览

```mermaid
flowchart TB
    subgraph GRA["graph-rag-agent"]
        GRA_T["🎯 定位：GraphRAG + DeepSearch 问答系统"]
        GRA_F["📍 聚焦：私域知识问答、多Agent协作"]
        GRA_L["🌐 语言：Python"]
        GRA_S["⭐ Stars：开源社区项目"]
    end
    
    subgraph Graphiti["Graphiti (Zep)"]
        G_T["🎯 定位：实时时序知识图谱引擎"]
        G_F["📍 聚焦：AI Agent 记忆系统、时序推理"]
        G_L["🌐 语言：Python"]
        G_S["⭐ Stars：Zep商业公司支持"]
    end
    
    style GRA fill:#87CEEB
    style Graphiti fill:#90EE90
```

| 维度 | graph-rag-agent | Graphiti |
|------|-----------------|----------|
| **开发者** | 个人/社区开源 | Zep 公司 (商业支持) |
| **主要用途** | 私域知识问答系统 | AI Agent 长期记忆 |
| **核心理念** | GraphRAG + DeepSearch | 时序知识图谱 + 情景记忆 |
| **数据库** | Neo4j | Neo4j |
| **MCP 支持** | ❌ 无 | ✅ 内置 MCP Server |

---

## 二、架构对比

```mermaid
flowchart TB
    subgraph GRA_Arch["graph-rag-agent 架构"]
        A1["文档处理<br/>PDF/MD/DOCX"] --> A2["实体抽取<br/>LLM驱动"]
        A2 --> A3["实体消歧<br/>向量+字符串"]
        A3 --> A4["图谱构建<br/>Neo4j"]
        A4 --> A5["多级检索<br/>Local/Global/Hybrid"]
        A5 --> A6["多Agent协作<br/>Plan-Execute-Report"]
        A6 --> A7["问答生成"]
    end
    
    subgraph Graphiti_Arch["Graphiti 架构"]
        B1["情景输入<br/>Episode"] --> B2["实体抽取<br/>LLM驱动"]
        B2 --> B3["双时态建模<br/>事件时间+摄入时间"]
        B3 --> B4["三层子图<br/>Episode/Entity/Community"]
        B4 --> B5["混合检索<br/>语义+关键词+遍历"]
        B5 --> B6["时序推理"]
    end
    
    style A6 fill:#FFD700
    style B3 fill:#FFD700
```

---

## 三、核心功能对比

### 3.1 功能矩阵

```mermaid
flowchart LR
    subgraph Features["功能对比"]
        subgraph GRA["graph-rag-agent ✓"]
            G1["✅ 多格式文档处理"]
            G2["✅ 实体消歧对齐"]
            G3["✅ 增量更新"]
            G4["✅ 社区检测"]
            G5["✅ 多Agent编排"]
            G6["✅ DeepSearch"]
            G7["✅ 证据链追踪"]
            G8["✅ 前后端界面"]
            G9["✅ 评估系统"]
        end
        
        subgraph GraphitiF["Graphiti ✓"]
            H1["✅ 时序建模"]
            H2["✅ 情景记忆"]
            H3["✅ 双时态追踪"]
            H4["✅ MCP Server"]
            H5["✅ 增量更新"]
            H6["✅ 混合检索"]
            H7["✅ 自定义实体"]
            H8["✅ 商业支持"]
        end
    end
    
    style G5 fill:#90EE90
    style G6 fill:#90EE90
    style H1 fill:#90EE90
    style H2 fill:#90EE90
    style H4 fill:#90EE90
```

### 3.2 详细功能表

| 功能类别 | graph-rag-agent | Graphiti | 优势方 |
|---------|-----------------|----------|--------|
| **文档处理** | ✅ PDF/MD/DOCX/CSV/JSON/YAML | ⚠️ 主要是文本/JSON | graph-rag-agent |
| **实体抽取** | ✅ LLM驱动 | ✅ LLM驱动 | 持平 |
| **实体消歧** | ✅ 字符串+向量+NIL检测 | ✅ 语义匹配 | graph-rag-agent |
| **时序建模** | ❌ 无 | ✅ 双时态模型 | **Graphiti** |
| **情景记忆** | ❌ 无 | ✅ Episode概念 | **Graphiti** |
| **增量更新** | ✅ 文件变更监控 | ✅ 实时增量 | 持平 |
| **社区检测** | ✅ Leiden + SLLPA | ✅ Community Subgraph | 持平 |
| **检索方式** | ✅ Local/Global/Hybrid/Deep | ✅ 语义+BM25+遍历 | graph-rag-agent |
| **Agent编排** | ✅ Plan-Execute-Report | ❌ 仅提供图谱API | **graph-rag-agent** |
| **MCP接口** | ❌ 无 | ✅ 内置 MCP Server | **Graphiti** |
| **前端界面** | ✅ 完整Web界面 | ❌ 仅后端API | graph-rag-agent |
| **评估系统** | ✅ 20+评估指标 | ❌ 无 | graph-rag-agent |
| **商业支持** | ❌ 社区维护 | ✅ Zep公司支持 | Graphiti |

---

## 四、时序处理能力对比

这是两个项目**最大的差异点**：

```mermaid
flowchart TB
    subgraph GRA_Time["graph-rag-agent 时序处理"]
        T1["创建时间戳"]
        T2["最后更新时间"]
        T3["文件变更检测"]
        
        T1 --> T4["基础时间记录"]
        T2 --> T4
        T3 --> T4
    end
    
    subgraph Graphiti_Time["Graphiti 时序处理"]
        S1["事件时间 t_event<br/>(事件发生时间)"]
        S2["摄入时间 t_ingest<br/>(系统学习时间)"]
        S3["有效期 t_valid/t_invalid<br/>(事实有效区间)"]
        
        S1 --> S4["双时态模型<br/>Bi-temporal"]
        S2 --> S4
        S3 --> S4
        
        S4 --> S5["时序查询能力"]
        S5 --> S6["'2023年CEO是谁?'"]
        S5 --> S7["'何时学到这个信息?'"]
    end
    
    style S4 fill:#FFD700
    style S6 fill:#90EE90
    style S7 fill:#90EE90
```

| 时序能力 | graph-rag-agent | Graphiti |
|---------|-----------------|----------|
| 记录创建时间 | ✅ | ✅ |
| 记录更新时间 | ✅ | ✅ |
| 事件发生时间 | ❌ | ✅ |
| 事实有效期 | ❌ | ✅ |
| 时间点查询 | ❌ | ✅ "2020年X是什么?" |
| 事实演变追踪 | ❌ | ✅ "X如何变化?" |

---

## 五、数据模型对比

```mermaid
erDiagram
    %% graph-rag-agent 模型
    GRA_DOCUMENT ||--o{ GRA_CHUNK : contains
    GRA_CHUNK ||--o{ GRA_ENTITY : mentions
    GRA_ENTITY ||--o{ GRA_ENTITY : relates_to
    GRA_ENTITY {
        string id
        string name
        string type
        string description
        datetime created_at
        datetime last_updated
        boolean needs_reembedding
    }
    
    %% Graphiti 模型
    GRAPHITI_EPISODE ||--o{ GRAPHITI_ENTITY : extracts
    GRAPHITI_ENTITY ||--o{ GRAPHITI_ENTITY : relates_to
    GRAPHITI_ENTITY {
        string uuid
        string name
        string entity_type
        datetime created_at
        string group_id
    }
    
    GRAPHITI_EDGE {
        string uuid
        string fact
        datetime t_valid
        datetime t_invalid
        datetime created_at
        boolean expired
    }
```

---

## 六、适用场景对比

```mermaid
flowchart TB
    subgraph Scenarios["适用场景"]
        subgraph GRA_Use["graph-rag-agent 适合"]
            U1["📚 企业知识库问答"]
            U2["📄 文档智能检索"]
            U3["🔍 深度研究分析"]
            U4["🎓 教育内容整合"]
            U5["💼 多文档综合问答"]
        end
        
        subgraph Graphiti_Use["Graphiti 适合"]
            V1["🤖 AI Agent长期记忆"]
            V2["💬 对话历史管理"]
            V3["📅 时序事件追踪"]
            V4["📊 动态数据更新"]
            V5["🔄 实时信息系统"]
        end
    end
    
    style U4 fill:#FFD700
    style V1 fill:#FFD700
```

---

## 七、性能与可扩展性

| 指标 | graph-rag-agent | Graphiti |
|------|-----------------|----------|
| **批量处理** | ✅ 支持大规模文档 | ⚠️ 偏向实时增量 |
| **并行处理** | ✅ MAX_WORKERS配置 | ✅ 异步处理 |
| **缓存机制** | ✅ 多级缓存 | ⚠️ 基础缓存 |
| **延迟** | 中等 (批量优化) | 低 (实时优化) |
| **可扩展性** | ✅ 模块化设计 | ✅ 模块化设计 |

---

## 八、总结对比图

```mermaid
radar
    title 能力雷达图
    x_axis_label 功能维度
    
    "graph-rag-agent" : [8, 9, 7, 3, 8, 9, 8, 2]
    "Graphiti" : [5, 7, 8, 10, 6, 6, 4, 9]
    
    labels: ["文档处理", "检索能力", "增量更新", "时序建模", "实体消歧", "Agent编排", "可视化", "MCP集成"]
```

> 注：由于 Mermaid 不支持雷达图，以下是文字版对比：

| 维度 | graph-rag-agent | Graphiti | 说明 |
|------|-----------------|----------|------|
| 文档处理 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | GRA 支持更多格式 |
| 检索能力 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | GRA 多级检索更丰富 |
| 增量更新 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Graphiti 实时性更强 |
| 时序建模 | ⭐⭐ | ⭐⭐⭐⭐⭐ | Graphiti 核心优势 |
| 实体消歧 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | GRA 方法更全面 |
| Agent编排 | ⭐⭐⭐⭐⭐ | ⭐⭐ | GRA 核心优势 |
| 可视化 | ⭐⭐⭐⭐⭐ | ⭐⭐ | GRA 有完整界面 |
| MCP集成 | ⭐ | ⭐⭐⭐⭐⭐ | Graphiti 内置 MCP |

---

## 九、选择建议

```mermaid
flowchart TB
    Q["您的需求是什么?"] --> A{"需要时序推理?"}
    
    A -->|"是，需要追踪事实变化"| G["选择 Graphiti"]
    A -->|"否，主要是静态知识"| B{"需要多Agent编排?"}
    
    B -->|"是，复杂问答流程"| C["选择 graph-rag-agent"]
    B -->|"否"| D{"需要 MCP 集成?"}
    
    D -->|"是，Claude/其他Agent调用"| G
    D -->|"否"| E{"需要可视化界面?"}
    
    E -->|"是，需要前端"| C
    E -->|"否，只要API"| F["两者都可以"]
    
    style C fill:#87CEEB
    style G fill:#90EE90
```

### 选择 graph-rag-agent 如果：
- ✅ 需要处理多种格式文档
- ✅ 需要多Agent协作问答
- ✅ 需要可视化的Web界面
- ✅ 需要深度研究和证据追踪
- ✅ 做教育内容整合项目

### 选择 Graphiti 如果：
- ✅ 需要时序推理（"过去X是什么"）
- ✅ 需要 AI Agent 长期记忆
- ✅ 需要 MCP 协议集成
- ✅ 数据频繁变化，需实时更新
- ✅ 需要商业支持和维护

---

## 十、组合使用建议

**两个项目可以互补**：

```mermaid
flowchart LR
    subgraph Combined["最佳组合方案"]
        A["Graphiti<br/>时序记忆层"] --> B["graph-rag-agent<br/>问答编排层"]
        B --> C["用户界面"]
        
        A -.->|"提供时序上下文"| B
        B -.->|"调用时序查询"| A
    end
    
    style A fill:#90EE90
    style B fill:#87CEEB
```

- 用 **Graphiti** 管理时序知识和 Agent 记忆
- 用 **graph-rag-agent** 做复杂问答编排和用户界面
