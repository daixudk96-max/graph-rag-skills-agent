# 修复知识图谱写入与 ATOM 集成问题

## 背景

用户在执行知识图谱构建和写入测试时遇到两个问题：

1. **ATOM 特性未体现**：写入的知识图谱缺少 ATOM 时序属性（`t_start`, `t_end`, `t_obs`），与传统图谱无区别
2. **节点/关系数量不一致**：命令输出显示 10 个实体、52 个关系，但 Neo4j 浏览器显示的数量远少于此

## 根因分析

### 问题 1：ATOM 特性未体现

- `build_kg_demo.py` 使用 `mock_llm_extract_entities_relations` 模拟函数
- 未调用已实现的 `AtomExtractionAdapter` 和 `Neo4jTemporalWriter`
- 输出的 JSON 格式无时序字段（`t_obs`, `t_start`, `t_end`）

### 问题 2：节点/关系数量不一致

**2.1 实体去重逻辑缺陷**
```python
# build_kg_demo.py:265-277
for e in all_entities:
    key = (e["name"], e["type"])
    if key not in unique_entities:
        unique_entities[key] = e
    id_mapping[e["id"]] = unique_entities[key]["id"]
```
- `id_mapping` 仅对 `all_entities` 中实际出现的实体建立映射
- 关系可能引用"悬空" ID（如 `e_12_7` 在实体列表中不存在）
- 这些悬空关系在 JSON 统计中被计入，但写入时失败

**2.2 Neo4j 写入静默失败**
```python
# write_kg_to_neo4j.py:72-88
cypher = """
MATCH (source:KGEntity {entity_id: $source_id})
MATCH (target:KGEntity {entity_id: $target_id})
MERGE (source)-[r:RELATES {type: $rel_type}]->(target)
"""
try:
    session.run(cypher, ...)
except Exception as e:
    pass  # 静默跳过！
```
- `MATCH` 找不到节点时，整个关系创建失败
- `try/except` 静默吞掉异常，无日志记录

**2.3 关系被 MERGE 折叠**
- 使用 `MERGE ... {type: $rel_type}` 作为关系键
- 同一对节点、同一类型的多条关系会被合并为一条

**2.4 属性被 JSON 序列化**
```python
# write_kg_to_neo4j.py:66
properties=json.dumps(entity.get("properties", {}), ensure_ascii=False)
```
- 属性被序列化为字符串，Neo4j 无法原生查询

## 提议的修复方案

### Phase 1: 接入 ATOM + 时序写入（高优先级）

创建 `build_kg_atom.py` 替代 `build_kg_demo.py`：
- 使用 `AtomExtractionAdapter.extract_from_chunks_sync()` 提取时序知识图谱
- 使用 `Neo4jTemporalWriter.write_temporal_kg()` 写入带时序属性的数据
- JSON 输出包含完整的 `TemporalKnowledgeGraph` 序列化

### Phase 2: 修复一致性校验（高优先级）

改进 `build_kg_demo.py` 和 `write_kg_to_neo4j.py`：
- 写入前校验 `source/target` 是否在实体集合中
- 过滤悬空关系并记录警告日志
- 移除静默 `try/except`，改为记录失败信息

### Phase 3: 修复关系键策略（中优先级）

- 为关系生成稳定唯一 ID（如基于 `source|target|type|chunk_id` 的哈希）
- `MERGE` 使用 `rel_id` 而非 `type` 作为关系键
- 或改用 `CREATE` 配合 Python 端去重

### Phase 4: 优化属性存储（低优先级）

- 直接传递 dict 给 Neo4j，不做 JSON 序列化
- 统一使用 `Neo4jTemporalWriter` 的 `atom_*` 属性命名规范

### Phase 5: 可选的实体质量后处理（默认关闭）

添加配置项启用 GraphRAG 的 `EntityQualityProcessor` 作为可选后处理：

```python
# graphrag_agent/config/settings.py
ENABLE_ENTITY_QUALITY_POSTPROCESS = os.getenv("ENABLE_ENTITY_QUALITY_POSTPROCESS", "false").lower() == "true"
```

**工作流程**:
```
文档 → 分块 → [ATOM 提取] → [ATOM 合并] → [Neo4j 写入]
                 (无LLM)        (无LLM)           ↓
                                        [EntityQualityProcessor] ← 可选
                                              (需LLM)
```

**功能**:
- 实体消歧 (`EntityDisambiguator`)：将 mention 映射到规范实体
- 实体对齐 (`EntityAligner`)：合并具有相同 canonical_id 的实体
- NIL 检测：识别知识库中不存在的新实体

**配置**:
| 参数 | 默认值 | 说明 |
|------|--------|------|
| `ENABLE_ENTITY_QUALITY_POSTPROCESS` | `false` | 是否启用后处理 |
| `DISAMBIG_VECTOR_THRESHOLD` | `0.85` | 向量相似度阈值 |
| `ALIGNMENT_CONFLICT_THRESHOLD` | `0.5` | 冲突检测阈值 |

## 设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 去重方法 | ATOM embedding 相似度 | 无需 LLM，速度快 |
| 关系键策略 | `rel_id` 哈希 | 避免有效关系被折叠 |
| 后处理 | 可选（默认关闭） | 兼顾速度和精度需求 |

## 交叉引用

- 依赖: `graphrag_agent/graph/extraction/atom_adapter.py` (ATOM 适配器)
- 依赖: `graphrag_agent/graph/extraction/temporal_writer.py` (时序写入器)
- 依赖: `graphrag_agent/graph/processing/entity_quality.py` (EntityQualityProcessor)
- 相关: `openspec/changes/archive/2025-12-13-integrate-atom-temporal-kg/` (ATOM 集成提案)

