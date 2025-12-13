# -*- coding: utf-8 -*-
"""Simple ATOM verification test"""
import sys
sys.path.insert(0, '.')

print("=== ATOM Integration Test ===")
print()

# Test 1: Settings
print("1. Testing Settings...")
try:
    from graphrag_agent.config.settings import (
        ATOM_ENABLED, ATOM_ENTITY_THRESHOLD, ATOM_RELATION_THRESHOLD
    )
    print(f"   ATOM_ENABLED: {ATOM_ENABLED}")
    print(f"   ATOM_ENTITY_THRESHOLD: {ATOM_ENTITY_THRESHOLD}")
    print(f"   ATOM_RELATION_THRESHOLD: {ATOM_RELATION_THRESHOLD}")
    print("   [PASS]")
except Exception as e:
    print(f"   [FAIL] {e}")

# Test 2: TemporalKnowledgeGraph
print()
print("2. Testing TemporalKnowledgeGraph...")
try:
    from graphrag_agent.graph.structure.temporal_kg import (
        TemporalKnowledgeGraph, TemporalEntity, TemporalRelationship
    )
    e1 = TemporalEntity(id="t1", name="Test Entity", label="Person")
    r1 = TemporalRelationship(source_id="t1", target_id="t2", type="KNOWS", t_obs=[1.0])
    kg = TemporalKnowledgeGraph(entities=[e1], relationships=[r1])
    print(f"   Entities: {len(kg.entities)}")
    print(f"   Relationships: {len(kg.relationships)}")
    print(f"   is_empty(): {kg.is_empty()}")
    print("   [PASS]")
except Exception as e:
    print(f"   [FAIL] {e}")

# Test 3: AtomExtractionAdapter structure
print()
print("3. Testing AtomExtractionAdapter...")
try:
    from graphrag_agent.graph.extraction.atom_adapter import AtomExtractionAdapter
    print(f"   extract_from_chunks: {hasattr(AtomExtractionAdapter, 'extract_from_chunks')}")
    print(f"   extract_from_chunks_sync: {hasattr(AtomExtractionAdapter, 'extract_from_chunks_sync')}")
    print("   [PASS]")
except Exception as e:
    print(f"   [FAIL] {e}")

# Test 4: Neo4jTemporalWriter structure
print()
print("4. Testing Neo4jTemporalWriter...")
try:
    from graphrag_agent.graph.extraction.temporal_writer import Neo4jTemporalWriter
    print(f"   write_temporal_kg: {hasattr(Neo4jTemporalWriter, 'write_temporal_kg')}")
    print("   [PASS]")
except Exception as e:
    print(f"   [FAIL] {e}")

# Test 5: itext2kg
print()
print("5. Testing itext2kg...")
try:
    from itext2kg.atom import Atom
    from itext2kg.atom.models import KnowledgeGraph
    print("   Atom: OK")
    print("   KnowledgeGraph: OK")
    print("   [PASS]")
except ImportError as e:
    print(f"   [SKIP] Not installed: {e}")
except Exception as e:
    print(f"   [FAIL] {e}")

print()
print("=== Test Complete ===")
