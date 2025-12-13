# -*- coding: utf-8 -*-
"""
Phase 2: ATOM 端到端测试 - 完整流程到写入知识图谱

使用 Mock LLM、Embeddings 和 Neo4j 测试完整的 ATOM 提取和写入流程。
记录所有错误但不修正。
"""
import sys
import os
import traceback
from datetime import datetime, timezone
from typing import List, Dict, Any
from unittest.mock import Mock, MagicMock, patch

sys.path.insert(0, '.')

# 设置 ATOM 为启用状态
os.environ["ATOM_ENABLED"] = "true"

# 错误收集器
errors_log: List[Dict[str, Any]] = []
warnings_log: List[Dict[str, Any]] = []

def log_error(test_name: str, error: Exception, context: str = ""):
    """记录错误到日志"""
    error_info = {
        "test_name": test_name,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "traceback": traceback.format_exc(),
        "context": context,
        "timestamp": datetime.now().isoformat()
    }
    errors_log.append(error_info)
    print(f"  [ERROR] {type(error).__name__}: {error}")

def log_warning(test_name: str, message: str, context: str = ""):
    """记录警告"""
    warning_info = {
        "test_name": test_name,
        "message": message,
        "context": context,
        "timestamp": datetime.now().isoformat()
    }
    warnings_log.append(warning_info)
    print(f"  [WARNING] {message}")

def log_success(test_name: str, message: str = ""):
    """记录成功"""
    print(f"  [PASS] {message}")


print("=" * 70)
print("Phase 2: ATOM 端到端测试 - 完整流程到写入知识图谱")
print("=" * 70)
print()

# ============================================================
# 准备阶段：创建 Mock 对象
# ============================================================
print("准备阶段：创建 Mock 对象...")

# Mock LLM - 模拟 ATOM 提取返回结果
mock_llm = MagicMock()
mock_llm.invoke = Mock(return_value=Mock(content="""
{
  "entities": [
    {"name": "学生", "label": "学生类型"},
    {"name": "国家奖学金", "label": "奖学金类型"},
    {"name": "学业成绩", "label": "评定标准"}
  ],
  "relationships": [
    {"subject": "学生", "predicate": "申请", "object": "国家奖学金"},
    {"subject": "国家奖学金", "predicate": "要求", "object": "学业成绩"}
  ]
}
"""))

# Mock Embeddings
mock_embeddings = MagicMock()
mock_embeddings.embed_documents = Mock(return_value=[[0.1] * 384 for _ in range(10)])
mock_embeddings.embed_query = Mock(return_value=[0.1] * 384)

# Mock Neo4j Graph
mock_neo4j_graph = MagicMock()
mock_neo4j_graph.query = Mock(return_value=[])
mock_neo4j_graph.refresh_schema = Mock()

print("  Mock LLM: OK")
print("  Mock Embeddings: OK")
print("  Mock Neo4j Graph: OK")
print()

# ============================================================
# Test 1: 直接导入核心组件（绕过 graphdatascience）
# ============================================================
print("1. 直接导入核心 ATOM 组件...")
try:
    # 直接导入需要的模块，避免触发 graphdatascience
    from graphrag_agent.graph.structure.temporal_kg import (
        TemporalKnowledgeGraph,
        TemporalEntity,
        TemporalRelationship
    )
    from graphrag_agent.graph.extraction.atom_adapter import AtomExtractionAdapter
    from graphrag_agent.graph.extraction.temporal_writer import Neo4jTemporalWriter
    
    log_success("核心组件导入", "TemporalKnowledgeGraph, AtomExtractionAdapter, Neo4jTemporalWriter")
except Exception as e:
    log_error("核心组件导入", e, "导入 ATOM 核心组件失败")

# ============================================================
# Test 2: 初始化 AtomExtractionAdapter（使用 Mock）
# ============================================================
print()
print("2. 初始化 AtomExtractionAdapter...")
adapter = None
try:
    adapter = AtomExtractionAdapter(
        llm_model=mock_llm,
        embeddings_model=mock_embeddings
    )
    log_success("AtomExtractionAdapter 初始化", 
                f"ent_threshold={adapter.ent_threshold}, rel_threshold={adapter.rel_threshold}")
except Exception as e:
    log_error("AtomExtractionAdapter 初始化", e, "使用 Mock 模型初始化失败")

# ============================================================
# Test 3: 准备测试数据（模拟 files/ 目录的文档内容）
# ============================================================
print()
print("3. 准备测试数据...")
test_chunks = [
    "第一条 为规范学生管理行为，维护普通高等学校正常的教育教学秩序和生活秩序，保障学生合法权益，培养德、智、体、美等方面全面发展的社会主义建设者和接班人，依据教育法、高等教育法以及有关法规，制定本规定。",
    "第二十一条 国家奖学金每学年评选一次，实行等额评审。各高校于每学年开学初启动评审工作，当年10月31日前完成评审。高校每年11月30日前将国家奖学金一次性发放给获奖学生。",
    "第三十五条 学生有下列情形之一，学校可以给予开除学籍处分：(一)违反宪法，反对四项基本原则、破坏安定团结、扰乱社会秩序的;",
]

# 转换为不同格式测试
from langchain_core.documents import Document
test_chunks_formatted = [
    Document(page_content=chunk) for chunk in test_chunks
]

print(f"  测试 chunks 数量: {len(test_chunks_formatted)}")
log_success("测试数据准备", f"{len(test_chunks)} 个文本块")

# ============================================================
# Test 4: 测试原子事实提取
# ============================================================
print()
print("4. 测试原子事实提取 (_extract_atomic_facts)...")
try:
    if adapter:
        facts = adapter._extract_atomic_facts(test_chunks_formatted)
        print(f"  提取的原子事实数量: {len(facts)}")
        for i, fact in enumerate(facts[:2]):  # 只显示前2个
            print(f"    [{i+1}] {fact[:50]}...")
        log_success("原子事实提取", f"成功提取 {len(facts)} 个原子事实")
    else:
        log_warning("原子事实提取", "跳过 - adapter 未初始化", "依赖失败")
except Exception as e:
    log_error("原子事实提取", e, "_extract_atomic_facts 调用失败")

# ============================================================
# Test 5: 测试 ATOM build_graph（Mock 调用）
# ============================================================
print()
print("5. 测试 ATOM build_graph（模拟异步调用）...")
temporal_kg = None
try:
    if adapter:
        import asyncio
        
        # Mock ATOM 的 build_graph 方法返回
        from itext2kg.atom.models import KnowledgeGraph as AtomKG, Entity as AtomEntity, Relationship as AtomRel
        
        # 创建模拟的 ATOM 返回结果
        mock_atom_entities = [
            AtomEntity(name="学生", label="学生类型"),
            AtomEntity(name="国家奖学金", label="奖学金类型"),
            AtomEntity(name="开除学籍", label="处分类型"),
        ]
        mock_atom_rels = [
            AtomRel(name="申请", startEntity=mock_atom_entities[0], endEntity=mock_atom_entities[1]),
            AtomRel(name="可能导致", startEntity=mock_atom_entities[0], endEntity=mock_atom_entities[2]),
        ]
        mock_atom_kg = AtomKG(entities=mock_atom_entities, relationships=mock_atom_rels)
        
        # Patch build_graph 方法
        async def mock_build_graph(*args, **kwargs):
            return mock_atom_kg
        
        adapter.atom.build_graph = mock_build_graph
        
        # 调用提取方法
        async def run_extraction():
            return await adapter.extract_from_chunks(
                test_chunks_formatted,
                observation_time=datetime.now(timezone.utc).isoformat()
            )
        
        temporal_kg = asyncio.run(run_extraction())
        
        print(f"  提取的实体数量: {len(temporal_kg.entities)}")
        print(f"  提取的关系数量: {len(temporal_kg.relationships)}")
        for ent in temporal_kg.entities:
            print(f"    - 实体: {ent.name} ({ent.label})")
        
        log_success("ATOM build_graph", 
                    f"{len(temporal_kg.entities)} 实体, {len(temporal_kg.relationships)} 关系")
    else:
        log_warning("ATOM build_graph", "跳过 - adapter 未初始化", "依赖失败")
except Exception as e:
    log_error("ATOM build_graph", e, "ATOM 图谱构建失败")

# ============================================================
# Test 6: 测试 TemporalKnowledgeGraph 转换
# ============================================================
print()
print("6. 测试 TemporalKnowledgeGraph 转换...")
try:
    if temporal_kg:
        # 转换为 GraphDocument
        graph_docs = temporal_kg.to_graph_documents(source_text="测试文档内容")
        print(f"  GraphDocument 数量: {len(graph_docs)}")
        if graph_docs:
            doc = graph_docs[0]
            print(f"  节点数量: {len(doc.nodes)}")
            print(f"  关系数量: {len(doc.relationships)}")
        log_success("GraphDocument 转换", f"{len(graph_docs)} 个 GraphDocument")
        
        # 测试 to_atom_kg 转换
        print("  测试 to_atom_kg 逆向转换...")
        try:
            atom_kg_back = temporal_kg.to_atom_kg()
            print(f"    ATOM KG 实体: {len(atom_kg_back.entities)}")
            print(f"    ATOM KG 关系: {len(atom_kg_back.relationships)}")
            log_success("to_atom_kg 转换", "逆向转换成功")
        except Exception as e:
            log_error("to_atom_kg 转换", e, "TemporalKnowledgeGraph -> ATOM KG 失败")
    else:
        log_warning("TemporalKnowledgeGraph 转换", "跳过 - temporal_kg 为空", "依赖失败")
except Exception as e:
    log_error("TemporalKnowledgeGraph 转换", e, "转换失败")

# ============================================================
# Test 7: 初始化 Neo4jTemporalWriter（使用 Mock）
# ============================================================
print()
print("7. 初始化 Neo4jTemporalWriter（使用 Mock Neo4j）...")
writer = None
try:
    writer = Neo4jTemporalWriter(
        graph=mock_neo4j_graph,
        batch_size=50,
        max_workers=4
    )
    log_success("Neo4jTemporalWriter 初始化", f"batch_size={writer.batch_size}")
except Exception as e:
    log_error("Neo4jTemporalWriter 初始化", e, "使用 Mock Neo4j 初始化失败")

# ============================================================
# Test 8: 测试写入实体
# ============================================================
print()
print("8. 测试写入实体...")
try:
    if writer and temporal_kg and temporal_kg.entities:
        # 调用内部方法测试
        entity_count = writer._batch_write_entities(temporal_kg.entities, "update")
        print(f"  写入实体数量: {entity_count}")
        
        # 检查 mock 调用
        query_calls = mock_neo4j_graph.query.call_count
        print(f"  Neo4j query 调用次数: {query_calls}")
        
        log_success("写入实体", f"{entity_count} 个实体写入成功（Mock）")
    else:
        log_warning("写入实体", "跳过 - writer 或 temporal_kg 未准备好", "依赖失败")
except Exception as e:
    log_error("写入实体", e, "_batch_write_entities 调用失败")

# ============================================================
# Test 9: 测试写入关系
# ============================================================
print()
print("9. 测试写入关系...")
try:
    if writer and temporal_kg and temporal_kg.relationships:
        # 重置 mock 调用计数
        mock_neo4j_graph.query.reset_mock()
        
        # 调用内部方法测试
        rel_count = writer._batch_write_relationships(temporal_kg.relationships, "update")
        print(f"  写入关系数量: {rel_count}")
        
        # 检查 mock 调用
        query_calls = mock_neo4j_graph.query.call_count
        print(f"  Neo4j query 调用次数: {query_calls}")
        
        log_success("写入关系", f"{rel_count} 个关系写入成功（Mock）")
    else:
        log_warning("写入关系", "跳过 - writer 或 temporal_kg 未准备好", "依赖失败")
except Exception as e:
    log_error("写入关系", e, "_batch_write_relationships 调用失败")

# ============================================================
# Test 10: 测试完整写入流程 (write_temporal_kg)
# ============================================================
print()
print("10. 测试完整写入流程 (write_temporal_kg)...")
try:
    if writer and temporal_kg:
        # 重置 mock
        mock_neo4j_graph.query.reset_mock()
        
        # 调用完整写入方法
        stats = writer.write_temporal_kg(temporal_kg, merge_strategy='update')
        
        print(f"  写入统计: {stats}")
        print(f"  实体写入: {stats.get('entities', 0)}")
        print(f"  关系写入: {stats.get('relationships', 0)}")
        
        # 验证 mock 被调用
        total_queries = mock_neo4j_graph.query.call_count
        print(f"  总 Neo4j query 调用: {total_queries}")
        
        log_success("完整写入流程", 
                    f"write_temporal_kg 成功 - {stats['entities']} 实体, {stats['relationships']} 关系")
    else:
        log_warning("完整写入流程", "跳过 - writer 或 temporal_kg 未准备好", "依赖失败")
except Exception as e:
    log_error("完整写入流程", e, "write_temporal_kg 调用失败")

# ============================================================
# Test 11: 测试 replace 合并策略
# ============================================================
print()
print("11. 测试 replace 合并策略...")
try:
    if writer and temporal_kg:
        mock_neo4j_graph.query.reset_mock()
        
        stats = writer.write_temporal_kg(temporal_kg, merge_strategy='replace')
        
        print(f"  replace 模式写入: {stats}")
        log_success("replace 合并策略", f"写入成功 - {stats}")
    else:
        log_warning("replace 合并策略", "跳过", "依赖失败")
except Exception as e:
    log_error("replace 合并策略", e, "replace 模式写入失败")

# ============================================================
# Test 12: 测试空图谱处理
# ============================================================
print()
print("12. 测试空图谱处理...")
try:
    if writer:
        empty_kg = TemporalKnowledgeGraph()
        stats = writer.write_temporal_kg(empty_kg)
        
        print(f"  空图谱写入结果: {stats}")
        if stats['entities'] == 0 and stats['relationships'] == 0:
            log_success("空图谱处理", "正确返回空统计")
        else:
            log_warning("空图谱处理", f"预期为空但返回 {stats}", "逻辑错误")
    else:
        log_warning("空图谱处理", "跳过", "依赖失败")
except Exception as e:
    log_error("空图谱处理", e, "空图谱写入失败")

# ============================================================
# Test 13: 测试 GraphDocument 写入方式
# ============================================================
print()
print("13. 测试 write_graph_documents_from_temporal_kg...")
try:
    if writer and temporal_kg:
        mock_neo4j_graph.query.reset_mock()
        
        # 这个方法使用父类的写入逻辑
        writer.write_graph_documents_from_temporal_kg(temporal_kg, source_text="测试")
        
        query_calls = mock_neo4j_graph.query.call_count
        print(f"  Neo4j query 调用: {query_calls}")
        
        log_success("GraphDocument 写入", f"调用成功 ({query_calls} queries)")
    else:
        log_warning("GraphDocument 写入", "跳过", "依赖失败")
except Exception as e:
    log_error("GraphDocument 写入", e, "write_graph_documents_from_temporal_kg 失败")

# ============================================================
# 生成完整错误报告
# ============================================================
print()
print("=" * 70)
print("端到端测试完成 - 完整报告")
print("=" * 70)

print(f"\n总计: {len(errors_log)} 个错误, {len(warnings_log)} 个警告")

if errors_log:
    print(f"\n错误列表 ({len(errors_log)}):")
    for i, err in enumerate(errors_log, 1):
        print(f"\n  [{i}] {err['test_name']}")
        print(f"      类型: {err['error_type']}")
        print(f"      消息: {err['error_message'][:100]}...")
        print(f"      时间: {err['timestamp']}")

if warnings_log:
    print(f"\n警告列表 ({len(warnings_log)}):")
    for i, warn in enumerate(warnings_log, 1):
        print(f"\n  [{i}] {warn['test_name']}")
        print(f"      消息: {warn['message']}")

# 输出 JSON 格式
import json
print("\n\n--- JSON 错误日志 ---")
print(json.dumps({
    "errors": errors_log,
    "warnings": warnings_log,
    "summary": {
        "total_errors": len(errors_log),
        "total_warnings": len(warnings_log),
        "test_time": datetime.now().isoformat()
    }
}, ensure_ascii=False, indent=2))
