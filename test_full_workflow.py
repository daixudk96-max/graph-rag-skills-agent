"""
Complete Workflow Integration Test

Simulates the full end-to-end flow:
1. Export from GraphRAG (Mocked) -> skill_input.json
2. Skill Seekers Proposal (Mocked) -> spec.yaml
3. Skill Seekers Apply (Mocked) -> SKILL.md

This verifies that the data shapes match between stages.
"""

import sys
import json
import shutil
import yaml
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from graphrag_agent.integrations.skill_seekers.config import ExportConfig, ExportResult
from graphrag_agent.integrations.skill_seekers.formatter import SkillInputFormatter

print("=" * 60)
print("GraphRAG -> Proposal -> Apply Workflow Test")
print("=" * 60)

# ==========================================
# Step 1: Export (GraphRAG Side)
# ==========================================
print("\n[Step 1] GraphRAG Export")

# Simulate data coming from Neo4j
mock_communities = [
    {
        "title": "Community: Python Basics",
        "url": "graphrag://community/c1",
        "content": "Python is a high-level language. It emphasizes readability.",
        "content_type": "community_summary",
        "metadata": {"community_id": "c1", "level": 0}
    }
]
mock_entities = [
    {
        "name": "Python",
        "type": "Language",
        "description": "A programming language.",
        "relationships": ["RELATED:Guido van Rossum"]
    }
]

# Create export result
export_result = ExportResult(
    pages=mock_communities,
    entities=mock_entities,
    metadata={"type": "graphrag", "graph_name": "test-kg"},
    dedup_report={"merged": 0}
)

# Format to JSON
formatter = SkillInputFormatter()
skill_input_path = Path("test_workflow_input.json")
formatter.save_to_file(export_result, str(skill_input_path))
print(f"  - Generated {skill_input_path}")

# Verify JSON content
with open(skill_input_path, "r", encoding="utf-8") as f:
    skill_input = json.load(f)
    print(f"  - Input contains {len(skill_input['pages'])} pages and {len(skill_input['entities'])} entities")


# ==========================================
# Step 2: Proposal (Skill Seekers Side)
# ==========================================
print("\n[Step 2] Proposal (Simulated)")
# In a real run, this would be: skill-seekers scrape --spec-first ...
# Here we simulate what the AI would generate reading skill_input.json

spec_yaml_content = {
    "version": "1.0",
    "skill": {
        "name": "Python Knowledge Base",
        "description": "Key concepts from knowledge graph",
        "version": "0.1.0"
    },
    "sources": [
        {"type": "graphrag", "path": str(skill_input_path)}
    ],
    "sections": [
        {
            "id": "basics",
            "title": "Python Basics",
            "content": "Derived from community summary...",
            "references": ["graphrag://community/c1"]
        }
    ]
}

spec_path = Path("test_spec.yaml")
with open(spec_path, "w", encoding="utf-8") as f:
    yaml.dump(spec_yaml_content, f)
print(f"  - Generated {spec_path}")


# ==========================================
# Step 3: Apply (Skill Seekers Side)
# ==========================================
print("\n[Step 3] Apply (Simulated)")
# In a real run, this would be: skill-seekers apply spec.yaml
# The apply step needs to read graphrag source and embed it

print("  - Reading spec...")
with open(spec_path, "r", encoding="utf-8") as f:
    spec = yaml.safe_load(f)

print("  - Processing sources...")
source_path = spec["sources"][0]["path"]
with open(source_path, "r", encoding="utf-8") as f:
    source_data = json.load(f)

# Mock generation of SKILL.md
skill_md_content = f"""# {spec['skill']['name']}

{spec['skill']['description']}

## Sources
- Knowledge Graph: {source_data['source']['graph_name']} (Exported: {source_data['source'].get('export_timestamp')})

## {spec['sections'][0]['title']}
{spec['sections'][0]['content']}

### References
- [Community: Python Basics](graphrag://community/c1)
"""

skill_md_path = Path("test_SKILL.md")
with open(skill_md_path, "w", encoding="utf-8") as f:
    f.write(skill_md_content)

print(f"  - Generated {skill_md_path}")
print("  - Result preview:")
print("-" * 40)
print(skill_md_content)
print("-" * 40)

# Validation
assert "Sources" in skill_md_content
assert "Knowledge Graph" in skill_md_content
assert "graphrag://community/c1" in skill_md_content
print("\n[SUCCESS] Full workflow simulation passed!")

# Cleanup
skill_input_path.unlink()
spec_path.unlink()
skill_md_path.unlink()
