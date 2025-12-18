"""
Dynamic Template Mechanism for Skill Seekers.

This module provides template-based content structuring for variable
transcript formats and content types.
"""

from .template_registry import TemplateRegistry, Template, TemplateInfo
from .template_filler import TemplateFiller, FilledContent, ValidationError
from .template_migrator import TemplateMigrator, MigrationReport
from .template_embedder import TemplateEmbedder

__all__ = [
    "TemplateRegistry",
    "Template",
    "TemplateInfo",
    "TemplateFiller",
    "FilledContent",
    "ValidationError",
    "TemplateMigrator",
    "MigrationReport",
    "TemplateEmbedder",
]
