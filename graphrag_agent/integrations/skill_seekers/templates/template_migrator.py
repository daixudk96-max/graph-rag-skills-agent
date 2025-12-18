"""
Template Migrator - Compares templates and generates migration guidance.

Helps maintain backward compatibility when template versions change,
by detecting differences and suggesting migration paths.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set, Tuple
from enum import Enum
import logging

from .template_registry import Template, Segment

logger = logging.getLogger(__name__)


class ChangeType(Enum):
    """Types of changes between template versions."""
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    RENAMED = "renamed"
    REORDERED = "reordered"


@dataclass
class SegmentChange:
    """Represents a change to a segment between template versions."""
    segment_key: str
    change_type: ChangeType
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "segment_key": self.segment_key,
            "change_type": self.change_type.value,
        }
        if self.old_value is not None:
            result["old_value"] = self.old_value
        if self.new_value is not None:
            result["new_value"] = self.new_value
        if self.details:
            result["details"] = self.details
        return result


@dataclass
class MigrationReport:
    """
    Report detailing differences between template versions.
    
    Used to generate migration guidance and compatibility warnings.
    """
    old_template_id: str
    old_version: str
    new_template_id: str
    new_version: str
    changes: List[SegmentChange] = field(default_factory=list)
    is_breaking: bool = False
    compatibility_notes: List[str] = field(default_factory=list)
    
    @property
    def has_changes(self) -> bool:
        """Check if there are any changes."""
        return len(self.changes) > 0
    
    @property
    def added_segments(self) -> List[SegmentChange]:
        """Get added segments."""
        return [c for c in self.changes if c.change_type == ChangeType.ADDED]
    
    @property
    def removed_segments(self) -> List[SegmentChange]:
        """Get removed segments."""
        return [c for c in self.changes if c.change_type == ChangeType.REMOVED]
    
    @property
    def modified_segments(self) -> List[SegmentChange]:
        """Get modified segments."""
        return [c for c in self.changes if c.change_type == ChangeType.MODIFIED]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "old_template": f"{self.old_template_id}@{self.old_version}",
            "new_template": f"{self.new_template_id}@{self.new_version}",
            "changes": [c.to_dict() for c in self.changes],
            "is_breaking": self.is_breaking,
            "compatibility_notes": self.compatibility_notes,
            "summary": {
                "total_changes": len(self.changes),
                "added": len(self.added_segments),
                "removed": len(self.removed_segments),
                "modified": len(self.modified_segments),
            },
        }


class TemplateMigrator:
    """
    Compares templates and generates migration reports and guidance.
    
    Features:
    - Detect segment additions, removals, and modifications
    - Identify breaking changes (removed required segments)
    - Generate human-readable migration guides
    - Suggest field mappings for renamed segments
    
    Example usage:
        migrator = TemplateMigrator()
        report = migrator.compare(old_template, new_template)
        guide = migrator.generate_migration_guide(report)
    """
    
    def __init__(self, similarity_threshold: float = 0.8):
        """
        Initialize the migrator.
        
        Args:
            similarity_threshold: Threshold for detecting renamed segments (0.0-1.0).
        """
        self.similarity_threshold = similarity_threshold
    
    def compare(
        self,
        old_template: Template,
        new_template: Template
    ) -> MigrationReport:
        """
        Compare two template versions and generate a migration report.
        
        Args:
            old_template: Previous template version.
            new_template: New template version.
        
        Returns:
            MigrationReport with detected changes.
        """
        report = MigrationReport(
            old_template_id=old_template.id,
            old_version=old_template.version,
            new_template_id=new_template.id,
            new_version=new_template.version,
        )
        
        old_keys = {s.key for s in old_template.segments}
        new_keys = {s.key for s in new_template.segments}
        
        # Detect removed segments
        removed_keys = old_keys - new_keys
        for key in removed_keys:
            old_segment = old_template.get_segment(key)
            change = SegmentChange(
                segment_key=key,
                change_type=ChangeType.REMOVED,
                old_value=old_segment.to_dict() if old_segment else None,
            )
            report.changes.append(change)
            
            # Breaking if segment was required
            if old_segment and old_segment.required:
                report.is_breaking = True
                report.compatibility_notes.append(
                    f"BREAKING: Required segment '{key}' was removed"
                )
        
        # Detect added segments
        added_keys = new_keys - old_keys
        for key in added_keys:
            new_segment = new_template.get_segment(key)
            change = SegmentChange(
                segment_key=key,
                change_type=ChangeType.ADDED,
                new_value=new_segment.to_dict() if new_segment else None,
            )
            report.changes.append(change)
            
            # Note if new required segment
            if new_segment and new_segment.required:
                report.compatibility_notes.append(
                    f"New required segment '{key}' may need manual population"
                )
        
        # Detect modified segments
        common_keys = old_keys & new_keys
        for key in common_keys:
            old_segment = old_template.get_segment(key)
            new_segment = new_template.get_segment(key)
            
            if old_segment and new_segment:
                changes = self._compare_segments(old_segment, new_segment)
                if changes:
                    change = SegmentChange(
                        segment_key=key,
                        change_type=ChangeType.MODIFIED,
                        old_value=old_segment.to_dict(),
                        new_value=new_segment.to_dict(),
                        details={"field_changes": changes},
                    )
                    report.changes.append(change)
                    
                    # Check for breaking constraint changes
                    for field_change in changes:
                        if field_change["field"] == "required" and field_change["new"]:
                            report.compatibility_notes.append(
                                f"Segment '{key}' is now required"
                            )
        
        # Check for possible renames (removed + added with similar structure)
        if removed_keys and added_keys:
            renames = self._detect_renames(
                old_template, new_template, removed_keys, added_keys
            )
            for old_key, new_key, similarity in renames:
                report.compatibility_notes.append(
                    f"Possible rename: '{old_key}' → '{new_key}' (similarity: {similarity:.0%})"
                )
        
        # Detect reordering
        old_order = [s.key for s in old_template.segments]
        new_order = [s.key for s in new_template.segments]
        if self._is_reordered(old_order, new_order, common_keys):
            report.compatibility_notes.append("Segment order has changed")
        
        return report
    
    def _compare_segments(
        self,
        old_segment: Segment,
        new_segment: Segment
    ) -> List[Dict[str, Any]]:
        """Compare two segments and return field-level changes."""
        changes = []
        
        # Fields to compare
        compare_fields = [
            "title", "description", "required", "repeatable",
            "format", "constraints"
        ]
        
        old_dict = old_segment.to_dict()
        new_dict = new_segment.to_dict()
        
        for field in compare_fields:
            old_val = old_dict.get(field)
            new_val = new_dict.get(field)
            
            if old_val != new_val:
                changes.append({
                    "field": field,
                    "old": old_val,
                    "new": new_val,
                })
        
        # Compare inputs separately (complex structure)
        if old_segment.inputs != new_segment.inputs:
            changes.append({
                "field": "inputs",
                "old": old_segment.inputs,
                "new": new_segment.inputs,
            })
        
        # Compare transform separately
        if old_segment.transform != new_segment.transform:
            changes.append({
                "field": "transform",
                "old": old_segment.transform,
                "new": new_segment.transform,
            })
        
        return changes
    
    def _detect_renames(
        self,
        old_template: Template,
        new_template: Template,
        removed_keys: Set[str],
        added_keys: Set[str]
    ) -> List[Tuple[str, str, float]]:
        """Detect possible renames based on segment similarity."""
        renames = []
        
        for old_key in removed_keys:
            old_segment = old_template.get_segment(old_key)
            if not old_segment:
                continue
            
            best_match = None
            best_similarity = 0.0
            
            for new_key in added_keys:
                new_segment = new_template.get_segment(new_key)
                if not new_segment:
                    continue
                
                similarity = self._calculate_segment_similarity(old_segment, new_segment)
                if similarity > best_similarity and similarity >= self.similarity_threshold:
                    best_match = new_key
                    best_similarity = similarity
            
            if best_match:
                renames.append((old_key, best_match, best_similarity))
        
        return renames
    
    def _calculate_segment_similarity(
        self,
        seg1: Segment,
        seg2: Segment
    ) -> float:
        """Calculate similarity between two segments (0.0 to 1.0)."""
        score = 0.0
        max_score = 0.0
        
        # Compare title (weighted higher)
        max_score += 2.0
        if seg1.title == seg2.title:
            score += 2.0
        elif self._string_similarity(seg1.title, seg2.title) > 0.5:
            score += 1.0
        
        # Compare required flag
        max_score += 1.0
        if seg1.required == seg2.required:
            score += 1.0
        
        # Compare repeatable flag
        max_score += 1.0
        if seg1.repeatable == seg2.repeatable:
            score += 1.0
        
        # Compare format
        max_score += 1.0
        if seg1.format == seg2.format:
            score += 1.0
        
        # Compare transform type if present
        if seg1.transform or seg2.transform:
            max_score += 1.0
            t1 = seg1.transform.get("type") if seg1.transform else None
            t2 = seg2.transform.get("type") if seg2.transform else None
            if t1 == t2:
                score += 1.0
        
        return score / max_score if max_score > 0 else 0.0
    
    def _string_similarity(self, s1: str, s2: str) -> float:
        """Calculate string similarity using simple ratio."""
        if not s1 or not s2:
            return 0.0
        
        # Simple character-based similarity
        s1_lower = s1.lower()
        s2_lower = s2.lower()
        
        if s1_lower == s2_lower:
            return 1.0
        
        # Check for containment
        if s1_lower in s2_lower or s2_lower in s1_lower:
            return 0.7
        
        # Character overlap
        common = set(s1_lower) & set(s2_lower)
        total = set(s1_lower) | set(s2_lower)
        
        return len(common) / len(total) if total else 0.0
    
    def _is_reordered(
        self,
        old_order: List[str],
        new_order: List[str],
        common_keys: Set[str]
    ) -> bool:
        """Check if common segments have been reordered."""
        old_common = [k for k in old_order if k in common_keys]
        new_common = [k for k in new_order if k in common_keys]
        return old_common != new_common
    
    def generate_migration_guide(
        self,
        report: MigrationReport,
        include_examples: bool = True
    ) -> str:
        """
        Generate a human-readable migration guide.
        
        Args:
            report: Migration report from compare().
            include_examples: Include example code snippets.
        
        Returns:
            Markdown-formatted migration guide.
        """
        lines = [
            f"# Migration Guide: {report.old_template_id}@{report.old_version} → {report.new_template_id}@{report.new_version}",
            "",
        ]
        
        if not report.has_changes:
            lines.append("No changes detected between versions.")
            return "\n".join(lines)
        
        # Summary
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- **Total Changes**: {len(report.changes)}")
        lines.append(f"- **Added Segments**: {len(report.added_segments)}")
        lines.append(f"- **Removed Segments**: {len(report.removed_segments)}")
        lines.append(f"- **Modified Segments**: {len(report.modified_segments)}")
        
        if report.is_breaking:
            lines.append("")
            lines.append("> ⚠️ **BREAKING CHANGES DETECTED**")
        
        lines.append("")
        
        # Compatibility notes
        if report.compatibility_notes:
            lines.append("## Compatibility Notes")
            lines.append("")
            for note in report.compatibility_notes:
                lines.append(f"- {note}")
            lines.append("")
        
        # Added segments
        if report.added_segments:
            lines.append("## Added Segments")
            lines.append("")
            for change in report.added_segments:
                new_val = change.new_value or {}
                required = " (required)" if new_val.get("required") else ""
                lines.append(f"### `{change.segment_key}`{required}")
                lines.append("")
                if new_val.get("title"):
                    lines.append(f"- **Title**: {new_val['title']}")
                if new_val.get("description"):
                    lines.append(f"- **Description**: {new_val['description']}")
                lines.append("")
            lines.append("")
        
        # Removed segments
        if report.removed_segments:
            lines.append("## Removed Segments")
            lines.append("")
            for change in report.removed_segments:
                old_val = change.old_value or {}
                required = " ⚠️ (was required)" if old_val.get("required") else ""
                lines.append(f"- `{change.segment_key}`{required}")
            lines.append("")
        
        # Modified segments
        if report.modified_segments:
            lines.append("## Modified Segments")
            lines.append("")
            for change in report.modified_segments:
                lines.append(f"### `{change.segment_key}`")
                lines.append("")
                
                field_changes = change.details.get("field_changes", [])
                if field_changes:
                    lines.append("| Field | Old Value | New Value |")
                    lines.append("|-------|-----------|-----------|")
                    for fc in field_changes:
                        old = str(fc.get("old", "—"))[:50]
                        new = str(fc.get("new", "—"))[:50]
                        lines.append(f"| {fc['field']} | {old} | {new} |")
                lines.append("")
        
        # Migration steps
        lines.append("## Migration Steps")
        lines.append("")
        
        step = 1
        if report.removed_segments:
            lines.append(f"{step}. **Handle Removed Segments**")
            lines.append("   - Review content from removed segments")
            lines.append("   - Move data to appropriate new segments or archive")
            step += 1
        
        if report.added_segments:
            for change in report.added_segments:
                new_val = change.new_value or {}
                if new_val.get("required"):
                    lines.append(f"{step}. **Populate Required Segment `{change.segment_key}`**")
                    lines.append(f"   - Add content for: {new_val.get('title', change.segment_key)}")
                    step += 1
        
        if report.modified_segments:
            lines.append(f"{step}. **Review Modified Segments**")
            lines.append("   - Check if existing content matches new constraints")
            lines.append("   - Update format if format property changed")
            step += 1
        
        lines.append("")
        lines.append("---")
        lines.append(f"*Generated at migration analysis time*")
        
        return "\n".join(lines)
