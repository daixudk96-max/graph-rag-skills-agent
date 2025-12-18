"""
Skill Input Formatter - Converts GraphRAG exports to Skill Seekers format.

Supports both legacy format and new template-based format for dynamic
content structuring.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import json
import logging
from pathlib import Path

from .config import ExportResult

logger = logging.getLogger(__name__)


class SkillInputFormatter:
    """
    Formats GraphRAG export results into Skill Seekers-compatible JSON.
    
    Supports two output modes:
    1. Legacy mode: Simple source/pages/entities structure
    2. Template mode: 4-layer structure (template/content/source/trace)
    
    The output format mimics Skill Seekers' `scraped_data.json` schema
    so it can be processed without modification.
    """
    
    def __init__(self, use_templates: bool = False):
        """
        Initialize the formatter.
        
        Args:
            use_templates: If True, use the new template-based format.
        """
        self.use_templates = use_templates
    
    def format(self, export_result: ExportResult) -> Dict:
        """
        Convert ExportResult to Skill Seekers compatible JSON structure.
        
        Uses legacy format for backward compatibility.
        
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
    
    def format_with_template(
        self,
        export_result: ExportResult,
        template: Optional["Template"] = None,
        content: Optional["FilledContent"] = None,
        trace_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict:
        """
        Convert ExportResult to template-based 4-layer structure.
        
        Structure:
        - template: Template definition (id, version, segments)
        - content: Filled content from template
        - source: Source metadata and raw data
        - trace: Generation trace for reproducibility
        
        Args:
            export_result: Result from GraphRAGExporter
            template: Optional Template object to embed
            content: Optional FilledContent from TemplateFiller
            trace_metadata: Optional additional trace metadata
        
        Returns:
            Dictionary with 4-layer structure
        """
        now = datetime.now(timezone.utc).isoformat()
        
        # Build source layer with raw data
        source = {
            **self._format_source(export_result.metadata),
            "pages": self._format_pages(export_result.pages),
            "entities": self._format_entities(export_result.entities),
            "dedup_report": export_result.dedup_report,
        }
        
        # Build trace layer
        trace = {
            "generated_at": now,
            "generator": "graphrag-skill-seekers",
            "export_mode": export_result.metadata.get("export_mode", "full"),
        }
        if template:
            trace["template_version_used"] = template.version
            trace["template_id"] = template.id
        if trace_metadata:
            trace.update(trace_metadata)
        
        result: Dict[str, Any] = {
            "source": source,
            "trace": trace,
        }
        
        # Add template layer if provided
        if template:
            result["template"] = {
                "id": template.id,
                "name": template.name,
                "version": template.version,
                "segments": [s.to_dict() for s in template.segments],
            }
        
        # Add content layer if provided
        if content:
            result["content"] = content.to_dict()
        else:
            # Create minimal content from pages
            result["content"] = {
                "status": "complete",
                "segments": {},
            }
        
        return result
    
    def _format_source(self, metadata: Dict) -> Dict:
        """Format source/metadata section."""
        return {
            "type": metadata.get("type", "graphrag"),
            "graph_name": metadata.get("graph_name", "knowledge-graph"),
            "export_timestamp": metadata.get("export_timestamp", datetime.now(timezone.utc).isoformat()),
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
    
    def save_to_file(
        self,
        export_result: ExportResult,
        output_path: str,
        template: Optional["Template"] = None,
        content: Optional["FilledContent"] = None
    ) -> str:
        """
        Format and save export result to JSON file.
        
        Args:
            export_result: Result from GraphRAGExporter
            output_path: Path for output JSON file
            template: Optional Template for template-based format
            content: Optional FilledContent for template-based format
            
        Returns:
            Absolute path to saved file
        """
        if template or self.use_templates:
            formatted = self.format_with_template(export_result, template, content)
        else:
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
        
        Supports both legacy and template-based formats.
        
        Args:
            data: Formatted output dictionary
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Detect format type
        is_template_format = "template" in data or "trace" in data
        
        if is_template_format:
            # Template format validation
            errors.extend(SkillInputFormatter._validate_template_format(data))
        else:
            # Legacy format validation
            errors.extend(SkillInputFormatter._validate_legacy_format(data))
        
        return errors
    
    @staticmethod
    def _validate_legacy_format(data: Dict) -> List[str]:
        """Validate legacy format."""
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
    
    @staticmethod
    def _validate_template_format(data: Dict) -> List[str]:
        """Validate template-based format."""
        errors = []
        
        # Check required top-level keys for template format
        if "source" not in data:
            errors.append("Missing required key: source")
        if "trace" not in data:
            errors.append("Missing required key: trace")
        
        # Validate template if present
        if "template" in data:
            template = data["template"]
            if not isinstance(template, dict):
                errors.append("'template' must be a dictionary")
            else:
                if "id" not in template:
                    errors.append("'template.id' is required")
                if "version" not in template:
                    errors.append("'template.version' is required")
        
        # Validate content if present
        if "content" in data:
            content = data["content"]
            if not isinstance(content, dict):
                errors.append("'content' must be a dictionary")
            elif "status" not in content:
                errors.append("'content.status' is required")
        
        # Validate trace
        if "trace" in data:
            trace = data["trace"]
            if not isinstance(trace, dict):
                errors.append("'trace' must be a dictionary")
            elif "generated_at" not in trace:
                errors.append("'trace.generated_at' is required")
        
        return errors
    
    @staticmethod
    def is_template_format(data: Dict) -> bool:
        """Check if data uses template-based format."""
        return "template" in data or ("trace" in data and "content" in data)


# Type hints for optional imports
try:
    from .templates import Template, FilledContent
except ImportError:
    Template = Any
    FilledContent = Any

