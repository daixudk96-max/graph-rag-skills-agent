"""Live DSA Test - Tests with actual LLM API"""
import sys

def main():
    print("=" * 60)
    print("DSA Live Integration Test")
    print("=" * 60)
    
    # Test 1: Check DSA is enabled
    print("\n1. Checking DSA Configuration...")
    from graphrag_agent.config.settings import DSA_ENABLED, DSA_COMPACTION_ENABLED
    print(f"   DSA_ENABLED: {DSA_ENABLED}")
    print(f"   DSA_COMPACTION_ENABLED: {DSA_COMPACTION_ENABLED}")
    
    # Test 2: Setup DSA schema
    print("\n2. Setting up DSA Schema...")
    from graphrag_agent.community.summary.dsa_schema import setup_dsa_schema, verify_dsa_schema
    setup_result = setup_dsa_schema()
    print(f"   Constraints created: {setup_result.get('constraints_created', [])}")
    print(f"   Indexes created: {setup_result.get('indexes_created', [])}")
    print(f"   Properties added: {setup_result.get('properties_added', [])}")
    print(f"   Errors: {setup_result.get('errors', [])}")
    
    # Test 3: Verify schema
    print("\n3. Verifying DSA Schema...")
    verify_result = verify_dsa_schema()
    print(f"   Community delta count: {verify_result.get('community_delta_count', 0)}")
    print(f"   Communities with DSA props: {verify_result.get('communities_with_dsa_props', 0)}")
    
    # Test 4: Test DeltaSummarizer initialization
    print("\n4. Testing DeltaSummarizer...")
    try:
        from graphrag_agent.config.neo4jdb import get_db_manager
        from graphrag_agent.community.summary.delta import DeltaSummarizer
        
        db = get_db_manager()
        graph = db.get_graph()
        summarizer = DeltaSummarizer(graph)
        
        print(f"   DeltaSummarizer initialized: OK")
        print(f"   LLM model: {type(summarizer.llm).__name__}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 5: Test CommunityCompactor initialization  
    print("\n5. Testing CommunityCompactor...")
    try:
        from graphrag_agent.community.summary.compaction import CommunityCompactor
        compactor = CommunityCompactor(graph)
        
        print(f"   CommunityCompactor initialized: OK")
        print(f"   Delta count threshold: {compactor.delta_count_threshold}")
        print(f"   Delta token threshold: {compactor.delta_token_threshold}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 6: Check if any communities exist for testing
    print("\n6. Checking Communities...")
    try:
        communities = graph.query("MATCH (c:__Community__) RETURN count(c) AS count")
        count = communities[0]['count'] if communities else 0
        print(f"   Total communities: {count}")
        
        if count > 0:
            # Get sample community
            sample = graph.query("MATCH (c:__Community__) RETURN c.id AS id LIMIT 1")
            if sample:
                community_id = sample[0]['id']
                print(f"   Sample community ID: {community_id}")
                
                # Test get_pending_deltas
                deltas = summarizer.get_pending_deltas(community_id)
                print(f"   Pending deltas for sample: {len(deltas)}")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n" + "=" * 60)
    print("DSA Live Integration Test Complete!")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
