"""
Template Filler - Populates templates with content and validates results.

Handles the mapping of raw content to template segments,
including transformation and constraint validation.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone
import logging
import re

from .template_registry import Template, Segment

logger = logging.getLogger(__name__)


@dataclass
class SegmentValue:
    """Represents a filled segment value."""
    value: Any
    source_ref: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {"value": self.value}
        if self.source_ref:
            result["source_ref"] = self.source_ref
        if self.metadata:
            result["metadata"] = self.metadata
        return result


@dataclass
class FilledContent:
    """
    Result of filling a template with content.
    
    Contains the completed segments and metadata about the fill operation.
    """
    status: str  # "complete", "partial", "failed"
    segments: Dict[str, Union[SegmentValue, List[SegmentValue]]]
    missing_required: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    filled_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    @property
    def is_complete(self) -> bool:
        """Check if all required segments are filled."""
        return self.status == "complete" and not self.missing_required
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        segments_dict = {}
        for key, value in self.segments.items():
            if isinstance(value, list):
                segments_dict[key] = [v.to_dict() for v in value]
            else:
                segments_dict[key] = value.to_dict()
        
        return {
            "status": self.status,
            "segments": segments_dict,
            "missing_required": self.missing_required,
            "warnings": self.warnings,
            "filled_at": self.filled_at,
        }


@dataclass
class ValidationError:
    """Represents a content validation error."""
    segment_key: str
    error_type: str  # "missing", "invalid_format", "constraint_violation", "type_error"
    message: str
    details: Optional[Dict[str, Any]] = None
    
    def __str__(self) -> str:
        return f"[{self.segment_key}] {self.error_type}: {self.message}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "segment_key": self.segment_key,
            "error_type": self.error_type,
            "message": self.message,
        }
        if self.details:
            result["details"] = self.details
        return result


class TemplateFiller:
    """
    Fills templates with raw content and validates the results.
    
    The filler handles:
    - Mapping raw content to template segments
    - Applying transformations (if defined)
    - Validating against segment constraints
    - Tracking source references for traceability
    
    Example usage:
        filler = TemplateFiller()
        content = filler.fill(template, raw_data)
        errors = filler.validate(content, template)
    """
    
    def __init__(self, strict_mode: bool = False):
        """
        Initialize the template filler.
        
        Args:
            strict_mode: If True, fail on any validation warning.
        """
        self.strict_mode = strict_mode
    
    def fill(
        self,
        template: Template,
        raw_content: Dict[str, Any],
        source_metadata: Optional[Dict[str, Any]] = None
    ) -> FilledContent:
        """
        Fill a template with raw content.
        
        Args:
            template: Template to fill.
            raw_content: Raw content dictionary with segment values.
            source_metadata: Optional metadata about content source.
        
        Returns:
            FilledContent with populated segments.
        """
        segments: Dict[str, Union[SegmentValue, List[SegmentValue]]] = {}
        missing_required: List[str] = []
        warnings: List[str] = []
        
        for segment in template.segments:
            key = segment.key
            raw_value = raw_content.get(key)
            
            if raw_value is None:
                # Check if segment is required
                if segment.required:
                    missing_required.append(key)
                    warnings.append(f"Required segment '{key}' is missing")
                continue
            
            try:
                filled_value = self._fill_segment(segment, raw_value, source_metadata)
                segments[key] = filled_value
            except Exception as e:
                logger.warning(f"Failed to fill segment '{key}': {e}")
                warnings.append(f"Failed to fill segment '{key}': {str(e)}")
                if segment.required:
                    missing_required.append(key)
        
        # Determine status
        if missing_required:
            status = "partial"
        elif warnings and self.strict_mode:
            status = "failed"
        else:
            status = "complete"
        
        return FilledContent(
            status=status,
            segments=segments,
            missing_required=missing_required,
            warnings=warnings,
        )
    
    def _fill_segment(
        self,
        segment: Segment,
        raw_value: Any,
        source_metadata: Optional[Dict[str, Any]]
    ) -> Union[SegmentValue, List[SegmentValue]]:
        """Fill a single segment with value(s)."""
        # Handle repeatable segments
        if segment.repeatable:
            if not isinstance(raw_value, list):
                raw_value = [raw_value]
            
            values = []
            for i, item in enumerate(raw_value):
                transformed = self._apply_transform(segment, item)
                formatted = self._apply_format(segment, transformed)
                
                source_ref = None
                if source_metadata and "file" in source_metadata:
                    source_ref = f"{source_metadata['file']}#{i}"
                
                values.append(SegmentValue(
                    value=formatted,
                    source_ref=source_ref,
                    metadata={"index": i},
                ))
            
            return values
        
        # Handle single-value segments
        transformed = self._apply_transform(segment, raw_value)
        formatted = self._apply_format(segment, transformed)
        
        source_ref = None
        if source_metadata and "file" in source_metadata:
            source_ref = source_metadata["file"]
        
        return SegmentValue(value=formatted, source_ref=source_ref)
    
    def _apply_transform(self, segment: Segment, value: Any) -> Any:
        """Apply segment transformation rules."""
        if not segment.transform:
            return value
        
        transform_type = segment.transform.get("type")
        
        if transform_type == "list-extract":
            # Extract list items from text
            if isinstance(value, str):
                return self._extract_list_items(value)
            return value
        
        elif transform_type == "summarize":
            # Placeholder for summarization
            # In production, this would call an LLM
            return value
        
        elif transform_type == "concatenate":
            # Concatenate multiple values
            if isinstance(value, list):
                separator = segment.transform.get("params", {}).get("separator", "\n")
                return separator.join(str(v) for v in value)
            return value
        
        elif transform_type == "map":
            # Apply mapping function
            mapping = segment.transform.get("params", {}).get("mapping", {})
            if value in mapping:
                return mapping[value]
            return value
        
        elif transform_type == "filter":
            # Filter values based on condition
            if isinstance(value, list):
                pattern = segment.transform.get("params", {}).get("pattern")
                if pattern:
                    return [v for v in value if re.search(pattern, str(v))]
            return value
        
        logger.debug(f"Unknown transform type '{transform_type}' for segment '{segment.key}'")
        return value
    
    def _apply_format(self, segment: Segment, value: Any) -> Any:
        """Apply output format to value."""
        target_format = segment.format
        
        if target_format == "markdown":
            if isinstance(value, list):
                return "\n".join(f"- {item}" for item in value)
            return str(value)
        
        elif target_format == "json":
            return value  # Keep as-is for JSON
        
        elif target_format == "plain":
            if isinstance(value, list):
                return "\n".join(str(item) for item in value)
            return str(value)
        
        elif target_format == "html":
            if isinstance(value, list):
                items = "".join(f"<li>{item}</li>" for item in value)
                return f"<ul>{items}</ul>"
            return f"<p>{value}</p>"
        
        return value
    
    def _extract_list_items(self, text: str) -> List[str]:
        """Extract list items from text content."""
        items = []
        
        # Match bullet points, numbered items, or line items
        patterns = [
            r"^[-•*]\s*(.+)$",  # Bullet points
            r"^\d+[.)]\s*(.+)$",  # Numbered items
            r"^(.+)$",  # Plain lines as fallback
        ]
        
        for line in text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            
            for pattern in patterns[:2]:  # Try bullets and numbers first
                match = re.match(pattern, line)
                if match:
                    items.append(match.group(1).strip())
                    break
            else:
                # Fallback to whole line
                items.append(line)
        
        return items
    
    def validate(
        self,
        content: FilledContent,
        template: Template
    ) -> List[ValidationError]:
        """
        Validate filled content against template constraints.
        
        Args:
            content: Filled content to validate.
            template: Template with validation rules.
        
        Returns:
            List of validation errors (empty if valid).
        """
        errors: List[ValidationError] = []
        
        # Check required segments
        for segment in template.get_required_segments():
            if segment.key not in content.segments:
                errors.append(ValidationError(
                    segment_key=segment.key,
                    error_type="missing",
                    message=f"Required segment '{segment.key}' is not filled",
                ))
        
        # Validate each filled segment
        for key, value in content.segments.items():
            segment = template.get_segment(key)
            if not segment:
                errors.append(ValidationError(
                    segment_key=key,
                    error_type="unknown",
                    message=f"Segment '{key}' not defined in template",
                ))
                continue
            
            segment_errors = self._validate_segment(segment, value)
            errors.extend(segment_errors)
        
        return errors
    
    def _validate_segment(
        self,
        segment: Segment,
        value: Union[SegmentValue, List[SegmentValue]]
    ) -> List[ValidationError]:
        """Validate a single segment value."""
        errors: List[ValidationError] = []
        constraints = segment.constraints or {}
        
        # Handle repeatable segments
        if isinstance(value, list):
            # Check item count constraints
            min_items = constraints.get("minItems", 0)
            max_items = constraints.get("maxItems")
            
            if len(value) < min_items:
                errors.append(ValidationError(
                    segment_key=segment.key,
                    error_type="constraint_violation",
                    message=f"Minimum {min_items} items required, got {len(value)}",
                    details={"constraint": "minItems", "expected": min_items, "actual": len(value)},
                ))
            
            if max_items and len(value) > max_items:
                errors.append(ValidationError(
                    segment_key=segment.key,
                    error_type="constraint_violation",
                    message=f"Maximum {max_items} items allowed, got {len(value)}",
                    details={"constraint": "maxItems", "expected": max_items, "actual": len(value)},
                ))
            
            # Validate each item
            for i, item in enumerate(value):
                item_errors = self._validate_single_value(segment, item, constraints, index=i)
                errors.extend(item_errors)
        else:
            errors.extend(self._validate_single_value(segment, value, constraints))
        
        return errors
    
    def _validate_single_value(
        self,
        segment: Segment,
        value: SegmentValue,
        constraints: Dict[str, Any],
        index: Optional[int] = None
    ) -> List[ValidationError]:
        """Validate a single segment value."""
        errors: List[ValidationError] = []
        val = value.value
        key_suffix = f"[{index}]" if index is not None else ""
        
        # Check if value is a string for length/pattern constraints
        if isinstance(val, str):
            # Length constraints
            min_length = constraints.get("minLength")
            max_length = constraints.get("maxLength")
            
            if min_length and len(val) < min_length:
                errors.append(ValidationError(
                    segment_key=f"{segment.key}{key_suffix}",
                    error_type="constraint_violation",
                    message=f"Value too short (min: {min_length}, actual: {len(val)})",
                    details={"constraint": "minLength", "expected": min_length, "actual": len(val)},
                ))
            
            if max_length and len(val) > max_length:
                errors.append(ValidationError(
                    segment_key=f"{segment.key}{key_suffix}",
                    error_type="constraint_violation",
                    message=f"Value too long (max: {max_length}, actual: {len(val)})",
                    details={"constraint": "maxLength", "expected": max_length, "actual": len(val)},
                ))
            
            # Pattern constraint
            pattern = constraints.get("pattern")
            if pattern:
                if not re.search(pattern, val):
                    errors.append(ValidationError(
                        segment_key=f"{segment.key}{key_suffix}",
                        error_type="constraint_violation",
                        message=f"Value does not match pattern: {pattern}",
                        details={"constraint": "pattern", "pattern": pattern},
                    ))
        
        return errors


def create_skill_input(
    template: Template,
    content: FilledContent,
    source: Optional[Dict[str, Any]] = None,
    trace: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a complete skill_input.json structure with template.
    
    Args:
        template: Template used for content.
        content: Filled content from TemplateFiller.
        source: Source metadata (transcript refs, etc.).
        trace: Generation trace metadata.
    
    Returns:
        Complete skill_input dictionary ready for serialization.
    """
    now = datetime.now(timezone.utc).isoformat()
    
    return {
        "template": {
            "id": template.id,
            "name": template.name,
            "version": template.version,
            "segments": [s.to_dict() for s in template.segments],
        },
        "content": content.to_dict(),
        "source": source or {},
        "trace": trace or {
            "generated_at": now,
            "template_version_used": template.version,
        },
    }
