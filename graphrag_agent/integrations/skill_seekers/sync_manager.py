"""
Sync Manager - Tracks export state for delta updates.

Enables efficient incremental exports by tracking which communities
have been exported and detecting changes since last sync.
"""

from typing import List, Dict, Optional, Set
from datetime import datetime
import json
import logging
from pathlib import Path

from langchain_community.graphs import Neo4jGraph

from graphrag_agent.config.settings import DSA_ENABLED

logger = logging.getLogger(__name__)


class GraphRAGSkillSyncManager:
    """
    Manages synchronization state between GraphRAG and Skill Seekers.
    
    Tracks:
    - Last export timestamp
    - Community IDs included in last export
    - Export hash for validation
    
    Enables delta-only exports by detecting changes since last sync.
    """
    
    def __init__(
        self,
        graph: Neo4jGraph,
        sync_state_path: str = ".skill_sync_state.json"
    ):
        """
        Initialize the sync manager.
        
        Args:
            graph: Neo4jGraph instance for querying
            sync_state_path: Path to sync state file
        """
        self.graph = graph
        self.sync_state_path = Path(sync_state_path)
        self._state: Dict = {}
        self._load_state()
    
    def _load_state(self) -> None:
        """Load sync state from file."""
        if self.sync_state_path.exists():
            try:
                with open(self.sync_state_path, "r", encoding="utf-8") as f:
                    self._state = json.load(f)
                logger.info(f"Loaded sync state from {self.sync_state_path}")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load sync state: {e}")
                self._state = {}
        else:
            self._state = {}
    
    def _save_state(self) -> None:
        """Save sync state to file."""
        try:
            self.sync_state_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.sync_state_path, "w", encoding="utf-8") as f:
                json.dump(self._state, f, indent=2)
            logger.info(f"Saved sync state to {self.sync_state_path}")
        except IOError as e:
            logger.error(f"Failed to save sync state: {e}")
    
    @property
    def last_export_timestamp(self) -> Optional[str]:
        """Get the timestamp of the last export."""
        return self._state.get("last_export_ts")
    
    @property
    def exported_community_ids(self) -> Set[str]:
        """Get the set of community IDs from last export."""
        return set(self._state.get("community_ids", []))
    
    def get_pending_updates(self, level: int = 0) -> List[str]:
        """
        Get community IDs that have changed since last export.
        
        Args:
            level: Community level to check
            
        Returns:
            List of community IDs with pending updates
        """
        if not self.last_export_timestamp:
            # No previous export, all communities are pending
            return self._get_all_community_ids(level)
        
        return self.get_changed_communities_since(
            self.last_export_timestamp,
            level
        )
    
    def get_changed_communities_since(
        self,
        timestamp: str,
        level: int = 0
    ) -> List[str]:
        """
        Get community IDs that have changed since a timestamp.
        
        Checks:
        1. Community updated_at timestamp
        2. Pending __CommunityDelta__ nodes (if DSA enabled)
        
        Args:
            timestamp: ISO format timestamp to compare against
            level: Community level to check
            
        Returns:
            List of changed community IDs
        """
        changed_ids: Set[str] = set()
        
        # Check community updated_at timestamps
        query_updated = """
        MATCH (c:__Community__)
        WHERE c.level = $level 
          AND (c.updated_at IS NOT NULL AND c.updated_at > datetime($timestamp))
        RETURN c.id as community_id
        """
        
        try:
            results = self.graph.query(
                query_updated, 
                params={"level": level, "timestamp": timestamp}
            )
            changed_ids.update(r["community_id"] for r in results if r.get("community_id"))
        except Exception as e:
            logger.warning(f"Failed to query updated communities: {e}")
        
        # If DSA is enabled, also check for pending deltas
        if DSA_ENABLED:
            query_deltas = """
            MATCH (c:__Community__)-[:HAS_DELTA]->(d:__CommunityDelta__ {status: 'pending'})
            WHERE c.level = $level
            RETURN DISTINCT c.id as community_id
            """
            
            try:
                results = self.graph.query(query_deltas, params={"level": level})
                changed_ids.update(r["community_id"] for r in results if r.get("community_id"))
            except Exception as e:
                logger.warning(f"Failed to query DSA deltas: {e}")
        
        # Also check for new communities not in previous export
        all_ids = set(self._get_all_community_ids(level))
        new_ids = all_ids - self.exported_community_ids
        changed_ids.update(new_ids)
        
        logger.info(f"Found {len(changed_ids)} communities with pending updates")
        return list(changed_ids)
    
    def _get_all_community_ids(self, level: int) -> List[str]:
        """Get all community IDs at a level."""
        query = """
        MATCH (c:__Community__)
        WHERE c.level = $level
        RETURN c.id as community_id
        """
        
        try:
            results = self.graph.query(query, params={"level": level})
            return [r["community_id"] for r in results if r.get("community_id")]
        except Exception as e:
            logger.error(f"Failed to query community IDs: {e}")
            return []
    
    def mark_synced(
        self,
        community_ids: List[str],
        export_mode: str = "full",
        level: int = 0
    ) -> None:
        """
        Update sync state after successful export.
        
        Args:
            community_ids: List of community IDs that were exported
            export_mode: "full" or "delta"
            level: Community level that was exported
        """
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        if export_mode == "full":
            # Full export replaces all tracked IDs
            self._state["community_ids"] = community_ids
        else:
            # Delta export adds to existing tracked IDs
            existing = set(self._state.get("community_ids", []))
            existing.update(community_ids)
            self._state["community_ids"] = list(existing)
        
        self._state["last_export_ts"] = timestamp
        self._state["last_export_mode"] = export_mode
        self._state["last_export_level"] = level
        self._state["export_count"] = self._state.get("export_count", 0) + 1
        
        self._save_state()
        logger.info(f"Marked {len(community_ids)} communities as synced")
    
    def reset_state(self) -> None:
        """Reset sync state (useful for forced full re-export)."""
        self._state = {}
        if self.sync_state_path.exists():
            self.sync_state_path.unlink()
        logger.info("Reset sync state")
    
    def get_status(self) -> Dict:
        """
        Get current sync status summary.
        
        Returns:
            Dictionary with sync status information
        """
        return {
            "last_export_timestamp": self.last_export_timestamp,
            "exported_community_count": len(self.exported_community_ids),
            "last_export_mode": self._state.get("last_export_mode"),
            "last_export_level": self._state.get("last_export_level"),
            "export_count": self._state.get("export_count", 0),
            "sync_state_path": str(self.sync_state_path),
            "has_previous_export": self.last_export_timestamp is not None,
        }
