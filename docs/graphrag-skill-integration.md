# GraphRAG ↔ Skill Seekers Integration

This guide explains how to generate Claude AI skills directly from your GraphRAG knowledge graph.

## Overview

The integration allows you to:
- Export knowledge graph content (community summaries, entities) to Skill Seekers format
- Generate Claude skills from your curated knowledge base
- Keep skills synchronized with knowledge graph updates

## Quick Start

### 1. Export Knowledge Graph

```bash
# Full export at community level 0
python -m graphrag_agent.integrations.skill_seekers.cli export \
  --output skill_input.json \
  --mode full \
  --level 0

# Delta export (only changes since last sync)
python -m graphrag_agent.integrations.skill_seekers.cli export \
  --output skill_input.json \
  --mode delta
```

### 2. Check Sync Status

```bash
python -m graphrag_agent.integrations.skill_seekers.cli status --level 0
```

### 3. Generate Skill (via /skill-seekers-proposal)

Use the `/skill-seekers-proposal` workflow with source type `graphrag`:

1. Select source type: **graphrag**
2. Choose template type (e.g., `technical-guide`)
3. AI assistant will run the export and generate `spec.yaml`
4. Review and approve the spec
5. Use `/skill-seekers-apply` to generate the final skill

## Configuration

Environment variables for customization:

| Variable | Default | Description |
|----------|---------|-------------|
| `SKILL_EXPORT_DEFAULT_LEVEL` | 0 | Default community level |
| `SKILL_EXPORT_INCLUDE_CHUNKS` | false | Include raw document chunks |
| `SKILL_EXPORT_DEDUP_THRESHOLD` | 0.85 | Entity deduplication threshold |
| `SKILL_EXPORT_MAX_COMMUNITIES` | None | Max communities to export |
| `SKILL_EXPORT_OUTPUT_PATH` | skill_input.json | Output file path |

## Export Modes

### Full Export (`--mode full`)
- Exports all communities at the specified level
- Use for initial skill generation
- Resets sync state

### Delta Export (`--mode delta`)
- Exports only communities changed since last sync
- Faster for incremental updates
- Requires previous export to exist

## Output Format

The export generates a `skill_input.json` file with:

```json
{
  "source": {
    "type": "graphrag",
    "export_timestamp": "2024-12-18T12:00:00Z",
    "community_level": 0
  },
  "pages": [
    {
      "title": "Community: Topic Name",
      "url": "graphrag://community/123",
      "content": "Community summary...",
      "content_type": "community_summary"
    }
  ],
  "entities": [
    {
      "name": "Entity Name",
      "type": "entity_type",
      "description": "...",
      "relationships": ["RELATED:other_entity"]
    }
  ],
  "dedup_report": {
    "original_entity_count": 100,
    "merged_entity_count": 85
  }
}
```

## Troubleshooting

### No pending updates found
- Use `--mode full` for initial export
- Check if knowledge graph has been updated

### Export is slow
- Use `--max-communities N` to limit scope
- Consider higher community level for fewer, larger communities

### Entities missing relationships
- Ensure `include_relationships=True` in config
- Check that entities have `RELATED` edges in Neo4j

## API Usage

For programmatic access:

```python
from langchain_community.graphs import Neo4jGraph
from graphrag_agent.integrations.skill_seekers import (
    GraphRAGExporter,
    SkillInputFormatter,
    ContentDeduplicator,
    ExportConfig,
)

# Setup
graph = Neo4jGraph(url="...", username="...", password="...")
config = ExportConfig(default_level=0, include_chunks=False)

# Export
exporter = GraphRAGExporter(graph, config)
result = exporter.export(mode="full", level=0)

# Deduplicate
deduplicator = ContentDeduplicator()
result.entities, _ = deduplicator.deduplicate_entities(result.entities)

# Save
formatter = SkillInputFormatter()
formatter.save_to_file(result, "skill_input.json")
```
