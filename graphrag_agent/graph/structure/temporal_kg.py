"""
时序知识图谱模型

提供 ATOM 时序知识图谱与 graph-rag-agent 格式之间的转换能力。
支持时序属性 t_obs（观察时间）、t_start（有效期开始）、t_end（有效期结束）。

设计决策:
- 使用 dataclass 保持简洁和可序列化
- 支持与 LangChain GraphDocument 格式的互转
- 时序属性使用 UNIX 时间戳存储以便于计算和比较
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, TYPE_CHECKING

from dateutil import parser as date_parser
from langchain_community.graphs.graph_document import (
    GraphDocument,
    Node,
    Relationship as LCRelationship,
)
from langchain_core.documents import Document

if TYPE_CHECKING:
    from itext2kg.atom.models import (
        Entity as AtomEntity,
        KnowledgeGraph as AtomKnowledgeGraph,
        Relationship as AtomRelationship,
    )


def _to_timestamp(value: Any) -> Optional[float]:
    """将各种时间格式统一转换为 UNIX 时间戳"""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value.strip():
        try:
            return date_parser.parse(value).timestamp()
        except Exception:
            return None
    if isinstance(value, datetime):
        return value.timestamp()
    return None


def _normalize_timestamps(values: Iterable[Any]) -> List[float]:
    """批量转换时间值列表为时间戳列表"""
    timestamps: List[float] = []
    for item in values:
        ts = _to_timestamp(item)
        if ts is not None:
            timestamps.append(ts)
    return timestamps


@dataclass
class TemporalEntity:
    """
    时序实体，扩展自 ATOM Entity。
    
    Attributes:
        id: 实体唯一标识符（通常为名称）
        name: 实体名称
        label: 实体类型/标签
        properties: 附加属性字典
        embeddings: 实体嵌入向量（可选）
    """
    id: str
    name: str
    label: str = "entity"
    properties: Dict[str, Any] = field(default_factory=dict)
    embeddings: Optional[List[float]] = None

    def to_node(self) -> Node:
        """转换为 LangChain Node 格式"""
        node_properties = {"name": self.name, **self.properties}
        if self.embeddings is not None:
            node_properties["atom_embeddings"] = self.embeddings
        return Node(id=self.id, type=self.label, properties=node_properties)

    @classmethod
    def from_atom_entity(cls, entity: "AtomEntity") -> "TemporalEntity":
        """从 ATOM Entity 创建"""
        embeddings = None
        if hasattr(entity, "properties") and hasattr(entity.properties, "embeddings"):
            emb = entity.properties.embeddings
            if emb is not None:
                embeddings = emb.tolist() if hasattr(emb, "tolist") else list(emb)
        
        return cls(
            id=entity.name,
            name=entity.name,
            label=entity.label or "entity",
            embeddings=embeddings,
        )


@dataclass
class TemporalRelationship:
    """
    时序关系，扩展自 ATOM Relationship。
    
    ATOM 5-元组模型: (subject, predicate, object, t_start, t_end)
    附加 t_obs 表示观察时间。
    
    Attributes:
        source_id: 源实体ID
        target_id: 目标实体ID
        type: 关系类型
        properties: 附加属性字典
        t_obs: 观察时间列表（UNIX 时间戳）
        t_start: 有效期开始时间列表
        t_end: 有效期结束时间列表（空列表表示持续有效）
        atomic_facts: 原始原子事实列表
        confidence: 置信度分数
        embeddings: 关系嵌入向量（可选）
    """
    source_id: str
    target_id: str
    type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    
    # 时序属性 (ATOM specific)
    t_obs: List[float] = field(default_factory=list)
    t_start: List[float] = field(default_factory=list)
    t_end: List[float] = field(default_factory=list)
    
    # 来源追踪
    atomic_facts: List[str] = field(default_factory=list)
    confidence: float = 1.0
    embeddings: Optional[List[float]] = None

    def to_lc_relationship(
        self, source_node: Node, target_node: Node
    ) -> LCRelationship:
        """转换为 LangChain Relationship 格式"""
        rel_properties = {
            **self.properties,
            "atom_t_obs": self.t_obs,
            "atom_t_start": self.t_start,
            "atom_t_end": self.t_end,
            "atom_atomic_facts": self.atomic_facts,
            "atom_confidence": self.confidence,
        }
        if self.embeddings is not None:
            rel_properties["atom_embeddings"] = self.embeddings
        
        return LCRelationship(
            source=source_node,
            target=target_node,
            type=self.type or "RELATED",
            properties=rel_properties,
        )

    @classmethod
    def from_atom_relationship(cls, rel: "AtomRelationship") -> "TemporalRelationship":
        """从 ATOM Relationship 创建"""
        # 提取时序属性
        t_obs = []
        t_start = []
        t_end = []
        atomic_facts = []
        embeddings = None
        
        if hasattr(rel, "properties"):
            props = rel.properties
            t_obs = _normalize_timestamps(getattr(props, "t_obs", []) or [])
            t_start = _normalize_timestamps(getattr(props, "t_start", []) or [])
            t_end = _normalize_timestamps(getattr(props, "t_end", []) or [])
            atomic_facts = list(getattr(props, "atomic_facts", []) or [])
            
            emb = getattr(props, "embeddings", None)
            if emb is not None:
                embeddings = emb.tolist() if hasattr(emb, "tolist") else list(emb)

        return cls(
            source_id=rel.startEntity.name if rel.startEntity else "",
            target_id=rel.endEntity.name if rel.endEntity else "",
            type=rel.name or "RELATED",
            t_obs=t_obs,
            t_start=t_start,
            t_end=t_end,
            atomic_facts=atomic_facts,
            embeddings=embeddings,
        )


@dataclass
class TemporalKnowledgeGraph:
    """
    时序知识图谱，封装 ATOM 提取结果。
    
    提供与 graph-rag-agent 其他组件的兼容性接口。
    
    Attributes:
        entities: 时序实体列表
        relationships: 时序关系列表
        created_at: 创建时间
        last_updated: 最后更新时间
        observation_times: 所有观察时间列表
    """
    entities: List[TemporalEntity] = field(default_factory=list)
    relationships: List[TemporalRelationship] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    observation_times: List[float] = field(default_factory=list)

    def is_empty(self) -> bool:
        """检查图谱是否为空"""
        return len(self.entities) == 0 and len(self.relationships) == 0

    def to_graph_documents(
        self, source_text: str = "", metadata: Optional[Dict[str, Any]] = None
    ) -> List[GraphDocument]:
        """
        转换为 LangChain GraphDocument 格式。
        
        Args:
            source_text: 源文本内容
            metadata: 附加元数据
            
        Returns:
            GraphDocument 列表
        """
        if self.is_empty():
            return []
        
        # 建立实体ID到Node的映射
        entity_map: Dict[str, Node] = {}
        nodes: List[Node] = []
        
        for entity in self.entities:
            node = entity.to_node()
            nodes.append(node)
            entity_map[entity.id] = node
        
        # 转换关系
        relationships: List[LCRelationship] = []
        for rel in self.relationships:
            source_node = entity_map.get(rel.source_id)
            target_node = entity_map.get(rel.target_id)
            
            # 如果源或目标节点不存在，创建占位节点
            if source_node is None:
                source_node = Node(
                    id=rel.source_id, type="entity", properties={"name": rel.source_id}
                )
                nodes.append(source_node)
                entity_map[rel.source_id] = source_node
            
            if target_node is None:
                target_node = Node(
                    id=rel.target_id, type="entity", properties={"name": rel.target_id}
                )
                nodes.append(target_node)
                entity_map[rel.target_id] = target_node
            
            relationships.append(rel.to_lc_relationship(source_node, target_node))
        
        # 构建源文档
        doc_metadata = metadata or {}
        doc_metadata.update({
            "atom_created_at": self.created_at.isoformat(),
            "atom_last_updated": self.last_updated.isoformat(),
            "atom_observation_times": self.observation_times,
        })
        
        source_doc = Document(page_content=source_text, metadata=doc_metadata)
        
        return [
            GraphDocument(nodes=nodes, relationships=relationships, source=source_doc)
        ]

    @classmethod
    def from_atom_kg(
        cls, 
        atom_kg: "AtomKnowledgeGraph", 
        observation_times: Optional[List[float]] = None
    ) -> "TemporalKnowledgeGraph":
        """
        从 ATOM KnowledgeGraph 创建 TemporalKnowledgeGraph。
        
        Args:
            atom_kg: ATOM 知识图谱对象
            observation_times: 观察时间列表
            
        Returns:
            TemporalKnowledgeGraph 实例
        """
        entities = [
            TemporalEntity.from_atom_entity(e) for e in (atom_kg.entities or [])
        ]
        relationships = [
            TemporalRelationship.from_atom_relationship(r) 
            for r in (atom_kg.relationships or [])
        ]
        
        now = datetime.now(timezone.utc)
        
        return cls(
            entities=entities,
            relationships=relationships,
            created_at=now,
            last_updated=now,
            observation_times=observation_times or [],
        )

    def to_atom_kg(self) -> "AtomKnowledgeGraph":
        """
        转换回 ATOM KnowledgeGraph 格式。
        
        Returns:
            ATOM KnowledgeGraph 实例
        """
        # 延迟导入以避免循环依赖
        from itext2kg.atom.models import (
            Entity as AtomEntity,
            EntityProperties,
            KnowledgeGraph as AtomKnowledgeGraph,
            Relationship as AtomRelationship,
            RelationshipProperties,
        )
        import numpy as np
        
        atom_entities = []
        entity_map: Dict[str, AtomEntity] = {}
        
        for ent in self.entities:
            embeddings = None
            if ent.embeddings is not None:
                embeddings = np.array(ent.embeddings)
            
            atom_ent = AtomEntity(
                name=ent.name,
                label=ent.label,
                properties=EntityProperties(embeddings=embeddings),
            )
            atom_entities.append(atom_ent)
            entity_map[ent.id] = atom_ent
        
        atom_relationships = []
        for rel in self.relationships:
            embeddings = None
            if rel.embeddings is not None:
                embeddings = np.array(rel.embeddings)
            
            start_entity = entity_map.get(rel.source_id)
            end_entity = entity_map.get(rel.target_id)
            
            # 如果实体不存在，创建临时实体
            if start_entity is None:
                start_entity = AtomEntity(name=rel.source_id, label="entity")
            if end_entity is None:
                end_entity = AtomEntity(name=rel.target_id, label="entity")
            
            atom_rel = AtomRelationship(
                name=rel.type,
                startEntity=start_entity,
                endEntity=end_entity,
                properties=RelationshipProperties(
                    embeddings=embeddings,
                    t_obs=rel.t_obs,
                    t_start=rel.t_start,
                    t_end=rel.t_end,
                    atomic_facts=rel.atomic_facts,
                ),
            )
            atom_relationships.append(atom_rel)
        
        return AtomKnowledgeGraph(
            entities=atom_entities, relationships=atom_relationships
        )

    def merge(self, other: "TemporalKnowledgeGraph") -> "TemporalKnowledgeGraph":
        """
        合并另一个时序知识图谱。
        
        简单合并策略：直接添加实体和关系，不做去重。
        复杂合并请使用 ATOM 的 parallel_atomic_merge。
        
        Args:
            other: 要合并的另一个 TemporalKnowledgeGraph
            
        Returns:
            合并后的新 TemporalKnowledgeGraph
        """
        merged_entities = self.entities + other.entities
        merged_relationships = self.relationships + other.relationships
        merged_obs_times = list(set(self.observation_times + other.observation_times))
        merged_obs_times.sort()
        
        return TemporalKnowledgeGraph(
            entities=merged_entities,
            relationships=merged_relationships,
            created_at=min(self.created_at, other.created_at),
            last_updated=datetime.now(timezone.utc),
            observation_times=merged_obs_times,
        )
