# Change: Delta-Summary Accumulation (DSA) Strategy

## Why

Current community summary generation is a high-cost operation that scales with **community size**, not with **delta size**. When new data enters a community, the system re-reads all entities and relationships to regenerate the entire summary. For large communities with small updates, this wastes ~80%+ of LLM tokens reading unchanged content.

This change introduces an LSM-Tree inspired incremental summary strategy: write small delta summaries quickly, merge them dynamically at read time, and compact them asynchronously in the background.

## What Changes

### Data Model
- **ADDED** `__CommunityDelta__` node type with properties: `id`, `summary`, `related_entities`, `created_at`, `status`
- **ADDED** `HAS_DELTA` relationship from `__Community__` to `__CommunityDelta__`
- **MODIFIED** `__Community__` node with new properties: `last_compacted_at`, `summary_tokens`

### Write Path (Fast Mode)
- When incremental update detects new entities in a community, generate a **delta summary** for only the new data
- Delta summaries are short (~50-200 tokens), describing what was added without reading existing content
- Store as `__CommunityDelta__` nodes linked to the parent community

### Read Path (Merge on Read)
- **MODIFIED** Global search and community queries to dynamically merge base + delta summaries
- Pattern: `base_summary + "\n\n[Incremental Updates]:\n" + join(delta_summaries, "\n")`

### Compaction (Background)
- Trigger when: delta count > 5 OR total delta tokens > 1000
- Merge deltas into base summary via LLM fusion prompt
- Delete/flag compacted deltas

## Impact

- **Affected specs**: `community-summary` (new capability)
- **Affected code**:
  - `graphrag_agent/community/summary/base.py` - Add delta storage/compaction logic
  - `graphrag_agent/community/summary/leiden.py` - Add `collect_delta_info()` method
  - `graphrag_agent/integrations/build/incremental_update.py` - Switch to delta mode
  - `graphrag_agent/search/global_search.py` - Read-path merge
  - `graphrag_agent/search/tool/reasoning/community_enhance.py` - Read-path merge
  - `graphrag_agent/config/settings.py` - New configuration parameters

## Benefits

| Metric | Traditional (Full Rewrite) | DSA (Proposed) |
|--------|---------------------------|----------------|
| Update Logic | Re-read entire community | Only new data |
| LLM Token Cost | O(community_size) | O(delta_size) |
| Update Latency | Medium (wait for summary) | **Low (seconds)** |
| Accuracy | High | High (read-time merge) |
| Expected Savings | Baseline | **~80% token reduction** |
