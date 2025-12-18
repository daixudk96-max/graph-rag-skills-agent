"""
DSA (Delta-Summary Accumulation) Schema Setup

This module provides Neo4j schema setup for DSA including:
- Constraints for __CommunityDelta__ nodes
- Indexes for efficient delta querying
- Property additions for __Community__ nodes

Run this module to initialize the DSA schema in Neo4j.
"""

import logging
from typing import Optional
from langchain_community.graphs import Neo4jGraph

from graphrag_agent.config.neo4jdb import get_db_manager

logger = logging.getLogger(__name__)


def setup_dsa_schema(graph: Optional[Neo4jGraph] = None) -> dict:
    """
    Set up DSA-related schema in Neo4j.
    
    Creates:
    - Constraint on __CommunityDelta__.id for uniqueness
    - Index on __CommunityDelta__.community_id for join performance
    - Index on __CommunityDelta__.created_at for ordering
    - Adds last_compacted_at, summary_tokens properties to __Community__ nodes
    
    Args:
        graph: Neo4j graph connection. If None, uses default connection.
        
    Returns:
        Dict with setup results
    """
    if graph is None:
        graph = get_db_manager().graph
    
    results = {
        "constraints_created": [],
        "indexes_created": [],
        "properties_added": [],
        "errors": []
    }
    
    # 1. Create uniqueness constraint for __CommunityDelta__.id
    try:
        graph.query("""
        CREATE CONSTRAINT community_delta_id_unique IF NOT EXISTS
        FOR (d:__CommunityDelta__)
        REQUIRE d.id IS UNIQUE
        """)
        results["constraints_created"].append("community_delta_id_unique")
        logger.info("Created constraint: community_delta_id_unique")
    except Exception as e:
        error_msg = str(e)
        if "already exists" not in error_msg.lower():
            results["errors"].append(f"constraint community_delta_id_unique: {error_msg}")
            logger.warning(f"Failed to create constraint: {error_msg}")
        else:
            logger.info("Constraint community_delta_id_unique already exists")
    
    # 2. Create index on __CommunityDelta__.community_id
    try:
        graph.query("""
        CREATE INDEX community_delta_community_id IF NOT EXISTS
        FOR (d:__CommunityDelta__)
        ON (d.community_id)
        """)
        results["indexes_created"].append("community_delta_community_id")
        logger.info("Created index: community_delta_community_id")
    except Exception as e:
        error_msg = str(e)
        if "already exists" not in error_msg.lower():
            results["errors"].append(f"index community_delta_community_id: {error_msg}")
            logger.warning(f"Failed to create index: {error_msg}")
        else:
            logger.info("Index community_delta_community_id already exists")
    
    # 3. Create index on __CommunityDelta__.created_at for ordering
    try:
        graph.query("""
        CREATE INDEX community_delta_created_at IF NOT EXISTS
        FOR (d:__CommunityDelta__)
        ON (d.created_at)
        """)
        results["indexes_created"].append("community_delta_created_at")
        logger.info("Created index: community_delta_created_at")
    except Exception as e:
        error_msg = str(e)
        if "already exists" not in error_msg.lower():
            results["errors"].append(f"index community_delta_created_at: {error_msg}")
            logger.warning(f"Failed to create index: {error_msg}")
        else:
            logger.info("Index community_delta_created_at already exists")
    
    # 4. Add last_compacted_at and summary_tokens properties to __Community__ nodes
    try:
        # Set default values for existing communities without these properties
        result = graph.query("""
        MATCH (c:__Community__)
        WHERE c.last_compacted_at IS NULL
        SET c.last_compacted_at = datetime()
        RETURN count(c) AS updated_count
        """)
        count = result[0]["updated_count"] if result else 0
        if count > 0:
            results["properties_added"].append(f"last_compacted_at ({count} nodes)")
            logger.info(f"Added last_compacted_at to {count} community nodes")
    except Exception as e:
        results["errors"].append(f"property last_compacted_at: {str(e)}")
        logger.warning(f"Failed to add last_compacted_at property: {e}")
    
    try:
        # Set default summary_tokens for communities without it
        result = graph.query("""
        MATCH (c:__Community__)
        WHERE c.summary_tokens IS NULL AND c.summary IS NOT NULL
        SET c.summary_tokens = size(c.summary) / 4  // Approximate token count
        RETURN count(c) AS updated_count
        """)
        count = result[0]["updated_count"] if result else 0
        if count > 0:
            results["properties_added"].append(f"summary_tokens ({count} nodes)")
            logger.info(f"Added summary_tokens to {count} community nodes")
    except Exception as e:
        results["errors"].append(f"property summary_tokens: {str(e)}")
        logger.warning(f"Failed to add summary_tokens property: {e}")
    
    # Log summary
    logger.info(
        f"DSA schema setup complete: "
        f"{len(results['constraints_created'])} constraints, "
        f"{len(results['indexes_created'])} indexes, "
        f"{len(results['properties_added'])} property updates, "
        f"{len(results['errors'])} errors"
    )
    
    return results


def verify_dsa_schema(graph: Optional[Neo4jGraph] = None) -> dict:
    """
    Verify that DSA schema is properly set up.
    
    Args:
        graph: Neo4j graph connection. If None, uses default connection.
        
    Returns:
        Dict with verification results
    """
    if graph is None:
        graph = get_db_manager().graph
    
    results = {
        "constraints": [],
        "indexes": [],
        "community_delta_count": 0,
        "communities_with_dsa_props": 0
    }
    
    # Check constraints
    try:
        constraints = graph.query("SHOW CONSTRAINTS")
        for c in constraints:
            if "__CommunityDelta__" in str(c.get("labelsOrTypes", [])):
                results["constraints"].append(c.get("name", "unknown"))
    except Exception as e:
        logger.warning(f"Failed to check constraints: {e}")
    
    # Check indexes
    try:
        indexes = graph.query("SHOW INDEXES")
        for idx in indexes:
            if "__CommunityDelta__" in str(idx.get("labelsOrTypes", [])):
                results["indexes"].append(idx.get("name", "unknown"))
    except Exception as e:
        logger.warning(f"Failed to check indexes: {e}")
    
    # Count delta nodes
    try:
        result = graph.query("MATCH (d:__CommunityDelta__) RETURN count(d) AS count")
        results["community_delta_count"] = result[0]["count"] if result else 0
    except Exception as e:
        logger.warning(f"Failed to count delta nodes: {e}")
    
    # Count communities with DSA properties
    try:
        result = graph.query("""
        MATCH (c:__Community__)
        WHERE c.last_compacted_at IS NOT NULL
        RETURN count(c) AS count
        """)
        results["communities_with_dsa_props"] = result[0]["count"] if result else 0
    except Exception as e:
        logger.warning(f"Failed to count communities with DSA properties: {e}")
    
    return results


if __name__ == "__main__":
    # Run schema setup when executed directly
    logging.basicConfig(level=logging.INFO)
    print("Setting up DSA schema...")
    results = setup_dsa_schema()
    print(f"Results: {results}")
    
    print("\nVerifying DSA schema...")
    verification = verify_dsa_schema()
    print(f"Verification: {verification}")
