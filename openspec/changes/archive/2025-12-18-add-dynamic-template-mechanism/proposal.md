# Proposal: Dynamic Template Mechanism for Skill Seekers

## Problem Statement

当前 Skill Seekers 的 transcript（转录文本）处理使用固定的 `segmented_summary.json` 格式，无法适应不同来源的内容结构变化。例如：
- 教学视频 vs 面试记录 vs 会议纪要需要不同的分段逻辑
- 固定的字段（如 `marker`, `homophone_notes`）不适用于所有场景
- 无法追踪和复现技能生成过程

## Proposed Solution

引入**动态模板机制**，将 `skill_input.json` 扩展为包含模板定义和填充内容的双层结构：

```
skill_input.json
├── template      # 模板定义（结构、字段、验证规则）
├── content       # 根据模板填充的内容
├── source        # 原文引用（transcript, metadata）
└── trace         # 生成追踪（用于复现）
```

## Scope

### In Scope
1. **新 skill_input.json 结构**：template + content + source + trace
2. **模板注册表**：按 id + version 管理模板
3. **模板嵌入**：生成的 SKILL.md 包含使用的模板信息
4. **迁移指南生成**：比较新旧模板差异，生成迁移建议
5. **工作流更新**：/skill-seekers-proposal 和 /skill-seekers-apply

### Out of Scope
- 模板 GUI 编辑器
- 自动模板推断（从内容自动生成模板）
- 多语言模板本地化

## User Stories

1. **作为内容创作者**，我希望根据内容类型选择或自定义模板，以便生成结构化的技能文档。
2. **作为技能维护者**，我希望在技能文件中看到生成时使用的模板，以便理解结构和复现过程。
3. **作为迁移管理员**，我希望在更新模板时获得旧→新的字段映射和迁移建议。

## Dependencies

- 现有 Skill Seekers 工作流（/skill-seekers-proposal, /skill-seekers-apply）
- GraphRAG 集成模块（skill_input.json 格式兼容）

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| 模板过于复杂导致学习成本高 | 中 | 提供默认模板和简化模式 |
| 旧格式不兼容 | 高 | 向后兼容：无 template 时降级为旧逻辑 |
| 模板版本管理混乱 | 中 | 强制 id + version 唯一标识 |

## Success Criteria

1. 新格式能处理 3 种不同类型的 transcript（教学、面试、会议）
2. 生成的 SKILL.md 包含 `<!-- TEMPLATE: ... -->` 注释块
3. 模板变更时 proposal 自动输出迁移建议
4. 现有无模板的 skill_input.json 仍能正常处理（向后兼容）
