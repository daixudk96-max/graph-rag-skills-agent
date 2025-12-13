"""
ATOM Integration Verification Script

验证 ATOM 时序知识图谱集成是否正确工作。
"""

import sys
from pathlib import Path

# 添加项目路径 (graphrag_agent/tests -> graph-rag-agent)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

def test_imports():
    """测试导入是否正常"""
    print("=" * 50)
    print("1. 测试导入...")
    print("=" * 50)
    
    try:
        from graphrag_agent.config import settings
        print(f"  [OK] settings 导入成功")
        print(f"    - ATOM_ENABLED: {settings.ATOM_ENABLED}")
        print(f"    - ATOM_ENTITY_THRESHOLD: {settings.ATOM_ENTITY_THRESHOLD}")
        print(f"    - ATOM_RELATION_THRESHOLD: {settings.ATOM_RELATION_THRESHOLD}")
        print(f"    - ATOM_MAX_WORKERS: {settings.ATOM_MAX_WORKERS}")
    except Exception as e:
        print(f"  [FAIL] settings 导入失败: {e}")
        return False
    
    try:
        from graphrag_agent.graph.structure import (
            TemporalKnowledgeGraph,
            TemporalEntity,
            TemporalRelationship,
        )
        print(f"  [OK] temporal_kg 模块导入成功")
    except Exception as e:
        print(f"  [FAIL] temporal_kg 导入失败: {e}")
        return False
    
    try:
        from graphrag_agent.graph.extraction import (
            AtomExtractionAdapter,
            create_atom_adapter,
            Neo4jTemporalWriter,
            create_temporal_writer,
        )
        print(f"  [OK] atom_adapter 和 temporal_writer 导入成功")
    except Exception as e:
        print(f"  [FAIL] extraction 模块导入失败: {e}")
        return False
    
    return True


def test_temporal_kg_model():
    """测试 TemporalKnowledgeGraph 模型"""
    print("\n" + "=" * 50)
    print("2. 测试 TemporalKnowledgeGraph 模型...")
    print("=" * 50)
    
    from graphrag_agent.graph.structure import (
        TemporalKnowledgeGraph,
        TemporalEntity,
        TemporalRelationship,
    )
    
    # 创建测试实体
    entity1 = TemporalEntity(id="entity1", name="测试实体1", label="Person")
    entity2 = TemporalEntity(id="entity2", name="测试实体2", label="Organization")
    
    # 创建测试关系
    rel = TemporalRelationship(
        source_id="entity1",
        target_id="entity2",
        type="WORKS_FOR",
        t_obs=[1702512000.0],  # 2023-12-14 00:00:00 UTC
        t_start=[1672531200.0],  # 2023-01-01 00:00:00 UTC
        atomic_facts=["测试实体1 works for 测试实体2"],
    )
    
    # 创建知识图谱
    kg = TemporalKnowledgeGraph(
        entities=[entity1, entity2],
        relationships=[rel],
    )
    
    print(f"  [OK] TemporalKnowledgeGraph 创建成功")
    print(f"    - 实体数量: {len(kg.entities)}")
    print(f"    - 关系数量: {len(kg.relationships)}")
    print(f"    - is_empty(): {kg.is_empty()}")
    
    # 测试转换为 GraphDocument
    graph_docs = kg.to_graph_documents(source_text="测试文本")
    print(f"  [OK] to_graph_documents() 成功")
    print(f"    - GraphDocument 数量: {len(graph_docs)}")
    
    if graph_docs:
        doc = graph_docs[0]
        print(f"    - 节点数量: {len(doc.nodes)}")
        print(f"    - 关系数量: {len(doc.relationships)}")
    
    return True


def test_itext2kg_import():
    """测试 itext2kg 导入"""
    print("\n" + "=" * 50)
    print("3. 测试 itext2kg 导入...")
    print("=" * 50)
    
    try:
        from itext2kg.atom import Atom
        print(f"  [OK] itext2kg.atom.Atom 导入成功")
    except ImportError as e:
        print(f"  [WARN] itext2kg 未安装或导入失败: {e}")
        print(f"    提示: 运行 'pip install -e ./itext2kg' 安装")
        return False
    
    try:
        from itext2kg.atom.models import KnowledgeGraph, Entity, Relationship
        print(f"  [OK] itext2kg.atom.models 导入成功")
    except ImportError as e:
        print(f"  [FAIL] itext2kg.atom.models 导入失败: {e}")
        return False
    
    return True


def test_adapter_creation():
    """测试适配器创建（不实际调用 LLM）"""
    print("\n" + "=" * 50)
    print("4. 测试适配器结构...")
    print("=" * 50)
    
    from graphrag_agent.graph.extraction.atom_adapter import AtomExtractionAdapter
    
    # 检查方法是否存在
    methods = [
        'extract_from_chunks',
        'extract_from_chunks_sync',
        'incremental_update',
        '_extract_atomic_facts',
    ]
    
    for method in methods:
        if hasattr(AtomExtractionAdapter, method):
            print(f"  [OK] AtomExtractionAdapter.{method}() 存在")
        else:
            print(f"  [FAIL] AtomExtractionAdapter.{method}() 不存在")
            return False
    
    return True


def test_writer_structure():
    """测试写入器结构"""
    print("\n" + "=" * 50)
    print("5. 测试写入器结构...")
    print("=" * 50)
    
    from graphrag_agent.graph.extraction.temporal_writer import Neo4jTemporalWriter
    
    methods = [
        'write_temporal_kg',
        '_write_entity',
        '_write_relationship',
        '_batch_write_entities',
        '_batch_write_relationships',
    ]
    
    for method in methods:
        if hasattr(Neo4jTemporalWriter, method):
            print(f"  [OK] Neo4jTemporalWriter.{method}() 存在")
        else:
            print(f"  [FAIL] Neo4jTemporalWriter.{method}() 不存在")
            return False
    
    return True


def main():
    """运行所有验证测试"""
    print("\n" + "=" * 60)
    print("  ATOM Temporal KG Integration Verification")
    print("=" * 60)
    
    results = []
    
    # 运行测试
    results.append(("导入测试", test_imports()))
    results.append(("模型测试", test_temporal_kg_model()))
    results.append(("itext2kg 导入", test_itext2kg_import()))
    results.append(("适配器结构", test_adapter_creation()))
    results.append(("写入器结构", test_writer_structure()))
    
    # 显示结果摘要
    print("\n" + "=" * 60)
    print("  验证结果摘要")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for name, result in results:
        status = "[OK] PASS" if result else "[FAIL] FAIL"
        print(f"  {status}: {name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\n  总计: {passed} 通过, {failed} 失败")
    
    if failed == 0:
        print("\n  [Success] 所有验证测试通过！")
    else:
        print("\n  [Warn] 部分测试失败，请检查上述错误信息。")
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
