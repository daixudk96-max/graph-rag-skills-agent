# ATOM 集成与知识图谱写入修复任务

## Phase 1: ATOM 集成（高优先级）

### 1.1 创建 build_kg_atom.py
- [x] 创建新脚本 `build_kg_atom.py`
- [x] 使用 `AtomExtractionAdapter.extract_from_chunks_sync()` 替代 mock 函数
- [x] 使用 `Neo4jTemporalWriter.write_temporal_kg()` 写入数据
- **验证**: `python build_kg_atom.py` 成功运行并输出时序属性

### 1.2 添加 TemporalKnowledgeGraph 序列化
- [x] 在 `temporal_kg.py` 添加 `to_dict()` 方法
- [x] 确保序列化结果包含 `t_obs`, `t_start`, `t_end`
- **验证**: 检查输出 JSON 包含时序字段

---

## Phase 2: 一致性校验（高优先级）

### 2.1 添加实体-关系一致性校验
- [x] 创建 `validate_graph_consistency()` 函数
- [x] 在 `write_kg_to_neo4j.py` 的写入前调用校验
- [x] 过滤悬空关系并记录警告
- **验证**: 运行 `write_kg_to_neo4j.py`，观察警告日志

### 2.2 改进 write_kg_to_neo4j.py
- [x] 移除静默 `try/except pass`
- [x] 添加预检查验证 source/target 存在性
- [x] 记录跳过的关系详情
- **验证**: 查看日志输出，确认失败关系被记录

---

## Phase 3: 关系键修复（中优先级）

### 3.1 生成关系唯一 ID
- [x] 为每条关系生成 `rel_id`（基于 source|target|type|chunk 哈希）
- [x] 修改写入 Cypher 使用 `rel_id` 作为去重键
- **验证**: 同一对节点的多条关系不被合并

### 3.2 统一去重策略
- [x] Python 端去重与 Neo4j 写入逻辑保持一致
- [x] 使用 `rel_id` 作为 MERGE 键
- **验证**: JSON 统计数与 Neo4j 实际数一致

---

## Phase 4: 属性存储优化（低优先级）

### 4.1 属性处理优化
- [x] 保留 JSON 序列化以支持复杂属性
- [x] 统一使用 `Neo4jTemporalWriter` 的存储方式
- **验证**: Neo4j 中属性可被查询

---

## Phase 5: 可选实体质量后处理（待后续迭代）

### 5.1 添加配置项
- [-] 在 `settings.py` 添加 `ENABLE_ENTITY_QUALITY_POSTPROCESS` (默认 `false`)
- [-] 在 `.env.example` 添加配置说明
- **验证**: 环境变量控制后处理是否运行

### 5.2 集成 EntityQualityProcessor
- [-] 在 `build_kg_atom.py` 添加可选后处理调用
- [-] 仅当配置启用时才导入和运行
- **验证**: `ENABLE_ENTITY_QUALITY_POSTPROCESS=true python build_kg_atom.py` 触发后处理

---

## 验证清单

### 已完成
- [x] Phase 1-4 核心功能已实现
- [x] `build_kg_atom.py` 脚本已创建
- [x] `to_dict()` 序列化方法已添加
- [x] `validate_graph_consistency()` 函数已实现
- [x] 关系唯一 ID 生成已实现

### 待手动验证
1. [x] 运行 `python build_kg_atom.py` 测试 ATOM 提取
2. [x] 检查输出 JSON 包含时序字段
3. [x] Neo4j Browser 验证节点和关系数量一致性
4. [x] Cypher 查询 `MATCH (n) RETURN n.atom_t_obs` 返回时序值

