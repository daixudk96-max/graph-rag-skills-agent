# 设计文档：修复知识图谱写入与 ATOM 集成

## 架构概览

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            完整数据流                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  [文档] ──► [分块器] ──► [AtomExtractionAdapter] ──► [TemporalKG]       │
│                                ▲                          │              │
│                                │                          ▼              │
│                          LLM/Embeddings        [Neo4jTemporalWriter]     │
│                                                          │               │
│                                                          ▼               │
│                                                    [Neo4j DB]            │
│                                                 (带时序属性)              │
│                                                          │               │
│                           ┌──────────────────────────────┴─────┐         │
│                           │                                    │         │
│                    (默认路径)                          (可选后处理)       │
│                           │                                    │         │
│                     ┌─────▼──────┐               ┌─────────────▼───────┐ │
│                     │   完成     │               │ EntityQualityProcessor│
│                     │  (无LLM)   │               │   (需LLM, 高精度)    │
│                     └────────────┘               └──────────────────────┘│
│                                                                          │
│  配置: ENABLE_ENTITY_QUALITY_POSTPROCESS=true 启用可选后处理             │
└─────────────────────────────────────────────────────────────────────────┘
```


## 组件设计

### 1. build_kg_atom.py（新增）

```python
# 新增脚本，替代 build_kg_demo.py 进行 ATOM 测试

from graphrag_agent.graph.extraction import (
    AtomExtractionAdapter,
    create_temporal_writer,
)
from graphrag_agent.graph.structure import TemporalKnowledgeGraph

async def build_knowledge_graph_with_atom():
    """使用 ATOM 适配器构建时序知识图谱"""
    
    # 1. 初始化 ATOM 适配器
    adapter = AtomExtractionAdapter(
        llm_model=llm,
        embeddings_model=embeddings,
    )
    
    # 2. 提取时序知识图谱
    temporal_kg = await adapter.extract_from_chunks(
        chunks=text_chunks,
        observation_time=datetime.now().isoformat(),
    )
    
    # 3. 写入 Neo4j（带时序属性）
    writer = create_temporal_writer()
    stats = writer.write_temporal_kg(temporal_kg, merge_strategy="replace")
    
    # 4. 保存 JSON（包含时序字段）
    output_data = temporal_kg.to_dict()  # 需要实现序列化
    ...
```

### 2. 一致性校验模块

```python
# 添加到 write_kg_to_neo4j.py 或单独模块

def validate_graph_consistency(entities: List[dict], relations: List[dict]) -> Tuple[List[dict], List[dict]]:
    """
    校验实体-关系一致性，过滤悬空关系
    
    Returns:
        (valid_relations, invalid_relations)
    """
    entity_ids = {e["id"] for e in entities}
    
    valid = []
    invalid = []
    
    for rel in relations:
        source_valid = rel["source"] in entity_ids
        target_valid = rel["target"] in entity_ids
        
        if source_valid and target_valid:
            valid.append(rel)
        else:
            invalid.append({
                **rel,
                "error": f"Missing {'source' if not source_valid else 'target'}: "
                         f"{rel['source'] if not source_valid else rel['target']}"
            })
    
    if invalid:
        logger.warning(f"Filtered {len(invalid)} invalid relations with missing endpoints")
        for r in invalid[:5]:  # 只显示前5个
            logger.warning(f"  - {r}")
    
    return valid, invalid
```

### 3. 改进的 Neo4j 写入

```python
# 修改 write_kg_to_neo4j.py

def write_relations_with_logging(session, relations: List[dict], entity_ids: set):
    """写入关系，记录失败详情"""
    
    success_count = 0
    fail_count = 0
    
    for relation in relations:
        # 预检查
        if relation["source"] not in entity_ids:
            logger.warning(f"Skipping relation: source {relation['source']} not found")
            fail_count += 1
            continue
            
        if relation["target"] not in entity_ids:
            logger.warning(f"Skipping relation: target {relation['target']} not found")
            fail_count += 1
            continue
        
        # 写入
        cypher = """
        MATCH (source:KGEntity {entity_id: $source_id})
        MATCH (target:KGEntity {entity_id: $target_id})
        CREATE (source)-[r:RELATES]->(target)
        SET r.type = $rel_type,
            r.rel_id = $rel_id,  // 添加唯一ID
            r.properties = $properties,
            r.created_at = datetime()
        RETURN r
        """
        result = session.run(cypher, 
            source_id=relation["source"],
            target_id=relation["target"],
            rel_type=relation["type"],
            rel_id=f"{relation['source']}|{relation['target']}|{relation['type']}",
            properties=relation.get("properties", {})  # 不做 json.dumps
        )
        success_count += 1
    
    logger.info(f"Relations written: {success_count} success, {fail_count} skipped")
    return success_count, fail_count
```

### 4. TemporalKnowledgeGraph 序列化

```python
# 添加到 temporal_kg.py

@dataclass
class TemporalKnowledgeGraph:
    # ... 现有字段 ...
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化为可 JSON 化的字典（保留时序字段）"""
        return {
            "build_time": datetime.now().isoformat(),
            "statistics": {
                "entities": len(self.entities),
                "relationships": len(self.relationships),
            },
            "entities": [
                {
                    "id": e.id,
                    "name": e.name,
                    "label": e.label,
                    "properties": e.properties,
                    "t_obs": e.observation_times,      # ATOM 时序
                    "t_start": e.t_start,             # ATOM 时序
                    "t_end": e.t_end,                 # ATOM 时序
                    "embeddings": e.embeddings,
                }
                for e in self.entities
            ],
            "relationships": [
                {
                    "source": r.source_id,
                    "target": r.target_id,
                    "type": r.rel_type,
                    "properties": r.properties,
                    "t_obs": r.t_obs,                 # ATOM 时序
                    "t_start": r.t_start,             # ATOM 时序
                    "t_end": r.t_end,                 # ATOM 时序
                    "atomic_facts": r.atomic_facts,
                    "confidence": r.confidence,
                }
                for r in self.relationships
            ],
        }
```

## 验证策略

### 自动化测试

1. **单元测试**：`validate_graph_consistency()` 函数测试
2. **集成测试**：完整 ATOM 提取 → 写入 → 查询流程

### 手动验证

1. 运行 `build_kg_atom.py` 构建图谱
2. 检查 JSON 输出包含 `t_obs`, `t_start`, `t_end` 字段
3. 在 Neo4j Browser 验证节点数量与命令输出一致
4. 查询时序属性：`MATCH (n:KGEntity) RETURN n.atom_t_obs, n.atom_t_start LIMIT 5`
