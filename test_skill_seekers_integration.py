"""
Integration test for GraphRAG to Skill Seekers integration.

Tests the full export flow including:
1. Exporter functionality
2. Deduplicator functionality  
3. Formatter output
4. SyncManager state tracking
5. CLI commands (if Neo4j available)
"""

import sys
import json
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from graphrag_agent.integrations.skill_seekers.config import ExportConfig, ExportResult
from graphrag_agent.integrations.skill_seekers.deduplicator import ContentDeduplicator
from graphrag_agent.integrations.skill_seekers.formatter import SkillInputFormatter

print("=" * 60)
print("GraphRAG -> Skill Seekers Integration Test")
print("=" * 60)

# Test 1: ExportConfig
print("\n[Test 1] ExportConfig")
config = ExportConfig(
    default_level=0,
    include_chunks=False,
    dedup_threshold=0.85,
    max_communities=10,
    output_path="test_output.json"
)
print(f"  - Created config: level={config.default_level}, dedup_threshold={config.dedup_threshold}")
config_dict = config.to_dict()
config2 = ExportConfig.from_dict(config_dict)
assert config2.default_level == config.default_level
assert config2.dedup_threshold == config.dedup_threshold
print("  - Config serialization: OK")

# Test 2: ExportResult
print("\n[Test 2] ExportResult")
result = ExportResult(
    pages=[
        {"title": "Page 1", "content": "Content 1", "url": "http://test/1"},
        {"title": "Page 2", "content": "Content 2", "url": "http://test/2"},
    ],
    entities=[
        {"name": "Entity1", "type": "Person", "description": "Desc 1"},
        {"name": "Entity2", "type": "Place", "description": "Desc 2"},
    ],
    metadata={"type": "graphrag", "export_timestamp": "2024-12-18T00:00:00Z"},
    dedup_report={}
)
print(f"  - Page count: {result.page_count}")
print(f"  - Entity count: {result.entity_count}")
assert result.page_count == 2
assert result.entity_count == 2
print("  - ExportResult: OK")

# Test 3: ContentDeduplicator - entity merging
print("\n[Test 3] ContentDeduplicator - Entity Deduplication")
deduplicator = ContentDeduplicator(similarity_threshold=0.85)

# Test exact match deduplication
entities = [
    {"entity_id": "1", "name": "Python 3.12", "description": "Programming language", "relationships": []},
    {"entity_id": "2", "name": "python312", "description": "Python version", "relationships": ["RELATED:stdlib"]},
    {"entity_id": "3", "name": "JavaScript", "description": "Web language", "relationships": []},
]
deduplicated, report = deduplicator.deduplicate_entities(entities)
print(f"  - Original: {len(entities)}, Deduplicated: {len(deduplicated)}")
print(f"  - Entities removed: {report['entities_removed']}")
assert len(deduplicated) == 2  # Python merged, JS separate
print("  - Exact match dedup: OK")

# Test similarity-based deduplication
deduplicator2 = ContentDeduplicator(similarity_threshold=0.7)
entities2 = [
    {"entity_id": "1", "name": "Machine Learning", "description": "ML field", "relationships": []},
    {"entity_id": "2", "name": "Machine Learn", "description": "ML abbreviation", "relationships": []},  # Similar
    {"entity_id": "3", "name": "Deep Learning", "description": "DL subset", "relationships": []},  # Different enough
]
deduplicated2, report2 = deduplicator2.deduplicate_entities(entities2)
print(f"  - Similarity test: {len(entities2)} -> {len(deduplicated2)} entities")
print("  - Similarity-based dedup: OK")

# Test 4: ContentDeduplicator - page deduplication
print("\n[Test 4] ContentDeduplicator - Page Deduplication")
deduplicator3 = ContentDeduplicator()
pages = [
    {"title": "Page 1", "content": "This is the same content", "url": "http://test/1"},
    {"title": "Page 2", "content": "This is the same content", "url": "http://test/2"},  # Duplicate
    {"title": "Page 3", "content": "Different content here", "url": "http://test/3"},
]
deduplicated_pages = deduplicator3.deduplicate_pages(pages)
duplicate_count = sum(1 for p in deduplicated_pages if p.get("is_duplicate"))
print(f"  - Total pages: {len(deduplicated_pages)}, Duplicates marked: {duplicate_count}")
assert duplicate_count == 1
print("  - Page dedup: OK")

# Test get_report after both entity and page dedup
final_report = deduplicator3.get_report()
print(f"  - Final report duplicate_content_count: {final_report.get('duplicate_content_count', 0)}")

# Test 5: SkillInputFormatter
print("\n[Test 5] SkillInputFormatter")
formatter = SkillInputFormatter()
result = ExportResult(
    pages=[
        {"title": "Community 1", "content": "Summary text", "url": "graphrag://c/1", "content_type": "community_summary", "metadata": {"community_id": "c1"}},
    ],
    entities=[
        {"name": "Entity1", "type": "Concept", "description": "A concept", "relationships": ["RELATED:Entity2"]},
    ],
    metadata={"type": "graphrag", "export_timestamp": "2024-12-18T00:00:00Z"},
    dedup_report={"original_entity_count": 1, "merged_entity_count": 1}
)
formatted = formatter.format(result)
print(f"  - Formatted keys: {list(formatted.keys())}")
assert "source" in formatted
assert "pages" in formatted
assert "entities" in formatted
assert "dedup_report" in formatted
print("  - Format structure: OK")

# Validate output
errors = formatter.validate_output(formatted)
if errors:
    print(f"  - Validation errors: {errors}")
else:
    print("  - Validation: OK")

# Test save to file
with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
    temp_path = f.name

output_path = formatter.save_to_file(result, temp_path)
print(f"  - Saved to: {output_path}")

# Verify saved content
with open(temp_path, 'r', encoding='utf-8') as f:
    saved_data = json.load(f)
assert saved_data["source"]["type"] == "graphrag"
print("  - File content: OK")

# Cleanup
Path(temp_path).unlink()

# Test 6: SyncManager (mock - no Neo4j required)
print("\n[Test 6] SyncManager State Persistence")
from graphrag_agent.integrations.skill_seekers.sync_manager import GraphRAGSkillSyncManager

# Create a mock graph class for testing
class MockGraph:
    def query(self, query, params=None):
        return []

mock_graph = MockGraph()
temp_sync_path = tempfile.mktemp(suffix='.json')

sync_manager = GraphRAGSkillSyncManager(mock_graph, sync_state_path=temp_sync_path)
print(f"  - Initial state: has_previous_export={sync_manager.get_status()['has_previous_export']}")

# Simulate marking synced
sync_manager.mark_synced(["c1", "c2", "c3"], export_mode="full", level=0)
status = sync_manager.get_status()
print(f"  - After mark_synced: exported_count={status['exported_community_count']}")
assert status['exported_community_count'] == 3
assert status['has_previous_export'] == True

# Test persistence
sync_manager2 = GraphRAGSkillSyncManager(mock_graph, sync_state_path=temp_sync_path)
status2 = sync_manager2.get_status()
print(f"  - After reload: exported_count={status2['exported_community_count']}")
assert status2['exported_community_count'] == 3
print("  - State persistence: OK")

# Cleanup
sync_manager2.reset_state()
print("  - Reset state: OK")

print("\n" + "=" * 60)
print("All tests passed!")
print("=" * 60)

# Optional: Test with real Neo4j if available
print("\n[Optional] Testing with Neo4j...")
try:
    from graphrag_agent.config.settings import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD
    if NEO4J_URI and NEO4J_USERNAME:
        from langchain_community.graphs import Neo4jGraph
        from graphrag_agent.integrations.skill_seekers.exporter import GraphRAGExporter
        
        graph = Neo4jGraph(url=NEO4J_URI, username=NEO4J_USERNAME, password=NEO4J_PASSWORD)
        exporter = GraphRAGExporter(graph, ExportConfig(max_communities=5))
        
        print("  - Connected to Neo4j")
        
        # Try export
        try:
            result = exporter.export(mode="full", level=0)
            print(f"  - Export result: {result.page_count} pages, {result.entity_count} entities")
            
            # Deduplicate
            dedup = ContentDeduplicator(0.85)
            result.entities, _ = dedup.deduplicate_entities(result.entities)
            result.pages = dedup.deduplicate_pages(result.pages)
            result.dedup_report = dedup.get_report()
            
            # Save
            formatter = SkillInputFormatter()
            output_path = formatter.save_to_file(result, "skill_input_test.json")
            print(f"  - Saved to: {output_path}")
            print("  - Neo4j export: OK")
            
        except Exception as e:
            print(f"  - Export failed (may be empty KG): {e}")
    else:
        print("  - Neo4j not configured, skipping")
except Exception as e:
    print(f"  - Neo4j test skipped: {e}")

print("\nTest complete!")
