# Tasks - Fix E2E Testing Issues

## Phase 1: 安装缺失依赖 (立即执行)

- [ ] 1.1 安装缺失的 3 个核心依赖
  ```bash
  pip install shutup==0.2.0 langgraph==0.3.18 graphdatascience==1.12
  ```

- [ ] 1.2 验证依赖安装成功
  ```bash
  python -c "import shutup; import langgraph; import graphdatascience; print('All dependencies OK')"
  ```

- [ ] 1.3 （可选）重新安装全部依赖确保一致性
  ```bash
  pip install -r requirements.txt
  ```

---

## Phase 2: 模块路径修正 (1天内)

- [ ] 2.1 添加 `TextChunker` 别名
  - 文件: `graphrag_agent/pipelines/ingestion/text_chunker.py`
  - 在文件末尾添加: `TextChunker = ChineseTextChunker`

- [ ] 2.2 更新 `graph/extraction/__init__.py` 导出
  - 文件: `graphrag_agent/graph/extraction/__init__.py`
  - 添加导出: `EntityRelationExtractor`, `GraphWriter`

- [ ] 2.3 更新 `search/__init__.py` 导出
  - 文件: `graphrag_agent/search/__init__.py`
  - 添加导出: `LocalSearch`, `GlobalSearch`

- [ ] 2.4 验证所有导入路径正确
  - 运行导入测试验证

---

## Phase 3: 测试脚本更新 (2天内)

- [ ] 3.1 创建/完善依赖检查脚本
  - 文件: `scripts/check_dependencies.py` 或 `check_deps.py`
  - 检查所有必需依赖

- [ ] 3.2 完善端到端 Mock 测试
  - 文件: `test_e2e_graphrag_mock.py`
  - 使用 Mock 模拟 LLM, Embeddings, Neo4j
  - 测试构建和查询流程

- [ ] 3.3 运行完整测试套件
  - 执行所有测试确保无回归

---

## Phase 4: 文档更新 (测试后)

- [ ] 4.1 更新 `assets/start.md`
  - 添加依赖检查说明
  - 添加常见问题解决方案

- [ ] 4.2 更新 `README.md`
  - 添加测试运行说明
  - 添加依赖问题排查指南

---

## Validation Checklist

- [ ] `python -c "import shutup; import langgraph; import graphdatascience"` 成功
- [ ] `python test_e2e_graphrag_mock.py` 无导入错误
- [ ] `python -c "from graphrag_agent.graph.extraction import EntityRelationExtractor, GraphWriter"` 成功
- [ ] `python -c "from graphrag_agent.search import LocalSearch"` 成功
- [ ] `python -c "from graphrag_agent.pipelines.ingestion.text_chunker import TextChunker"` 成功

---

## Error Summary (修复前)

| # | 阶段 | 错误类型 | 修复方式 |
|---|------|----------|----------|
| 1 | Import | `ModuleNotFoundError: shutup` | 安装 shutup |
| 2 | Import | `ModuleNotFoundError: langgraph` | 安装 langgraph |
| 3 | Document | `ImportError: TextChunker` | 添加别名 |
| 4 | Extraction | `ModuleNotFoundError: entity_relation_extractor` | 更新 __init__.py |
| 5 | Neo4j | `ModuleNotFoundError: graph_writer` | 更新 __init__.py |
| 6 | Search | `ImportError: local_search` | 更新 __init__.py |
| 7 | Agent | `ModuleNotFoundError: langgraph` | 安装 langgraph |
| 8 | Build | `ModuleNotFoundError: shutup` | 安装 shutup |
