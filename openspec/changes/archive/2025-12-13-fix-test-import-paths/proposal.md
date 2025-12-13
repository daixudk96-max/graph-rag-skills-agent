# Change: 修复 ATOM 集成测试发现的错误

## Why

在 Phase 2 (enable-atom-default) 测试中发现 5 个错误 + 若干警告，阻碍了 ATOM 时序知识图谱功能的正常使用和验证。这些问题包括依赖缺失、模块导入错误和测试脚本路径问题。

## What Changes

- **[高优先级]** 延迟导入 `graphdatascience` 模块，避免模块加载时直接崩溃
- **[高优先级]** 修复 `itext2kg.atom.models` 导出缺失 `EntityProperties`
- **[高优先级]** 修复 `temporal_kg.py` 中 `to_atom_kg()` 的导入语句
- **[中优先级]** 修复测试脚本的 `sys.path` 路径设置
- **[低优先级]** 更新 `requirements.txt` 添加 `graphdatascience` 依赖

## Impact

- Affected specs: `atom-extraction`
- Affected code:
  - `graphrag_agent/graph/processing/similar_entity.py` (延迟导入)
  - `itext2kg/itext2kg/atom/models/__init__.py` (导出 EntityProperties)
  - `graphrag_agent/graph/structure/temporal_kg.py` (修复导入)
  - `graphrag_agent/tests/verify_atom_integration.py` (路径修复)
  - `graphrag_agent/evaluation/test/evaluate_*.py` (6 个文件路径修复)

---

## 问题详情

### 错误 1: 缺少 graphdatascience 模块 [高优先级]
```
ModuleNotFoundError: No module named 'graphdatascience'
```
- **位置**: `graphrag_agent/graph/processing/similar_entity.py:2`
- **影响**: 导入 settings 和 build_graph.py 时会触发
- **修复**: 将 `from graphdatascience import GraphDataScience` 移至 `__init__` 方法内，添加 try-except 保护

### 错误 2: Neo4jTemporalWriter 方法检查失败 [跳过]
```
AttributeError: 缺少方法: ['_write_entities', '_write_relationships']
```
- **状态**: ⚠️ 测试预期错误，非实际代码错误
- **说明**: 测试检查的方法名与实现名称不匹配（实际为 `_batch_write_*`）

### 错误 3 & 4: EntityProperties 导入失败 [高优先级]
```
ImportError: cannot import name 'EntityProperties' from 'itext2kg.atom.models'
```
- **位置**: `graphrag_agent/graph/structure/temporal_kg.py:321-327`
- **原因**: `EntityProperties` 定义在 `entity.py` 但未在 `__init__.py` 中导出
- **修复**: 
  1. 在 `itext2kg/atom/models/__init__.py` 添加 `EntityProperties` 导出
  2. 或直接从 `itext2kg.atom.models.entity` 导入

### 错误 5: 测试脚本路径问题 [中优先级]
```
ModuleNotFoundError: No module named 'graphrag_agent'
```
- **位置**: `graphrag_agent/tests/verify_atom_integration.py:11`
- **修复**: 使用 `Path(__file__).resolve().parents[2]`

---

## 修复方案

### Patch 1: similar_entity.py 延迟导入
```diff
-import time
-from graphdatascience import GraphDataScience
+import time
 from typing import Tuple, List, Any, Dict
```
并在 `__init__` 方法内添加：
```python
try:
    from graphdatascience import GraphDataScience
except ImportError as exc:
    raise ImportError(
        "graphdatascience package is required. "
        "Install with `pip install graphdatascience`."
    ) from exc
```

### Patch 2: itext2kg models 导出 EntityProperties
```diff
-from .entity import Entity
+from .entity import Entity, EntityProperties
-__all__ = ["Entity", "Relationship", ...]
+__all__ = ["Entity", "EntityProperties", "Relationship", ...]
```

### Patch 3: temporal_kg.py 修复导入
```diff
+from itext2kg.atom.models.entity import EntityProperties
```

### Patch 4: 测试脚本路径修复
```diff
-sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
+from pathlib import Path
+PROJECT_ROOT = Path(__file__).resolve().parents[2]
+sys.path.insert(0, str(PROJECT_ROOT))
```

---

## 警告信息 (不在本阶段修复)

| 警告 | 原因 | 建议 |
|------|------|------|
| UnicodeEncodeError (GBK) | Windows 终端编码限制 | 设置 UTF-8 或移除日志表情符号 |
| LLM Provider 自动检测失败 | Mock 测试不影响生产 | 仅测试警告，可忽略 |

## Out of Scope

- 项目根目录下的测试文件 (`test_atom.py` 等)
- 其他非 ATOM 相关的代码
