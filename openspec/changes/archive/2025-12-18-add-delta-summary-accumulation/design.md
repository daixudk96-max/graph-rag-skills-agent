# Design: Delta-Summary Accumulation (DSA)

## Context

The graph-rag-agent project uses community detection (Leiden/SLLPA) to cluster related entities, then generates summaries for each community. These summaries power Global Search queries by providing high-level context.

Currently, **every incremental update** triggers a full summary regeneration via `summarizer.process_communities()`, which:
1. Collects all entities and relationships in each community
2. Formats them into a large context string
3. Calls LLM to generate a new summary

This approach is correct but suboptimal for incremental scenarios.

### Stakeholders
- **Developers**: Need to modify community summary pipeline
- **End Users**: Expect fast updates and accurate search results
- **Operations**: Benefit from reduced LLM API costs

## Goals / Non-Goals

### Goals
- Reduce incremental update LLM costs by ~80%
- Maintain search accuracy through read-time merging
- Provide clear compaction controls for background optimization
- Preserve backward compatibility with existing `__Community__` schema

### Non-Goals
- Real-time streaming of delta updates (out of scope)
- Multi-language summary support (unchanged)
- Changing the community detection algorithm itself

## Decisions

### D1: LSM-Tree Inspired Model
**Decision**: Use a Log-Structured Merge approach where writes are append-only (create deltas), reads merge layers, and background compaction optimizes storage.

**Rationale**: This pattern is proven in databases (RocksDB, Cassandra) for write-heavy workloads. Community summaries follow a similar pattern: frequent small updates, less frequent reads.

**Alternatives Considered**:
1. **Partial re-summarization**: Only re-read entities modified after a timestamp. Still requires reading substantial context for coherent summary generation.
2. **Hierarchical caching**: Cache summaries per entity cluster. Adds complexity without solving the fundamental cost issue.

### D2: Delta Node Schema

```cypher
(:__CommunityDelta__ {
    id: "community_id::delta_uuid",
    summary: "Short description of what changed...",
    summary_tokens: 87,
    related_entities: ["entity_1", "entity_2"],
    created_at: datetime(),
    status: "pending"  // or "compacted"
})

(:__Community__)-[:HAS_DELTA]->(:__CommunityDelta__)
```

**Rationale**: Separate node type enables efficient querying and selective deletion during compaction.

### D3: Mode-Based Processing

**Decision**: Add a `mode` parameter to `process_communities()`:
- `mode="full"`: Traditional full regeneration (cold start, forced refresh)
- `mode="delta"`: Generate delta summaries only for affected communities
- `mode="compact"`: Merge deltas into base summaries

**Rationale**: Enables gradual adoption and fallback to proven behavior.

### D4: Read-Path Query Pattern

```cypher
MATCH (c:__Community__ {level: $level})
OPTIONAL MATCH (c)-[:HAS_DELTA]->(d:__CommunityDelta__ {status: 'pending'})
WITH c, collect(d.summary) AS deltas ORDER BY d.created_at
RETURN {
    communityId: c.id,
    full_content: coalesce(c.full_content, c.summary, '') + 
        CASE WHEN size(deltas) > 0 
             THEN '\n\n[Recent Updates]:\n' + apoc.text.join(deltas, '\n') 
             ELSE '' END
} AS output
```

**Rationale**: APOC's `text.join` handles variable-length delta lists efficiently. The pattern gracefully degrades when no APOC is available (fallback to Cypher string concatenation).

## Risks / Trade-offs

| Risk | Impact | Mitigation |
|------|--------|------------|
| Delta accumulation unbounded | Read performance degrades | Compaction thresholds (count > 5, tokens > 1000) |
| Community merges during Leiden re-run | Orphan deltas reference old community IDs | Cascade delete on community ID change, or garbage collection |
| APOC dependency for text.join | Query fails without APOC | Provide fallback Cypher using `reduce()` |
| Compaction race conditions | Duplicate deltas or lost updates | Use Neo4j transactions with MERGE patterns |

## Migration Plan

1. **Phase 1 (Non-breaking)**: Add `__CommunityDelta__` schema without modifying existing flows
2. **Phase 2**: Implement `mode="delta"` and `mode="compact"` in summarizer
3. **Phase 3**: Update `incremental_update.py` to use delta mode by default
4. **Phase 4**: Update read paths in search tools
5. **Rollback**: Set `DSA_ENABLED=false` to revert to full regeneration

### Rollback Steps
1. Set `DSA_ENABLED = False` in settings
2. Run `MATCH (d:__CommunityDelta__) DETACH DELETE d` to clean up deltas
3. Trigger full community summary regeneration

## Open Questions

1. **Q**: Should compaction be triggered synchronously after write or purely background?
   - **Tentative**: Background via scheduler, with optional manual trigger.

2. **Q**: What happens to deltas when a community is split by Leiden re-detection?
   - **Tentative**: Orphan deltas are deleted during the next full community detection pass.

3. **Q**: Should we track delta lineage (which document triggered which delta)?
   - **Tentative**: Store `source_file_ids` in delta node for debugging, but not enforce referential integrity.
