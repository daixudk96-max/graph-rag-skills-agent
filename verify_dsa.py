"""DSA Verification Script - Tests all DSA components"""
import sys

def main():
    results = []
    
    # Test 1: DSA Configuration
    print("=" * 60)
    print("Test 1: DSA Configuration")
    try:
        from graphrag_agent.config.settings import (
            DSA_ENABLED, DSA_DELTA_COUNT_THRESHOLD, 
            DSA_DELTA_TOKEN_THRESHOLD, DSA_COMPACTION_ENABLED
        )
        assert DSA_ENABLED == True
        assert DSA_DELTA_COUNT_THRESHOLD == 5
        assert DSA_DELTA_TOKEN_THRESHOLD == 1000
        assert DSA_COMPACTION_ENABLED == True
        print("  [PASS] All DSA config values correct")
        results.append(("DSA Configuration", True))
    except Exception as e:
        print(f"  [FAIL] {e}")
        results.append(("DSA Configuration", False))
    
    # Test 2: DSA Schema Module
    print("\nTest 2: DSA Schema Module")
    try:
        from graphrag_agent.community.summary.dsa_schema import (
            setup_dsa_schema, verify_dsa_schema
        )
        print("  [PASS] dsa_schema.py imported successfully")
        results.append(("DSA Schema Module", True))
    except Exception as e:
        print(f"  [FAIL] {e}")
        results.append(("DSA Schema Module", False))
    
    # Test 3: LeidenSummarizer.collect_delta_info
    print("\nTest 3: LeidenSummarizer.collect_delta_info")
    try:
        from graphrag_agent.community.summary.leiden import LeidenSummarizer
        import inspect
        assert hasattr(LeidenSummarizer, 'collect_delta_info')
        sig = inspect.signature(LeidenSummarizer.collect_delta_info)
        params = list(sig.parameters.keys())
        assert 'community_id' in params
        assert 'changed_entity_ids' in params
        print("  [PASS] collect_delta_info method exists with correct signature")
        results.append(("LeidenSummarizer.collect_delta_info", True))
    except Exception as e:
        print(f"  [FAIL] {e}")
        results.append(("LeidenSummarizer.collect_delta_info", False))
    
    # Test 4: Scheduler DSA Compaction Config
    print("\nTest 4: Scheduler DSA Compaction Config")
    try:
        from graphrag_agent.integrations.build.incremental.incremental_update_scheduler import IncrementalUpdateScheduler
        scheduler = IncrementalUpdateScheduler()
        assert 'dsa_compaction_threshold' in scheduler.default_config
        assert scheduler.default_config['dsa_compaction_threshold'] == 3600
        print("  [PASS] dsa_compaction_threshold configured (3600s)")
        results.append(("Scheduler DSA Config", True))
    except Exception as e:
        print(f"  [FAIL] {e}")
        results.append(("Scheduler DSA Config", False))
    
    # Test 5: BaseSummarizer mode parameter
    print("\nTest 5: BaseSummarizer mode parameter")
    try:
        from graphrag_agent.community.summary.base import BaseSummarizer
        import inspect
        sig = inspect.signature(BaseSummarizer.process_communities)
        params = list(sig.parameters.keys())
        assert 'mode' in params
        assert 'targets' in params
        mode_default = sig.parameters['mode'].default
        assert mode_default == 'full'
        print("  [PASS] process_communities has mode/targets params")
        results.append(("BaseSummarizer Mode Param", True))
    except Exception as e:
        print(f"  [FAIL] {e}")
        results.append(("BaseSummarizer Mode Param", False))
    
    # Test 6: DeltaSummarizer Class
    print("\nTest 6: DeltaSummarizer Class")
    try:
        from graphrag_agent.community.summary.delta import DeltaSummarizer
        import inspect
        methods = ['collect_delta_info', 'generate_delta_summary', 
                   'store_delta', 'process_deltas', 'get_pending_deltas',
                   'merge_summaries_for_read']
        for method in methods:
            assert hasattr(DeltaSummarizer, method), f"Missing {method}"
        print(f"  [PASS] All {len(methods)} DeltaSummarizer methods present")
        results.append(("DeltaSummarizer Class", True))
    except Exception as e:
        print(f"  [FAIL] {e}")
        results.append(("DeltaSummarizer Class", False))
    
    # Test 7: CommunityCompactor Class
    print("\nTest 7: CommunityCompactor Class")
    try:
        from graphrag_agent.community.summary.compaction import CommunityCompactor
        import inspect
        methods = ['check_compaction_needed', 'compact_community', 
                   'compact_all', 'cleanup_compacted_deltas']
        for method in methods:
            assert hasattr(CommunityCompactor, method), f"Missing {method}"
        print(f"  [PASS] All {len(methods)} CommunityCompactor methods present")
        results.append(("CommunityCompactor Class", True))
    except Exception as e:
        print(f"  [FAIL] {e}")
        results.append(("CommunityCompactor Class", False))
    
    # Summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    passed = sum(1 for _, ok in results if ok)
    failed = sum(1 for _, ok in results if not ok)
    for name, ok in results:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}")
    print(f"\nTotal: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
