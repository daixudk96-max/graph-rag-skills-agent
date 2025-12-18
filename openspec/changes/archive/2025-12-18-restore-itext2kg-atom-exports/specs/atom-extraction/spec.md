# atom-extraction Spec Delta

## Purpose

This delta confirms compliance with the existing `atom-extraction` spec requirement regarding `EntityProperties` export. No new requirements are added.

## MODIFIED Requirements

### Requirement: itext2kg 模型完整导出

`itext2kg.atom.models` 模块 MUST 导出所有在 `temporal_kg.py` 中使用的类型。

> **Note**: This restores compliance with the existing requirement after an accidental reset of the itext2kg folder.

#### Scenario: EntityProperties 可从 itext2kg.atom.models 导入

**Given** itext2kg 包已安装
**When** 执行 `from itext2kg.atom.models import EntityProperties`
**Then** 导入应成功
**And** `EntityProperties` 类可用于创建实体属性对象
