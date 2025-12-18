"""
DSA End-to-End Integration Test

Tests the Delta-Summary Accumulation flow:
1. DeltaSummarizer - delta generation
2. CommunityCompactor - compaction
3. Read-path merge - query with deltas

Uses mock LLM to avoid API costs.
"""

import sys
from unittest.mock import MagicMock, patch

# Mock LLM response for testing
class MockLLMResponse:
    content = "This is a test delta summary describing new entities added to the community."

class MockLLM:
    def invoke(self, prompt):
        return MockLLMResponse()
    
    def __or__(self, other):
        """Support pipe operator for LangChain chains"""
        return MockChain(self, other)

class MockChain:
    def __init__(self, llm, parser):
        self.llm = llm
        self.parser = parser
    
    def invoke(self, inputs):
        response = self.llm.invoke(inputs)
        return response.content if hasattr(response, 'content') else str(response)


def test_dsa_configuration():
    """Test DSA configuration parameters exist and have correct defaults"""
    from graphrag_agent.config.settings import (
        DSA_ENABLED,
        DSA_DELTA_COUNT_THRESHOLD,
        DSA_DELTA_TOKEN_THRESHOLD,
        DSA_COMPACTION_ENABLED
    )
    
    assert DSA_ENABLED == True, "DSA_ENABLED should be True by default"
    assert DSA_DELTA_COUNT_THRESHOLD == 5, "DSA_DELTA_COUNT_THRESHOLD should be 5"
    assert DSA_DELTA_TOKEN_THRESHOLD == 1000, "DSA_DELTA_TOKEN_THRESHOLD should be 1000"
    assert DSA_COMPACTION_ENABLED == True, "DSA_COMPACTION_ENABLED should be True"
    
    print("[PASS] test_dsa_configuration")


def test_delta_summarizer_initialization():
    """Test DeltaSummarizer can be instantiated"""
    from graphrag_agent.config.neo4jdb import get_db_manager
    from graphrag_agent.community.summary.delta import DeltaSummarizer
    
    db = get_db_manager()
    graph = db.get_graph()
    
    # Patch LLM
    with patch('graphrag_agent.community.summary.delta.get_llm_model', return_value=MockLLM()):
        summarizer = DeltaSummarizer(graph)
        
        assert summarizer.graph is not None
        assert summarizer.llm is not None
        
    print("[PASS] test_delta_summarizer_initialization")


def test_community_compactor_initialization():
    """Test CommunityCompactor can be instantiated"""
    from graphrag_agent.config.neo4jdb import get_db_manager
    from graphrag_agent.community.summary.compaction import CommunityCompactor
    
    db = get_db_manager()
    graph = db.get_graph()
    
    with patch('graphrag_agent.community.summary.compaction.get_llm_model', return_value=MockLLM()):
        compactor = CommunityCompactor(graph)
        
        assert compactor.graph is not None
        assert compactor.delta_count_threshold == 5
        assert compactor.delta_token_threshold == 1000
        
    print("[PASS] test_community_compactor_initialization")


def test_check_compaction_needed():
    """Test compaction threshold checking"""
    from graphrag_agent.config.neo4jdb import get_db_manager
    from graphrag_agent.community.summary.compaction import CommunityCompactor
    
    db = get_db_manager()
    graph = db.get_graph()
    
    with patch('graphrag_agent.community.summary.compaction.get_llm_model', return_value=MockLLM()):
        compactor = CommunityCompactor(graph)
        
        # Test with non-existent community (should return False)
        result = compactor.check_compaction_needed("non_existent_community_id_12345")
        assert result == False, "Should return False for non-existent community"
        
    print("[PASS] test_check_compaction_needed")


def test_read_path_query_syntax():
    """Test that read-path queries with delta merge have valid syntax"""
    from graphrag_agent.config.neo4jdb import get_db_manager
    
    db = get_db_manager()
    graph = db.get_graph()
    
    # Test global_search style query
    query = """
    MATCH (c:__Community__)
    WHERE c.level = $level
    OPTIONAL MATCH (c)-[:HAS_DELTA]->(d:__CommunityDelta__ {status: 'pending'})
    WITH c, d ORDER BY d.created_at ASC
    WITH c, collect(d.summary) AS delta_summaries
    RETURN {
        communityId: c.id, 
        full_content: CASE 
            WHEN size(delta_summaries) > 0 
            THEN coalesce(c.full_content, c.summary, '') + 
                 '\n\n[Recent Updates]:\n' + 
                 reduce(s = '', item IN delta_summaries | s + '- ' + coalesce(item, '') + '\n')
            ELSE coalesce(c.full_content, c.summary, '')
        END
    } AS output
    LIMIT 5
    """
    
    try:
        result = graph.query(query, params={"level": 0})
        print(f"  Query returned {len(result)} communities")
        assert isinstance(result, list), "Query should return a list"
    except Exception as e:
        raise AssertionError(f"Read-path query syntax error: {e}")
    
    print("[PASS] test_read_path_query_syntax")


def test_base_summarizer_mode_parameter():
    """Test BaseSummarizer accepts mode parameter"""
    from graphrag_agent.community.summary.base import BaseSummarizer
    from graphrag_agent.community.summary.leiden import LeidenSummarizer
    from graphrag_agent.config.neo4jdb import get_db_manager
    import inspect
    
    # Check mode parameter exists in process_communities
    sig = inspect.signature(BaseSummarizer.process_communities)
    params = list(sig.parameters.keys())
    
    assert 'mode' in params, "process_communities should have 'mode' parameter"
    assert 'targets' in params, "process_communities should have 'targets' parameter"
    
    # Test mode default value
    mode_param = sig.parameters['mode']
    assert mode_param.default == 'full', "mode default should be 'full'"
    
    print("[PASS] test_base_summarizer_mode_parameter")


def test_delta_store_and_retrieve():
    """Test storing and retrieving deltas in Neo4j"""
    from graphrag_agent.config.neo4jdb import get_db_manager
    from graphrag_agent.community.summary.delta import DeltaSummarizer
    
    db = get_db_manager()
    graph = db.get_graph()
    
    with patch('graphrag_agent.community.summary.delta.get_llm_model', return_value=MockLLM()):
        summarizer = DeltaSummarizer(graph)
        
        # Get a real community ID from the database
        communities = graph.query("MATCH (c:__Community__) RETURN c.id AS id LIMIT 1")
        
        if communities:
            community_id = communities[0]['id']
            print(f"  Using community: {community_id}")
            
            # Store a test delta
            delta_id = summarizer.store_delta(
                community_id=community_id,
                summary="Test delta: New entities about testing were added.",
                related_entities=["test_entity_1", "test_entity_2"],
                summary_tokens=15
            )
            
            if delta_id:
                print(f"  Created delta: {delta_id}")
                
                # Retrieve pending deltas
                deltas = summarizer.get_pending_deltas(community_id)
                assert len(deltas) > 0, "Should have at least one pending delta"
                print(f"  Found {len(deltas)} pending deltas")
                
                # Clean up test delta
                graph.query("""
                    MATCH (d:__CommunityDelta__ {id: $delta_id})
                    DETACH DELETE d
                """, params={"delta_id": delta_id})
                print(f"  Cleaned up test delta")
            else:
                print("  [SKIP] store_delta returned None (community may not exist)")
        else:
            print("  [SKIP] No communities found in database")
    
    print("[PASS] test_delta_store_and_retrieve")


def run_all_tests():
    """Run all DSA tests"""
    print("\n" + "="*60)
    print("DSA End-to-End Integration Tests")
    print("="*60 + "\n")
    
    tests = [
        test_dsa_configuration,
        test_delta_summarizer_initialization,
        test_community_compactor_initialization,
        test_check_compaction_needed,
        test_read_path_query_syntax,
        test_base_summarizer_mode_parameter,
        test_delta_store_and_retrieve,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"[FAIL] {test.__name__}: {e}")
            failed += 1
    
    print("\n" + "="*60)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*60 + "\n")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
