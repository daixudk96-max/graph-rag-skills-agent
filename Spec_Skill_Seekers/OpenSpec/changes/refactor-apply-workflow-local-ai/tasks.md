# Tasks

## 代码变更

### 1. 扩展 ContentSynthesizer
- **文件**: `src/skill_seekers/core/content_synthesizer.py`
- **变更**:
  - [x] 新增 `GenerationMode` 枚举（api, workflow-assistant, deterministic）
  - [x] 新增 `ContentTask` 数据类
  - [x] 修改 `__init__` 支持 `generation_mode` 参数
  - [x] 新增 `build_tasks_for_delegate()` 方法
  - [x] 修改 `synthesize_*` 方法支持任务清单模式

### 2. 更新 CLI
- **文件**: `src/skill_seekers/cli/main.py`
- **变更**:
  - [x] 新增 `--generation-mode` 参数到 `apply-spec` 子命令
  - [x] 保持 `--no-llm` 向后兼容（映射到 deterministic）

### 3. 更新 UnifiedSkillBuilder
- **文件**: `src/skill_seekers/cli/unified_skill_builder.py`
- **变更**:
  - [x] 传递 `generation_mode` 到 ContentSynthesizer
  - [x] 在 workflow-assistant 模式下输出 tasks.json

---

## 工作流变更

### 4. 更新主工作流文档
- **文件**: `.agent/workflows/skill-seekers-apply.md`
- **变更**:
  - 默认使用 `--generation-mode workflow-assistant`
  - 新增"AI 助手内容生成"步骤
  - 说明如何处理任务清单

### 5. 同步更新 slash 模板
- **文件**: `src/skill_seekers/cli/slash_templates/apply.md`
- **变更**: 与主工作流保持一致

---

## 测试

### 6. 新增单元测试
- **文件**: `tests/test_content_synthesizer.py`
- **新增**:
  - 测试 `workflow-assistant` 模式任务清单生成
  - 测试占位符输出格式
  - 测试模式切换行为

---

## 验证

### 7. 端到端验证
- 使用现有 spec.yaml 测试三种模式
- 确认 workflow-assistant 模式正确输出 tasks.json
