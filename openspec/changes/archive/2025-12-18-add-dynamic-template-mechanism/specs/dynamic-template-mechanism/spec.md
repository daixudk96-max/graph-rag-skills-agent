# Specification: Dynamic Template Mechanism

## Capability Overview

This capability enables flexible, template-based content generation for Skill Seekers, supporting variable transcript formats and enabling template versioning, embedding, and migration.

---

## ADDED Requirements

### Requirement: DYNAMIC-TPL-001 - Template-Based skill_input.json Structure

The system SHALL support a new skill_input.json format that separates template definition from populated content.

#### Scenario: skill_input.json with template

**Given** a user provides a transcript file
**And** selects the "transcript-segmented" template
**When** the proposal workflow generates skill_input.json
**Then** the output contains:
- `template` object with id, version, and segments array
- `content` object with populated segment values
- `source` object with transcript references
- `trace` object with generation metadata

#### Scenario: Backward compatibility with legacy format

**Given** a skill_input.json without `template` field
**When** the apply workflow processes the file
**Then** the system falls back to legacy segmented_summary logic
**And** logs a warning suggesting migration to template-based format

---

### Requirement: DYNAMIC-TPL-002 - Template Registry

The system SHALL provide a template registry for managing template definitions.

#### Scenario: Load template by ID and version

**Given** a template "transcript-interview@1.0.0" exists in the registry
**When** the user requests this template
**Then** the system returns the full template definition

#### Scenario: List available templates

**Given** multiple templates exist in the registry
**When** the user lists templates
**Then** the system returns id, name, version, and description for each

---

### Requirement: DYNAMIC-TPL-003 - Template Embedding in Skills

The system SHALL embed template metadata in generated SKILL.md files.

#### Scenario: Template embedded during apply

**Given** a spec.yaml generated from template-based skill_input.json
**When** /skill-seekers-apply generates SKILL.md
**Then** the file contains `<!-- TEMPLATE_META: {...} -->` comment
**And** the comment includes template id, version, and generation timestamp

#### Scenario: Extract template from existing skill

**Given** a SKILL.md file with embedded template metadata
**When** the system extracts the template
**Then** it returns the original template definition used for generation

---

### Requirement: DYNAMIC-TPL-004 - Template Migration Guidance

The system SHALL generate migration guidance when templates change.

#### Scenario: Detect template changes

**Given** an old template version "transcript-segmented@1.0.0"
**And** a new template version "transcript-segmented@1.1.0"
**When** migration comparison is performed
**Then** the system identifies:
- Added segments
- Removed segments
- Modified segments (changed constraints, inputs, etc.)

#### Scenario: Generate migration steps

**Given** a migration report with changes
**When** migration guide is generated
**Then** the output includes:
- Step-by-step migration instructions
- Field mapping suggestions
- Data transformation recommendations

---

## Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `template.registry_path` | str | "templates/" | Path to template storage |
| `template.default_id` | str | "transcript-segmented" | Default template when none specified |
| `template.embed_in_skill` | bool | true | Whether to embed template in SKILL.md |
| `template.strict_validation` | bool | false | Fail on validation warnings |

---

## Cross-References

- **Related**: [graphrag-skill-integration](../integrate-graphrag-skill-seekers/specs/graphrag-skill-integration/spec.md) - skill_input.json format compatibility
- **Extends**: /skill-seekers-proposal workflow
- **Extends**: /skill-seekers-apply workflow
