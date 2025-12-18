"""
Delta-Summary Accumulation (DSA) - Delta Summarizer Module

This module provides delta summary generation for incremental community updates.
Instead of regenerating full community summaries, it creates small delta summaries
for newly added entities, reducing LLM token costs by ~80%.

Design reference: openspec/changes/add-delta-summary-accumulation/design.md
"""

import uuid
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any

from langchain_community.graphs import Neo4jGraph
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from graphrag_agent.models.get_models import get_llm_model
from graphrag_agent.config.settings import (
    DSA_ENABLED,
    DSA_DELTA_COUNT_THRESHOLD,
    DSA_DELTA_TOKEN_THRESHOLD,
)

logger = logging.getLogger(__name__)


# Delta summary generation prompt
DELTA_SUMMARY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a knowledge graph analyst. Generate a brief summary describing 
what NEW information has been added to a community. Focus only on the new entities 
and relationships provided, without referencing existing community content.

Keep the summary concise (50-200 tokens) and factual."""),
    ("human", """The following entities and relationships were recently added to a community:

New Entities:
{entities}

New Relationships:
{relationships}

Generate a brief delta summary describing what information was added.""")
])


class DeltaSummarizer:
    """
    Delta summary generator for incremental community updates.
    
    Instead of regenerating full community summaries, creates small delta summaries
    for newly added entities, following LSM-Tree inspired write-ahead pattern.
    
    Attributes:
        graph: Neo4j graph connection
        llm: Language model for summary generation
        chain: LangChain processing chain
    """
    
    def __init__(self, graph: Neo4jGraph):
        """
        Initialize DeltaSummarizer.
        
        Args:
            graph: Neo4j graph connection for delta storage
        """
        self.graph = graph
        self.llm = get_llm_model()
        self.chain = DELTA_SUMMARY_PROMPT | self.llm | StrOutputParser()
        logger.info("DeltaSummarizer initialized with DSA_ENABLED=%s", DSA_ENABLED)
    
    def collect_delta_info(
        self, 
        community_id: str, 
        changed_entity_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Collect information about newly added entities in a community.
        
        Args:
            community_id: Target community ID
            changed_entity_ids: List of entity IDs that were recently added/modified
            
        Returns:
            Dict with 'entities' and 'relationships' lists for the specified entities
        """
        if not changed_entity_ids:
            return {"entities": [], "relationships": [], "community_id": community_id}
        
        # Query only the specified entities and their inter-relationships
        result = self.graph.query("""
            MATCH (e:__Entity__)
            WHERE e.id IN $entity_ids
            OPTIONAL MATCH (e)-[:IN_COMMUNITY]->(c:__Community__ {id: $community_id})
            WITH e WHERE c IS NOT NULL
            
            WITH collect(e) AS entities
            
            // Get relationships between the new entities
            UNWIND entities AS e1
            UNWIND entities AS e2
            OPTIONAL MATCH (e1)-[r]->(e2)
            WHERE e1 <> e2 AND type(r) <> 'IN_COMMUNITY'
            
            WITH entities, collect(DISTINCT {
                start: startNode(r).id,
                type: type(r),
                end: endNode(r).id,
                description: r.description
            }) AS relationships
            
            RETURN [n IN entities | {
                id: n.id,
                description: n.description,
                type: CASE 
                    WHEN size([l IN labels(n) WHERE l <> '__Entity__']) > 0 
                    THEN [l IN labels(n) WHERE l <> '__Entity__'][0] 
                    ELSE 'Unknown' 
                END
            }] AS entities,
            [r IN relationships WHERE r.start IS NOT NULL] AS relationships
        """, params={
            "entity_ids": changed_entity_ids,
            "community_id": community_id
        })
        
        if result:
            return {
                "entities": result[0].get("entities", []),
                "relationships": result[0].get("relationships", []),
                "community_id": community_id
            }
        
        return {"entities": [], "relationships": [], "community_id": community_id}
    
    def generate_delta_summary(self, delta_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a delta summary using LLM for the provided entity/relationship info.
        
        Args:
            delta_info: Dict containing 'entities', 'relationships', and 'community_id'
            
        Returns:
            Dict with 'summary', 'summary_tokens', 'related_entities', 'community_id'
        """
        entities = delta_info.get("entities", [])
        relationships = delta_info.get("relationships", [])
        community_id = delta_info.get("community_id", "")
        
        if not entities:
            return {
                "summary": "",
                "summary_tokens": 0,
                "related_entities": [],
                "community_id": community_id
            }
        
        # Format entities and relationships for the prompt
        entities_text = "\n".join([
            f"- {e.get('id', 'Unknown')} ({e.get('type', 'Unknown')}): {e.get('description', 'No description')}"
            for e in entities
        ])
        
        relationships_text = "\n".join([
            f"- {r.get('start', '?')} --[{r.get('type', '?')}]--> {r.get('end', '?')}: {r.get('description', '')}"
            for r in relationships
        ]) if relationships else "No new relationships"
        
        try:
            summary = self.chain.invoke({
                "entities": entities_text,
                "relationships": relationships_text
            })
            
            # Estimate token count (rough approximation)
            summary_tokens = len(summary.split()) * 1.3  # ~1.3 tokens per word
            
            return {
                "summary": summary.strip(),
                "summary_tokens": int(summary_tokens),
                "related_entities": [e.get("id") for e in entities if e.get("id")],
                "community_id": community_id
            }
        except Exception as e:
            logger.error("Failed to generate delta summary: %s", e)
            return {
                "summary": "",
                "summary_tokens": 0,
                "related_entities": [],
                "community_id": community_id,
                "error": str(e)
            }
    
    def store_delta(
        self, 
        community_id: str, 
        summary: str, 
        related_entities: List[str],
        summary_tokens: int = 0
    ) -> Optional[str]:
        """
        Store a delta summary as a __CommunityDelta__ node linked to the community.
        
        Args:
            community_id: Parent community ID
            summary: The delta summary text
            related_entities: List of entity IDs covered by this delta
            summary_tokens: Estimated token count of the summary
            
        Returns:
            The delta ID if successful, None otherwise
        """
        if not summary:
            return None
        
        delta_id = f"{community_id}::delta_{uuid.uuid4().hex[:8]}"
        
        try:
            self.graph.query("""
                MATCH (c:__Community__ {id: $community_id})
                CREATE (d:__CommunityDelta__ {
                    id: $delta_id,
                    summary: $summary,
                    summary_tokens: $summary_tokens,
                    related_entities: $related_entities,
                    created_at: datetime(),
                    status: 'pending'
                })
                CREATE (c)-[:HAS_DELTA]->(d)
                RETURN d.id AS delta_id
            """, params={
                "community_id": community_id,
                "delta_id": delta_id,
                "summary": summary,
                "summary_tokens": summary_tokens,
                "related_entities": related_entities
            })
            
            logger.info("Stored delta %s for community %s", delta_id, community_id)
            return delta_id
            
        except Exception as e:
            logger.error("Failed to store delta for community %s: %s", community_id, e)
            return None
    
    def process_deltas(
        self, 
        targets: Optional[Dict[str, List[str]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Process delta summaries for the specified communities and entities.
        
        This is the main entry point for delta generation. It collects info,
        generates summaries, and stores the deltas.
        
        Args:
            targets: Dict mapping community_id -> list of changed entity IDs.
                    If None, no processing is done.
                    
        Returns:
            List of stored delta information dicts
        """
        if not DSA_ENABLED:
            logger.info("DSA is disabled, skipping delta processing")
            return []
        
        if not targets:
            logger.info("No targets specified for delta processing")
            return []
        
        results = []
        
        for community_id, entity_ids in targets.items():
            try:
                # Collect delta info
                delta_info = self.collect_delta_info(community_id, entity_ids)
                
                if not delta_info.get("entities"):
                    logger.debug("No entities found for community %s", community_id)
                    continue
                
                # Generate summary
                summary_result = self.generate_delta_summary(delta_info)
                
                if not summary_result.get("summary"):
                    logger.warning("Empty summary for community %s", community_id)
                    continue
                
                # Store delta
                delta_id = self.store_delta(
                    community_id=community_id,
                    summary=summary_result["summary"],
                    related_entities=summary_result["related_entities"],
                    summary_tokens=summary_result["summary_tokens"]
                )
                
                if delta_id:
                    results.append({
                        "delta_id": delta_id,
                        "community_id": community_id,
                        "summary": summary_result["summary"],
                        "summary_tokens": summary_result["summary_tokens"],
                        "entity_count": len(entity_ids)
                    })
                    
            except Exception as e:
                logger.error("Error processing delta for community %s: %s", community_id, e)
                continue
        
        logger.info("Processed %d deltas for %d communities", len(results), len(targets))
        return results
    
    def get_pending_deltas(self, community_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve all pending (non-compacted) deltas for a community.
        
        Args:
            community_id: Target community ID
            
        Returns:
            List of delta dicts with summary, tokens, created_at
        """
        result = self.graph.query("""
            MATCH (c:__Community__ {id: $community_id})-[:HAS_DELTA]->(d:__CommunityDelta__)
            WHERE d.status = 'pending'
            RETURN d.id AS id,
                   d.summary AS summary,
                   d.summary_tokens AS summary_tokens,
                   d.related_entities AS related_entities,
                   d.created_at AS created_at
            ORDER BY d.created_at ASC
        """, params={"community_id": community_id})
        
        return result if result else []
    
    def merge_summaries_for_read(
        self, 
        base_summary: str, 
        deltas: List[Dict[str, Any]]
    ) -> str:
        """
        Merge base summary with pending deltas for read-time query.
        
        This implements the read-path merge pattern: base + deltas.
        
        Args:
            base_summary: The original community summary
            deltas: List of pending delta dicts with 'summary' key
            
        Returns:
            Merged summary string
        """
        if not deltas:
            return base_summary
        
        delta_texts = [d.get("summary", "") for d in deltas if d.get("summary")]
        
        if not delta_texts:
            return base_summary
        
        merged = base_summary or ""
        if merged:
            merged += "\n\n[Recent Updates]:\n"
        merged += "\n".join(f"- {text}" for text in delta_texts)
        
        return merged
