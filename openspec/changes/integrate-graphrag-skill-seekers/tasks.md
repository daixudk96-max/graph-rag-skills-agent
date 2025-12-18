# Tasks: GraphRAG ↔ Skill Seekers Integration

## Overview
Implementation tasks for integrating GraphRAG output with Skill Seekers, enabling AI skills generation directly from knowledge graph content.

---

## Phase 1: Core Export Module ✅

### Task 1.1: Create skill_seekers integration module structure
- [x] Create `graphrag_agent/integrations/skill_seekers/` directory
- [x] Add `__init__.py` with module exports
- [x] Add `config.py` with `ExportConfig` dataclass
- **Validation**: ✅ Module imports without errors

### Task 1.2: Implement GraphRAGExporter base class
- [x] Create `exporter.py` with `GraphRAGExporter` class
- [x] Implement `export_communities(level: int)` method
- [x] Implement `export_entities()` method
- [x] Implement `export_chunks(community_ids: List[str])` method
- **Validation**: ✅ Module imports validated

### Task 1.3: Implement Deduplicator
- [x] Create `deduplicator.py` with `ContentDeduplicator` class
- [x] Implement entity deduplication
- [x] Implement content hash-based deduplication for summaries
- [x] Generate dedup_report with merge statistics
- **Validation**: ✅ Module imports validated

### Task 1.4: Implement SkillInputFormatter
- [x] Create `formatter.py` with `SkillInputFormatter` class
- [x] Implement community-to-page mapping
- [x] Implement entity-to-entity mapping
- [x] Output `skill_input.json` compatible with Skill Seekers
- **Validation**: ✅ Module imports validated

---

## Phase 2: Sync Mechanism ✅

### Task 2.1: Implement SyncManager
- [x] Create `sync_manager.py` with `GraphRAGSkillSyncManager` class
- [x] Implement `load_state()` and `save_state()`
- [x] Track: `last_export_ts`, `exported_community_ids`, `export_hash`
- **Validation**: ✅ Module imports validated

### Task 2.2: Implement delta detection
- [x] Add `get_changed_communities_since(timestamp)` method
- [x] Add `get_pending_updates()` public method
- **Validation**: ✅ Implemented in sync_manager.py

### Task 2.3: Integrate sync with exporter
- [x] Add `mode` parameter to `GraphRAGExporter.export()`
- [x] Implement `mode="full"` and `mode="delta"`
- [x] Auto-update sync state after successful export
- **Validation**: ✅ Integrated in CLI

---

## Phase 3: CLI Integration ✅

### Task 3.1: Add CLI commands
- [x] Create `cli.py` with click-based CLI
- [x] Add `export` command and `status` command
- **Validation**: ✅ CLI commands implemented

### Task 3.2: Add configuration support
- [x] Add `SKILL_EXPORT_*` settings to `settings.py`
- **Validation**: ✅ Settings added

---

## Phase 4: Workflow Integration ✅

### Task 4.1: Update /skill-seekers-proposal workflow
- [x] Add `graphrag` source type
- [x] Add GraphRAG export steps
- **Validation**: ✅ Workflow updated

### Task 4.2: Update /skill-seekers-apply workflow
- [x] Compatible with existing workflow
- **Validation**: ✅ No changes needed

---

## Phase 5: Documentation & Testing ✅

### Task 5.1: Add integration tests
- [ ] Deferred - manual testing completed

### Task 5.2: Add user documentation
- [x] Create `docs/graphrag-skill-integration.md`
- **Validation**: ✅ Documentation created
