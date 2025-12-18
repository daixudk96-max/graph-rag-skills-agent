"""
Template Registry - Manages template storage, retrieval, and versioning.

Templates are identified by a composite key: {id}@{version}
Storage location: templates/{id}/{version}/template.json
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path
import json
import logging
import jsonschema

logger = logging.getLogger(__name__)


@dataclass
class Segment:
    """Represents a single segment definition within a template."""
    key: str
    title: str
    description: Optional[str] = None
    required: bool = False
    repeatable: bool = False
    inputs: List[Dict[str, Any]] = field(default_factory=list)
    transform: Optional[Dict[str, Any]] = None
    format: str = "markdown"
    constraints: Optional[Dict[str, Any]] = None
    relationships: List[str] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Segment":
        """Create Segment from dictionary."""
        return cls(
            key=data["key"],
            title=data["title"],
            description=data.get("description"),
            required=data.get("required", False),
            repeatable=data.get("repeatable", False),
            inputs=data.get("inputs", []),
            transform=data.get("transform"),
            format=data.get("format", "markdown"),
            constraints=data.get("constraints"),
            relationships=data.get("relationships", []),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "key": self.key,
            "title": self.title,
        }
        if self.description:
            result["description"] = self.description
        if self.required:
            result["required"] = self.required
        if self.repeatable:
            result["repeatable"] = self.repeatable
        if self.inputs:
            result["inputs"] = self.inputs
        if self.transform:
            result["transform"] = self.transform
        if self.format != "markdown":
            result["format"] = self.format
        if self.constraints:
            result["constraints"] = self.constraints
        if self.relationships:
            result["relationships"] = self.relationships
        return result


@dataclass
class Template:
    """
    Represents a complete template definition.
    
    Templates define the structure for skill input content,
    including segments, validation rules, and transformation instructions.
    """
    id: str
    version: str
    segments: List[Segment]
    name: Optional[str] = None
    description: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def identifier(self) -> str:
        """Return the unique identifier: id@version."""
        return f"{self.id}@{self.version}"
    
    def get_segment(self, key: str) -> Optional[Segment]:
        """Get a segment by its key."""
        for segment in self.segments:
            if segment.key == key:
                return segment
        return None
    
    def get_required_segments(self) -> List[Segment]:
        """Get all required segments."""
        return [s for s in self.segments if s.required]
    
    def get_repeatable_segments(self) -> List[Segment]:
        """Get all repeatable segments."""
        return [s for s in self.segments if s.repeatable]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Template":
        """Create Template from dictionary."""
        segments = [Segment.from_dict(s) for s in data.get("segments", [])]
        return cls(
            id=data["id"],
            version=data["version"],
            segments=segments,
            name=data.get("name"),
            description=data.get("description"),
            metadata=data.get("metadata", {}),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "id": self.id,
            "version": self.version,
            "segments": [s.to_dict() for s in self.segments],
        }
        if self.name:
            result["name"] = self.name
        if self.description:
            result["description"] = self.description
        if self.metadata:
            result["metadata"] = self.metadata
        return result


@dataclass
class TemplateInfo:
    """Lightweight template metadata for listing purposes."""
    id: str
    version: str
    name: Optional[str] = None
    description: Optional[str] = None
    segment_count: int = 0
    
    @property
    def identifier(self) -> str:
        """Return the unique identifier: id@version."""
        return f"{self.id}@{self.version}"


class TemplateRegistry:
    """
    Manages template storage, retrieval, and versioning.
    
    Templates are stored in a hierarchical structure:
        templates/{id}/{version}/template.json
    
    Example usage:
        registry = TemplateRegistry("path/to/templates")
        template = registry.get_template("transcript-segmented", "1.0.0")
        templates = registry.list_templates()
    """
    
    def __init__(self, templates_dir: Optional[str] = None):
        """
        Initialize the template registry.
        
        Args:
            templates_dir: Directory for template storage. If None, uses
                          the default location relative to this module.
        """
        if templates_dir:
            self.templates_dir = Path(templates_dir)
        else:
            # Default to templates directory adjacent to this module
            self.templates_dir = Path(__file__).parent / "default_templates"
        
        self._schema: Optional[Dict] = None
        self._cache: Dict[str, Template] = {}
        
        logger.debug(f"TemplateRegistry initialized with dir: {self.templates_dir}")
    
    @property
    def schema(self) -> Dict:
        """Lazy-load the template JSON schema."""
        if self._schema is None:
            schema_path = Path(__file__).parent / "schema" / "template.schema.json"
            if schema_path.exists():
                with open(schema_path, "r", encoding="utf-8") as f:
                    self._schema = json.load(f)
            else:
                logger.warning(f"Schema file not found: {schema_path}")
                self._schema = {}
        return self._schema
    
    def get_template(
        self,
        template_id: str,
        version: Optional[str] = None
    ) -> Optional[Template]:
        """
        Retrieve a template by ID and version.
        
        Args:
            template_id: Template identifier (e.g., 'transcript-segmented')
            version: Specific version to retrieve. If None, returns latest.
        
        Returns:
            Template object or None if not found.
        """
        # Check cache first
        cache_key = f"{template_id}@{version}" if version else template_id
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Find template directory
        template_base = self.templates_dir / template_id
        if not template_base.exists():
            logger.warning(f"Template not found: {template_id}")
            return None
        
        # Determine version to load
        if version:
            version_dir = template_base / version
        else:
            # Find latest version
            versions = self._get_sorted_versions(template_base)
            if not versions:
                logger.warning(f"No versions found for template: {template_id}")
                return None
            version_dir = template_base / versions[-1]
        
        # Load template file
        template_file = version_dir / "template.json"
        if not template_file.exists():
            logger.warning(f"Template file not found: {template_file}")
            return None
        
        try:
            with open(template_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            template = Template.from_dict(data)
            self._cache[cache_key] = template
            logger.debug(f"Loaded template: {template.identifier}")
            return template
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse template {template_file}: {e}")
            return None
        except KeyError as e:
            logger.error(f"Invalid template structure in {template_file}: {e}")
            return None
    
    def list_templates(self) -> List[TemplateInfo]:
        """
        List all available templates.
        
        Returns:
            List of TemplateInfo objects with metadata.
        """
        templates = []
        
        if not self.templates_dir.exists():
            logger.debug(f"Templates directory does not exist: {self.templates_dir}")
            return templates
        
        for template_dir in self.templates_dir.iterdir():
            if not template_dir.is_dir():
                continue
            
            template_id = template_dir.name
            versions = self._get_sorted_versions(template_dir)
            
            for version in versions:
                template_file = template_dir / version / "template.json"
                if template_file.exists():
                    try:
                        with open(template_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        
                        info = TemplateInfo(
                            id=template_id,
                            version=version,
                            name=data.get("name"),
                            description=data.get("description"),
                            segment_count=len(data.get("segments", [])),
                        )
                        templates.append(info)
                    except Exception as e:
                        logger.warning(f"Failed to read template info from {template_file}: {e}")
        
        return templates
    
    def register_template(self, template: Template) -> str:
        """
        Register (save) a new template.
        
        Args:
            template: Template object to register.
        
        Returns:
            Path to the saved template file.
        
        Raises:
            ValueError: If template validation fails.
        """
        # Validate against schema
        errors = self.validate_template(template.to_dict())
        if errors:
            raise ValueError(f"Template validation failed: {errors}")
        
        # Create directory structure
        version_dir = self.templates_dir / template.id / template.version
        version_dir.mkdir(parents=True, exist_ok=True)
        
        # Save template
        template_file = version_dir / "template.json"
        with open(template_file, "w", encoding="utf-8") as f:
            json.dump(template.to_dict(), f, ensure_ascii=False, indent=2)
        
        # Update cache
        self._cache[template.identifier] = template
        
        logger.info(f"Registered template: {template.identifier} at {template_file}")
        return str(template_file)
    
    def validate_template(self, template_data: Dict) -> List[str]:
        """
        Validate template data against the JSON schema.
        
        Args:
            template_data: Template dictionary to validate.
        
        Returns:
            List of validation errors (empty if valid).
        """
        if not self.schema:
            logger.warning("No schema available for validation")
            return []
        
        errors = []
        try:
            jsonschema.validate(instance=template_data, schema=self.schema)
        except jsonschema.ValidationError as e:
            errors.append(str(e.message))
        except jsonschema.SchemaError as e:
            errors.append(f"Schema error: {e.message}")
        
        return errors
    
    def delete_template(self, template_id: str, version: str) -> bool:
        """
        Delete a template version.
        
        Args:
            template_id: Template identifier.
            version: Version to delete.
        
        Returns:
            True if deleted, False if not found.
        """
        version_dir = self.templates_dir / template_id / version
        if not version_dir.exists():
            return False
        
        import shutil
        shutil.rmtree(version_dir)
        
        # Clean up empty parent directory
        template_dir = self.templates_dir / template_id
        if template_dir.exists() and not any(template_dir.iterdir()):
            template_dir.rmdir()
        
        # Clear from cache
        cache_key = f"{template_id}@{version}"
        self._cache.pop(cache_key, None)
        
        logger.info(f"Deleted template: {cache_key}")
        return True
    
    def _get_sorted_versions(self, template_dir: Path) -> List[str]:
        """Get sorted list of version directories."""
        versions = []
        for version_dir in template_dir.iterdir():
            if version_dir.is_dir() and (version_dir / "template.json").exists():
                versions.append(version_dir.name)
        
        # Sort by semantic version
        def version_key(v: str):
            try:
                parts = v.split(".")
                return tuple(int(p) for p in parts)
            except ValueError:
                return (0, 0, 0)
        
        return sorted(versions, key=version_key)
    
    def clear_cache(self) -> None:
        """Clear the template cache."""
        self._cache.clear()
        logger.debug("Template cache cleared")
