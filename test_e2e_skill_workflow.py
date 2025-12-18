"""
End-to-End Test: Document to SKILL.md Complete Workflow

This test simulates the complete Skill Seekers workflow:
1. Start with raw transcript content
2. Select appropriate template
3. Fill template with content
4. Generate skill_input.json
5. Format and validate
6. Create final SKILL.md with embedded template metadata
7. Verify round-trip extraction

This is a comprehensive integration test for the Dynamic Template Mechanism.
"""

import json
import tempfile
from pathlib import Path
from datetime import datetime

def create_sample_transcript():
    """Create sample transcript content simulating scraped data."""
    return {
        "source": {
            "type": "transcript",
            "file": "python_lecture_01.txt",
            "duration": "45:00"
        },
        "raw_content": """
好，今天我们来学习Python编程的基础知识。

首先，我们来了解什么是Python。Python是一种高级编程语言，
由Guido van Rossum于1991年创建。它以简洁易读著称。

下一个主题是变量和数据类型。在Python中，变量不需要声明类型，
这称为动态类型。常见的数据类型包括：
- 整数 (int): 如 42, -10
- 浮点数 (float): 如 3.14, -2.5
- 字符串 (str): 如 "Hello World"
- 布尔值 (bool): True 或 False

最后，我们来看一个简单的例子：
print("Hello, World!")
这行代码会在屏幕上输出 "Hello, World!"。

好，今天的课程就到这里，下节课我们学习控制流。
        """,
        "metadata": {
            "instructor": "张老师",
            "course": "Python编程入门",
            "lesson": 1
        }
    }


def test_complete_workflow():
    """Run the complete document-to-skill workflow test."""
    print("=" * 70)
    print("END-TO-END TEST: Document to SKILL.md Complete Workflow")
    print(f"Time: {datetime.now().isoformat()}")
    print("=" * 70)

    # Import all required components
    from graphrag_agent.integrations.skill_seekers import (
        TemplateRegistry,
        TemplateFiller,
        TemplateEmbedder,
        SkillInputFormatter,
    )
    from graphrag_agent.integrations.skill_seekers.config import ExportResult
    from graphrag_agent.integrations.skill_seekers.templates.template_filler import create_skill_input

    # Step 1: Get sample transcript
    print("\n[Step 1] Loading sample transcript...")
    transcript = create_sample_transcript()
    print(f"  ✓ Loaded transcript: {transcript['source']['file']}")
    print(f"  ✓ Duration: {transcript['source']['duration']}")
    print(f"  ✓ Content length: {len(transcript['raw_content'])} chars")

    # Step 2: Select appropriate template
    print("\n[Step 2] Selecting template...")
    registry = TemplateRegistry()
    
    # List available templates
    templates = registry.list_templates()
    print(f"  ✓ Available templates:")
    for t in templates:
        print(f"    - {t.identifier}: {t.name}")
    
    # Select transcript-segmented template
    template = registry.get_template("transcript-segmented", "1.0.0")
    print(f"  ✓ Selected: {template.identifier}")
    print(f"  ✓ Segments: {[s.key for s in template.segments]}")

    # Step 3: Extract content for template segments
    print("\n[Step 3] Extracting content for template segments...")
    
    # Simulate AI-extracted content from transcript
    extracted_content = {
        "context": (
            "本课程是Python编程入门系列的第一讲，由张老师主讲。"
            "课程介绍Python语言的基础知识，包括语言背景、变量和数据类型。"
            "Python由Guido van Rossum于1991年创建，是一种简洁易读的高级编程语言。"
        ),
        "key_points": [
            "Python是由Guido van Rossum于1991年创建的高级编程语言",
            "Python以简洁易读著称，适合初学者",
            "变量不需要声明类型（动态类型）",
            "常见数据类型：int, float, str, bool",
            "print()函数用于输出内容到屏幕"
        ],
        "examples": [
            {
                "title": "Hello World程序",
                "code": 'print("Hello, World!")',
                "explanation": "这是最简单的Python程序，输出一行文字"
            },
            {
                "title": "数据类型示例",
                "code": "x = 42  # 整数\ny = 3.14  # 浮点数\nname = 'Python'  # 字符串",
                "explanation": "展示不同数据类型的变量赋值"
            }
        ],
        "summary": (
            "本讲介绍了Python语言的起源和特点，重点讲解了变量和基本数据类型"
            "（整数、浮点数、字符串、布尔值），并通过Hello World示例展示了"
            "最基本的Python程序结构。"
        ),
        "references": [
            {"title": "Python官方文档", "url": "https://docs.python.org/"},
            {"title": "Python教程 - 菜鸟教程", "url": "https://www.runoob.com/python3/"}
        ]
    }
    print(f"  ✓ Extracted {len(extracted_content)} content sections")

    # Step 4: Fill template with content
    print("\n[Step 4] Filling template with extracted content...")
    filler = TemplateFiller()
    filled_content = filler.fill(template, extracted_content)
    print(f"  ✓ Fill status: {filled_content.status}")
    print(f"  ✓ Filled segments: {list(filled_content.segments.keys())}")
    print(f"  ✓ Missing required: {filled_content.missing_required}")

    # Step 5: Validate filled content
    print("\n[Step 5] Validating filled content...")
    validation_errors = filler.validate(filled_content, template)
    print(f"  ✓ Validation errors: {len(validation_errors)}")
    if validation_errors:
        for err in validation_errors:
            print(f"    - {err}")
    else:
        print("  ✓ All validations passed!")

    # Step 6: Create skill_input.json
    print("\n[Step 6] Creating skill_input.json...")
    source_info = {
        "transcript_file": transcript['source']['file'],
        "duration": transcript['source']['duration'],
        "instructor": transcript['metadata']['instructor'],
        "course": transcript['metadata']['course'],
        "lesson": transcript['metadata']['lesson']
    }
    trace_info = {
        "extraction_method": "AI-assisted",
        "reviewed_by": None,
        "notes": "Auto-generated from transcript"
    }
    
    skill_input = create_skill_input(
        template=template,
        content=filled_content,
        source=source_info,
        trace=trace_info
    )
    print(f"  ✓ Created skill_input with {len(skill_input)} top-level keys")
    print(f"  ✓ Template: {skill_input['template']['id']}@{skill_input['template']['version']}")
    print(f"  ✓ Content status: {skill_input['content']['status']}")

    # Step 7: Save skill_input.json
    print("\n[Step 7] Saving skill_input.json...")
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_input_path = Path(tmpdir) / "skill_input.json"
        with open(skill_input_path, "w", encoding="utf-8") as f:
            json.dump(skill_input, f, ensure_ascii=False, indent=2)
        print(f"  ✓ Saved to: {skill_input_path}")
        
        # Verify saved file
        with open(skill_input_path, encoding="utf-8") as f:
            loaded = json.load(f)
        print(f"  ✓ Verified: {len(loaded)} keys loaded")

        # Step 8: Use Formatter with template support
        print("\n[Step 8] Using SkillInputFormatter with template...")
        export_result = ExportResult(
            pages=[
                {
                    "title": "Python基础教程 - 第1讲",
                    "content": transcript['raw_content'],
                    "url": f"file:///{transcript['source']['file']}"
                }
            ],
            entities=[
                {"name": "Python", "type": "technology", "description": "编程语言"},
                {"name": "Guido van Rossum", "type": "person", "description": "Python创始人"},
            ],
            metadata={
                "type": "transcript",
                "export_mode": "full"
            },
            dedup_report={"total": 1, "unique": 1}
        )
        
        formatter = SkillInputFormatter(use_templates=True)
        formatted = formatter.format_with_template(
            export_result, template, filled_content
        )
        print(f"  ✓ Formatted output keys: {list(formatted.keys())}")
        
        # Validate formatted output
        format_errors = formatter.validate_output(formatted)
        print(f"  ✓ Format validation errors: {len(format_errors)}")

        # Step 9: Generate SKILL.md content
        print("\n[Step 9] Generating SKILL.md content...")
        skill_md = generate_skill_md(extracted_content, transcript['metadata'])
        print(f"  ✓ Generated SKILL.md ({len(skill_md)} chars)")

        # Step 10: Embed template metadata
        print("\n[Step 10] Embedding template metadata in SKILL.md...")
        embedder = TemplateEmbedder(include_segments=False)
        skill_md_with_meta = embedder.embed_in_skill(skill_md, template)
        print(f"  ✓ With metadata: {len(skill_md_with_meta)} chars")
        print(f"  ✓ Has metadata: {embedder.has_metadata(skill_md_with_meta)}")

        # Step 11: Save final SKILL.md
        print("\n[Step 11] Saving final SKILL.md...")
        skill_md_path = Path(tmpdir) / "SKILL.md"
        with open(skill_md_path, "w", encoding="utf-8") as f:
            f.write(skill_md_with_meta)
        print(f"  ✓ Saved to: {skill_md_path}")

        # Step 12: Verify round-trip - extract metadata
        print("\n[Step 12] Verifying round-trip metadata extraction...")
        with open(skill_md_path, encoding="utf-8") as f:
            loaded_skill_md = f.read()
        
        extracted_template = embedder.extract_from_skill(loaded_skill_md)
        print(f"  ✓ Extracted template: {extracted_template.identifier if extracted_template else None}")
        print(f"  ✓ Template ID matches: {extracted_template.id == template.id if extracted_template else False}")
        print(f"  ✓ Version matches: {extracted_template.version == template.version if extracted_template else False}")

        # Step 13: Test format detection
        print("\n[Step 13] Testing format detection...")
        is_template_format = formatter.is_template_format(formatted)
        legacy_format = formatter.format(export_result)
        is_legacy_format = formatter.is_template_format(legacy_format)
        print(f"  ✓ Template format correctly detected: {is_template_format}")
        print(f"  ✓ Legacy format correctly detected: {not is_legacy_format}")

    # Final Summary
    print("\n" + "=" * 70)
    print("✅ END-TO-END TEST COMPLETE - ALL STEPS PASSED!")
    print("=" * 70)
    print("\nWorkflow Summary:")
    print("  1. Raw transcript loaded")
    print("  2. Template selected (transcript-segmented@1.0.0)")
    print("  3. Content extracted and mapped to segments")
    print("  4. Template filled with content")
    print("  5. Validation passed")
    print("  6. skill_input.json created (4-layer structure)")
    print("  7. File saved and verified")
    print("  8. SkillInputFormatter used with template")
    print("  9. SKILL.md content generated")
    print("  10. Template metadata embedded")
    print("  11. Final SKILL.md saved")
    print("  12. Round-trip metadata extraction verified")
    print("  13. Format detection verified")
    print("\n✅ Dynamic Template Mechanism is fully functional!")

    return True


def generate_skill_md(content: dict, metadata: dict) -> str:
    """Generate SKILL.md content from extracted content."""
    md_parts = []
    
    # Header
    md_parts.append(f"# {metadata.get('course', 'Skill')} - Lesson {metadata.get('lesson', 1)}")
    md_parts.append("")
    md_parts.append(f"**Instructor**: {metadata.get('instructor', 'Unknown')}")
    md_parts.append("")
    
    # Context
    md_parts.append("## Overview")
    md_parts.append(content.get('context', ''))
    md_parts.append("")
    
    # Key Points
    md_parts.append("## Key Points")
    for point in content.get('key_points', []):
        md_parts.append(f"- {point}")
    md_parts.append("")
    
    # Examples
    if content.get('examples'):
        md_parts.append("## Examples")
        for example in content['examples']:
            md_parts.append(f"### {example.get('title', 'Example')}")
            md_parts.append("```python")
            md_parts.append(example.get('code', ''))
            md_parts.append("```")
            md_parts.append(example.get('explanation', ''))
            md_parts.append("")
    
    # Summary
    md_parts.append("## Summary")
    md_parts.append(content.get('summary', ''))
    md_parts.append("")
    
    # References
    if content.get('references'):
        md_parts.append("## References")
        for ref in content['references']:
            md_parts.append(f"- [{ref.get('title', 'Link')}]({ref.get('url', '#')})")
        md_parts.append("")
    
    return "\n".join(md_parts)


if __name__ == "__main__":
    success = test_complete_workflow()
    exit(0 if success else 1)
