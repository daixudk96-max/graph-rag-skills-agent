"""
Template Embedder - Embeds and extracts template metadata from SKILL.md files.

Enables traceability by storing template information directly in generated
skill documents as HTML comments.
"""

from typing import Dict, Optional, Any, Tuple
import json
import re
import logging

from .template_registry import Template

logger = logging.getLogger(__name__)

# Pattern for matching TEMPLATE_META comment start (captures until we find the JSON)
_META_START_PATTERN = re.compile(r'<!--\s*TEMPLATE_META:\s*')
_META_END = '-->'


def _find_json_in_comment(text: str) -> Tuple[Optional[str], int, int]:
    """
    Find and extract JSON from a TEMPLATE_META comment.
    
    Handles nested braces properly by counting brace depth.
    
    Returns:
        Tuple of (json_str, start_pos, end_pos) or (None, -1, -1) if not found.
    """
    match = _META_START_PATTERN.search(text)
    if not match:
        return None, -1, -1
    
    json_start = match.end()
    brace_count = 0
    json_end = -1
    in_string = False
    escape_next = False
    
    for i, char in enumerate(text[json_start:], start=json_start):
        if escape_next:
            escape_next = False
            continue
        
        if char == '\\':
            escape_next = True
            continue
        
        if char == '"' and not escape_next:
            in_string = not in_string
            continue
        
        if in_string:
            continue
        
        if char == '{':
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0:
                json_end = i + 1
                break
    
    if json_end == -1:
        return None, -1, -1
    
    # Verify we have the closing comment marker after the JSON
    rest = text[json_end:].lstrip()
    if not rest.startswith(_META_END):
        return None, -1, -1
    
    # Find the full comment end position
    comment_end = text.find(_META_END, json_end) + len(_META_END)
    
    return text[json_start:json_end], match.start(), comment_end


class TemplateEmbedder:
    """
    Embeds template metadata in SKILL.md files and extracts it back.
    
    Template metadata is stored as an HTML comment at the top of the file:
        <!-- TEMPLATE_META: {"id":"template-id","version":"1.0.0",...} -->
    
    This allows:
    - Traceability: Know which template generated a skill document
    - Reproducibility: Re-run generation with the same template
    - Validation: Verify content against the original template
    
    Example usage:
        embedder = TemplateEmbedder()
        skill_md = embedder.embed_in_skill(skill_content, template)
        template_info = embedder.extract_from_skill(skill_md)
    """
    
    def __init__(self, include_segments: bool = False):
        """
        Initialize the embedder.
        
        Args:
            include_segments: If True, include full segment definitions in metadata.
                            If False, only include template id, version, name.
        """
        self.include_segments = include_segments
    
    def embed_in_skill(
        self,
        skill_md: str,
        template: Template,
        position: str = "top"
    ) -> str:
        """
        Embed template metadata into a SKILL.md document.
        
        Args:
            skill_md: Original skill document content.
            template: Template used to generate the skill.
            position: Where to embed metadata ("top" or "bottom").
        
        Returns:
            Updated skill document with embedded metadata.
        
        Raises:
            TypeError: If skill_md is not a string.
        """
        if not isinstance(skill_md, str):
            raise TypeError("skill_md must be a string")
        
        # Build metadata dictionary
        metadata = self._build_metadata(template)
        
        # Serialize to JSON
        serialized = json.dumps(metadata, sort_keys=True, separators=(",", ":"))
        meta_comment = f"<!-- TEMPLATE_META: {serialized} -->"
        
        # Check if metadata already exists
        json_str, start_pos, end_pos = _find_json_in_comment(skill_md)
        if json_str is not None:
            # Replace existing metadata
            updated = skill_md[:start_pos] + meta_comment + skill_md[end_pos:]
            logger.debug(f"Replaced existing template metadata for {template.identifier}")
        else:
            # Add new metadata
            if position == "bottom":
                updated = f"{skill_md.rstrip()}\n\n{meta_comment}\n"
            else:  # top
                updated = f"{meta_comment}\n\n{skill_md.lstrip()}"
            logger.debug(f"Embedded template metadata for {template.identifier}")
        
        return updated
    
    def extract_from_skill(self, skill_md: str) -> Optional[Template]:
        """
        Extract template information from a SKILL.md document.
        
        Args:
            skill_md: Skill document content.
        
        Returns:
            Template object with extracted info, or None if not found.
        
        Raises:
            TypeError: If skill_md is not a string.
        """
        if not isinstance(skill_md, str):
            raise TypeError("skill_md must be a string")
        
        json_str, _, _ = _find_json_in_comment(skill_md)
        if json_str is None:
            logger.debug("No TEMPLATE_META block found in skill document")
            return None
        
        try:
            metadata = json.loads(json_str)
            
            template_id = metadata.get("id")
            version = metadata.get("version")
            
            if not template_id or not version:
                logger.warning("TEMPLATE_META found but missing id/version fields")
                return None
            
            # Reconstruct minimal Template object
            segments = []
            if "segments" in metadata:
                from .template_registry import Segment
                for seg_data in metadata["segments"]:
                    segments.append(Segment.from_dict(seg_data))
            
            template = Template(
                id=template_id,
                version=version,
                segments=segments,
                name=metadata.get("name"),
                description=metadata.get("description"),
                metadata={
                    k: v for k, v in metadata.items()
                    if k not in {"id", "version", "name", "description", "segments"}
                },
            )
            
            logger.debug(f"Extracted template info: {template.identifier}")
            return template
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse TEMPLATE_META block: {e}")
            return None
        except Exception as e:
            logger.error(f"Error extracting template from skill: {e}", exc_info=True)
            return None
    
    def remove_from_skill(self, skill_md: str) -> str:
        """
        Remove template metadata from a SKILL.md document.
        
        Args:
            skill_md: Skill document content.
        
        Returns:
            Document with metadata removed.
        """
        if not isinstance(skill_md, str):
            raise TypeError("skill_md must be a string")
        
        # Find and remove the metadata comment
        _, start_pos, end_pos = _find_json_in_comment(skill_md)
        if start_pos == -1:
            return skill_md
        
        result = skill_md[:start_pos] + skill_md[end_pos:]
        
        # Clean up extra blank lines at start/end
        result = re.sub(r'^\n+', '', result)
        result = re.sub(r'\n{3,}', '\n\n', result)
        
        return result
    
    def update_metadata(
        self,
        skill_md: str,
        updates: Dict[str, Any]
    ) -> str:
        """
        Update specific fields in embedded metadata.
        
        Args:
            skill_md: Skill document content.
            updates: Dictionary of fields to update.
        
        Returns:
            Document with updated metadata.
        """
        existing_template = self.extract_from_skill(skill_md)
        if not existing_template:
            logger.warning("No existing metadata to update")
            return skill_md
        
        # Create updated template
        updated_data = existing_template.to_dict()
        updated_data.update(updates)
        
        # Handle segments separately if not in updates
        if "segments" not in updates:
            updated_data["segments"] = [s.to_dict() for s in existing_template.segments]
        
        updated_template = Template.from_dict(updated_data)
        
        # Re-embed with updated template
        return self.embed_in_skill(skill_md, updated_template)
    
    def _build_metadata(self, template: Template) -> Dict[str, Any]:
        """Build the metadata dictionary for embedding."""
        metadata: Dict[str, Any] = {
            "id": template.id,
            "version": template.version,
            "identifier": template.identifier,
        }
        
        if template.name:
            metadata["name"] = template.name
        
        if template.description:
            metadata["description"] = template.description
        
        if self.include_segments and template.segments:
            metadata["segments"] = [s.to_dict() for s in template.segments]
        
        return metadata
    
    def has_metadata(self, skill_md: str) -> bool:
        """
        Check if a SKILL.md document has embedded template metadata.
        
        Args:
            skill_md: Skill document content.
        
        Returns:
            True if metadata is present.
        """
        if not isinstance(skill_md, str):
            return False
        json_str, _, _ = _find_json_in_comment(skill_md)
        return json_str is not None
    
    def get_template_identifier(self, skill_md: str) -> Optional[str]:
        """
        Get just the template identifier from embedded metadata.
        
        Args:
            skill_md: Skill document content.
        
        Returns:
            Template identifier (id@version) or None.
        """
        json_str, _, _ = _find_json_in_comment(skill_md)
        if json_str is None:
            return None
        
        try:
            metadata = json.loads(json_str)
            if "identifier" in metadata:
                return metadata["identifier"]
            
            template_id = metadata.get("id")
            version = metadata.get("version")
            if template_id and version:
                return f"{template_id}@{version}"
            
            return None
        except json.JSONDecodeError:
            return None
