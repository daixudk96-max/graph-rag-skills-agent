# [Phase 1] Integrate ATOM Temporal Knowledge Graph Extraction

> **分阶段迁移计划 Phase 1/3**: 添加 ATOM 作为可选提取器，默认关闭 (`ATOM_ENABLED=false`)

## Summary

将 ATOM（AdapTive and OptiMized Dynamic Temporal Knowledge Graph Construction）从 iText2KG 项目整合到 graph-rag-agent 项目中，作为**可选的**时序知识图谱提取器。

**本阶段（Phase 1）目标**：
- ✅ 添加 ATOM 提取能力（默认关闭）
- ✅ 保持完全向后兼容
- ✅ 验证 ATOM 在项目中的效果

**后续阶段**：
- Phase 2: 验证通过后，修改默认值为 `ATOM_ENABLED=true`
- Phase 3: 确认稳定后，可选择移除旧提取器

**ATOM 核心优势**：
1. **时序知识图谱**：双时间建模（`t_obs` 观察时间 vs `t_start/t_end` 有效期）
2. **原子事实分解**：解决 LLM 在长文本中"遗忘"事实的问题
3. **并行 5-元组提取**：`(subject, predicate, object, t_start, t_end)` 直接提取
4. **高效并行合并**：基于余弦相似度，93.8% 延迟降低


## Problem Statement

当前 graph-rag-agent 的实体关系提取（`EntityRelationExtractor`）存在以下限制：

1. **无时序建模**：无法追踪事实的时间有效性
2. **分离式提取**：先提取实体再提取关系，LLM 调用次数翻倍
3. **串行处理**：合并依赖 LLM，难以并行化
4. **增量更新困难**：缺乏高效的图谱合并机制

ATOM 提供了经过验证的解决方案：
- ~31% 事实完整性提升
- ~18% 时序完整性提升  
- ~17% 稳定性提升
- 93.8% 延迟降低（vs Graphiti）

## Proposed Solution

### Integration Strategy: Adapter Pattern

创建适配层将 ATOM 能力整合到现有架构中，而非替换现有组件：

```
┌────────────────────────────────────────────────────────────┐
│                graph-rag-agent/graphrag_agent              │
│                                                            │
│  ┌─────────────────┐    ┌─────────────────────────────┐   │
│  │ DocumentProcessor│───▶│     AtomExtractionAdapter    │   │
│  │  (chunking)      │    │ ┌─────────────────────────┐ │   │
│  └─────────────────┘    │ │ Module-1: Atomic Facts  │ │   │
│                          │ │ Module-2: 5-Tuple Ext   │ │   │
│                          │ │ Module-3: Parallel Merge│ │   │
│                          │ └─────────────────────────┘ │   │
│                          └──────────────┬──────────────┘   │
│                                         │                   │
│  ┌─────────────────┐                   ▼                   │
│  │ EntityExtractor │◀──fallback── AtomKnowledgeGraph      │
│  │   (existing)    │                    │                   │
│  └─────────────────┘                   ▼                   │
│                          ┌─────────────────────────────┐   │
│                          │   Neo4jGraphWriter          │   │
│                          │   (unified storage)         │   │
│                          └─────────────────────────────┘   │
└────────────────────────────────────────────────────────────┘
```

### Key Components

1. **AtomExtractionAdapter** (`graphrag_agent/graph/extraction/atom_adapter.py`)
   - 包装 ATOM 的 `Atom` 类
   - 适配现有的 LLM 和 embedding 模型接口
   - 提供与 `EntityRelationExtractor` 兼容的接口

2. **TemporalKnowledgeGraph** (`graphrag_agent/graph/structure/temporal_kg.py`)
   - 扩展现有知识图谱模型以支持时序属性
   - 转换 ATOM 的 `KnowledgeGraph` 到 graph-rag-agent 格式

3. **Neo4jTemporalWriter** (`graphrag_agent/graph/extraction/temporal_writer.py`)
   - 扩展 `GraphWriter` 支持时序属性存储
   - 支持 ATOM 的 5-元组关系模型

4. **Configuration Extension** (`graphrag_agent/config/settings.py`)
   - 添加 ATOM 相关配置参数
   - 支持选择提取策略（ATOM vs 传统）

## Capabilities Delivered

| Capability | Description |
|------------|-------------|
| `atom-extraction` | 使用 ATOM 提取时序知识图谱 |
| `temporal-kg-storage` | 支持时序属性的 Neo4j 存储 |
| `incremental-merge` | ATOM 并行增量合并机制 |

## Out of Scope

- 修改现有 `EntityRelationExtractor` 核心逻辑
- 更改现有 Neo4j 数据模型（仅添加新属性）
- 社区检测算法的集成（保持现有 Leiden/SLLPA）

## Dependencies

- `itext2kg` package（已在 `C:\github\graph-rag-agent\itext2kg` 本地部署）
- LangChain compatible LLM and embeddings
- Neo4j 5.x+ (for temporal property support)

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| ATOM API 变更 | 使用 adapter pattern 隔离依赖 |
| 性能回归 | 保留现有提取器作为 fallback |
| Neo4j schema 冲突 | 使用新属性名前缀 `atom_` |
