
import sys
import os
import json
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch
from dataclasses import dataclass, field
from typing import List, Any, Dict, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Mock ATOM classes structure
@dataclass
class MockAtomEntity:
    name: str
    label: str
    properties: Any = None

@dataclass
class MockAtomRelationship:
    startEntity: MockAtomEntity
    endEntity: MockAtomEntity
    name: str
    properties: Any = None

@dataclass
class MockAtomKG:
    entities: List[MockAtomEntity]
    relationships: List[MockAtomRelationship]

# Create mock data
def create_mock_data():
    e1 = MockAtomEntity(name="Li Ming", label="Person")
    e2 = MockAtomEntity(name="Peking University", label="Organization")
    e3 = MockAtomEntity(name="Beijing", label="Location")
    e4 = MockAtomEntity(name="National Scholarship", label="Award")
    
    r1 = MockAtomRelationship(startEntity=e1, endEntity=e2, name="ATTENDS")
    r2 = MockAtomRelationship(startEntity=e2, endEntity=e3, name="LOCATED_IN")
    r3 = MockAtomRelationship(startEntity=e1, endEntity=e4, name="APPLIES_FOR")
    
    return MockAtomKG(entities=[e1, e2, e3, e4], relationships=[r1, r2, r3])

# Mock Adapter
class MockAtomExtractionAdapter:
    def __init__(self, *args, **kwargs):
        pass

    def extract_from_chunks_sync(self, chunks, observation_time=None, existing_atom_kg=None):
        print(f"[MockAdapter] Extracting from {len(chunks)} chunks...")
        # Check if input text is relevant? 
        # For this verification, we just return the hardcoded graph regardless of input.
        
        mock_atom_kg = create_mock_data()
        
        # We need to return a TemporalKnowledgeGraph
        from graphrag_agent.graph.structure.temporal_kg import TemporalKnowledgeGraph
        
        # We can implement a simplified from_atom_kg logic here or rely on the real one 
        # if we mocked the Atom objects correctly.
        # Let's try to use the real from_atom_kg, assuming our Mock objects have enough attributes.
        # TemporalKnowledgeGraph.from_atom_kg checks attributes.
        
        return TemporalKnowledgeGraph.from_atom_kg(mock_atom_kg, observation_times=[0.0])

# Mock writer to avoid Neo4j dependency
def mock_write_to_neo4j(temporal_kg, merge_strategy="replace"):
    print(f"[MockWriter] Pretending to write {len(temporal_kg.entities)} entities to Neo4j...")
    return {"entities": len(temporal_kg.entities), "relationships": len(temporal_kg.relationships)}

def generate_visualization(json_path: Path):
    data = json.loads(json_path.read_text(encoding="utf-8"))
    
    nodes = []
    links = []
    
    for ent in data.get("entities", []):
        nodes.append({"id": ent["id"], "label": ent["label"], "group": ent["label"]})
        
    for rel in data.get("relationships", []):
        links.append({
            # vis-network expects `from`/`to` for edges
            "from": rel["source_id"],
            "to": rel["target_id"],
            "label": rel["type"]
        })
        
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>GraphRAG Verification Result</title>
        <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
        <style type="text/css">
            #mynetwork {{
                width: 800px;
                height: 600px;
                border: 1px solid lightgray;
            }}
        </style>
    </head>
    <body>
    <h2>Verification Result: Graph Visualization</h2>
    <div id="mynetwork"></div>
    <script type="text/javascript">
        var nodes = new vis.DataSet({json.dumps(nodes)});
        var edges = new vis.DataSet({json.dumps(links)});

        var container = document.getElementById('mynetwork');
        var data = {{
            nodes: nodes,
            edges: edges
        }};
        var options = {{
            nodes: {{
                shape: 'dot',
                size: 16
            }},
            edges: {{
                arrows: 'to',
                font: {{ align: 'middle' }}
            }},
            physics: {{
                forceAtlas2Based: {{
                    gravitationalConstant: -26,
                    centralGravity: 0.005,
                    springLength: 230,
                    springConstant: 0.18
                }},
                maxVelocity: 146,
                solver: 'forceAtlas2Based',
                timestep: 0.35,
                stabilization: {{iterations: 150}}
            }}
        }};
        var network = new vis.Network(container, data, options);
    </script>
    </body>
    </html>
    """
    
    output_html = PROJECT_ROOT / "verification_result.html"
    output_html.write_text(html_content, encoding="utf-8")
    print(f"[Visualization] Generated {output_html}")
    return output_html

def main():
    # Patch the adapter where it is imported in build_kg_atom.py
    input_file = PROJECT_ROOT / "files" / "test_dir"
    
    # We also need to patch get_llm_model and get_embeddings_model because they are called BEFORE the adapter is initialized
    with patch('graphrag_agent.graph.extraction.atom_adapter.AtomExtractionAdapter', side_effect=MockAtomExtractionAdapter), \
         patch('build_kg_atom_debug.write_to_neo4j', side_effect=mock_write_to_neo4j), \
         patch('graphrag_agent.models.get_models.get_llm_model', return_value=MagicMock()), \
         patch('graphrag_agent.models.get_models.get_embeddings_model', return_value=MagicMock()):
        
        import build_kg_atom_debug
        
        # Override args
        sys.argv = ["build_kg_atom_debug.py", "--input", str(input_file)]
        
        print("Running build_kg_atom_debug.main()...")
        try:
            build_kg_atom_debug.main()
        except SystemExit as e:
            if e.code != 0:
                print(f"Build script exited with error code {e.code}")
                # Don't return, let's see if file was created anyway (unlikely)

    
    # Find the latest output file
    output_dir = PROJECT_ROOT / "output" / "kg_build"
    files = list(output_dir.glob("kg_atom_*.json"))
    if not files:
        print("No output file found!")
        return
        
    latest_file = max(files, key=os.path.getctime)
    print(f"Found output: {latest_file}")
    
    # Generate visualization
    html_path = generate_visualization(latest_file)
    print(f"OPEN THIS IN BROWSER: {html_path}")

if __name__ == "__main__":
    main()
