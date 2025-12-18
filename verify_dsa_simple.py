"""Simple DSA Verification - No Neo4j Required"""
import inspect

def main():
    passed = 0
    failed = 0
    
    # Test 1: DSA Config
    print("Test 1: DSA Configuration")
    try:
        from graphrag_agent.config.settings import (
            DSA_ENABLED, DSA_DELTA_COUNT_THRESHOLD, 
            DSA_DELTA_TOKEN_THRESHOLD, DSA_COMPACTION_ENABLED
        )
        print(f"  DSA_ENABLED={DSA_ENABLED}")
        print(f"  DSA_DELTA_COUNT_THRESHOLD={DSA_DELTA_COUNT_THRESHOLD}")
        print(f"  DSA_DELTA_TOKEN_THRESHOLD={DSA_DELTA_TOKEN_THRESHOLD}")
        print(f"  DSA_COMPACTION_ENABLED={DSA_COMPACTION_ENABLED}")
        print("  [PASS]")
        passed += 1
    except Exception as e:
        print(f"  [FAIL] {e}")
        failed += 1

    # Test 2: DSA Schema Module
    print("\nTest 2: DSA Schema Module")
    try:
        from graphrag_agent.community.summary.dsa_schema import setup_dsa_schema
        print("  [PASS] Module imported")
        passed += 1
    except Exception as e:
        print(f"  [FAIL] {e}")
        failed += 1

    # Test 3: LeidenSummarizer.collect_delta_info
    print("\nTest 3: LeidenSummarizer.collect_delta_info")
    try:
        from graphrag_agent.community.summary.leiden import LeidenSummarizer
        sig = inspect.signature(LeidenSummarizer.collect_delta_info)
        params = list(sig.parameters.keys())
        print(f"  Params: {params}")
        assert 'community_id' in params
        assert 'changed_entity_ids' in params
        print("  [PASS]")
        passed += 1
    except Exception as e:
        print(f"  [FAIL] {e}")
        failed += 1

    # Test 4: Scheduler config
    print("\nTest 4: Scheduler DSA Config")
    try:
        from graphrag_agent.integrations.build.incremental.incremental_update_scheduler import IncrementalUpdateScheduler
        s = IncrementalUpdateScheduler()
        threshold = s.default_config.get("dsa_compaction_threshold")
        print(f"  dsa_compaction_threshold={threshold}")
        assert threshold == 3600
        print("  [PASS]")
        passed += 1
    except Exception as e:
        print(f"  [FAIL] {e}")
        failed += 1

    # Test 5: BaseSummarizer mode param
    print("\nTest 5: BaseSummarizer mode parameter")
    try:
        from graphrag_agent.community.summary.base import BaseSummarizer
        sig = inspect.signature(BaseSummarizer.process_communities)
        params = list(sig.parameters.keys())
        print(f"  Params: {params}")
        assert 'mode' in params
        assert 'targets' in params
        print("  [PASS]")
        passed += 1
    except Exception as e:
        print(f"  [FAIL] {e}")
        failed += 1

    print("\n" + "=" * 40)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 40)
    return failed == 0

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
