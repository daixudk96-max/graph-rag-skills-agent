---
description: skill-seekers-apply workflow
---
<!-- SKILL_SEEKERS:START -->
# /skill-seekers-apply

## 角色
- 你是 AI 编程助手，已拿到批准的 SkillSpec，需要执行构建并自检。

## 目标
- 使用已批准的 `spec.yaml` 产出最终技能内容。
- 检查缺失项并记录需要人工补充的部分。

## 步骤

### 1. 确认输入
询问用户提供以下信息：
- **spec.yaml 路径**：已批准的规格文件
- **skill_input.json 路径**（可选）：模板化内容文件
- **输出目录**：默认为 `output/`
- **是否禁用 LLM**：添加 `--no-llm` 使用回退提取模式

### 1.5 读取模板（如使用模板格式）

> **适用条件**：当存在 `skill_input.json` 且包含 `template` 字段时执行

```python
from graphrag_agent.integrations.skill_seekers import TemplateRegistry
import json

# 读取 skill_input.json
with open("skill_input.json") as f:
    skill_input = json.load(f)

# 检查是否为模板格式
if "template" in skill_input:
    template_id = skill_input["template"]["id"]
    version = skill_input["template"]["version"]
    print(f"使用模板: {template_id}@{version}")
    
    # 从 content 层获取已填充的段落
    content = skill_input.get("content", {})
    segments = content.get("segments", {})
```

### 2. 执行构建（需用户同意后再运行）
```bash
skill-seekers apply-spec <spec.yaml> --output-dir <output_dir>
```
- 如需禁用 LLM 内容生成：添加 `--no-llm` 标志。

### 3. 验证产物
构建完成后，检查以下内容：
- **SKILL.md**：主技能文件是否完整
- **references/**：参考资料是否生成
- **assets/**：资产文件是否到位（如有）
- **scripts/**：脚本文件是否正确（如有）

### 3.5 嵌入模板元数据

> **适用条件**：当使用模板格式时执行

```python
from graphrag_agent.integrations.skill_seekers import TemplateEmbedder, TemplateRegistry

# 读取生成的 SKILL.md
with open("output/SKILL.md") as f:
    skill_md = f.read()

# 嵌入模板元数据
registry = TemplateRegistry()
template = registry.get_template(template_id, version)
embedder = TemplateEmbedder(include_segments=False)
skill_md = embedder.embed_in_skill(skill_md, template)

# 保存更新后的 SKILL.md
with open("output/SKILL.md", "w") as f:
    f.write(skill_md)
```

### 4. 质量检查
- 验证所有章节内容是否填充（非占位符）
- 检查内部链接是否有效
- 确认格式符合 Claude Skills 标准
- 记录任何需要手动修正的问题
- 如使用模板，验证 `<!-- TEMPLATE_META: {...} -->` 注释存在

### 5. 报告结果
- 构建成功/失败状态
- 生成的文件列表
- 需要人工补充的内容清单
- 使用的模板信息（如有）
- 下一步操作建议（package / 手动修改）

## 输出
- 构建状态总结
- 生成文件路径列表
- 缺失内容清单
- 下一步操作建议

<!-- SKILL_SEEKERS:END -->

