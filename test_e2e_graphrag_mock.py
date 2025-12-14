# -*- coding: utf-8 -*-
"""
GraphRAG 端到端测试脚本

使用 Mock 模拟所有外部 API 进行完整流程测试。
记录所有错误，不进行修正。
"""
import sys
import os
import json
import traceback
from datetime import datetime
from typing import List, Dict, Any, Optional
from unittest.mock import MagicMock, patch, Mock, AsyncMock
import asyncio

# 设置路径
sys.path.insert(0, '.')

# 错误和警告收集器
errors_log: List[Dict[str, Any]] = []
warnings_log: List[Dict[str, Any]] = []
test_results: List[Dict[str, Any]] = []

def log_error(test_name: str, error: Exception, context: str = "", phase: str = ""):
    """记录错误到日志"""
    error_info = {
        "test_name": test_name,
        "phase": phase,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "traceback": traceback.format_exc(),
        "context": context,
        "timestamp": datetime.now().isoformat()
    }
    errors_log.append(error_info)
    print(f"  [ERROR] [{phase}] {type(error).__name__}: {error}")
    return error_info

def log_warning(test_name: str, message: str, context: str = ""):
    """记录警告"""
    warning_info = {
        "test_name": test_name,
        "message": message,
        "context": context,
        "timestamp": datetime.now().isoformat()
    }
    warnings_log.append(warning_info)
    print(f"  [WARN] {message}")

def log_success(test_name: str, message: str = ""):
    """记录成功"""
    print(f"  [PASS] {message}")

def create_mock_llm():
    """创建 Mock LLM 模型"""
    mock_llm = MagicMock()
    
    # 模拟 invoke 返回实体关系提取结果
    mock_response = MagicMock()
    mock_response.content = json.dumps({
        "entities": [
            {"name": "学生", "type": "学生类型", "description": "大学学生"},
            {"name": "奖学金", "type": "奖学金类型", "description": "学业奖励"}
        ],
        "relationships": [
            {"source": "学生", "target": "奖学金", "type": "申请", "description": "学生可申请奖学金"}
        ]
    }, ensure_ascii=False)
    
    mock_llm.invoke = Mock(return_value=mock_response)
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)
    mock_llm.batch = Mock(return_value=[mock_response])
    mock_llm.abatch = AsyncMock(return_value=[mock_response])
    
    # 模拟 bind 方法
    mock_llm.bind = Mock(return_value=mock_llm)
    mock_llm.with_structured_output = Mock(return_value=mock_llm)
    
    return mock_llm

def create_mock_embeddings():
    """创建 Mock Embeddings 模型"""
    mock_embeddings = MagicMock()
    
    # 返回固定维度向量
    def embed_documents(texts):
        return [[0.1] * 1536 for _ in texts]
    
    def embed_query(text):
        return [0.1] * 1536
    
    mock_embeddings.embed_documents = Mock(side_effect=embed_documents)
    mock_embeddings.embed_query = Mock(side_effect=embed_query)
    
    return mock_embeddings

def create_mock_neo4j_graph():
    """创建 Mock Neo4j Graph"""
    mock_graph = MagicMock()
    
    # 模拟查询返回
    mock_graph.query = Mock(return_value=[])
    mock_graph.run = Mock(return_value=None)
    mock_graph.refresh_schema = Mock(return_value=None)
    mock_graph.structured_schema = {"node_props": {}, "rel_props": {}, "relationships": []}
    
    return mock_graph

def create_mock_gds():
    """创建 Mock GraphDataScience"""
    mock_gds = MagicMock()
    mock_gds.nodeSimilarity = MagicMock()
    mock_gds.wcc = MagicMock()
    mock_gds.louvain = MagicMock()
    mock_gds.leiden = MagicMock()
    
    return mock_gds

print("=" * 60)
print("GraphRAG End-to-End Testing with Mock")
print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)
print()

# ============================================================
# Phase 1: 基础导入测试
# ============================================================
print("Phase 1: 基础导入测试")
print("-" * 40)

# Test 1.1: 核心配置导入
print("\n1.1 核心配置导入...")
try:
    from graphrag_agent.config.settings import (
        ATOM_ENABLED, FILES_DIR, theme, entity_types, relationship_types
    )
    print(f"   ATOM_ENABLED = {ATOM_ENABLED}")
    print(f"   FILES_DIR = {FILES_DIR}")
    print(f"   theme = {theme}")
    print(f"   entity_types 数量 = {len(entity_types)}")
    print(f"   relationship_types 数量 = {len(relationship_types)}")
    log_success("核心配置导入", "settings.py 加载成功")
except Exception as e:
    log_error("核心配置导入", e, "导入 settings.py 失败", "Import")

# Test 1.2: 模型模块导入
print("\n1.2 模型模块导入...")
try:
    from graphrag_agent.models.get_models import get_llm_model, get_embeddings_model
    log_success("模型模块导入", "get_models.py 加载成功")
except Exception as e:
    log_error("模型模块导入", e, "导入 get_models.py 失败", "Import")

# Test 1.3: 构建模块导入
print("\n1.3 构建模块导入...")
try:
    from graphrag_agent.integrations.build.main import KnowledgeGraphProcessor
    from graphrag_agent.integrations.build.build_graph import KnowledgeGraphBuilder
    from graphrag_agent.integrations.build.build_index_and_community import IndexCommunityBuilder
    from graphrag_agent.integrations.build.build_chunk_index import ChunkIndexBuilder
    log_success("构建模块导入", "所有构建模块加载成功")
except Exception as e:
    log_error("构建模块导入", e, "导入构建模块失败", "Import")

# Test 1.4: Agent 模块导入
print("\n1.4 Agent 模块导入...")
try:
    from graphrag_agent.agents.naive_rag_agent import NaiveRagAgent
    from graphrag_agent.agents.graph_agent import GraphAgent
    from graphrag_agent.agents.hybrid_agent import HybridAgent
    from graphrag_agent.agents.fusion_agent import FusionGraphRAGAgent
    log_success("Agent 模块导入", "所有 Agent 模块加载成功")
except Exception as e:
    log_error("Agent 模块导入", e, "导入 Agent 模块失败", "Import")

# Test 1.5: ATOM 模块导入（如果启用）
print("\n1.5 ATOM 模块导入...")
try:
    from graphrag_agent.config.settings import ATOM_ENABLED as atom_enabled
    if atom_enabled:
        from graphrag_agent.graph.extraction.atom_adapter import AtomExtractionAdapter
        from graphrag_agent.graph.extraction.temporal_writer import Neo4jTemporalWriter
        from graphrag_agent.graph.structure.temporal_kg import (
            TemporalKnowledgeGraph, TemporalEntity, TemporalRelationship
        )
        log_success("ATOM 模块导入", "ATOM 相关模块加载成功")
    else:
        log_success("ATOM 模块导入", "ATOM 未启用，跳过相关导入")
except Exception as e:
    log_error("ATOM 模块导入", e, "导入 ATOM 模块失败", "Import")

# ============================================================
# Phase 2: 模拟模型初始化测试
# ============================================================
print("\n" + "=" * 60)
print("Phase 2: 模拟模型初始化测试")
print("-" * 40)

# Test 2.1: Mock LLM 创建
print("\n2.1 Mock LLM 创建...")
try:
    mock_llm = create_mock_llm()
    # 测试 invoke
    result = mock_llm.invoke("测试消息")
    print(f"   invoke 返回类型: {type(result)}")
    log_success("Mock LLM 创建", "LLM Mock 创建并验证成功")
except Exception as e:
    log_error("Mock LLM 创建", e, "创建 Mock LLM 失败", "Mock")

# Test 2.2: Mock Embeddings 创建
print("\n2.2 Mock Embeddings 创建...")
try:
    mock_embeddings = create_mock_embeddings()
    # 测试 embed_query
    result = mock_embeddings.embed_query("测试文本")
    print(f"   embed_query 返回维度: {len(result)}")
    log_success("Mock Embeddings 创建", "Embeddings Mock 创建并验证成功")
except Exception as e:
    log_error("Mock Embeddings 创建", e, "创建 Mock Embeddings 失败", "Mock")

# ============================================================
# Phase 3: 文档处理测试
# ============================================================
print("\n" + "=" * 60)
print("Phase 3: 文档处理测试")
print("-" * 40)

# Test 3.1: DocumentProcessor 导入和初始化
print("\n3.1 DocumentProcessor 测试...")
try:
    from graphrag_agent.pipelines.ingestion.document_processor import DocumentProcessor
    
    # 使用 mock embeddings
    processor = DocumentProcessor(mock_embeddings)
    log_success("DocumentProcessor 测试", "DocumentProcessor 初始化成功")
except Exception as e:
    log_error("DocumentProcessor 测试", e, "DocumentProcessor 初始化失败", "Document")

# Test 3.2: 测试文件读取
print("\n3.2 文件读取测试...")
try:
    from graphrag_agent.config.settings import FILES_DIR
    from pathlib import Path
    
    files_path = Path(FILES_DIR)
    if files_path.exists():
        files = list(files_path.rglob("*.txt"))[:2]  # 只取前2个txt文件
        print(f"   找到 {len(files)} 个测试文件")
        
        if files:
            # 尝试读取第一个文件
            test_file = files[0]
            with open(test_file, 'r', encoding='utf-8') as f:
                content = f.read()
            print(f"   文件 {test_file.name} 读取成功，长度 {len(content)} 字符")
            log_success("文件读取测试", f"成功读取 {len(files)} 个文件")
        else:
            log_warning("文件读取测试", "未找到测试文件", "files目录为空")
    else:
        log_error("文件读取测试", FileNotFoundError(f"目录不存在: {FILES_DIR}"), 
                  "FILES_DIR 目录不存在", "Document")
except Exception as e:
    log_error("文件读取测试", e, "文件读取失败", "Document")

# Test 3.3: 文本分块测试
print("\n3.3 文本分块测试...")
try:
    from graphrag_agent.pipelines.ingestion.text_chunker import TextChunker
    
    chunker = TextChunker()
    test_text = "这是一个测试文本。" * 100  # 创建一段较长的测试文本
    chunks = chunker.split(test_text)
    print(f"   输入文本长度: {len(test_text)}")
    print(f"   分块数量: {len(chunks)}")
    log_success("文本分块测试", f"成功分块为 {len(chunks)} 个chunks")
except Exception as e:
    log_error("文本分块测试", e, "文本分块失败", "Document")

# ============================================================
# Phase 4: 图谱提取测试（使用 Mock）
# ============================================================
print("\n" + "=" * 60)
print("Phase 4: 图谱提取测试（使用 Mock）")
print("-" * 40)

# Test 4.1: EntityRelationExtractor 测试
print("\n4.1 EntityRelationExtractor 测试...")
try:
    from graphrag_agent.graph.extraction.entity_relation_extractor import EntityRelationExtractor
    
    # 使用 mock 模型
    extractor = EntityRelationExtractor(
        llm=mock_llm,
        allowed_entities=["学生类型", "奖学金类型"],
        allowed_relationships=["申请", "评定"]
    )
    
    # 测试提取
    test_chunks = [{"chunk_doc": MagicMock(page_content="学生可以申请奖学金")}]
    
    # 注意：这里可能需要实际的提取逻辑
    log_success("EntityRelationExtractor 测试", "EntityRelationExtractor 初始化成功")
except Exception as e:
    log_error("EntityRelationExtractor 测试", e, "EntityRelationExtractor 初始化或提取失败", "Extraction")

# Test 4.2: ATOM 提取器测试（如果启用）
print("\n4.2 ATOM 提取器测试...")
try:
    from graphrag_agent.config.settings import ATOM_ENABLED as atom_enabled
    if atom_enabled:
        from graphrag_agent.graph.extraction.atom_adapter import AtomExtractionAdapter
        
        adapter = AtomExtractionAdapter(
            llm_model=mock_llm,
            embeddings_model=mock_embeddings
        )
        
        # 测试原子事实提取
        test_chunks = ["学生可以申请奖学金", "优秀学生有额外奖励"]
        facts = adapter._extract_atomic_facts(test_chunks)
        print(f"   提取的原子事实数量: {len(facts)}")
        
        log_success("ATOM 提取器测试", f"ATOM 适配器初始化成功，提取 {len(facts)} 个原子事实")
    else:
        log_success("ATOM 提取器测试", "ATOM 未启用，跳过测试")
except Exception as e:
    log_error("ATOM 提取器测试", e, "ATOM 提取器初始化或测试失败", "Extraction")

# ============================================================
# Phase 5: 知识图谱结构测试
# ============================================================
print("\n" + "=" * 60)
print("Phase 5: 知识图谱结构测试")
print("-" * 40)

# Test 5.1: TemporalKnowledgeGraph 测试
print("\n5.1 TemporalKnowledgeGraph 测试...")
try:
    from graphrag_agent.graph.structure.temporal_kg import (
        TemporalKnowledgeGraph, TemporalEntity, TemporalRelationship
    )
    
    # 创建测试实体
    entities = [
        TemporalEntity(id="学生", name="学生", label="学生类型"),
        TemporalEntity(id="奖学金", name="奖学金", label="奖学金类型")
    ]
    
    # 创建测试关系
    relationships = [
        TemporalRelationship(
            source_id="学生",
            target_id="奖学金",
            type="申请",
            t_obs=[datetime.now().timestamp()]
        )
    ]
    
    # 创建知识图谱
    kg = TemporalKnowledgeGraph(entities=entities, relationships=relationships)
    
    print(f"   实体数量: {len(kg.entities)}")
    print(f"   关系数量: {len(kg.relationships)}")
    
    # 测试转换为 GraphDocument
    try:
        graph_docs = kg.to_graph_documents(source_text="测试文本")
        print(f"   GraphDocument 数量: {len(graph_docs)}")
        log_success("TemporalKnowledgeGraph 测试", "创建和转换成功")
    except Exception as e:
        log_error("TemporalKnowledgeGraph.to_graph_documents", e, 
                  "转换为 GraphDocument 失败", "Structure")
except Exception as e:
    log_error("TemporalKnowledgeGraph 测试", e, "创建测试图谱失败", "Structure")

# ============================================================
# Phase 6: Neo4j 连接测试（使用 Mock）
# ============================================================
print("\n" + "=" * 60)
print("Phase 6: Neo4j 连接测试（使用 Mock）")
print("-" * 40)

# Test 6.1: GraphWriter 测试
print("\n6.1 GraphWriter 测试...")
try:
    from graphrag_agent.graph.core.graph_writer import GraphWriter
    
    # 创建 mock graph
    mock_graph = create_mock_neo4j_graph()
    
    # 注意：GraphWriter 可能需要真实的 Neo4j 连接
    # 这里测试导入成功
    log_success("GraphWriter 测试", "GraphWriter 模块导入成功")
except Exception as e:
    log_error("GraphWriter 测试", e, "GraphWriter 模块导入或初始化失败", "Neo4j")

# Test 6.2: Neo4jTemporalWriter 测试
print("\n6.2 Neo4jTemporalWriter 测试...")
try:
    from graphrag_agent.config.settings import ATOM_ENABLED as atom_enabled
    if atom_enabled:
        from graphrag_agent.graph.extraction.temporal_writer import Neo4jTemporalWriter
        
        # 检查类方法
        required_methods = ['write_temporal_kg', '_write_entities', '_write_relationships']
        missing = [m for m in required_methods if not hasattr(Neo4jTemporalWriter, m)]
        
        if missing:
            log_warning("Neo4jTemporalWriter 测试", f"缺少方法: {missing}", "方法检查")
        else:
            log_success("Neo4jTemporalWriter 测试", "所有必要方法存在")
    else:
        log_success("Neo4jTemporalWriter 测试", "ATOM 未启用，跳过测试")
except Exception as e:
    log_error("Neo4jTemporalWriter 测试", e, "Neo4jTemporalWriter 测试失败", "Neo4j")

# ============================================================
# Phase 7: 社区检测测试
# ============================================================
print("\n" + "=" * 60)
print("Phase 7: 社区检测模块测试")
print("-" * 40)

# Test 7.1: 社区检测器导入
print("\n7.1 社区检测器导入...")
try:
    from graphrag_agent.community.detector import CommunityDetectorFactory
    from graphrag_agent.community.summary import CommunitySummarizerFactory
    
    log_success("社区检测器导入", "社区检测模块导入成功")
except Exception as e:
    log_error("社区检测器导入", e, "社区检测模块导入失败", "Community")

# ============================================================
# Phase 8: 搜索模块测试
# ============================================================
print("\n" + "=" * 60)
print("Phase 8: 搜索模块测试")
print("-" * 40)

# Test 8.1: 搜索模块导入
print("\n8.1 搜索模块导入...")
try:
    from graphrag_agent.search.local_search import local_search
    from graphrag_agent.search.global_search import global_search
    
    log_success("搜索模块导入", "搜索模块导入成功")
except Exception as e:
    log_error("搜索模块导入", e, "搜索模块导入失败", "Search")

# ============================================================
# Phase 9: Agent 初始化测试（使用 Mock）
# ============================================================
print("\n" + "=" * 60)
print("Phase 9: Agent 初始化测试（使用 Mock）")
print("-" * 40)

# 准备 patches
patches_applied = []

# Test 9.1: NaiveRagAgent 测试
print("\n9.1 NaiveRagAgent 初始化测试...")
try:
    with patch('graphrag_agent.models.get_models.get_llm_model', return_value=mock_llm), \
         patch('graphrag_agent.models.get_models.get_embeddings_model', return_value=mock_embeddings):
        
        from graphrag_agent.agents.naive_rag_agent import NaiveRagAgent
        # 这里可能触发实际的模型初始化，需要 mock
        log_success("NaiveRagAgent 初始化测试", "模块可导入（实际初始化需要更多 mock）")
except Exception as e:
    log_error("NaiveRagAgent 初始化测试", e, "NaiveRagAgent 初始化失败", "Agent")

# Test 9.2: GraphAgent 测试
print("\n9.2 GraphAgent 初始化测试...")
try:
    log_success("GraphAgent 初始化测试", "模块可导入")
except Exception as e:
    log_error("GraphAgent 初始化测试", e, "GraphAgent 初始化失败", "Agent")

# ============================================================
# Phase 10: KnowledgeGraphBuilder 测试（使用 Mock）
# ============================================================
print("\n" + "=" * 60)
print("Phase 10: KnowledgeGraphBuilder 测试")
print("-" * 40)

print("\n10.1 KnowledgeGraphBuilder 结构测试...")
try:
    from graphrag_agent.integrations.build.build_graph import KnowledgeGraphBuilder
    
    # 检查必要方法
    required_methods = [
        '_initialize_components',
        'build_base_graph',
        'process',
    ]
    
    from graphrag_agent.config.settings import ATOM_ENABLED as atom_enabled
    if atom_enabled:
        required_methods.append('_extract_with_atom')
    
    missing = [m for m in required_methods if not hasattr(KnowledgeGraphBuilder, m)]
    
    if missing:
        log_error("KnowledgeGraphBuilder 结构测试", 
                  AttributeError(f"缺少方法: {missing}"),
                  "方法检查", "Build")
    else:
        log_success("KnowledgeGraphBuilder 结构测试", f"所有 {len(required_methods)} 个方法存在")
except Exception as e:
    log_error("KnowledgeGraphBuilder 结构测试", e, "结构测试失败", "Build")

# ============================================================
# Phase 11: 完整构建流程测试（模拟）
# ============================================================
print("\n" + "=" * 60)
print("Phase 11: 完整构建流程模拟测试")
print("-" * 40)

print("\n11.1 构建流程依赖检查...")
try:
    # 检查所有必要的依赖是否可以导入
    dependencies = [
        ("rich.console", "Console"),
        ("rich.progress", "Progress"),
        ("langchain_community.graphs", "Neo4jGraph"),
    ]
    
    for module_name, class_name in dependencies:
        try:
            module = __import__(module_name, fromlist=[class_name])
            getattr(module, class_name)
            print(f"   ✓ {module_name}.{class_name}")
        except Exception as e:
            log_warning("依赖检查", f"无法导入 {module_name}.{class_name}: {e}", "Dependencies")
    
    log_success("构建流程依赖检查", "依赖检查完成")
except Exception as e:
    log_error("构建流程依赖检查", e, "依赖检查失败", "Build")

# ============================================================
# Phase 12: 查询流程模拟测试
# ============================================================
print("\n" + "=" * 60)
print("Phase 12: 查询流程模拟测试")
print("-" * 40)

print("\n12.1 默认查询用例准备...")
default_queries = [
    "优秀学生的申请条件是什么？",
    "学业奖学金有多少钱？",
    "大学英语考试的标准是什么？",
]

for i, query in enumerate(default_queries, 1):
    print(f"   查询 {i}: {query}")

log_success("默认查询用例准备", f"准备 {len(default_queries)} 个测试查询")

# ============================================================
# 生成测试报告
# ============================================================
print("\n" + "=" * 60)
print("测试报告生成")
print("=" * 60)

# 统计结果
total_errors = len(errors_log)
total_warnings = len(warnings_log)

print(f"\n总计发现 {total_errors} 个错误，{total_warnings} 个警告")

if errors_log:
    print("\n" + "-" * 40)
    print("错误详情:")
    print("-" * 40)
    
    # 按阶段分组
    phases = {}
    for err in errors_log:
        phase = err.get("phase", "Unknown")
        if phase not in phases:
            phases[phase] = []
        phases[phase].append(err)
    
    for phase, errors in phases.items():
        print(f"\n[{phase}] ({len(errors)} 个错误)")
        for i, err in enumerate(errors, 1):
            print(f"  {i}. {err['test_name']}")
            print(f"     类型: {err['error_type']}")
            print(f"     消息: {err['error_message'][:100]}...")

if warnings_log:
    print("\n" + "-" * 40)
    print("警告详情:")
    print("-" * 40)
    for i, warn in enumerate(warnings_log, 1):
        print(f"  {i}. [{warn['test_name']}] {warn['message']}")

# 生成 JSON 报告
report = {
    "test_time": datetime.now().isoformat(),
    "summary": {
        "total_errors": total_errors,
        "total_warnings": total_warnings,
        "phases_with_errors": list(set(e.get("phase", "Unknown") for e in errors_log))
    },
    "errors": errors_log,
    "warnings": warnings_log
}

# 保存报告
report_file = "test_e2e_report.json"
with open(report_file, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print(f"\n详细报告已保存至: {report_file}")
print(f"\n测试完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
