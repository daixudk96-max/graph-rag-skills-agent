# Specification: GraphRAG Skill Integration

## Capability Overview

This capability enables exporting knowledge graph content from GraphRAG in a format compatible with Skill Seekers, allowing users to generate Claude AI skills directly from their knowledge graph.

---

## ADDED Requirements

### Requirement: GRAPHRAG-SKILL-001 - Export Knowledge Graph for Skill Generation

The system SHALL provide an export mechanism that outputs knowledge graph content in a format consumable by Skill Seekers.

#### Scenario: Full export of community summaries

**Given** a knowledge graph with community summaries at level 0
**When** the user runs `graphrag export-for-skill --mode full --level 0`
**Then** the system generates `skill_input.json` containing:
- All community summaries as pages
- Deduplicated entities with relationships
- Export metadata with timestamp and source info

#### Scenario: Delta export after incremental update

**Given** a knowledge graph that was previously exported
**And** new documents have been added triggering community summary updates
**When** the user runs `graphrag export-for-skill --mode delta`
**Then** the system generates `skill_input.json` containing:
- Only communities modified since last export
- Updated entities from modified communities
- Delta metadata showing what changed

#### Scenario: Export with custom level selection

**Given** a knowledge graph with multi-level community hierarchy (levels 0, 1, 2)
**When** the user runs `graphrag export-for-skill --level 1`
**Then** the system exports only level 1 community summaries

---

### Requirement: GRAPHRAG-SKILL-002 - Content Deduplication

The system SHALL deduplicate content during export to prevent redundant information in generated skills.

#### Scenario: Entity deduplication

**Given** the knowledge graph contains entities: ["Python 3.12", "Python3", "python"]
**When** exporting for skill generation
**Then** the entities are merged into a single canonical entity
**And** the `dedup_report` includes the merge group

#### Scenario: Content hash deduplication

**Given** multiple community summaries contain identical text passages
**When** exporting for skill generation
**Then** duplicate passages are identified and marked
**And** the output includes only one copy of each unique passage

---

### Requirement: GRAPHRAG-SKILL-003 - Sync State Tracking

The system SHALL track export state to enable efficient delta updates.

#### Scenario: Initial export creates sync state

**Given** no previous export has been performed
**When** the user runs a full export
**Then** a `.skill_sync_state.json` file is created
**And** it contains the export timestamp and community IDs

#### Scenario: Delta detection uses sync state

**Given** a previous export was performed at timestamp T1
**And** communities C1, C2 have been updated after T1
**When** the user queries pending updates
**Then** the system returns [C1, C2] as pending

#### Scenario: Sync state updates after export

**Given** pending updates exist for communities C1, C2
**When** a delta export completes successfully
**Then** the sync state is updated with new timestamp
**And** C1, C2 are marked as synced

---

### Requirement: GRAPHRAG-SKILL-004 - Workflow Integration

The system SHALL integrate with existing `/skill-seekers-*` slash commands.

#### Scenario: Proposal workflow with GraphRAG source

**Given** a user wants to create a skill from their knowledge graph
**When** they invoke `/skill-seekers-proposal` with source type "graphrag"
**Then** the workflow:
1. Runs `graphrag export-for-skill` to generate input
2. Uses the generated `skill_input.json` for spec generation
3. Produces a `spec.yaml` ready for review

#### Scenario: Apply workflow preserves GraphRAG metadata

**Given** a `spec.yaml` was generated from GraphRAG source
**When** the user runs `/skill-seekers-apply`
**Then** the generated `SKILL.md` includes:
- Source attribution to knowledge graph
- Community references in metadata
- Entity relationship diagrams (if enabled)

---

## Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `skill_export.default_level` | int | 0 | Default community level for export |
| `skill_export.include_chunks` | bool | false | Include raw chunks in export |
| `skill_export.dedup_threshold` | float | 0.85 | Similarity threshold for deduplication |
| `skill_export.max_communities` | int | null | Limit number of communities to export |
| `skill_export.output_path` | str | "skill_input.json" | Default output file path |

---

## Cross-References

- **Related**: [community-summary](../../specs/community-summary/spec.md) - Source of community summaries
- **Related**: [atom-extraction](../../specs/atom-extraction/spec.md) - Temporal entity extraction
- **Uses**: Skill Seekers `scraped_data.json` schema
- **Extends**: `/skill-seekers-proposal` workflow
