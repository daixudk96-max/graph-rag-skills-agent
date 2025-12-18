"""
Configuration for GraphRAG to Skill Seekers export.
"""

from dataclasses import dataclass, field
from typing import Optional, List
from pathlib import Path


@dataclass
class ExportConfig:
    """
    Configuration for exporting GraphRAG content to Skill Seekers format.
    
    Attributes:
        default_level: Default community level for export (0 = most granular)
        include_chunks: Whether to include raw document chunks in export
        dedup_threshold: Similarity threshold for entity deduplication (0.0-1.0)
        max_communities: Maximum number of communities to export (None = unlimited)
        output_path: Default output file path for the generated JSON
        include_relationships: Whether to include entity relationships
        summary_field: Which field to use for community content ('full_content' or 'summary')
    """
    default_level: int = 0
    include_chunks: bool = False
    dedup_threshold: float = 0.85
    max_communities: Optional[int] = None
    output_path: str = "skill_input.json"
    include_relationships: bool = True
    summary_field: str = "full_content"
    
    # DSA-related settings
    include_delta_summaries: bool = True  # Include pending delta summaries
    
    # Sync settings
    sync_state_path: str = ".skill_sync_state.json"
    auto_update_sync: bool = True
    
    @classmethod
    def from_dict(cls, config_dict: dict) -> "ExportConfig":
        """Create ExportConfig from dictionary."""
        return cls(**{k: v for k, v in config_dict.items() if k in cls.__dataclass_fields__})
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "default_level": self.default_level,
            "include_chunks": self.include_chunks,
            "dedup_threshold": self.dedup_threshold,
            "max_communities": self.max_communities,
            "output_path": self.output_path,
            "include_relationships": self.include_relationships,
            "summary_field": self.summary_field,
            "include_delta_summaries": self.include_delta_summaries,
            "sync_state_path": self.sync_state_path,
            "auto_update_sync": self.auto_update_sync,
        }


@dataclass
class ExportResult:
    """
    Result of a GraphRAG export operation.
    
    Attributes:
        pages: List of pages (community summaries, chunks)
        entities: List of entities with relationships
        metadata: Export metadata (source info, timestamps)
        dedup_report: Deduplication statistics
    """
    pages: List[dict] = field(default_factory=list)
    entities: List[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    dedup_report: dict = field(default_factory=dict)
    
    @property
    def page_count(self) -> int:
        return len(self.pages)
    
    @property
    def entity_count(self) -> int:
        return len(self.entities)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "source": self.metadata,
            "pages": self.pages,
            "entities": self.entities,
            "dedup_report": self.dedup_report,
        }
