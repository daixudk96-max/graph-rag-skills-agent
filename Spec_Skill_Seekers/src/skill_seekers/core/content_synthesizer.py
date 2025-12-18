#!/usr/bin/env python3
"""
Content Synthesizer for Spec-Driven Skill Generation

Generates actual content for SKILL.md sections and reference files
from source_config data. Supports both LLM-enhanced generation and
deterministic fallback extraction.

Usage:
    synthesizer = ContentSynthesizer(spec, source_config)
    content = synthesizer.synthesize_section_content(section)
"""

import logging
import os
import re
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class GenerationMode(str, Enum):
    """
    Controls how content is produced by ContentSynthesizer.
    
    Attributes:
        API: Use external Claude API for content generation
        WORKFLOW_ASSISTANT: Output task list for AI workflow assistant
        DETERMINISTIC: Use deterministic extraction only (no LLM)
    """
    API = "api"
    WORKFLOW_ASSISTANT = "workflow-assistant"
    DETERMINISTIC = "deterministic"


@dataclass
class ContentTask:
    """
    Task definition for workflow-assistant generation mode.
    
    Each task represents a content generation job to be completed
    by an AI programming assistant during workflow execution.
    """
    id: str
    type: str  # "section" or "reference"
    title: str
    purpose: str
    expected_content: List[str] = field(default_factory=list)
    target_path: str = ""
    source_excerpt: str = ""
    instructions: str = ""


class ContentSynthesizer:
    """
    Synthesizes content for skill sections and references from source data.
    
    Attributes:
        spec: SkillSpec controlling the output structure
        source_config: Dict containing raw content (e.g., lessons, transcripts)
        use_llm: Whether to use Claude API for content generation
        max_source_chars: Maximum characters to include from source per section
    """
    
    # LLM Prompt Templates
    SECTION_PROMPT = """你是一个教育内容专家。根据以下原始材料，为 "{title}" 章节生成内容。

**章节目标**: {purpose}

**期望内容**:
{expected_list}

**原始材料**:
{source_text}

请生成专业、简洁、有教育价值的内容。使用 markdown 格式。确保：
1. 准确提取原文的核心观点，不要编造
2. 使用清晰的语言组织信息
3. 保持结构化和可读性"""

    REFERENCE_PROMPT = """你是技术写作者。请根据以下来源生成参考文档 "{filename}"。

**文档目的**: {purpose}

**内容来源**: {sources}

**原始材料**:
{source_text}

请使用 Markdown 格式输出，包含必要的小节、要点和示例。"""

    def __init__(
        self,
        spec: "SkillSpec",  # noqa: F821 - forward reference
        source_config: Dict[str, Any],
        generation_mode: Optional[GenerationMode] = None,
        max_source_chars: int = 8000,
        use_llm: Optional[bool] = None,  # Deprecated, for backward compatibility
    ) -> None:
        """
        Initialize ContentSynthesizer.
        
        Args:
            spec: SkillSpec controlling output structure
            source_config: Dict with source data (lessons, transcripts, etc.)
            generation_mode: Content generation mode (api, workflow-assistant, deterministic)
            max_source_chars: Max chars from source per section
            use_llm: DEPRECATED - Use generation_mode instead. Kept for backward compatibility.
        """
        self.spec = spec
        self.source_config = source_config or {}
        self.max_source_chars = max_source_chars
        self._pending_tasks: List[ContentTask] = []
        
        # Resolve generation_mode with backward compatibility
        if generation_mode is not None:
            # Explicit generation_mode takes precedence
            self.generation_mode = (
                generation_mode if isinstance(generation_mode, GenerationMode)
                else GenerationMode(generation_mode)
            )
        elif use_llm is not None:
            # Map legacy use_llm parameter
            self.generation_mode = (
                GenerationMode.API if use_llm else GenerationMode.DETERMINISTIC
            )
        else:
            # Default to API mode
            self.generation_mode = GenerationMode.API
        
        # Check API availability for API mode
        self._api_available = self._check_api_key()
        
        # Compute effective use_llm for backward compatibility
        if self.generation_mode == GenerationMode.API:
            self.use_llm = self._api_available
            if not self._api_available:
                logger.warning(
                    "API mode requested but ANTHROPIC_API_KEY not set. "
                    "Falling back to deterministic extraction."
                )
                self.generation_mode = GenerationMode.DETERMINISTIC
        else:
            self.use_llm = False
    
    def _check_api_key(self) -> bool:
        """Check if Anthropic API key is available."""
        return bool(os.environ.get("ANTHROPIC_API_KEY"))
    
    def build_tasks_for_delegate(self, skill_dir: str = "") -> List[ContentTask]:
        """
        Retrieve collected tasks for AI workflow assistant.
        
        Call this after synthesize_section_content/synthesize_reference_content
        have been invoked for all sections/references in workflow-assistant mode.
        
        Args:
            skill_dir: Base directory path for the skill output.
                       Used to construct full target_path values.
        
        Returns:
            List of ContentTask objects representing pending content generation jobs.
        """
        # Update target_path with full path if skill_dir provided
        if skill_dir:
            for task in self._pending_tasks:
                if task.target_path.startswith("SKILL.md"):
                    task.target_path = f"{skill_dir}/{task.target_path}"
                elif task.target_path.startswith("references/"):
                    task.target_path = f"{skill_dir}/{task.target_path}"
        
        return self._pending_tasks.copy()
    
    def _get_source_text(self) -> str:
        """Extract raw text from source_config.
        
        Supports multiple source formats:
        1. lessons.lessons.content (legacy string format)
        2. lessons.lessons[] (array of lesson objects with segments)
        3. lessons.content (direct content string)
        4. transcript (raw transcript text)
        5. content (direct content field)
        """
        # Try common source structures
        if "lessons" in self.source_config:
            lessons_data = self.source_config["lessons"]
            if isinstance(lessons_data, dict):
                # Check for nested 'lessons' key (from spec.yaml format)
                if "lessons" in lessons_data:
                    inner = lessons_data["lessons"]
                    # Legacy format: {lessons: {lessons: {content: "..."}}}
                    if isinstance(inner, dict) and "content" in inner:
                        return inner["content"]
                    # Array format: {lessons: {lessons: [{title, summary, segments}]}}
                    if isinstance(inner, list):
                        formatted = self._format_lessons_list(inner)
                        if formatted:
                            return formatted
                # Direct content
                if "content" in lessons_data:
                    return lessons_data["content"]
        
        if "transcript" in self.source_config:
            return self.source_config["transcript"]
        
        if "content" in self.source_config:
            return self.source_config["content"]
        
        # Last resort: stringify non-empty source_config
        if self.source_config:
            return str(self.source_config)
        
        return ""  # Return empty string for empty source
    
    def _format_lessons_list(self, lessons: List[Any]) -> str:
        """Format a list of lesson objects into readable markdown text.
        
        Priority order for extracting content from each lesson:
        1. segments[].summary_full (most detailed)
        2. summary + key_points (structured fallback)
        
        Args:
            lessons: List of lesson dictionaries with title, summary, segments, etc.
            
        Returns:
            Formatted markdown text suitable for LLM processing or display.
        """
        lesson_blocks: List[str] = []
        
        for lesson in lessons:
            if not isinstance(lesson, dict):
                continue
            
            parts: List[str] = []
            
            # Add lesson title as header
            title = lesson.get("title")
            if title:
                parts.append(f"### {title}")
            
            # Try extracting from segments first (priority: summary_full)
            segments = lesson.get("segments")
            segment_summaries: List[str] = []
            
            if isinstance(segments, list):
                for segment in segments:
                    if isinstance(segment, dict):
                        summary_full = segment.get("summary_full")
                        if summary_full:
                            segment_summaries.append(str(summary_full).strip())
            
            if segment_summaries:
                # Use detailed segment summaries
                parts.append("\n\n".join(segment_summaries))
            else:
                # Fallback: use lesson-level summary and key_points
                summary = lesson.get("summary")
                if summary:
                    parts.append(str(summary).strip())
                
                key_points = lesson.get("key_points")
                if isinstance(key_points, list) and key_points:
                    bullet_points = [f"- {kp}" for kp in key_points if kp]
                    if bullet_points:
                        parts.append("\n".join(bullet_points))
            
            if parts:
                lesson_blocks.append("\n\n".join(parts))
        
        return "\n\n---\n\n".join(lesson_blocks)
    
    def synthesize_section_content(self, section: "SectionSpec") -> str:  # noqa: F821
        """
        Generate content for a SKILL.md section.
        
        Args:
            section: SectionSpec defining the section requirements
            
        Returns:
            Markdown content string for the section
        """
        source_text = self._get_source_text()
        
        if not source_text:
            logger.warning(f"No source content available for section: {section.title}")
            return self._generate_empty_placeholder(section)
        
        # Truncate source to max length
        truncated_source = source_text[:self.max_source_chars]
        if len(source_text) > self.max_source_chars:
            truncated_source += "\n\n...[内容已截断]..."
        
        # Handle workflow-assistant mode: create task entry and return placeholder
        if self.generation_mode == GenerationMode.WORKFLOW_ASSISTANT:
            task_id = f"section-{len(self._pending_tasks) + 1:03d}"
            clean_title = section.title.lstrip("#").strip()
            task = ContentTask(
                id=task_id,
                type="section",
                title=clean_title,
                purpose=section.purpose or "生成章节内容",
                expected_content=section.expected_content or [],
                target_path=f"SKILL.md#{clean_title}",
                source_excerpt=truncated_source[:2000],
                instructions=f"根据原始材料为 \"{clean_title}\" 章节生成结构化内容"
            )
            self._pending_tasks.append(task)
            return f"<!-- TASK:{task_id} -->\n*[待 AI 助手生成: {clean_title}]*\n"
        
        # API mode: use LLM
        if self.use_llm:
            llm_content = self._generate_with_llm(section, truncated_source)
            if llm_content:
                return llm_content
        
        # Fallback to deterministic extraction
        return self._extract_fallback_content(section, truncated_source)
    
    def synthesize_reference_content(self, ref: "ReferenceSpec") -> str:  # noqa: F821
        """
        Generate content for a reference file.
        
        Args:
            ref: ReferenceSpec defining the reference requirements
            
        Returns:
            Markdown content string for the reference file
        """
        source_text = self._get_source_text()
        
        if not source_text:
            return f"\n*无可用的源内容来生成 {ref.filename}*\n"
        
        truncated_source = source_text[:self.max_source_chars]
        
        # Handle workflow-assistant mode: create task entry and return placeholder
        if self.generation_mode == GenerationMode.WORKFLOW_ASSISTANT:
            task_id = f"ref-{len(self._pending_tasks) + 1:03d}"
            sources = ", ".join(ref.content_sources) if ref.content_sources else "原始材料"
            task = ContentTask(
                id=task_id,
                type="reference",
                title=ref.filename,
                purpose=ref.purpose or "生成参考文档",
                expected_content=[],
                target_path=f"references/{ref.filename}",
                source_excerpt=truncated_source[:2000],
                instructions=f"根据 {sources} 生成参考文档 {ref.filename}"
            )
            self._pending_tasks.append(task)
            return f"<!-- TASK:{task_id} -->\n*[待 AI 助手生成: {ref.filename}]*\n"
        
        # API mode: use LLM
        if self.use_llm:
            llm_content = self._generate_reference_with_llm(ref, truncated_source)
            if llm_content:
                return llm_content
        
        # Fallback: include raw source excerpt
        return self._extract_reference_fallback(ref, truncated_source)
    
    def _generate_with_llm(self, section: "SectionSpec", source_text: str) -> Optional[str]:
        """Generate section content using Claude API."""
        try:
            import anthropic
        except ImportError:
            logger.warning("anthropic package not installed. Use 'pip install anthropic'.")
            return None
        
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return None
        
        # Build expected content list
        expected_list = "\n".join(f"- {item}" for item in (section.expected_content or []))
        if not expected_list:
            expected_list = "- 相关内容"
        
        prompt = self.SECTION_PROMPT.format(
            title=section.title.lstrip("#").strip(),
            purpose=section.purpose or "提供相关内容",
            expected_list=expected_list,
            source_text=source_text,
        )
        
        try:
            client = anthropic.Anthropic(api_key=api_key)
            
            logger.info(f"🤖 Generating content for: {section.title}")
            
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}],
            )
            
            content = message.content[0].text
            logger.info(f"✅ Generated {len(content)} chars for {section.title}")
            return content
            
        except Exception as e:
            logger.error(f"Claude API error for section '{section.title}': {e}")
            return None
    
    def _generate_reference_with_llm(self, ref: "ReferenceSpec", source_text: str) -> Optional[str]:
        """Generate reference file content using Claude API."""
        try:
            import anthropic
        except ImportError:
            return None
        
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return None
        
        sources = ", ".join(ref.content_sources) if ref.content_sources else "原始材料"
        
        prompt = self.REFERENCE_PROMPT.format(
            filename=ref.filename,
            purpose=ref.purpose or "参考文档",
            sources=sources,
            source_text=source_text,
        )
        
        try:
            client = anthropic.Anthropic(api_key=api_key)
            
            logger.info(f"🤖 Generating reference: {ref.filename}")
            
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}],
            )
            
            content = message.content[0].text
            logger.info(f"✅ Generated {len(content)} chars for {ref.filename}")
            return content
            
        except Exception as e:
            logger.error(f"Claude API error for reference '{ref.filename}': {e}")
            return None
    
    def _extract_fallback_content(self, section: "SectionSpec", source_text: str) -> str:
        """
        Extract content using deterministic rules when LLM unavailable.
        
        Strategy based on section title/purpose:
        - 摘要/Overview: First N characters
        - 要点/Key: Extract bullet-style points
        - 概念: Extract definition-like content
        - 练习/Exercises: Mark as requiring LLM
        - 延伸学习/Extended: Mark as requiring LLM
        """
        title_lower = section.title.lower()
        purpose_lower = (section.purpose or "").lower()
        combined = title_lower + " " + purpose_lower
        
        # Summary/Overview sections: use first portion
        if any(kw in combined for kw in ["摘要", "overview", "概述", "简介", "summary"]):
            return self._extract_summary(source_text, max_chars=1000)
        
        # Key points sections: extract bullet points or paragraphs
        if any(kw in combined for kw in ["要点", "key", "关键", "重点", "point"]):
            return self._extract_key_points(source_text)
        
        # Concept sections: extract definitions
        if any(kw in combined for kw in ["概念", "concept", "定义", "详解"]):
            return self._extract_concepts(source_text)
        
        # Exercise sections: cannot generate without LLM
        if any(kw in combined for kw in ["练习", "exercise", "实践", "practice"]):
            return self._generate_exercise_placeholder()
        
        # Extended learning sections: also require LLM
        if any(kw in combined for kw in ["延伸", "extended", "进阶", "further", "resources"]):
            return self._generate_extended_learning_placeholder()
        
        # Default: use summary extraction
        return self._extract_summary(source_text, max_chars=800)
    
    def _extract_summary(self, text: str, max_chars: int = 1000) -> str:
        """Extract first N characters as summary, breaking at sentence."""
        if not text:
            return "*内容待填充*\n"
        
        # Find good break point (sentence end)
        excerpt = text[:max_chars]
        last_period = max(
            excerpt.rfind("。"),
            excerpt.rfind("."),
            excerpt.rfind("！"),
            excerpt.rfind("？"),
        )
        
        if last_period > max_chars // 2:
            excerpt = excerpt[:last_period + 1]
        
        return f"{excerpt.strip()}\n\n*[内容摘自原始材料]*\n"
    
    def _extract_key_points(self, text: str) -> str:
        """Extract key points from text."""
        if not text:
            return "*内容待填充*\n"
        
        lines = text.split("\n")
        key_points = []
        
        # Look for timestamped sections or numbered items
        timestamp_pattern = re.compile(r"^\d{2}:\d{2}")
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Skip timestamps themselves
            if timestamp_pattern.match(line):
                continue
            
            # Include lines that look like key points
            if len(line) > 20 and len(line) < 200:
                if any(kw in line for kw in ["分别是", "包含", "重要", "关键", "核心", "需要"]):
                    key_points.append(f"- {line}")
                    if len(key_points) >= 10:
                        break
        
        if key_points:
            return "\n".join(key_points) + "\n\n*[要点提取自原始材料，建议使用 LLM 增强]*\n"
        
        # Fallback: first few sentences
        return self._extract_summary(text, max_chars=600)
    
    def _extract_concepts(self, text: str) -> str:
        """Extract concept definitions from text."""
        if not text:
            return "*内容待填充*\n"
        
        # Look for definition patterns
        concepts = []
        sentences = re.split(r"[。！？]", text)
        
        for sent in sentences:
            sent = sent.strip()
            if not sent:
                continue
            
            # Look for definition-like patterns
            if any(kw in sent for kw in ["就是", "是指", "意味着", "定义", "概念"]):
                concepts.append(f"- {sent}")
                if len(concepts) >= 5:
                    break
        
        if concepts:
            return "\n".join(concepts) + "\n\n*[概念提取自原始材料]*\n"
        
        return self._extract_summary(text, max_chars=800)
    
    def _extract_reference_fallback(self, ref: "ReferenceSpec", source_text: str) -> str:
        """Generate fallback content for reference file."""
        # Include relevant excerpt based on reference purpose
        max_chars = min(self.max_source_chars, 5000)
        excerpt = source_text[:max_chars]
        
        if len(source_text) > max_chars:
            excerpt += "\n\n...[完整内容请参考原始材料]..."
        
        return f"""## 内容

{excerpt}

---
*此参考文档由确定性提取生成，建议使用 LLM 增强以获得更好的结构化内容。*
"""
    
    def _generate_exercise_placeholder(self) -> str:
        """Generate placeholder for exercise section (requires LLM)."""
        return """*[练习题需要 LLM 生成]*

请设置 `ANTHROPIC_API_KEY` 环境变量并重新运行 `apply-spec` 命令，
或使用 `skill-seekers apply-spec <spec.yaml>` 生成完整练习题。

**建议的练习方向**：
- 根据课程内容设计实践任务
- 设计理解检测题
- 设计应用场景题
"""
    
    def _generate_extended_learning_placeholder(self) -> str:
        """Generate placeholder for extended learning section (requires LLM)."""
        return """*[延伸学习内容需要 LLM 生成]*

请设置 `ANTHROPIC_API_KEY` 环境变量以生成个性化学习建议，
或手动添加相关学习资源。

**可考虑的延伸方向**：
- 相关课程或书籍推荐
- 进阶话题探索
- 实践项目建议
"""
    
    def _generate_empty_placeholder(self, section: "SectionSpec") -> str:
        """Generate placeholder when no source content available."""
        return f"*[{section.title.lstrip('#').strip()}：无可用源内容]*\n"
