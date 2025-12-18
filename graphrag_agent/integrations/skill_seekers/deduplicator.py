"""
Content Deduplicator for GraphRAG exports.

Handles entity-level and content-level deduplication to prevent
redundant information in generated skills.
"""

from typing import List, Dict, Set, Tuple
from hashlib import md5
from difflib import SequenceMatcher
import logging

logger = logging.getLogger(__name__)


class ContentDeduplicator:
    """
    Deduplicates content in GraphRAG exports.
    
    Provides two levels of deduplication:
    1. Entity-level: Merges similar entities based on name similarity
    2. Content-level: Hash-based deduplication for identical text passages
    """
    
    def __init__(self, similarity_threshold: float = 0.85):
        """
        Initialize the deduplicator.
        
        Args:
            similarity_threshold: Similarity threshold for entity merging (0.0-1.0)
        """
        self.similarity_threshold = similarity_threshold
        self._merge_groups: List[List[str]] = []
        self._content_hashes: Dict[str, str] = {}  # hash -> first entity_id
        self._duplicate_hashes: Set[str] = set()
        self._original_entity_count: int = 0
        self._merged_entity_count: int = 0
    
    def deduplicate_entities(self, entities: List[Dict]) -> Tuple[List[Dict], Dict]:
        """
        Deduplicate entities by merging similar ones.
        
        Args:
            entities: List of entity dictionaries
            
        Returns:
            Tuple of (deduplicated entities, dedup report)
        """
        if not entities:
            return [], self._build_report(0, 0, [])
        
        self._original_entity_count = len(entities)
        
        # Group entities by normalized name for exact match merging
        name_groups: Dict[str, List[Dict]] = {}
        for entity in entities:
            normalized = self._normalize_name(entity.get("name", ""))
            if normalized not in name_groups:
                name_groups[normalized] = []
            name_groups[normalized].append(entity)
        
        # Merge entities with same normalized name
        deduplicated = []
        merge_groups = []
        
        for normalized_name, group in name_groups.items():
            if len(group) == 1:
                deduplicated.append(group[0])
            else:
                # Merge: keep the one with longest description
                merged = self._merge_entity_group(group)
                deduplicated.append(merged)
                merge_groups.append([e.get("name", "") for e in group])
        
        # Apply similarity-based merging if threshold < 1.0
        if self.similarity_threshold < 1.0:
            deduplicated, additional_groups = self._merge_similar_entities(deduplicated)
            merge_groups.extend(additional_groups)
        
        self._merge_groups = merge_groups
        self._merged_entity_count = len(deduplicated)
        
        report = self._build_report(
            original_count=self._original_entity_count,
            merged_count=self._merged_entity_count,
            merge_groups=merge_groups
        )
        
        logger.info(f"Deduplicated {self._original_entity_count} -> {len(deduplicated)} entities")
        return deduplicated, report
    
    def _merge_similar_entities(self, entities: List[Dict]) -> Tuple[List[Dict], List[List[str]]]:
        """
        Merge entities with similar names based on similarity threshold.
        
        Args:
            entities: List of entity dictionaries
            
        Returns:
            Tuple of (merged entities, merge groups)
        """
        if len(entities) <= 1:
            return entities, []
        
        merged_indices: Set[int] = set()
        merge_groups: List[List[str]] = []
        result: List[Dict] = []
        
        for i, entity_i in enumerate(entities):
            if i in merged_indices:
                continue
            
            similar_group = [entity_i]
            name_i = entity_i.get("name", "")
            
            for j, entity_j in enumerate(entities[i + 1:], start=i + 1):
                if j in merged_indices:
                    continue
                
                name_j = entity_j.get("name", "")
                similarity = SequenceMatcher(None, name_i.lower(), name_j.lower()).ratio()
                
                if similarity >= self.similarity_threshold:
                    similar_group.append(entity_j)
                    merged_indices.add(j)
            
            if len(similar_group) > 1:
                merged = self._merge_entity_group(similar_group)
                result.append(merged)
                merge_groups.append([e.get("name", "") for e in similar_group])
            else:
                result.append(entity_i)
        
        return result, merge_groups
    
    def deduplicate_pages(self, pages: List[Dict]) -> List[Dict]:
        """
        Deduplicate pages by content hash.
        
        Args:
            pages: List of page dictionaries
            
        Returns:
            List of unique pages (duplicates marked)
        """
        seen_hashes: Dict[str, int] = {}  # hash -> first page index
        result = []
        
        for i, page in enumerate(pages):
            content = page.get("content", "")
            content_hash = self._hash_content(content)
            
            if content_hash in seen_hashes:
                # Mark as duplicate, reference original
                page_copy = page.copy()
                page_copy["is_duplicate"] = True
                page_copy["duplicate_of"] = pages[seen_hashes[content_hash]].get("url", "")
                self._duplicate_hashes.add(content_hash)
                result.append(page_copy)
            else:
                seen_hashes[content_hash] = i
                result.append(page)
        
        duplicate_count = len(self._duplicate_hashes)
        if duplicate_count > 0:
            logger.info(f"Found {duplicate_count} duplicate content hashes")
        
        return result
    
    def _normalize_name(self, name: str) -> str:
        """Normalize entity name for comparison."""
        # Lowercase, remove spaces and special chars
        return "".join(c.lower() for c in name if c.isalnum())
    
    def _merge_entity_group(self, entities: List[Dict]) -> Dict:
        """Merge a group of similar entities into one canonical entity."""
        # Sort by description length (longest first)
        sorted_entities = sorted(
            entities,
            key=lambda e: len(e.get("description", "")),
            reverse=True
        )
        
        # Use the entity with the longest description as base
        merged = sorted_entities[0].copy()
        
        # Collect all relationships from all entities
        all_relationships = set()
        for entity in entities:
            for rel in entity.get("relationships", []):
                all_relationships.add(rel)
        
        merged["relationships"] = list(all_relationships)
        merged["merged_from"] = [e.get("entity_id") for e in entities[1:]]
        
        return merged
    
    def _hash_content(self, content: str) -> str:
        """Generate hash for content comparison."""
        # Normalize whitespace before hashing
        normalized = " ".join(content.split())
        return md5(normalized.encode()).hexdigest()
    
    def _build_report(
        self,
        original_count: int,
        merged_count: int,
        merge_groups: List[List[str]]
    ) -> Dict:
        """Build deduplication report."""
        return {
            "original_entity_count": original_count,
            "merged_entity_count": merged_count,
            "entities_removed": original_count - merged_count,
            "merge_groups": merge_groups,
            "duplicate_content_count": len(self._duplicate_hashes),
        }
    
    def get_report(self) -> Dict:
        """Get the current deduplication report with latest stats."""
        return {
            "original_entity_count": self._original_entity_count,
            "merged_entity_count": self._merged_entity_count,
            "entities_removed": self._original_entity_count - self._merged_entity_count,
            "merge_groups": self._merge_groups,
            "duplicate_content_count": len(self._duplicate_hashes),
        }
