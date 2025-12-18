# Restore itext2kg ATOM Module Exports

## Summary

The `itext2kg` submodule folder was accidentally reset to a pre-integration state, undoing the fixes made in the archived change `2025-12-13-fix-test-import-paths`. This change restores the necessary exports so `EntityProperties` can be imported from `itext2kg.atom.models`.

## Problem

After the reset, importing `EntityProperties` fails:
```
ImportError: cannot import name 'EntityProperties' from 'itext2kg.atom.models'
```

This breaks `TemporalKnowledgeGraph.to_atom_kg()` in `graphrag_agent/graph/structure/temporal_kg.py`.

## Proposed Changes

### itext2kg/itext2kg/atom/models

#### [MODIFY] [__init__.py](file:///c:/github/graph-rag-agent/itext2kg/itext2kg/atom/models/__init__.py)

Add `EntityProperties` to the module exports:

```diff
-from .entity import Entity
+from .entity import Entity, EntityProperties

-__all__ = ["Entity", "Relationship", "RelationshipProperties", "KnowledgeGraph", "RelationshipsExtractor", "Factoid", "AtomicFact", "Prompt"]
+__all__ = ["Entity", "EntityProperties", "Relationship", "RelationshipProperties", "KnowledgeGraph", "RelationshipsExtractor", "Factoid", "AtomicFact", "Prompt"]
```

## Verification Plan

### Automated Tests

1. **Import test**:
   ```bash
   python -c "from itext2kg.atom.models import EntityProperties; print('OK')"
   ```

2. **Integration test**:
   ```bash
   python -c "from graphrag_agent.graph.structure.temporal_kg import TemporalKnowledgeGraph; print('Import OK')"
   ```

## Cross References

- **Archived change**: `openspec/changes/archive/2025-12-13-fix-test-import-paths/`
- **Related spec**: `openspec/specs/atom-extraction/spec.md`
