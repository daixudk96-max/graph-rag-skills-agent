# spec-first-skill-workflow Specification Delta

## ADDED Requirements

### Requirement: apply-spec Command Respects output-dir Parameter
The system SHALL use the user-specified `--output-dir` path when provided, otherwise default to `output/{skill_name}`.

#### Scenario: Apply spec with custom output directory
- **GIVEN** an approved SkillSpec file at `spec.yaml`
- **WHEN** the user runs `skill-seekers apply-spec spec.yaml --output-dir /custom/path`
- **THEN** the skill folder is created at `/custom/path/`
- **AND** SKILL.md is written to `/custom/path/SKILL.md`
- **AND** references/ is created at `/custom/path/references/`

#### Scenario: Apply spec without output-dir uses default
- **GIVEN** an approved SkillSpec with `name: my-skill`
- **WHEN** the user runs `skill-seekers apply-spec spec.yaml` without `--output-dir`
- **THEN** the skill folder is created at `output/my-skill/`
- **AND** this matches the existing default behavior

#### Scenario: UnifiedSkillBuilder accepts output_dir parameter
- **GIVEN** `UnifiedSkillBuilder` is instantiated with `output_dir="/tmp/test"`
- **WHEN** `build_from_spec()` is called
- **THEN** all generated files are placed in `/tmp/test/`
- **AND** the `skill_dir` attribute equals `/tmp/test`

## Related Capabilities
- [spec-first-skill-workflow](../../specs/spec-first-skill-workflow/spec.md): Parent capability for spec-driven workflow
