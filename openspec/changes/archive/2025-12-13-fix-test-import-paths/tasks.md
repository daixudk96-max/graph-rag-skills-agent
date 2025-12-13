# fix-test-import-paths Tasks

## Phase 1: 修复核心依赖问题 (高优先级)

### 1.1 修复 graphdatascience 导入
- [x] 修改 `graphrag_agent/graph/processing/similar_entity.py`
- [x] 移除顶层 `from graphdatascience import GraphDataScience`
- [x] 在 `SimilarEntityDetector.__init__()` 中添加延迟导入和 try-except
- **验证**: `python -c "from graphrag_agent.config import settings; print('OK')"`

### 1.2 修复 EntityProperties 导出
- [x] 修改 `itext2kg/itext2kg/atom/models/__init__.py`
- [x] 添加 `from .entity import EntityProperties`
- [x] 更新 `__all__` 列表包含 `"EntityProperties"`
- **验证**: `python -c "from itext2kg.atom.models import EntityProperties; print('OK')"`

### 1.3 修复 temporal_kg.py 导入
- [x] 无需修改 `graphrag_agent/graph/structure/temporal_kg.py`
- [x] 在 `to_atom_kg()` 方法中已有从 `itext2kg.atom.models` 导入 EntityProperties
- **验证**: 在修复 1.2 后自动生效

---

## Phase 2: 修复测试脚本路径 (中优先级)

### 2.1 修复 verify_atom_integration.py
- [x] 修改 `graphrag_agent/tests/verify_atom_integration.py`
- [x] 替换 `os.path` 为 `pathlib.Path`
- [x] 设置 `PROJECT_ROOT = Path(__file__).resolve().parents[2]`
- **验证**: `python graphrag_agent/tests/verify_atom_integration.py`

### 2.2 修复 evaluate_all_agents.py
- [x] 修改 `graphrag_agent/evaluation/test/evaluate_all_agents.py`
- [x] 设置 `PROJECT_ROOT = Path(__file__).resolve().parents[3]`

### 2.3 修复 evaluate_deep_agent.py
- [x] 修改 `graphrag_agent/evaluation/test/evaluate_deep_agent.py`
- [x] 设置 `PROJECT_ROOT = Path(__file__).resolve().parents[3]`

### 2.4 修复 evaluate_fusion_agent.py
- [x] 修改 `graphrag_agent/evaluation/test/evaluate_fusion_agent.py`
- [x] 设置 `PROJECT_ROOT = Path(__file__).resolve().parents[3]`

### 2.5 修复 evaluate_graph_agent.py
- [x] 修改 `graphrag_agent/evaluation/test/evaluate_graph_agent.py`
- [x] 设置 `PROJECT_ROOT = Path(__file__).resolve().parents[3]`

### 2.6 修复 evaluate_hybrid_agent.py
- [x] 修改 `graphrag_agent/evaluation/test/evaluate_hybrid_agent.py`
- [x] 设置 `PROJECT_ROOT = Path(__file__).resolve().parents[3]`

### 2.7 修复 evaluate_naive_agent.py
- [x] 修改 `graphrag_agent/evaluation/test/evaluate_naive_agent.py`
- [x] 设置 `PROJECT_ROOT = Path(__file__).resolve().parents[3]`

---

## Phase 3: 验证 (依赖: Phase 1, Phase 2)

### 3.1 运行基础导入测试
- [x] 验证 graphdatascience 延迟导入生效
- [x] 确认模块可以被导入而不会崩溃

### 3.2 运行 ATOM 集成验证
- [x] 验证 EntityProperties 可从 itext2kg.atom.models 导入
- [x] 确认导出列表正确

### 3.3 验证测试脚本路径
- [x] 验证所有测试脚本使用 pathlib.Path.parents
- [x] 确认路径层级正确

---

## 并行化建议

```
Phase 1.1 ──┬──▶ Phase 3.1
Phase 1.2 ──┤
Phase 1.3 ──┤
            │
Phase 2.1 ──┼──▶ Phase 3.2
Phase 2.2 ──┤
Phase 2.3 ──┤
Phase 2.4 ──┼──▶ Phase 3.3
Phase 2.5 ──┤
Phase 2.6 ──┤
Phase 2.7 ──┘
```

- Phase 1.1, 1.2, 1.3 需要按顺序执行（存在依赖）
- Phase 2.x 可以并行执行
- Phase 3 在所有修改完成后统一验证

---

## 跳过的项目

| 项目 | 原因 |
|------|------|
| Neo4jTemporalWriter 方法检查 | 测试预期错误，非代码问题 |
| UnicodeEncodeError 警告 | 低优先级，不影响功能 |
| LLM Provider 检测警告 | Mock 测试相关，不影响生产 |
