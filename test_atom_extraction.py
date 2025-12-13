# -*- coding: utf-8 -*-
"""
Phase 2: ATOM Default Testing - 提取测试

使用模拟 LLM 和 Embeddings 测试 ATOM 提取流程。
记录所有错误但不修正。
"""
import sys
import os
import traceback
from datetime import datetime
from typing import List, Dict, Any

sys.path.insert(0, '.')

# 设置 ATOM 为启用状态
os.environ["ATOM_ENABLED"] = "true"

# 错误收集器
errors_log: List[Dict[str, Any]] = []

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

def log_success(test_name: str, message: str = ""):
    """记录成功"""
    print(f"  [PASS] {message}")


print("=" * 60)
print("Phase 2: ATOM Default Extraction Testing")
print("=" * 60)
print()

# ============================================================
# Test 1: 基础导入测试
# ============================================================
print("1. 基础导入测试...")
try:
    from graphrag_agent.config.settings import ATOM_ENABLED
    print(f"   ATOM_ENABLED = {ATOM_ENABLED}")
    if ATOM_ENABLED:
        log_success("基础导入", "ATOM 已启用")
    else:
        log_error("基础导入", ValueError("ATOM_ENABLED 应为 True"), "环境变量设置")
except Exception as e:
    log_error("基础导入", e, "导入 settings 失败")

# ============================================================
# Test 2: itext2kg ATOM 模块导入
# ============================================================
print()
print("2. itext2kg ATOM 模块导入...")
try:
    from itext2kg.atom import Atom
    from itext2kg.atom.models import KnowledgeGraph, Entity, Relationship
    log_success("itext2kg 导入", "Atom, KnowledgeGraph, Entity, Relationship")
except Exception as e:
    log_error("itext2kg 导入", e, "导入 ATOM 核心模块失败")

# ============================================================
# Test 3: TemporalKnowledgeGraph 模型测试
# ============================================================
print()
print("3. TemporalKnowledgeGraph 模型测试...")
try:
    from graphrag_agent.graph.structure.temporal_kg import (
        TemporalKnowledgeGraph,
        TemporalEntity,
        TemporalRelationship
    )
    
    # 创建测试实体
    e1 = TemporalEntity(id="学生", name="学生", label="学生类型")
    e2 = TemporalEntity(id="奖学金", name="奖学金", label="奖学金类型")
    
    # 创建测试关系
    r1 = TemporalRelationship(
        source_id="学生",
        target_id="奖学金",
        type="申请",
        t_obs=[datetime.now().timestamp()]
    )
    
    # 创建知识图谱
    kg = TemporalKnowledgeGraph(entities=[e1, e2], relationships=[r1])
    
    print(f"   实体数量: {len(kg.entities)}")
    print(f"   关系数量: {len(kg.relationships)}")
    print(f"   is_empty(): {kg.is_empty()}")
    
    # 测试转换为 GraphDocument
    graph_docs = kg.to_graph_documents(source_text="测试文本")
    print(f"   GraphDocument 数量: {len(graph_docs)}")
    
    log_success("TemporalKnowledgeGraph", f"创建成功 - {len(kg.entities)} 实体, {len(kg.relationships)} 关系")
except Exception as e:
    log_error("TemporalKnowledgeGraph", e, "创建或转换测试图谱失败")

# ============================================================
# Test 4: AtomExtractionAdapter 结构测试（不实际调用 API）
# ============================================================
print()
print("4. AtomExtractionAdapter 结构测试...")
try:
    from graphrag_agent.graph.extraction.atom_adapter import AtomExtractionAdapter
    
    # 检查必要方法是否存在
    methods_to_check = [
        'extract_from_chunks',
        'extract_from_chunks_sync',
        'incremental_update',
        '_extract_atomic_facts',
        '_get_observation_timestamp'
    ]
    
    missing_methods = []
    for method in methods_to_check:
        if not hasattr(AtomExtractionAdapter, method):
            missing_methods.append(method)
    
    if missing_methods:
        log_error("AtomExtractionAdapter 结构", 
                  AttributeError(f"缺少方法: {missing_methods}"),
                  "方法检查")
    else:
        log_success("AtomExtractionAdapter 结构", f"所有 {len(methods_to_check)} 个方法存在")
except Exception as e:
    log_error("AtomExtractionAdapter 结构", e, "导入或检查失败")

# ============================================================
# Test 5: Mock LLM/Embeddings 初始化测试
# ============================================================
print()
print("5. Mock LLM/Embeddings 初始化测试...")
try:
    from unittest.mock import Mock, MagicMock
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.embeddings import Embeddings
    
    # 创建 Mock LLM
    mock_llm = MagicMock(spec=BaseChatModel)
    mock_llm.invoke = Mock(return_value=Mock(content="mock response"))
    
    # 创建 Mock Embeddings
    mock_embeddings = MagicMock(spec=Embeddings)
    mock_embeddings.embed_documents = Mock(return_value=[[0.1] * 384])
    mock_embeddings.embed_query = Mock(return_value=[0.1] * 384)
    
    log_success("Mock 模型创建", "LLM 和 Embeddings Mock 创建成功")
    
    # 尝试初始化 AtomExtractionAdapter
    print("   尝试初始化 AtomExtractionAdapter...")
    try:
        from graphrag_agent.graph.extraction.atom_adapter import AtomExtractionAdapter
        adapter = AtomExtractionAdapter(
            llm_model=mock_llm,
            embeddings_model=mock_embeddings
        )
        log_success("AtomExtractionAdapter 初始化", f"阈值: ent={adapter.ent_threshold}, rel={adapter.rel_threshold}")
    except Exception as e:
        log_error("AtomExtractionAdapter 初始化", e, "使用 Mock 模型初始化失败")
        
except Exception as e:
    log_error("Mock 模型创建", e, "创建 Mock 对象失败")

# ============================================================
# Test 6: _extract_atomic_facts 测试
# ============================================================
print()
print("6. _extract_atomic_facts 测试...")
try:
    from graphrag_agent.graph.extraction.atom_adapter import AtomExtractionAdapter
    from unittest.mock import MagicMock
    from langchain_core.documents import Document
    
    # 准备不同格式的输入
    test_chunks = [
        "这是一个纯文本块",
        {"chunk_doc": Document(page_content="这是字典格式的文本块")},
        Document(page_content="这是 LangChain Document 格式"),
        {"text": "使用 text 键的字典"},
        {"content": "使用 content 键的字典"},
    ]
    
    # 创建 mock adapter 来测试方法
    mock_llm = MagicMock()
    mock_embeddings = MagicMock()
    
    try:
        adapter = AtomExtractionAdapter(mock_llm, mock_embeddings)
        facts = adapter._extract_atomic_facts(test_chunks)
        print(f"   输入 chunks: {len(test_chunks)}")
        print(f"   提取的 facts: {len(facts)}")
        
        if len(facts) == len(test_chunks):
            log_success("_extract_atomic_facts", f"成功提取 {len(facts)} 个原子事实")
        else:
            log_error("_extract_atomic_facts", 
                      ValueError(f"预期 {len(test_chunks)} 个 facts，实际 {len(facts)}"),
                      "数量不匹配")
    except Exception as e:
        log_error("_extract_atomic_facts", e, "提取原子事实失败")
        
except Exception as e:
    log_error("_extract_atomic_facts 测试", e, "测试设置失败")

# ============================================================
# Test 7: Neo4jTemporalWriter 结构测试
# ============================================================
print()
print("7. Neo4jTemporalWriter 结构测试...")
try:
    from graphrag_agent.graph.extraction.temporal_writer import Neo4jTemporalWriter
    
    # 检查必要方法
    methods_to_check = [
        'write_temporal_kg',
        '_write_entities',
        '_write_relationships',
    ]
    
    missing_methods = []
    for method in methods_to_check:
        if not hasattr(Neo4jTemporalWriter, method):
            missing_methods.append(method)
    
    if missing_methods:
        log_error("Neo4jTemporalWriter 结构", 
                  AttributeError(f"缺少方法: {missing_methods}"),
                  "方法检查")
    else:
        log_success("Neo4jTemporalWriter 结构", f"所有 {len(methods_to_check)} 个方法存在")
except Exception as e:
    log_error("Neo4jTemporalWriter 结构", e, "导入或检查失败")

# ============================================================
# Test 8: build_graph.py ATOM 集成测试
# ============================================================
print()
print("8. build_graph.py ATOM 集成测试...")
try:
    # 注意：这里只测试导入，不实际运行（需要数据库连接）
    from graphrag_agent.integrations.build.build_graph import KnowledgeGraphBuilder
    
    # 检查 ATOM 相关属性和方法
    if hasattr(KnowledgeGraphBuilder, '_extract_with_atom'):
        log_success("build_graph.py ATOM 集成", "_extract_with_atom 方法存在")
    else:
        log_error("build_graph.py ATOM 集成", 
                  AttributeError("缺少 _extract_with_atom 方法"),
                  "方法检查")
except Exception as e:
    log_error("build_graph.py 导入", e, "导入 KnowledgeGraphBuilder 失败")

# ============================================================
# Test 9: to_atom_kg 转换测试
# ============================================================
print()
print("9. to_atom_kg 转换测试...")
try:
    from graphrag_agent.graph.structure.temporal_kg import (
        TemporalKnowledgeGraph,
        TemporalEntity,
        TemporalRelationship
    )
    
    # 创建测试数据
    kg = TemporalKnowledgeGraph(
        entities=[
            TemporalEntity(id="e1", name="测试实体1", label="类型A"),
            TemporalEntity(id="e2", name="测试实体2", label="类型B"),
        ],
        relationships=[
            TemporalRelationship(
                source_id="e1", target_id="e2", type="关联",
                t_obs=[1.0], atomic_facts=["测试事实"]
            )
        ]
    )
    
    # 尝试转换
    try:
        atom_kg = kg.to_atom_kg()
        print(f"   ATOM KG 实体数: {len(atom_kg.entities)}")
        print(f"   ATOM KG 关系数: {len(atom_kg.relationships)}")
        log_success("to_atom_kg 转换", "TemporalKnowledgeGraph -> ATOM KnowledgeGraph 成功")
    except Exception as e:
        log_error("to_atom_kg 转换", e, "转换失败")
        
except Exception as e:
    log_error("to_atom_kg 测试", e, "测试设置失败")

# ============================================================
# Test 10: from_atom_kg 转换测试
# ============================================================
print()
print("10. from_atom_kg 转换测试...")
try:
    from itext2kg.atom.models import (
        KnowledgeGraph as AtomKG,
        Entity as AtomEntity,
        Relationship as AtomRel,
        EntityProperties,
        RelationshipProperties
    )
    from graphrag_agent.graph.structure.temporal_kg import TemporalKnowledgeGraph
    
    # 创建 ATOM KnowledgeGraph
    atom_entities = [
        AtomEntity(name="实体A", label="TypeA"),
        AtomEntity(name="实体B", label="TypeB"),
    ]
    
    atom_rels = [
        AtomRel(
            name="关系类型",
            startEntity=atom_entities[0],
            endEntity=atom_entities[1],
            properties=RelationshipProperties(t_obs=[1.0], atomic_facts=["fact1"])
        )
    ]
    
    atom_kg = AtomKG(entities=atom_entities, relationships=atom_rels)
    
    # 转换
    try:
        temporal_kg = TemporalKnowledgeGraph.from_atom_kg(atom_kg, observation_times=[1.0])
        print(f"   Temporal KG 实体数: {len(temporal_kg.entities)}")
        print(f"   Temporal KG 关系数: {len(temporal_kg.relationships)}")
        log_success("from_atom_kg 转换", "ATOM KnowledgeGraph -> TemporalKnowledgeGraph 成功")
    except Exception as e:
        log_error("from_atom_kg 转换", e, "转换失败")
        
except Exception as e:
    log_error("from_atom_kg 测试", e, "测试设置失败")

# ============================================================
# 生成错误报告
# ============================================================
print()
print("=" * 60)
print("测试完成 - 错误报告")
print("=" * 60)

if errors_log:
    print(f"\n发现 {len(errors_log)} 个错误:\n")
    for i, err in enumerate(errors_log, 1):
        print(f"--- 错误 {i}: {err['test_name']} ---")
        print(f"类型: {err['error_type']}")
        print(f"消息: {err['error_message']}")
        print(f"上下文: {err['context']}")
        print(f"时间: {err['timestamp']}")
        print()
else:
    print("\n[SUCCESS] 所有测试通过，未发现错误！\n")

# 输出 JSON 格式的错误日志供后续处理
import json
print("\n--- JSON 错误日志 ---")
print(json.dumps(errors_log, ensure_ascii=False, indent=2))
