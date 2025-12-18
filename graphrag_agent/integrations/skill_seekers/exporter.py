"""
GraphRAG Exporter - Exports knowledge graph content for Skill Seekers.
"""

from typing import List, Dict, Optional, Literal
from datetime import datetime
import logging

from langchain_community.graphs import Neo4jGraph

from .config import ExportConfig, ExportResult
from graphrag_agent.config.settings import DSA_ENABLED

logger = logging.getLogger(__name__)

# Default chunk limit when no community filter is provided
DEFAULT_CHUNK_LIMIT = 1000


class ExportError(Exception):
    """Raised when an export operation fails."""
    pass


class GraphRAGExporter:
    """
    Exports GraphRAG knowledge graph content to Skill Seekers-compatible format.
    
    This class queries Neo4j for community summaries, entities, and chunks,
    then formats them for consumption by Skill Seekers.
    """
    
    def __init__(self, graph: Neo4jGraph, config: Optional[ExportConfig] = None):
        """
        Initialize the exporter.
        
        Args:
            graph: Neo4jGraph instance for querying
            config: Export configuration (uses defaults if not provided)
        """
        self.graph = graph
        self.config = config or ExportConfig()
        self._export_timestamp: Optional[str] = None
    
    def export(
        self,
        mode: Literal["full", "delta"] = "full",
        level: Optional[int] = None,
        changed_community_ids: Optional[List[str]] = None,
    ) -> ExportResult:
        """
        Export knowledge graph content.
        
        Args:
            mode: Export mode - "full" for all content, "delta" for changes only
            level: Community level to export (overrides config default)
            changed_community_ids: For delta mode, specific community IDs to export
            
        Returns:
            ExportResult containing pages, entities, and metadata
        """
        self._export_timestamp = datetime.utcnow().isoformat() + "Z"
        level = level if level is not None else self.config.default_level
        
        logger.info(f"Starting {mode} export at level {level}")
        
        # Export communities
        if mode == "delta" and changed_community_ids:
            communities = self._export_communities_by_ids(changed_community_ids, level)
        else:
            communities = self.export_communities(level)
        
        # Export entities
        entities = self.export_entities(include_relationships=self.config.include_relationships)
        
        # Export chunks if configured
        chunks = []
        if self.config.include_chunks:
            community_ids = [c.get("community_id") for c in communities if c.get("community_id")]
            chunks = self.export_chunks(community_ids)
        
        # Build pages from communities and chunks
        pages = self._build_pages(communities, chunks)
        
        # Build metadata
        metadata = {
            "type": "graphrag",
            "graph_name": "knowledge-graph",
            "export_timestamp": self._export_timestamp,
            "export_mode": mode,
            "community_level": level,
            "dsa_enabled": DSA_ENABLED,
        }
        
        result = ExportResult(
            pages=pages,
            entities=entities,
            metadata=metadata,
            dedup_report={}  # Will be populated by deduplicator
        )
        
        logger.info(f"Export complete: {result.page_count} pages, {result.entity_count} entities")
        return result
    
    def export_communities(self, level: int = 0) -> List[Dict]:
        """
        Export community summaries at specified level.
        
        Args:
            level: Community hierarchy level (0 = most granular)
            
        Returns:
            List of community dictionaries with summary content
        """
        summary_field = self.config.summary_field
        
        # Query communities
        query = """
        MATCH (c:__Community__)
        WHERE c.level = $level
        OPTIONAL MATCH (c)-[:HAS_DELTA]->(d:__CommunityDelta__ {status: 'pending'})
        WITH c, collect(d) as deltas
        RETURN 
            c.id as community_id,
            c.title as title,
            c.level as level,
            c.summary as summary,
            c.full_content as full_content,
            c.weight as weight,
            size(deltas) as delta_count,
            [d in deltas | d.summary] as delta_summaries
        ORDER BY c.weight DESC
        """
        
        if self.config.max_communities:
            query += f" LIMIT {self.config.max_communities}"
        
        try:
            results = self.graph.query(query, params={"level": level})
        except Exception as e:
            logger.error(f"Failed to query communities: {e}")
            raise ExportError(f"Failed to query communities: {e}") from e
        
        communities = []
        for record in results:
            community = {
                "community_id": record.get("community_id"),
                "title": record.get("title", f"Community {record.get('community_id')}"),
                "level": record.get("level", level),
                "weight": record.get("weight", 0),
            }
            
            # Get content - prefer full_content, fallback to summary
            content = record.get(summary_field) or record.get("summary") or ""
            
            # Append delta summaries if DSA enabled and configured
            if self.config.include_delta_summaries and record.get("delta_summaries"):
                delta_content = "\n\n[Recent Updates]:\n" + "\n".join(record["delta_summaries"])
                content += delta_content
                community["has_pending_deltas"] = True
                community["delta_count"] = record.get("delta_count", 0)
            
            community["content"] = content
            communities.append(community)
        
        logger.info(f"Exported {len(communities)} communities at level {level}")
        return communities
    
    def _export_communities_by_ids(self, community_ids: List[str], level: int) -> List[Dict]:
        """Export specific communities by their IDs."""
        query = """
        MATCH (c:__Community__)
        WHERE c.id IN $community_ids AND c.level = $level
        OPTIONAL MATCH (c)-[:HAS_DELTA]->(d:__CommunityDelta__ {status: 'pending'})
        WITH c, collect(d) as deltas
        RETURN 
            c.id as community_id,
            c.title as title,
            c.level as level,
            c.summary as summary,
            c.full_content as full_content,
            c.weight as weight,
            [d in deltas | d.summary] as delta_summaries
        """
        
        try:
            results = self.graph.query(query, params={"community_ids": community_ids, "level": level})
        except Exception as e:
            logger.error(f"Failed to query communities by IDs: {e}")
            raise ExportError(f"Failed to query communities by IDs: {e}") from e
        
        communities = []
        for record in results:
            content = record.get(self.config.summary_field) or record.get("summary") or ""
            if self.config.include_delta_summaries and record.get("delta_summaries"):
                content += "\n\n[Recent Updates]:\n" + "\n".join(record["delta_summaries"])
            
            communities.append({
                "community_id": record.get("community_id"),
                "title": record.get("title", f"Community {record.get('community_id')}"),
                "level": record.get("level", level),
                "content": content,
                "weight": record.get("weight", 0),
            })
        
        return communities
    
    def export_entities(self, include_relationships: bool = True) -> List[Dict]:
        """
        Export entities from the knowledge graph.
        
        Args:
            include_relationships: Whether to include relationship information
            
        Returns:
            List of entity dictionaries
        """
        if include_relationships:
            query = """
            MATCH (e:__Entity__)
            OPTIONAL MATCH (e)-[r:RELATED]->(e2:__Entity__)
            WITH e, collect({type: type(r), target: e2.id, description: r.description}) as relationships
            RETURN 
                e.id as entity_id,
                e.name as name,
                labels(e) as types,
                e.description as description,
                relationships
            """
        else:
            query = """
            MATCH (e:__Entity__)
            RETURN 
                e.id as entity_id,
                e.name as name,
                labels(e) as types,
                e.description as description
            """
        
        try:
            results = self.graph.query(query)
        except Exception as e:
            logger.error(f"Failed to query entities: {e}")
            raise ExportError(f"Failed to query entities: {e}") from e
        
        entities = []
        for record in results:
            # Get entity type (exclude __Entity__ label)
            types = [t for t in record.get("types", []) if t != "__Entity__"]
            entity_type = types[0] if types else "unknown"
            
            entity = {
                "entity_id": record.get("entity_id"),
                "name": record.get("name", record.get("entity_id")),
                "type": entity_type,
                "description": record.get("description", ""),
            }
            
            if include_relationships:
                relationships = record.get("relationships", [])
                # Filter out empty relationships
                entity["relationships"] = [
                    f"{r['type']}:{r['target']}" 
                    for r in relationships 
                    if r.get("target")
                ]
            
            entities.append(entity)
        
        logger.info(f"Exported {len(entities)} entities")
        return entities
    
    def export_chunks(self, community_ids: Optional[List[str]] = None) -> List[Dict]:
        """
        Export document chunks, optionally filtered by community.
        
        Args:
            community_ids: If provided, only export chunks linked to these communities
            
        Returns:
            List of chunk dictionaries
        """
        if community_ids:
            query = """
            MATCH (c:__Community__)-[:HAS_ENTITY]->(e:__Entity__)<-[:MENTIONS]-(chunk:__Chunk__)
            WHERE c.id IN $community_ids
            WITH DISTINCT chunk
            RETURN 
                chunk.id as chunk_id,
                chunk.content as content,
                chunk.file_name as file_name,
                chunk.page as page
            """
            params = {"community_ids": community_ids}
        else:
            query = f"""
            MATCH (chunk:__Chunk__)
            RETURN 
                chunk.id as chunk_id,
                chunk.content as content,
                chunk.file_name as file_name,
                chunk.page as page
            LIMIT {DEFAULT_CHUNK_LIMIT}
            """
            params = {}
            logger.warning(
                f"No community filter provided for chunk export; limiting to {DEFAULT_CHUNK_LIMIT} chunks. "
                "Use community_ids to export specific chunks."
            )
        
        try:
            results = self.graph.query(query, params=params)
        except Exception as e:
            logger.error(f"Failed to query chunks: {e}")
            raise ExportError(f"Failed to query chunks: {e}") from e
        
        chunks = []
        for record in results:
            chunks.append({
                "chunk_id": record.get("chunk_id"),
                "content": record.get("content", ""),
                "file_name": record.get("file_name", ""),
                "page": record.get("page"),
            })
        
        logger.info(f"Exported {len(chunks)} chunks")
        return chunks
    
    def _build_pages(self, communities: List[Dict], chunks: List[Dict]) -> List[Dict]:
        """Build Skill Seekers-compatible pages from communities and chunks."""
        pages = []
        
        # Add community summaries as pages
        for community in communities:
            page = {
                "title": community.get("title", f"Community {community.get('community_id')}"),
                "url": f"graphrag://community/{community.get('community_id')}",
                "content": community.get("content", ""),
                "content_type": "community_summary",
                "metadata": {
                    "community_id": community.get("community_id"),
                    "level": community.get("level"),
                    "weight": community.get("weight"),
                }
            }
            if community.get("has_pending_deltas"):
                page["metadata"]["has_pending_deltas"] = True
                page["metadata"]["delta_count"] = community.get("delta_count", 0)
            
            pages.append(page)
        
        # Add chunks as reference pages
        for chunk in chunks:
            pages.append({
                "title": f"Reference: {chunk.get('file_name', 'Document')}",
                "url": f"graphrag://chunk/{chunk.get('chunk_id')}",
                "content": chunk.get("content", ""),
                "content_type": "reference",
                "metadata": {
                    "chunk_id": chunk.get("chunk_id"),
                    "file_name": chunk.get("file_name"),
                    "page": chunk.get("page"),
                }
            })
        
        return pages
