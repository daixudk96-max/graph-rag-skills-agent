# Tasks: Dynamic Template Mechanism for Skill Seekers

## Overview
Implementation tasks for introducing dynamic template mechanism to handle variable transcript formats.

---

## Phase 1: Core Template Infrastructure

### Task 1.1: Define Template JSON Schema
- [x] Create `templates/schema/template.schema.json` with JSON Schema definition
- [x] Include segment, inputs, transform, constraints definitions
- [x] Add schema validation tests
- **Validation**: Schema validates example templates ✅

### Task 1.2: Implement TemplateRegistry
- [x] Create `template_registry.py` with TemplateRegistry class
- [x] `get_template(id, version)` - load from files
- [x] `list_templates()` - enumerate available templates
- [x] `register_template(template)` - save new template
- **Validation**: Can load/save templates ✅

### Task 1.3: Create Default Templates
- [x] `transcript-segmented` - 分段转录（现有逻辑）
- [x] `transcript-interview` - 面试记录
- [x] `transcript-meeting` - 会议纪要
- **Validation**: Templates pass schema validation ✅

---

## Phase 2: Template Processing

### Task 2.1: Implement TemplateFiller
- [x] Create `template_filler.py` with TemplateFiller class
- [x] `fill(template, raw_content)` - populate segments
- [x] Handle required/repeatable/inputs logic
- **Validation**: Filler correctly maps content to template ✅

### Task 2.2: Implement Content Validator
- [x] Add `validate(content, template)` method
- [x] Check required fields, constraints, format
- [x] Return actionable validation errors
- **Validation**: Invalid content rejected with clear messages ✅

### Task 2.3: Extend skill_input.json Format
- [x] Update `ExportResult` to support template structure
- [x] Add backward compatibility check (no template = legacy mode)
- [x] Update `SkillInputFormatter` for new format
- **Validation**: Both old and new formats work ✅

---

## Phase 3: Template Migration

### Task 3.1: Implement TemplateMigrator
- [x] Create `template_migrator.py` with TemplateMigrator class
- [x] `compare(old, new)` - diff template segments
- [x] Generate migration report (added/removed/changed fields)
- **Validation**: Correctly detects template differences ✅

### Task 3.2: Generate Migration Guidance
- [x] `generate_migration_guide(report)` - human-readable migration steps
- [x] Include field mapping suggestions
- [x] Output in proposal-friendly format
- **Validation**: Guide covers all migration scenarios ✅

---

## Phase 4: Template Embedding

### Task 4.1: Implement TemplateEmbedder
- [x] Create `template_embedder.py` with TemplateEmbedder class
- [x] `embed_in_skill(skill_md, template)` - add template metadata to SKILL.md
- [x] Use `<!-- TEMPLATE_META: {...} -->` comment format
- **Validation**: Template extractable from generated SKILL.md ✅

### Task 4.2: Template Extraction
- [x] `extract_from_skill(skill_md)` - parse embedded template
- [x] Handle missing/malformed embedded template gracefully
- **Validation**: Round-trip embed → extract preserves template ✅

---

## Phase 5: Workflow Updates

### Task 5.1: Update /skill-seekers-proposal Workflow
- [x] Add template selection step
- [x] Integrate TemplateFiller for content extraction
- [x] Add migration guidance when template changes
- **Validation**: Workflow generates template-based skill_input.json ✅

### Task 5.2: Update /skill-seekers-apply Workflow
- [x] Read template from skill_input.json
- [x] Generate spec.yaml sections from template segments
- [x] Embed template in final SKILL.md
- **Validation**: Generated SKILL.md contains template metadata ✅

---

## Phase 6: Documentation & Testing

### Task 6.1: Add Integration Tests
- [x] Test template loading/saving
- [x] Test content filling and validation
- [x] Test migration guide generation
- [x] Test SKILL.md embedding/extraction
- [x] End-to-end workflow test (13 steps)
- **Validation**: All tests pass ✅

### Task 6.2: Create User Documentation
- [x] Document template schema
- [x] Provide template creation guide
- [x] Add migration workflow examples
- [x] Created `docs/skill_seekers_templates.md`
- **Validation**: Documentation complete ✅

---

## Dependencies

```
Task 1.1 ← Task 1.2, 1.3
Phase 1 ← Phase 2
Task 2.3 ← Phase 3, Phase 4
Phase 2, 3, 4 ← Phase 5
All phases ← Phase 6
```

## Parallelizable Work

- Task 1.2, 1.3 can run in parallel
- Task 3.1, 4.1 can run in parallel
- Task 5.1, 5.2 can run in parallel

---

## ✅ IMPLEMENTATION COMPLETE

All 17 tasks have been completed and verified. The Dynamic Template Mechanism is fully functional.
