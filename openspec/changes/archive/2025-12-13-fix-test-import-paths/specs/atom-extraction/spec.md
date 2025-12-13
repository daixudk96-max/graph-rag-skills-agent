## ADDED Requirements

### Requirement: 模块加载容错性

ATOM 相关模块 MUST 在可选依赖缺失时提供明确的错误信息，而非在模块加载阶段直接崩溃。

#### Scenario: graphdatascience 未安装时的优雅降级

**Given** `graphdatascience` 包未安装
**When** 用户导入 `graphrag_agent.config.settings` 或相关模块
**Then** 模块应成功导入
**And** 仅在实际调用 `SimilarEntityDetector` 时抛出明确的 `ImportError`

### Requirement: itext2kg 模型完整导出

`itext2kg.atom.models` 模块 MUST 导出所有在 `temporal_kg.py` 中使用的类型。

#### Scenario: EntityProperties 可从 itext2kg.atom.models 导入

**Given** itext2kg 包已安装
**When** 执行 `from itext2kg.atom.models import EntityProperties`
**Then** 导入应成功
**And** `EntityProperties` 类可用于创建实体属性对象

#### Scenario: TemporalKnowledgeGraph 到 ATOM KG 转换

**Given** 存在一个 `TemporalKnowledgeGraph` 实例
**When** 调用 `kg.to_atom_kg()` 方法
**Then** 转换应成功完成
**And** 返回有效的 `itext2kg.atom.models.KnowledgeGraph` 对象

### Requirement: 测试脚本可移植性

ATOM 相关的验证和测试脚本 MUST 能够从项目根目录正确运行，无需额外配置。

#### Scenario: 从项目根目录运行 ATOM 集成验证

**Given** 用户在项目根目录 (`graph-rag-agent/`)
**When** 用户执行 `python graphrag_agent/tests/verify_atom_integration.py`
**Then** 脚本应成功导入 `graphrag_agent` 包
**And** 完成所有验证测试

#### Scenario: 从项目根目录运行评估脚本

**Given** 用户在项目根目录 (`graph-rag-agent/`)
**When** 用户执行 `python graphrag_agent/evaluation/test/evaluate_*_agent.py`
**Then** 脚本应成功导入 `graphrag_agent` 包
**And** 正确显示帮助信息或执行评估
