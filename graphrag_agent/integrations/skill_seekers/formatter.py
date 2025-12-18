"""
Skill Input Formatter - Converts GraphRAG exports to Skill Seekers format.
"""

from typing import Dict, List, Optional
from datetime import datetime
import json
import logging
from pathlib import Path

from .config import ExportResult

logger = logging.getLogger(__name__)


class SkillInputFormatter:
    """
    Formats GraphRAG export results into Skill Seekers-compatible JSON.
    
    The output format mimics Skill Seekers' `scraped_data.json` schema
    so it can be processed without modification.
    """
    
    def format(self, export_result: ExportResult) -> Dict:
        """
        Convert ExportResult to Skill Seekers compatible JSON structure.
        
        Args:
            export_result: Result from GraphRAGExporter
            
        Returns:
            Dictionary ready for JSON serialization
        """
        return {
            "source": self._format_source(export_result.metadata),
            "pages": self._format_pages(export_result.pages),
            "entities": self._format_entities(export_result.entities),
            "dedup_report": export_result.dedup_report,
        }
    
    def _format_source(self, metadata: Dict) -> Dict:
        """Format source/metadata section."""
        return {
            "type": metadata.get("type", "graphrag"),
            "graph_name": metadata.get("graph_name", "knowledge-graph"),
            "export_timestamp": metadata.get("export_timestamp", datetime.utcnow().isoformat() + "Z"),
            "export_mode": metadata.get("export_mode", "full"),
            "community_level": metadata.get("community_level", 0),
            "dsa_enabled": metadata.get("dsa_enabled", False),
        }
    
    def _format_pages(self, pages: List[Dict]) -> List[Dict]:
        """
        Format pages for Skill Seekers consumption.
        
        Maps GraphRAG pages to Skill Seekers page schema:
        - title: Page title
        - url: Unique identifier URL
        - content: Main content text
        - content_type: Type classification
        - metadata: Additional info
        """
        formatted = []
        for page in pages:
            formatted_page = {
                "title": page.get("title", "Untitled"),
                "url": page.get("url", ""),
                "content": page.get("content", ""),
                "content_type": page.get("content_type", "unknown"),
            }
            
            # Include metadata if present
            if page.get("metadata"):
                formatted_page["metadata"] = page["metadata"]
            
            # Mark duplicates
            if page.get("is_duplicate"):
                formatted_page["is_duplicate"] = True
                formatted_page["duplicate_of"] = page.get("duplicate_of", "")
            
            formatted.append(formatted_page)
        
        return formatted
    
    def _format_entities(self, entities: List[Dict]) -> List[Dict]:
        """
        Format entities for Skill Seekers consumption.
        
        Maps GraphRAG entities to Skill Seekers entity schema:
        - name: Entity name
        - type: Entity type/category
        - description: Entity description
        - relationships: List of relationship strings
        """
        formatted = []
        for entity in entities:
            formatted_entity = {
                "name": entity.get("name", entity.get("entity_id", "Unknown")),
                "type": entity.get("type", "unknown"),
                "description": entity.get("description", ""),
            }
            
            # Include relationships if present
            if entity.get("relationships"):
                formatted_entity["relationships"] = entity["relationships"]
            
            # Include merge info if entity was deduplicated
            if entity.get("merged_from"):
                formatted_entity["merged_from"] = entity["merged_from"]
            
            formatted.append(formatted_entity)
        
        return formatted
    
    def save_to_file(self, export_result: ExportResult, output_path: str) -> str:
        """
        Format and save export result to JSON file.
        
        Args:
            export_result: Result from GraphRAGExporter
            output_path: Path for output JSON file
            
        Returns:
            Absolute path to saved file
        """
        formatted = self.format(export_result)
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(formatted, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved skill input to {output_path}")
        return str(output_path.absolute())
    
    @staticmethod
    def validate_output(data: Dict) -> List[str]:
        """
        Validate that output conforms to expected schema.
        
        Args:
            data: Formatted output dictionary
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check required top-level keys
        required_keys = ["source", "pages", "entities"]
        for key in required_keys:
            if key not in data:
                errors.append(f"Missing required key: {key}")
        
        # Check source
        if "source" in data:
            if not isinstance(data["source"], dict):
                errors.append("'source' must be a dictionary")
            elif "type" not in data["source"]:
                errors.append("'source.type' is required")
        
        # Check pages
        if "pages" in data:
            if not isinstance(data["pages"], list):
                errors.append("'pages' must be a list")
            else:
                for i, page in enumerate(data["pages"]):
                    if not isinstance(page, dict):
                        errors.append(f"pages[{i}] must be a dictionary")
                    elif "content" not in page:
                        errors.append(f"pages[{i}].content is required")
        
        # Check entities
        if "entities" in data:
            if not isinstance(data["entities"], list):
                errors.append("'entities' must be a list")
            else:
                for i, entity in enumerate(data["entities"]):
                    if not isinstance(entity, dict):
                        errors.append(f"entities[{i}] must be a dictionary")
                    elif "name" not in entity:
                        errors.append(f"entities[{i}].name is required")
        
        return errors
