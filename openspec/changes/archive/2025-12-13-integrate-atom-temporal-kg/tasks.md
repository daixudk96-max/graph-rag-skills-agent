# ATOM Integration Tasks

## Phase 1: Foundation (依赖: 无)

### 1.1 配置 iText2KG 依赖
- [ ] 将 `itext2kg` 添加到 `requirements.txt`
- [ ] 验证本地 `itext2kg` 包导入正常
- [ ] 添加 ATOM 相关环境变量到 `.env.example`
- **验证**: `python -c "from itext2kg.atom import Atom; print('OK')"`

### 1.2 扩展配置模块
- [ ] 在 `graphrag_agent/config/settings.py` 添加 ATOM 配置参数
- [ ] 更新 `.env.example` 文档
- **验证**: 检查配置加载正确

---

## Phase 2: 核心组件 (依赖: Phase 1)

### 2.1 创建时序知识图谱模型
- [ ] 创建 `graphrag_agent/graph/structure/temporal_kg.py`
- [ ] 定义 `TemporalRelationship` 和 `TemporalKnowledgeGraph` 数据类
- [ ] 实现 ATOM KG 到 graph-rag-agent 格式的转换方法
- **验证**: 单元测试 `test/test_temporal_kg.py`

### 2.2 创建 ATOM 适配器
- [ ] 创建 `graphrag_agent/graph/extraction/atom_adapter.py`
- [ ] 实现 `AtomExtractionAdapter` 类
- [ ] 适配 LLM 和 embeddings 模型接口
- [ ] 实现 `extract_from_chunks()` 异步方法
- [ ] 实现 `incremental_update()` 增量更新方法
- **验证**: 单元测试 `test/test_atom_adapter.py`

### 2.3 创建时序 Neo4j 写入器
- [ ] 创建 `graphrag_agent/graph/extraction/temporal_writer.py`
- [ ] 继承 `GraphWriter` 添加时序属性支持
- [ ] 实现 `write_temporal_kg()` 方法
- [ ] 实现时序属性的 Cypher 查询生成
- **验证**: 单元测试 + Neo4j 集成测试

---

## Phase 3: 集成 (依赖: Phase 2)

### 3.1 更新图谱构建入口
- [ ] 修改 `graphrag_agent/integrations/build/build_graph.py`
- [ ] 添加 ATOM 提取策略选项
- [ ] 实现策略切换逻辑
- **验证**: 端到端测试

### 3.2 添加增量更新支持
- [ ] 修改 `graphrag_agent/integrations/build/incremental_update.py`
- [ ] 集成 ATOM 的并行合并机制
- **验证**: 增量更新测试

---

## Phase 4: 测试与文档 (依赖: Phase 3)

### 4.1 添加单元测试
- [ ] `test/test_atom_adapter.py` - 适配器测试
- [ ] `test/test_temporal_kg.py` - 时序模型测试
- [ ] `test/test_temporal_writer.py` - Neo4j 写入测试

### 4.2 添加集成测试
- [ ] 端到端文档处理测试
- [ ] Neo4j 数据验证测试
- [ ] 性能对比测试

### 4.3 更新文档
- [ ] 更新 `graphrag_agent/readme.md`
- [ ] 更新 `graphrag_agent/graph/readme.md`
- [ ] 添加 ATOM 使用示例

---

## 并行化建议

```
Phase 1.1 ──┬──▶ Phase 2.1 ──┬──▶ Phase 3.1 ──▶ Phase 4.1-4.3
Phase 1.2 ──┘                │
                             │
           Phase 2.2 ────────┤
           Phase 2.3 ────────┘──▶ Phase 3.2
```

- Phase 2.1, 2.2, 2.3 可以并行开发
- Phase 3.1, 3.2 依赖 Phase 2 完成
- Phase 4 测试和文档可以随进度逐步添加
