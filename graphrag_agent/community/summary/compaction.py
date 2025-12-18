"""
Delta-Summary Accumulation (DSA) - Community Compaction Module

This module provides background compaction for delta summaries.
When delta count or total tokens exceed thresholds, it merges deltas
into the base community summary and marks them as compacted.

Design reference: openspec/changes/add-delta-summary-accumulation/design.md
"""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime

from langchain_community.graphs import Neo4jGraph
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from graphrag_agent.models.get_models import get_llm_model
from graphrag_agent.config.settings import (
    DSA_ENABLED,
    DSA_COMPACTION_ENABLED,
    DSA_DELTA_COUNT_THRESHOLD,
    DSA_DELTA_TOKEN_THRESHOLD,
)

logger = logging.getLogger(__name__)


# Compaction merge prompt
COMPACTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a knowledge graph analyst. Merge the existing community 
summary with recent delta updates to create a unified, coherent summary.

Maintain the overall structure and comprehensiveness of the original summary
while incorporating the new information from deltas. Avoid redundancy."""),
    ("human", """Original Community Summary:
{base_summary}

Recent Updates to Incorporate:
{delta_summaries}

Generate a unified summary that incorporates all the information.""")
])


class CommunityCompactor:
    """
    Background compaction service for delta summaries.
    
    Monitors delta accumulation and triggers compaction when thresholds
    are exceeded. Merges deltas into base summary and cleans up.
    
    Attributes:
        graph: Neo4j graph connection
        llm: Language model for summary merging
        chain: LangChain processing chain
        delta_count_threshold: Max deltas before compaction
        delta_token_threshold: Max total delta tokens before compaction
    """
    
    def __init__(
        self, 
        graph: Neo4jGraph,
        delta_count_threshold: Optional[int] = None,
        delta_token_threshold: Optional[int] = None
    ):
        """
        Initialize CommunityCompactor.
        
        Args:
            graph: Neo4j graph connection
            delta_count_threshold: Override for delta count threshold
            delta_token_threshold: Override for delta token threshold
        """
        self.graph = graph
        self.llm = get_llm_model()
        self.chain = COMPACTION_PROMPT | self.llm | StrOutputParser()
        
        self.delta_count_threshold = delta_count_threshold or DSA_DELTA_COUNT_THRESHOLD
        self.delta_token_threshold = delta_token_threshold or DSA_DELTA_TOKEN_THRESHOLD
        
        logger.info(
            "CommunityCompactor initialized (count_threshold=%d, token_threshold=%d)",
            self.delta_count_threshold,
            self.delta_token_threshold
        )
    
    def check_compaction_needed(self, community_id: str) -> bool:
        """
        Check if a community needs compaction based on delta thresholds.
        
        Args:
            community_id: Target community ID
            
        Returns:
            True if compaction is needed, False otherwise
        """
        if not DSA_COMPACTION_ENABLED:
            return False
        
        result = self.graph.query("""
            MATCH (c:__Community__ {id: $community_id})-[:HAS_DELTA]->(d:__CommunityDelta__)
            WHERE d.status = 'pending'
            RETURN count(d) AS delta_count,
                   coalesce(sum(d.summary_tokens), 0) AS total_tokens
        """, params={"community_id": community_id})
        
        if not result:
            return False
        
        delta_count = result[0].get("delta_count", 0)
        total_tokens = result[0].get("total_tokens", 0)
        
        needs_compaction = (
            delta_count > self.delta_count_threshold or
            total_tokens > self.delta_token_threshold
        )
        
        if needs_compaction:
            logger.info(
                "Compaction needed for %s: %d deltas, %d tokens",
                community_id, delta_count, total_tokens
            )
        
        return needs_compaction
    
    def compact_community(self, community_id: str) -> Optional[Dict[str, Any]]:
        """
        Compact all pending deltas for a community into its base summary.
        
        This operation:
        1. Retrieves base summary and all pending deltas
        2. Uses LLM to merge them into a unified summary
        3. Updates the community's summary
        4. Marks deltas as 'compacted'
        
        Args:
            community_id: Target community ID
            
        Returns:
            Compaction result dict, or None if failed/skipped
        """
        if not DSA_COMPACTION_ENABLED:
            logger.info("Compaction disabled, skipping %s", community_id)
            return None
        
        # Fetch base summary and pending deltas
        result = self.graph.query("""
            MATCH (c:__Community__ {id: $community_id})
            OPTIONAL MATCH (c)-[:HAS_DELTA]->(d:__CommunityDelta__ {status: 'pending'})
            WITH c, collect(d) AS deltas ORDER BY d.created_at ASC
            RETURN c.summary AS base_summary,
                   c.full_content AS full_content,
                   [d IN deltas | {
                       id: d.id,
                       summary: d.summary,
                       summary_tokens: d.summary_tokens
                   }] AS deltas
        """, params={"community_id": community_id})
        
        if not result:
            logger.warning("Community %s not found", community_id)
            return None
        
        base_summary = result[0].get("full_content") or result[0].get("base_summary") or ""
        deltas = result[0].get("deltas", [])
        
        if not deltas:
            logger.debug("No pending deltas for %s", community_id)
            return None
        
        # Prepare delta text for merging
        delta_texts = "\n".join([
            f"- {d.get('summary', '')}" for d in deltas if d.get('summary')
        ])
        
        try:
            # Generate merged summary
            merged_summary = self.chain.invoke({
                "base_summary": base_summary,
                "delta_summaries": delta_texts
            })
            
            # Update community and mark deltas as compacted
            delta_ids = [d.get("id") for d in deltas if d.get("id")]
            
            self.graph.query("""
                MATCH (c:__Community__ {id: $community_id})
                SET c.full_content = $merged_summary,
                    c.last_compacted_at = datetime(),
                    c.summary_tokens = $summary_tokens
                
                WITH c
                MATCH (c)-[:HAS_DELTA]->(d:__CommunityDelta__)
                WHERE d.id IN $delta_ids
                SET d.status = 'compacted',
                    d.compacted_at = datetime()
                
                RETURN c.id AS community_id
            """, params={
                "community_id": community_id,
                "merged_summary": merged_summary.strip(),
                "summary_tokens": len(merged_summary.split()) * 1.3,
                "delta_ids": delta_ids
            })
            
            compaction_result = {
                "community_id": community_id,
                "deltas_compacted": len(deltas),
                "merged_summary_tokens": int(len(merged_summary.split()) * 1.3),
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(
                "Compacted %d deltas for community %s",
                len(deltas), community_id
            )
            
            return compaction_result
            
        except Exception as e:
            logger.error("Compaction failed for %s: %s", community_id, e)
            return None
    
    def compact_all(self) -> List[Dict[str, Any]]:
        """
        Scan all communities and compact those exceeding thresholds.
        
        Returns:
            List of compaction result dicts
        """
        if not DSA_ENABLED or not DSA_COMPACTION_ENABLED:
            logger.info("DSA or compaction disabled, skipping compact_all")
            return []
        
        # Find communities needing compaction
        result = self.graph.query("""
            MATCH (c:__Community__)-[:HAS_DELTA]->(d:__CommunityDelta__ {status: 'pending'})
            WITH c.id AS community_id, 
                 count(d) AS delta_count,
                 sum(coalesce(d.summary_tokens, 0)) AS total_tokens
            WHERE delta_count > $count_threshold OR total_tokens > $token_threshold
            RETURN community_id, delta_count, total_tokens
        """, params={
            "count_threshold": self.delta_count_threshold,
            "token_threshold": self.delta_token_threshold
        })
        
        if not result:
            logger.info("No communities need compaction")
            return []
        
        logger.info("Found %d communities needing compaction", len(result))
        
        results = []
        for row in result:
            community_id = row.get("community_id")
            compaction_result = self.compact_community(community_id)
            if compaction_result:
                results.append(compaction_result)
        
        logger.info("Completed compaction for %d communities", len(results))
        return results
    
    def cleanup_compacted_deltas(self, older_than_days: int = 7) -> int:
        """
        Remove old compacted deltas to save storage.
        
        Args:
            older_than_days: Delete deltas compacted more than N days ago
            
        Returns:
            Number of deltas deleted
        """
        result = self.graph.query("""
            MATCH (d:__CommunityDelta__ {status: 'compacted'})
            WHERE d.compacted_at < datetime() - duration({days: $days})
            WITH d, d.id AS delta_id
            DETACH DELETE d
            RETURN count(*) AS deleted_count
        """, params={"days": older_than_days})
        
        deleted_count = result[0].get("deleted_count", 0) if result else 0
        
        if deleted_count > 0:
            logger.info("Cleaned up %d old compacted deltas", deleted_count)
        
        return deleted_count
