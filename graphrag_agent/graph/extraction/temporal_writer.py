"""
时序 Neo4j 写入器

扩展 GraphWriter 以支持写入 ATOM 时序知识图谱。

设计决策:
- 使用 atom_ 前缀的属性避免与现有 schema 冲突
- 支持 'update' 和 'replace' 两种合并策略
- 批量写入以提高性能
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from langchain_community.graphs import Neo4jGraph

from graphrag_agent.graph.core import connection_manager
from graphrag_agent.graph.extraction.graph_writer import GraphWriter
from graphrag_agent.graph.structure.temporal_kg import (
    TemporalKnowledgeGraph,
    TemporalEntity,
    TemporalRelationship,
)
from graphrag_agent.config.settings import (
    BATCH_SIZE as DEFAULT_BATCH_SIZE,
    MAX_WORKERS as DEFAULT_MAX_WORKERS,
)

logger = logging.getLogger(__name__)

# 用于清理标签的正则表达式
LABEL_PATTERN = re.compile(r"[^A-Za-z0-9_\u4e00-\u9fa5]")


class Neo4jTemporalWriter(GraphWriter):
    """
    时序 Neo4j 图写入器。
    
    扩展 GraphWriter 以支持 ATOM 时序知识图谱的写入。
    时序属性使用 atom_ 前缀存储，避免与现有 schema 冲突。
    
    Temporal Properties:
    - atom_t_obs: 观察时间列表 (UNIX timestamp)
    - atom_t_start: 有效期开始时间列表
    - atom_t_end: 有效期结束时间列表
    - atom_atomic_facts: 原始原子事实列表
    - atom_confidence: 置信度分数
    - atom_embeddings: 嵌入向量 (可选)
    
    Example:
        >>> writer = Neo4jTemporalWriter(graph)
        >>> writer.write_temporal_kg(temporal_kg, merge_strategy='update')
    """

    def __init__(
        self,
        graph: Optional[Neo4jGraph] = None,
        batch_size: int = 50,
        max_workers: int = 4,
    ):
        """
        初始化时序写入器。
        
        Args:
            graph: Neo4j 图数据库连接
            batch_size: 批处理大小
            max_workers: 并行工作线程数
        """
        super().__init__(
            graph=graph,
            batch_size=batch_size or DEFAULT_BATCH_SIZE,
            max_workers=max_workers or DEFAULT_MAX_WORKERS,
        )
        logger.info(f"Neo4jTemporalWriter initialized with batch_size={self.batch_size}")

    def write_temporal_kg(
        self,
        kg: TemporalKnowledgeGraph,
        merge_strategy: str = "update",
    ) -> Dict[str, int]:
        """
        将时序知识图谱写入 Neo4j。
        
        Args:
            kg: 时序知识图谱
            merge_strategy: 合并策略
                - 'update': 追加时序数据到现有记录
                - 'replace': 替换现有记录的时序数据
                
        Returns:
            写入统计 {\"entities\": n, \"relationships\": m}
        """
        if kg.is_empty():
            logger.warning("Empty TemporalKnowledgeGraph, nothing to write")
            return {"entities": 0, "relationships": 0}
        
        logger.info(
            f"Writing TemporalKnowledgeGraph: "
            f"{len(kg.entities)} entities, {len(kg.relationships)} relationships"
        )
        
        # 批量写入实体
        entity_count = self._batch_write_entities(kg.entities, merge_strategy)
        
        # 批量写入关系
        relationship_count = self._batch_write_relationships(
            kg.relationships, merge_strategy
        )
        
        logger.info(
            f"Write complete: {entity_count} entities, {relationship_count} relationships"
        )
        
        return {"entities": entity_count, "relationships": relationship_count}

    def _batch_write_entities(
        self,
        entities: List[TemporalEntity],
        merge_strategy: str,
    ) -> int:
        """批量写入实体"""
        if not entities:
            return 0
        
        written = 0
        
        for i in range(0, len(entities), self.batch_size):
            batch = entities[i : i + self.batch_size]
            try:
                for entity in batch:
                    self._write_entity(entity)
                    written += 1
            except Exception as e:
                logger.error(f"Error writing entity batch: {e}")
                # 逐个重试
                for entity in batch[written % self.batch_size :]:
                    try:
                        self._write_entity(entity)
                        written += 1
                    except Exception as e2:
                        logger.error(f"Error writing entity {entity.id}: {e2}")
        
        return written

    def _write_entity(self, entity: TemporalEntity) -> None:
        """写入单个实体"""
        label = self._sanitize_label(entity.label or "Entity")
        
        query = f"""
        MERGE (n:`{label}` {{id: $id}})
        SET n.name = $name
        SET n += $properties
        """
        
        properties = dict(entity.properties or {})
        if entity.embeddings is not None:
            # 将嵌入向量转换为字符串存储
            properties["atom_embeddings"] = ",".join(map(str, entity.embeddings))
        
        params = {
            "id": entity.id,
            "name": entity.name,
            "properties": properties,
        }
        
        self.graph.query(query, params=params)

    def _batch_write_relationships(
        self,
        relationships: List[TemporalRelationship],
        merge_strategy: str,
    ) -> int:
        """批量写入关系"""
        if not relationships:
            return 0
        
        written = 0
        
        for i in range(0, len(relationships), self.batch_size):
            batch = relationships[i : i + self.batch_size]
            try:
                for rel in batch:
                    self._write_relationship(rel, merge_strategy)
                    written += 1
            except Exception as e:
                logger.error(f"Error writing relationship batch: {e}")
                # 逐个重试
                for rel in batch[written % self.batch_size :]:
                    try:
                        self._write_relationship(rel, merge_strategy)
                        written += 1
                    except Exception as e2:
                        logger.error(
                            f"Error writing relationship {rel.source_id}->{rel.target_id}: {e2}"
                        )
        
        return written

    def _write_relationship(
        self,
        rel: TemporalRelationship,
        merge_strategy: str,
    ) -> None:
        """写入单个关系"""
        rel_type = self._sanitize_label(rel.type or "RELATED")
        
        # 根据合并策略选择不同的 Cypher
        if merge_strategy == "replace":
            query = self._create_replace_relationship_query(rel_type)
        else:
            query = self._create_update_relationship_query(rel_type)
        
        # 准备参数
        properties = self._filter_relationship_properties(rel)
        
        params = {
            "source_id": rel.source_id,
            "target_id": rel.target_id,
            "properties": properties,
            "confidence": rel.confidence,
            "t_obs": list(rel.t_obs),
            "t_start": list(rel.t_start),
            "t_end": list(rel.t_end),
            "atomic_facts": list(rel.atomic_facts),
        }
        
        if rel.embeddings is not None:
            params["embeddings"] = ",".join(map(str, rel.embeddings))
        else:
            params["embeddings"] = None
        
        self.graph.query(query, params=params)

    def _create_update_relationship_query(self, rel_type: str) -> str:
        """创建追加模式的关系写入 Cypher"""
        return f"""
        MATCH (s {{id: $source_id}}), (t {{id: $target_id}})
        MERGE (s)-[r:`{rel_type}`]->(t)
        SET r += $properties
        SET r.atom_confidence = $confidence
        SET r.atom_embeddings = CASE 
            WHEN $embeddings IS NOT NULL THEN $embeddings 
            ELSE r.atom_embeddings 
        END
        SET r.atom_t_obs = COALESCE(r.atom_t_obs, []) + $t_obs
        SET r.atom_t_start = COALESCE(r.atom_t_start, []) + $t_start
        SET r.atom_t_end = COALESCE(r.atom_t_end, []) + $t_end
        SET r.atom_atomic_facts = COALESCE(r.atom_atomic_facts, []) + $atomic_facts
        """

    def _create_replace_relationship_query(self, rel_type: str) -> str:
        """创建替换模式的关系写入 Cypher"""
        return f"""
        MATCH (s {{id: $source_id}}), (t {{id: $target_id}})
        MERGE (s)-[r:`{rel_type}`]->(t)
        SET r += $properties
        SET r.atom_confidence = $confidence
        SET r.atom_embeddings = $embeddings
        SET r.atom_t_obs = $t_obs
        SET r.atom_t_start = $t_start
        SET r.atom_t_end = $t_end
        SET r.atom_atomic_facts = $atomic_facts
        """

    def _filter_relationship_properties(
        self,
        rel: TemporalRelationship,
    ) -> Dict[str, Any]:
        """过滤关系属性，移除时序相关属性（单独处理）"""
        properties = dict(rel.properties or {})
        
        # 移除时序属性（这些将单独设置）
        temporal_keys = [
            "atom_t_obs",
            "atom_t_start",
            "atom_t_end",
            "atom_atomic_facts",
            "atom_confidence",
            "atom_embeddings",
        ]
        for key in temporal_keys:
            properties.pop(key, None)
        
        return properties

    def _sanitize_label(self, value: str) -> str:
        """
        清理标签，确保符合 Neo4j 命名规范。
        
        保留中文字符和英文字母数字下划线。
        """
        if not value:
            return "Entity"
        
        sanitized = LABEL_PATTERN.sub("_", value)
        # 移除连续下划线
        sanitized = re.sub(r"_+", "_", sanitized)
        # 移除首尾下划线
        sanitized = sanitized.strip("_")
        
        return sanitized or "Entity"

    def write_graph_documents_from_temporal_kg(
        self,
        kg: TemporalKnowledgeGraph,
        source_text: str = "",
    ) -> None:
        """
        将时序知识图谱转换为 GraphDocument 并使用父类方法写入。
        
        这是一个备选方案，使用父类的 add_graph_documents 方法。
        时序属性会作为关系属性一起写入。
        
        Args:
            kg: 时序知识图谱
            source_text: 源文本
        """
        graph_docs = kg.to_graph_documents(source_text=source_text)
        
        if graph_docs:
            self._batch_write_graph_documents(graph_docs)


def create_temporal_writer(
    graph: Optional[Neo4jGraph] = None,
) -> Neo4jTemporalWriter:
    """
    工厂函数：创建时序 Neo4j 写入器。
    
    Args:
        graph: 可选的 Neo4j 连接
        
    Returns:
        Neo4jTemporalWriter 实例
    """
    if graph is None:
        graph = connection_manager.get_connection()
    
    return Neo4jTemporalWriter(graph=graph)
