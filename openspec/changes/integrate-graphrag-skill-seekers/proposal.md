# Proposal: Integrate GraphRAG Output with Skill Seekers

## Summary

This change integrates the GraphRAG output pipeline with Spec_Skill_Seekers, enabling:
1. GraphRAG to generate deduplicated, structured documents suitable for skill generation
2. These documents to serve as key inputs/templates for Skill Seekers
3. Synchronization between Knowledge Graph updates and skill regeneration
4. Unified slash commands for AI-assisted skill creation/modification

## Problem Statement

Currently, GraphRAG and Skill Seekers operate independently:
- **GraphRAG**: Builds knowledge graphs from documents, generates community summaries, and answers queries
- **Skill Seekers**: Scrapes documentation/repos, generates Claude AI skills via `spec.yaml` → `SKILL.md` workflow

Users who want to create skills from knowledge graph content must manually:
1. Export GraphRAG outputs
2. Reformat them for Skill Seekers
3. Manually track updates when the knowledge graph changes

## Proposed Solution

Add a **GraphRAG-to-Skill bridge** that:
1. **Exports structured content** from GraphRAG (community summaries, entity relationships, search results)
2. **Generates Skill Seekers-compatible documents** (similar to `scraped_data.json` format)
3. **Provides a sync mechanism** to regenerate skill templates when the KG updates
4. **Integrates with existing workflows** (`/skill-seekers-proposal`, `/skill-seekers-apply`)

## Scope

### In Scope
- New `graphrag_agent/integrations/skill_seekers/` module
- Export pipeline for GraphRAG → skill-compatible format
- Slash command integration for end-to-end workflow
- Delta-aware skill updates (only regenerate affected sections)
- Configuration for output customization

### Out of Scope
- Changes to core Skill Seekers library (use existing APIs)
- Real-time streaming of KG updates to skills
- Multi-language skill generation
- Automatic skill upload to Claude

## User Stories

1. **As a developer**, I want to generate Claude skills directly from my knowledge graph, so I can leverage my curated knowledge base without re-scraping documentation.

2. **As a content maintainer**, I want skills to automatically update when the knowledge graph changes, so skills stay synchronized with the latest information.

3. **As an AI assistant user**, I want to use slash commands like `/skill-seekers-proposal` with GraphRAG as the source, so I can seamlessly create skills from my knowledge graph.

## Dependencies

- Existing `graphrag_agent/community/summary/` module
- Existing `graphrag_agent/search/` tools
- Spec_Skill_Seekers library (already in `Spec_Skill_Seekers/`)
- Existing `/skill-seekers-*` workflow files

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| GraphRAG output format incompatible with Skill Seekers | Medium | High | Create adapter layer with format transformation |
| Performance degradation during export | Low | Medium | Use async processing, chunked exports |
| Skill-KG sync complexity | Medium | Medium | Start with manual trigger, add auto-sync later |

## Success Criteria

1. Users can run `/skill-seekers-proposal` with `--source graphrag` flag
2. Generated skills contain accurate, deduplicated content from KG
3. Skills update correctly when `process_communities()` is re-run
4. Export completes within 2x time of a comparable documentation scrape
