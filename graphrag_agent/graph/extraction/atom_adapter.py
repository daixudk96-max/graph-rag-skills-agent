"""
ATOM 提取适配器

提供 ATOM 时序知识图谱提取能力的适配层，与现有 EntityRelationExtractor 兼容。

设计决策:
- 使用 Adapter Pattern 包装 ATOM，便于逐步迁移
- 提供同步和异步接口以适配不同调用场景
- 默认开启原子事实分解以提高提取质量
"""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Union

from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel

from graphrag_agent.graph.structure.temporal_kg import TemporalKnowledgeGraph
from graphrag_agent.config import settings

logger = logging.getLogger(__name__)


class AtomExtractionAdapter:
    """
    ATOM 时序知识图谱提取适配器。
    
    包装 itext2kg 的 Atom 类，提供与 graph-rag-agent 兼容的接口。
    支持从文本块提取时序知识图谱，以及增量更新现有图谱。
    
    Example:
        >>> from langchain_openai import ChatOpenAI, OpenAIEmbeddings
        >>> adapter = AtomExtractionAdapter(
        ...     llm_model=ChatOpenAI(),
        ...     embeddings_model=OpenAIEmbeddings()
        ... )
        >>> kg = await adapter.extract_from_chunks(chunks)
    """

    def __init__(
        self,
        llm_model: BaseChatModel,
        embeddings_model: Embeddings,
        ent_threshold: Optional[float] = None,
        rel_threshold: Optional[float] = None,
        max_workers: Optional[int] = None,
        entity_name_weight: Optional[float] = None,
        entity_label_weight: Optional[float] = None,
    ):
        """
        初始化 ATOM 提取适配器。
        
        Args:
            llm_model: LangChain 兼容的聊天模型
            embeddings_model: LangChain 兼容的嵌入模型
            ent_threshold: 实体合并阈值 (默认从配置读取)
            rel_threshold: 关系合并阈值 (默认从配置读取)
            max_workers: 并行工作线程数 (默认从配置读取)
            entity_name_weight: 实体名称嵌入权重 (默认从配置读取)
            entity_label_weight: 实体标签嵌入权重 (默认从配置读取)
        """
        # 延迟导入 ATOM 以避免在未启用时加载
        from itext2kg.atom import Atom
        
        self.llm_model = llm_model
        self.embeddings_model = embeddings_model
        
        # 使用配置或默认值
        self.ent_threshold = ent_threshold or settings.ATOM_ENTITY_THRESHOLD
        self.rel_threshold = rel_threshold or settings.ATOM_RELATION_THRESHOLD
        self.max_workers = max_workers or settings.ATOM_MAX_WORKERS
        self.entity_name_weight = entity_name_weight or settings.ATOM_ENTITY_NAME_WEIGHT
        self.entity_label_weight = entity_label_weight or settings.ATOM_ENTITY_LABEL_WEIGHT
        
        # 初始化 ATOM 实例
        self.atom = Atom(
            llm_model=llm_model,
            embeddings_model=embeddings_model,
        )
        
        logger.info(
            f"AtomExtractionAdapter initialized with "
            f"ent_threshold={self.ent_threshold}, "
            f"rel_threshold={self.rel_threshold}, "
            f"max_workers={self.max_workers}"
        )

    async def extract_from_chunks(
        self,
        chunks: Sequence[Any],
        observation_time: Optional[str] = None,
        existing_atom_kg: Optional[Any] = None,
    ) -> TemporalKnowledgeGraph:
        """
        从文本块提取时序知识图谱。
        
        Args:
            chunks: 文本块列表，支持多种格式：
                   - str: 纯文本
                   - dict: 包含 chunk_doc 键的字典
                   - Document: LangChain Document 对象
            observation_time: 观察时间戳 (ISO 格式)，默认使用当前时间
            existing_atom_kg: 现有的 ATOM KnowledgeGraph (用于增量更新)
            
        Returns:
            TemporalKnowledgeGraph: 提取的时序知识图谱
        """
        # 提取原子事实
        atomic_facts = self._extract_atomic_facts(chunks)
        
        if not atomic_facts:
            logger.warning("No atomic facts extracted from chunks")
            return TemporalKnowledgeGraph()
        
        logger.info(f"Extracted {len(atomic_facts)} atomic facts from {len(chunks)} chunks")
        
        # 获取观察时间戳
        obs_ts = self._get_observation_timestamp(observation_time)
        obs_ts_float = self._timestamp_to_float(obs_ts)
        
        # 调用 ATOM 构建图谱
        try:
            atom_kg = await self.atom.build_graph(
                atomic_facts=atomic_facts,
                obs_timestamp=obs_ts,
                existing_knowledge_graph=existing_atom_kg,
                ent_threshold=self.ent_threshold,
                rel_threshold=self.rel_threshold,
                entity_name_weight=self.entity_name_weight,
                entity_label_weight=self.entity_label_weight,
                max_workers=self.max_workers,
            )
        except Exception as e:
            logger.error(f"ATOM build_graph failed: {e}")
            raise
        
        # 转换为 TemporalKnowledgeGraph
        result = TemporalKnowledgeGraph.from_atom_kg(
            atom_kg, 
            observation_times=[obs_ts_float]
        )
        
        logger.info(
            f"Extraction complete: {len(result.entities)} entities, "
            f"{len(result.relationships)} relationships"
        )
        
        return result

    async def incremental_update(
        self,
        new_chunks: Sequence[Any],
        existing_temporal_kg: Optional[TemporalKnowledgeGraph] = None,
        observation_time: Optional[str] = None,
    ) -> TemporalKnowledgeGraph:
        """
        增量更新现有知识图谱。
        
        Args:
            new_chunks: 新的文本块列表
            existing_temporal_kg: 现有的 TemporalKnowledgeGraph
            observation_time: 观察时间戳
            
        Returns:
            TemporalKnowledgeGraph: 更新后的时序知识图谱
        """
        existing_atom_kg = None
        if existing_temporal_kg is not None:
            existing_atom_kg = existing_temporal_kg.to_atom_kg()
        
        return await self.extract_from_chunks(
            new_chunks, 
            observation_time=observation_time, 
            existing_atom_kg=existing_atom_kg
        )

    def extract_from_chunks_sync(
        self,
        chunks: Sequence[Any],
        observation_time: Optional[str] = None,
        existing_atom_kg: Optional[Any] = None,
    ) -> TemporalKnowledgeGraph:
        """
        同步版本的文本块提取方法。
        
        在非异步环境中使用此方法。
        """
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 如果已有运行中的事件循环，使用线程池执行
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    asyncio.run,
                    self.extract_from_chunks(chunks, observation_time, existing_atom_kg)
                )
                return future.result()
        else:
            return loop.run_until_complete(
                self.extract_from_chunks(chunks, observation_time, existing_atom_kg)
            )

    def _extract_atomic_facts(self, chunks: Sequence[Any]) -> List[str]:
        """
        从文本块中提取原子事实。
        
        支持多种输入格式：
        - str: 直接作为原子事实
        - dict: 从 chunk_doc 键提取
        - Document: 从 page_content 提取
        """
        facts: List[str] = []
        
        for chunk in chunks:
            text = None
            
            if isinstance(chunk, str):
                text = chunk
            elif isinstance(chunk, dict):
                # graph-rag-agent 格式: {"chunk_id": ..., "chunk_doc": Document}
                chunk_doc = chunk.get("chunk_doc")
                if chunk_doc is not None:
                    text = getattr(chunk_doc, "page_content", None)
                # 或者直接包含 text
                if text is None:
                    text = chunk.get("text") or chunk.get("content")
            elif hasattr(chunk, "page_content"):
                # LangChain Document
                text = chunk.page_content
            
            if text:
                normalized = str(text).strip()
                if normalized:
                    facts.append(normalized)
        
        return facts

    def _get_observation_timestamp(self, observation_time: Optional[str]) -> str:
        """获取观察时间戳，默认使用当前 UTC 时间"""
        if observation_time:
            return observation_time
        return datetime.now(timezone.utc).isoformat()

    def _timestamp_to_float(self, timestamp: str) -> float:
        """将 ISO 时间戳转换为 UNIX 时间戳"""
        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            return dt.timestamp()
        except Exception:
            return datetime.now(timezone.utc).timestamp()


def create_atom_adapter(
    llm_model: Optional[BaseChatModel] = None,
    embeddings_model: Optional[Embeddings] = None,
) -> AtomExtractionAdapter:
    """
    工厂函数：创建 ATOM 提取适配器。
    
    如果未提供模型，将使用默认的 OpenAI 模型。
    
    Args:
        llm_model: 可选的 LLM 模型
        embeddings_model: 可选的嵌入模型
        
    Returns:
        AtomExtractionAdapter 实例
    """
    if llm_model is None:
        from langchain_openai import ChatOpenAI
        llm_model = ChatOpenAI(
            model=settings.OPENAI_LLM_MODEL or "gpt-4o",
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL or None,
        )
    
    if embeddings_model is None:
        from langchain_openai import OpenAIEmbeddings
        embeddings_model = OpenAIEmbeddings(
            model=settings.OPENAI_EMBEDDINGS_MODEL or "text-embedding-3-small",
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL or None,
        )
    
    return AtomExtractionAdapter(
        llm_model=llm_model,
        embeddings_model=embeddings_model,
    )
