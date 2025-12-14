# Fix End-to-End Testing Issues

## Summary

本提案旨在修复 GraphRAG 项目端到端测试中发现的 8 个关键错误，这些错误阻止了项目的完整流程测试。问题主要涉及：

1. **依赖缺失**：`shutup`、`langgraph` 和 `graphdatascience` 未正确安装
2. **模块路径错误**：多个模块的导入路径与实际文件位置不匹配
3. **类名不一致**：部分类的导入名称与实际定义不符

## Problem Statement

在执行端到端测试（知识图谱构建到查询响应的完整流程）时，发现以下错误：

| # | 阶段 | 错误类型 | 根本原因 |
|---|------|----------|----------|
| 1 | Import | `ModuleNotFoundError: shutup` | `build_graph.py` 依赖 `shutup` 包未安装 |
| 2 | Import | `ModuleNotFoundError: langgraph` | Agent 基类依赖 `langgraph` 包未安装 |
| 3 | Document | `ImportError: TextChunker` | 类名为 `ChineseTextChunker` 而非 `TextChunker` |
| 4 | Extraction | `ModuleNotFoundError: entity_relation_extractor` | 实际文件名为 `entity_extractor.py` |
| 5 | Neo4j | `ModuleNotFoundError: graph_writer` | `graph_writer.py` 位于 `graph/extraction/` 而非 `graph/core/` |
| 6 | Search | `ImportError: local_search` | `LocalSearch` 是类不是函数 |
| 7 | Agent | `ModuleNotFoundError: langgraph` | 同错误 #2 |
| 8 | Build | `ModuleNotFoundError: shutup` | 同错误 #1 |

### 依赖检查结果

经过依赖检查，发现以下 3 个核心依赖未安装：

| 依赖 | 版本 | 用途 | 状态 |
|------|------|------|------|
| `shutup` | 0.2.0 | 抑制警告输出（构建模块需要） | ❌ 未安装 |
| `langgraph` | 0.3.18 | Agent 编排框架（所有 Agent 需要） | ❌ 未安装 |
| `graphdatascience` | 1.12 | Neo4j 图数据科学库（社区检测需要） | ❌ 未安装 |

## Proposed Solution

### 1. 安装缺失依赖

**立即执行以下命令安装缺失依赖**：

```bash
pip install shutup==0.2.0 langgraph==0.3.18 graphdatascience==1.12
```

或者重新安装全部依赖：

```bash
pip install -r requirements.txt
```

**验证安装**：

```bash
python -c "import shutup; import langgraph; import graphdatascience; print('All dependencies OK')"
```

### 2. 模块路径修正

**2.1 文本分块器别名**

在 `graphrag_agent/pipelines/ingestion/text_chunker.py` 添加别名：
```python
TextChunker = ChineseTextChunker  # 兼容别名
```

**2.2 提取模块导出**

更新 `graphrag_agent/graph/extraction/__init__.py`：
```python
from .entity_extractor import EntityRelationExtractor
from .graph_writer import GraphWriter
from .atom_adapter import AtomExtractionAdapter
from .temporal_writer import Neo4jTemporalWriter

__all__ = [
    'EntityRelationExtractor',
    'GraphWriter', 
    'AtomExtractionAdapter',
    'Neo4jTemporalWriter'
]
```

**2.3 搜索模块导出**

更新 `graphrag_agent/search/__init__.py`：
```python
from .local_search import LocalSearch
from .global_search import GlobalSearch

__all__ = ['LocalSearch', 'GlobalSearch']
```

### 3. 测试脚本更新

**4.1 创建端到端 Mock 测试**

新增 `test/test_e2e_graphrag_mock.py`：
- 使用 Mock 模拟所有外部 API
- 测试完整构建-查询流程
- 记录所有错误供后续修复

**4.2 依赖检查测试**

新增 `test/test_dependencies.py`：
- 验证所有必需依赖已安装
- 验证可选依赖缺失时有友好提示

### 4. 依赖注入支持（可选）

为核心类添加依赖注入支持，便于测试：

```python
class KnowledgeGraphBuilder:
    def __init__(self, llm=None, embeddings=None, graph=None):
        self.llm = llm or get_llm_model()
        self.embeddings = embeddings or get_embeddings_model()
        # ...
```

## Files to Modify

| 文件 | 修改类型 | 说明 |
|------|----------|------|
| `graphrag_agent/pipelines/ingestion/text_chunker.py` | MODIFY | 添加 TextChunker 别名 |
| `graphrag_agent/graph/extraction/__init__.py` | MODIFY | 统一导出常用类 |
| `graphrag_agent/search/__init__.py` | MODIFY | 统一导出搜索类 |
| `test/test_e2e_graphrag_mock.py` | NEW | 新增端到端 Mock 测试 |
| `scripts/check_dependencies.py` | NEW | 依赖检查脚本 |

## Testing Strategy

1. **依赖测试**：验证依赖检查脚本正确识别缺失依赖
2. **端到端测试**：使用 Mock 运行完整流程
3. **导入测试**：验证模块路径修正后导入正常

## Risks and Mitigations

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 别名导致命名混乱 | 低 | 文档中明确推荐用法 |
| 依赖安装失败 | 中 | 提供依赖检查脚本和安装指南 |

## Timeline

- Phase 1 (立即): 安装缺失依赖
- Phase 2 (1天): 更新模块导出和别名
- Phase 3 (2天): 新增测试脚本和验证
