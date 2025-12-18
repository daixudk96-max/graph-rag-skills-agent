"""
Comprehensive Verification Script for Dynamic Template Mechanism.

Tests all components:
1. TemplateRegistry - load, list, register templates
2. TemplateFiller - fill content, validate
3. TemplateMigrator - compare templates, generate migration guide
4. TemplateEmbedder - embed/extract from SKILL.md
5. SkillInputFormatter - format with template support
"""

import json
from pathlib import Path
from datetime import datetime

def test_template_registry():
    """Test Template Registry functionality."""
    print("\n" + "="*60)
    print("1. Testing TemplateRegistry")
    print("="*60)
    
    from graphrag_agent.integrations.skill_seekers import TemplateRegistry, Template
    
    registry = TemplateRegistry()
    
    # Test list_templates
    templates = registry.list_templates()
    print(f"✓ Found {len(templates)} templates:")
    for t in templates:
        print(f"  - {t.identifier}: {t.name} ({t.segment_count} segments)")
    
    # Test get_template
    template = registry.get_template("transcript-segmented", "1.0.0")
    assert template is not None, "Failed to load transcript-segmented template"
    print(f"✓ Loaded template: {template.identifier}")
    print(f"  Segments: {[s.key for s in template.segments]}")
    
    # Test get_template without version (latest)
    template_latest = registry.get_template("transcript-meeting")
    if template_latest:
        print(f"✓ Loaded latest version: {template_latest.identifier}")
    
    return template


def test_template_filler(template):
    """Test Template Filler functionality."""
    print("\n" + "="*60)
    print("2. Testing TemplateFiller")
    print("="*60)
    
    from graphrag_agent.integrations.skill_seekers import TemplateFiller
    
    filler = TemplateFiller()
    
    # Test filling with sample content
    raw_content = {
        "context": "This is a lecture about Python programming fundamentals.",
        "key_points": [
            "Variables and data types",
            "Control flow statements",
            "Functions and modules"
        ],
        "summary": "An introduction to Python covering core concepts.",
        "examples": ["Hello World example", "Calculator program"]
    }
    
    filled = filler.fill(template, raw_content)
    print(f"✓ Fill status: {filled.status}")
    print(f"  Filled segments: {list(filled.segments.keys())}")
    print(f"  Missing required: {filled.missing_required}")
    print(f"  Warnings: {filled.warnings}")
    
    # Test validation
    errors = filler.validate(filled, template)
    print(f"✓ Validation errors: {len(errors)}")
    for err in errors:
        print(f"  - {err}")
    
    return filled


def test_template_migrator():
    """Test Template Migrator functionality."""
    print("\n" + "="*60)
    print("3. Testing TemplateMigrator")
    print("="*60)
    
    from graphrag_agent.integrations.skill_seekers import (
        TemplateRegistry, TemplateMigrator, Template
    )
    from graphrag_agent.integrations.skill_seekers.templates.template_registry import Segment
    
    registry = TemplateRegistry()
    migrator = TemplateMigrator()
    
    # Get existing template
    old_template = registry.get_template("transcript-segmented", "1.0.0")
    
    # Create a modified version for comparison
    new_segments = [
        Segment(key="context", title="背景信息（更新）", required=True),
        Segment(key="key_points", title="核心要点", required=True, repeatable=True),
        Segment(key="new_segment", title="新增段落", required=True),  # Added
        Segment(key="summary", title="总结"),
        # Removed: examples, references
    ]
    new_template = Template(
        id="transcript-segmented",
        version="2.0.0",
        segments=new_segments,
        name="分段转录模板 v2",
    )
    
    # Compare templates
    report = migrator.compare(old_template, new_template)
    print(f"✓ Migration report generated:")
    print(f"  Changes: {len(report.changes)}")
    print(f"  Added: {len(report.added_segments)}")
    print(f"  Removed: {len(report.removed_segments)}")
    print(f"  Modified: {len(report.modified_segments)}")
    print(f"  Breaking: {report.is_breaking}")
    
    # Generate migration guide
    guide = migrator.generate_migration_guide(report)
    print(f"✓ Migration guide generated ({len(guide)} chars)")
    print("  First 500 chars:")
    print("-" * 40)
    print(guide[:500])
    print("-" * 40)
    
    return report


def test_template_embedder(template):
    """Test Template Embedder functionality."""
    print("\n" + "="*60)
    print("4. Testing TemplateEmbedder")
    print("="*60)
    
    from graphrag_agent.integrations.skill_seekers import TemplateEmbedder
    
    embedder = TemplateEmbedder(include_segments=False)
    
    # Sample SKILL.md content
    skill_md = """# Python Programming Fundamentals

## Overview
This skill covers Python basics.

## Key Concepts
- Variables
- Control flow
- Functions
"""
    
    # Embed template metadata
    embedded = embedder.embed_in_skill(skill_md, template)
    print(f"✓ Embedded metadata into SKILL.md")
    print(f"  Original length: {len(skill_md)} chars")
    print(f"  With metadata: {len(embedded)} chars")
    
    # Check if metadata exists
    has_meta = embedder.has_metadata(embedded)
    print(f"✓ Has metadata: {has_meta}")
    
    # Get template identifier
    identifier = embedder.get_template_identifier(embedded)
    print(f"✓ Extracted identifier: {identifier}")
    
    # Extract full template
    extracted = embedder.extract_from_skill(embedded)
    print(f"✓ Extracted template: {extracted.identifier if extracted else None}")
    
    # Test with include_segments=True
    embedder_full = TemplateEmbedder(include_segments=True)
    embedded_full = embedder_full.embed_in_skill(skill_md, template)
    extracted_full = embedder_full.extract_from_skill(embedded_full)
    print(f"✓ With segments: extracted {len(extracted_full.segments) if extracted_full else 0} segments")
    
    # Test remove
    removed = embedder.remove_from_skill(embedded)
    has_meta_after = embedder.has_metadata(removed)
    print(f"✓ After removal, has metadata: {has_meta_after}")
    
    return embedded


def test_formatter_with_template(template, filled):
    """Test SkillInputFormatter with template support."""
    print("\n" + "="*60)
    print("5. Testing SkillInputFormatter with Template")
    print("="*60)
    
    from graphrag_agent.integrations.skill_seekers import SkillInputFormatter
    from graphrag_agent.integrations.skill_seekers.config import ExportResult
    
    # Create sample export result
    export_result = ExportResult(
        pages=[
            {"title": "Page 1", "content": "Content 1", "url": "http://example.com/1"},
            {"title": "Page 2", "content": "Content 2", "url": "http://example.com/2"},
        ],
        entities=[
            {"name": "Python", "type": "technology", "description": "Programming language"},
        ],
        metadata={
            "type": "graphrag",
            "graph_name": "test-graph",
            "export_mode": "full",
        },
        dedup_report={"total": 2, "unique": 2},
    )
    
    formatter = SkillInputFormatter()
    
    # Test legacy format
    legacy = formatter.format(export_result)
    print(f"✓ Legacy format keys: {list(legacy.keys())}")
    
    # Test template format
    template_output = formatter.format_with_template(export_result, template, filled)
    print(f"✓ Template format keys: {list(template_output.keys())}")
    print(f"  Has template: {'template' in template_output}")
    print(f"  Has content: {'content' in template_output}")
    print(f"  Has source: {'source' in template_output}")
    print(f"  Has trace: {'trace' in template_output}")
    
    # Validate output
    legacy_errors = formatter.validate_output(legacy)
    template_errors = formatter.validate_output(template_output)
    print(f"✓ Legacy validation errors: {len(legacy_errors)}")
    print(f"✓ Template validation errors: {len(template_errors)}")
    
    # Check format detection
    is_template = formatter.is_template_format(template_output)
    is_legacy = formatter.is_template_format(legacy)
    print(f"✓ Template format detected: {is_template}")
    print(f"✓ Legacy format detected as template: {is_legacy}")
    
    # Save to temp file
    output_path = Path("test_skill_input_template.json")
    formatter.save_to_file(export_result, str(output_path), template, filled)
    print(f"✓ Saved to: {output_path}")
    
    # Verify saved content
    with open(output_path) as f:
        saved = json.load(f)
    print(f"✓ Saved file contains template: {'template' in saved}")
    
    # Cleanup
    output_path.unlink()
    print(f"✓ Cleaned up test file")
    
    return template_output


def test_create_skill_input():
    """Test create_skill_input helper function."""
    print("\n" + "="*60)
    print("6. Testing create_skill_input Helper")
    print("="*60)
    
    from graphrag_agent.integrations.skill_seekers import TemplateRegistry, TemplateFiller
    from graphrag_agent.integrations.skill_seekers.templates.template_filler import create_skill_input
    
    registry = TemplateRegistry()
    template = registry.get_template("transcript-interview", "1.0.0")
    
    filler = TemplateFiller()
    raw_content = {
        "interview_info": {"position": "Python Developer", "date": "2024-12-19"},
        "questions_answers": [
            {"q": "Tell me about yourself", "a": "I am a developer..."},
            {"q": "Python experience?", "a": "5 years..."},
        ],
        "overall_evaluation": "Strong candidate",
    }
    filled = filler.fill(template, raw_content)
    
    skill_input = create_skill_input(
        template=template,
        content=filled,
        source={"transcript_file": "interview_recording.txt"},
        trace={"interviewer": "John Doe"}
    )
    
    print(f"✓ Created skill_input with keys: {list(skill_input.keys())}")
    print(f"  Template ID: {skill_input['template']['id']}")
    print(f"  Content status: {skill_input['content']['status']}")
    print(f"  Source keys: {list(skill_input['source'].keys())}")
    print(f"  Trace keys: {list(skill_input['trace'].keys())}")
    
    return skill_input


def main():
    """Run all verification tests."""
    print("="*60)
    print("DYNAMIC TEMPLATE MECHANISM - COMPLETE VERIFICATION")
    print(f"Time: {datetime.now().isoformat()}")
    print("="*60)
    
    try:
        # 1. Test Registry
        template = test_template_registry()
        
        # 2. Test Filler
        filled = test_template_filler(template)
        
        # 3. Test Migrator
        report = test_template_migrator()
        
        # 4. Test Embedder
        embedded = test_template_embedder(template)
        
        # 5. Test Formatter
        output = test_formatter_with_template(template, filled)
        
        # 6. Test Helper
        skill_input = test_create_skill_input()
        
        print("\n" + "="*60)
        print("✅ ALL VERIFICATION TESTS PASSED!")
        print("="*60)
        
        return True
        
    except Exception as e:
        print("\n" + "="*60)
        print(f"❌ VERIFICATION FAILED: {e}")
        print("="*60)
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
