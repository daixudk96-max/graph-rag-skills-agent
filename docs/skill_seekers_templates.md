# Dynamic Template System - User Guide

## Overview

The Dynamic Template System enables flexible content structuring for Skill Seekers by defining templates for different transcript types. Templates specify the structure, required fields, and validation rules for skill input content.

## Quick Start

```python
from graphrag_agent.integrations.skill_seekers import (
    TemplateRegistry, TemplateFiller, TemplateEmbedder
)

# 1. Load a template
registry = TemplateRegistry()
template = registry.get_template("transcript-segmented", "1.0.0")

# 2. Fill content into template
filler = TemplateFiller()
content = filler.fill(template, {
    "context": "Course introduction...",
    "key_points": ["Point 1", "Point 2"],
    "summary": "Summary of the lecture..."
})

# 3. Validate filled content
errors = filler.validate(content, template)
if errors:
    print(f"Validation failed: {errors}")

# 4. Embed template metadata in SKILL.md
embedder = TemplateEmbedder()
skill_md = embedder.embed_in_skill(skill_content, template)
```

## Available Templates

| Template ID | Version | Description | Segments |
|-------------|---------|-------------|----------|
| `transcript-segmented` | 1.0.0 | 分段转录 (lectures, tutorials) | 5 |
| `transcript-interview` | 1.0.0 | 面试记录 (Q&A interviews) | 7 |
| `transcript-meeting` | 1.0.0 | 会议纪要 (meeting minutes) | 7 |

## Template Schema

Each template has the following structure:

```json
{
  "id": "template-id",
  "version": "1.0.0",
  "name": "Template Name",
  "description": "What this template is for",
  "segments": [
    {
      "key": "segment_key",
      "title": "Segment Title",
      "description": "What content goes here",
      "required": true,
      "repeatable": false,
      "format": "markdown",
      "constraints": {
        "min_length": 100,
        "max_length": 5000
      }
    }
  ]
}
```

### Segment Properties

| Property | Type | Description |
|----------|------|-------------|
| `key` | string | Unique identifier for the segment |
| `title` | string | Display title |
| `description` | string | Description for content creators |
| `required` | boolean | Whether the segment must be filled |
| `repeatable` | boolean | Whether multiple values are allowed |
| `format` | string | Output format: `markdown`, `json`, `text` |
| `inputs` | array | Expected input fields |
| `transform` | object | Content transformation rules |
| `constraints` | object | Validation constraints |

## skill_input.json Format

The new 4-layer structure:

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
      "context": {"value": "...", "source_ref": "..."},
      "key_points": [{"value": "point 1"}, {"value": "point 2"}]
    }
  },
  "source": {
    "transcript_refs": [
      {"file": "lecture.txt", "segments": [0, 100]}
    ]
  },
  "trace": {
    "generated_at": "2024-12-19T00:00:00Z",
    "template_version_used": "1.0.0",
    "generator": "graphrag-skill-seekers"
  }
}
```

## Creating Custom Templates

### Step 1: Define the Template

Create a JSON file at:
`templates/default_templates/{template-id}/{version}/template.json`

Example:

```json
{
  "id": "podcast-episode",
  "version": "1.0.0",
  "name": "播客节目模板",
  "description": "Template for podcast transcripts",
  "segments": [
    {
      "key": "episode_info",
      "title": "节目信息",
      "required": true,
      "inputs": [
        {"name": "title", "type": "string"},
        {"name": "hosts", "type": "array"},
        {"name": "date", "type": "string"}
      ]
    },
    {
      "key": "topics",
      "title": "讨论话题",
      "required": true,
      "repeatable": true
    },
    {
      "key": "takeaways",
      "title": "要点总结",
      "required": true,
      "repeatable": true
    }
  ]
}
```

### Step 2: Validate the Template

```python
from graphrag_agent.integrations.skill_seekers import TemplateRegistry

registry = TemplateRegistry()
template_data = {...}  # Your template dict
errors = registry.validate_template(template_data)
if errors:
    print(f"Validation errors: {errors}")
```

### Step 3: Register the Template

```python
from graphrag_agent.integrations.skill_seekers import Template

template = Template.from_dict(template_data)
registry.register_template(template)
```

## Template Migration

When updating templates, use the migrator to generate migration guidance:

```python
from graphrag_agent.integrations.skill_seekers import TemplateMigrator

migrator = TemplateMigrator()
report = migrator.compare(old_template, new_template)

if report.is_breaking:
    print("WARNING: Breaking changes detected!")
    
guide = migrator.generate_migration_guide(report)
print(guide)
```

### Migration Report Contents

- **Added segments**: New fields that need content
- **Removed segments**: Fields that will be dropped
- **Modified segments**: Changed properties (type, constraints)
- **Breaking changes**: Required new fields, type changes

## SKILL.md Metadata Embedding

Templates are embedded as HTML comments:

```html
<!-- TEMPLATE_META: {"id":"transcript-segmented","version":"1.0.0",...} -->

# Skill Title

Content here...
```

### Extracting Metadata

```python
from graphrag_agent.integrations.skill_seekers import TemplateEmbedder

embedder = TemplateEmbedder()
template = embedder.extract_from_skill(skill_md)
if template:
    print(f"Used template: {template.identifier}")
```

## Workflow Integration

### /skill-seekers-proposal

1. User selects source type and template
2. System loads template from registry
3. Content is extracted and filled into template
4. `skill_input.json` is generated with 4-layer structure

### /skill-seekers-apply

1. System reads `skill_input.json`
2. Template segments map to spec.yaml sections
3. SKILL.md is generated
4. Template metadata is embedded in final output

## Best Practices

1. **Version your templates**: Use semantic versioning (1.0.0, 1.1.0, 2.0.0)
2. **Mark required fields carefully**: Only truly required fields should be marked
3. **Use meaningful keys**: Segment keys should be descriptive
4. **Add constraints**: Use min/max length to guide content creation
5. **Document segments**: Good descriptions help content creators

## Troubleshooting

### Template not found
- Check the template directory structure
- Verify template.json exists in the version folder
- Ensure JSON syntax is valid

### Validation errors
- Review required fields
- Check constraint violations
- Verify input types match expected types

### Migration issues
- Always generate migration guide before upgrading
- Test with sample content before production migration
- Keep old templates for backward compatibility
