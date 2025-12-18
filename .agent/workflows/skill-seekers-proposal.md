---
description: skill-seekers-proposal workflow
---
<!-- SKILL_SEEKERS:START -->
# /skill-seekers-proposal

## 角色
- 你是 AI 编程助手，负责读取 `--output-raw` 的原始数据并完成内容增强。

## 目标
- 为 Skill Seekers 生成初始 SkillSpec（spec-first），便于后续 apply。
- 输出原始抓取数据供二次分析，避免直接依赖外部 LLM API。

## 步骤

### 1. 确认输入
询问用户提供以下信息：
- **来源类型**：docs（文档网站）/ repo（GitHub 仓库）/ pdf（PDF 文件）/ transcript（音视频转录）
- **模板类型**：technical-guide / workflow-skill / course-tutorial / brand-enterprise / tool-utility
- **技能名称与描述**：技能的标题和简短说明

### 1.5 选择动态模板（可选）

> **适用条件**：当来源类型为 `transcript` 时推荐使用

**可用模板**：
- `transcript-segmented@1.0.0` - 分段转录模板（教学视频、讲座）
- `transcript-interview@1.0.0` - 面试记录模板（问答对话）
- `transcript-meeting@1.0.0` - 会议纪要模板（会议记录）

**执行步骤**：
1. 询问用户选择模板或使用默认 `transcript-segmented`
2. 如果存在旧版本技能，检查模板版本变更
3. 如有模板升级，使用 `TemplateMigrator` 生成迁移建议

```python
from graphrag_agent.integrations.skill_seekers import TemplateRegistry, TemplateMigrator

registry = TemplateRegistry()
template = registry.get_template("transcript-segmented", "1.0.0")

# 如果存在旧版本，生成迁移指南
if old_template:
    migrator = TemplateMigrator()
    report = migrator.compare(old_template, template)
    if report.has_changes:
        guide = migrator.generate_migration_guide(report)
        print(guide)
```

### 2. 执行抓取（需用户同意后再运行）
```bash
skill-seekers scrape --spec-first --output-raw \
  --template <template> \
  --name "<skill_name>" \
  --url <source_url> \
  --description "<short goal>"
```
- 可加 `--auto-approve` 跳过交互。
- 对于 GitHub 仓库，使用 `skill-seekers github` 命令。
- 对于 PDF 文件，使用 `skill-seekers pdf` 命令。

### 3. 分析原始数据
阅读生成的 `scraped_data.json`，执行以下分析：
- 提炼 **章节结构**：识别主要主题和子主题
- 总结 **要点**：提取核心概念和关键信息
- 识别 **缺口**：标记需要补充的内容领域
- 评估 **风险与假设**：记录数据质量问题或不确定性

### 3.5 分段总结（仅 transcript 类型）

> **适用条件**：当来源类型为 `transcript` 时执行

**目的**：使用动态模板对转录文本进行语义分段和结构化总结

**执行步骤**：

1. **读取原始 transcript**
   - 阅读 `scraped_data.json` 中的原始内容
   - 记录文件名和时间戳信息

2. **使用模板填充内容**
```python
from graphrag_agent.integrations.skill_seekers import TemplateFiller, TemplateRegistry

registry = TemplateRegistry()
template = registry.get_template("transcript-segmented", "1.0.0")
filler = TemplateFiller()

# 填充模板
raw_content = {
    "context": "背景信息...",
    "key_points": ["要点1", "要点2", "要点3"],
    "summary": "总结内容..."
}
filled = filler.fill(template, raw_content)

# 验证填充结果
errors = filler.validate(filled, template)
```

3. **语义分段**
   - 根据模板定义的 segments 进行内容分段
   - 应用 transform 规则提取列表项

4. **撰写全面总结**
   - `summary_full`：详尽准确，让未读原文者能完全理解
   - `summary_brief`：2-3 句核心内容
   - `key_points`：列表形式的重点

5. **输出 skill_input.json**（新格式）
```json
{
  "template": {
    "id": "transcript-segmented",
    "version": "1.0.0",
    "segments": [...]
  },
  "content": {
    "status": "complete",
    "segments": {
      "context": {"value": "..."},
      "key_points": [{"value": "要点1"}, {"value": "要点2"}]
    }
  },
  "source": {
    "transcript_refs": [{"file": "lecture.md", "segments": [0, 10]}]
  },
  "trace": {
    "generated_at": "2024-12-18T00:00:00Z",
    "template_version_used": "1.0.0"
  }
}
```

### 3.6 综合生成 Spec（使用分段总结 + 原文）

> **适用条件**：已完成 Step 3.5，存在 `skill_input.json`

**输入**：
- `scraped_data.json`（原始数据，用于验证准确性）
- `skill_input.json`（模板化内容）

**处理**：
- 对照原文验证总结准确性
- 将模板 segments 结构融入 `spec.yaml` 的 lessons
- 使用分段总结增强 sections 内容

### 4. 生成/修订 spec.yaml
基于分析结果增强 spec.yaml：
- 写入增强后的 **摘要**（synopsis）
- 提取 **关键信息**（key points）
- 建议 **练习/示例**（exercises, examples）
- 标注需要补充的素材

### 5. 交付物
- `scraped_data.json`（原始数据）
- `skill_input.json`（模板化内容，仅 transcript 类型）
- `spec.yaml`（草稿规格）
- 未决问题清单

## 输出
- 来源与模板选择说明
- 风险与假设清单
- 生成的文件路径与下一步建议

<!-- SKILL_SEEKERS:END -->

