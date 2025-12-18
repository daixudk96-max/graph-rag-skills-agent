"""
CLI commands for GraphRAG to Skill Seekers integration.

Provides command-line interface for exporting knowledge graph
content and managing sync state.
"""

import click
import json
from typing import Optional

from langchain_community.graphs import Neo4jGraph

from .config import ExportConfig
from .exporter import GraphRAGExporter
from .formatter import SkillInputFormatter
from .deduplicator import ContentDeduplicator
from .sync_manager import GraphRAGSkillSyncManager
from graphrag_agent.config.settings import (
    NEO4J_URI,
    NEO4J_USERNAME,
    NEO4J_PASSWORD,
)


def get_graph() -> Neo4jGraph:
    """Create Neo4j graph connection."""
    return Neo4jGraph(
        url=NEO4J_URI,
        username=NEO4J_USERNAME,
        password=NEO4J_PASSWORD,
    )


@click.group()
def skill_export():
    """GraphRAG to Skill Seekers export commands."""
    pass


@skill_export.command("export")
@click.option(
    "--output", "-o",
    default="skill_input.json",
    help="Output file path for the generated JSON"
)
@click.option(
    "--mode", "-m",
    type=click.Choice(["full", "delta"]),
    default="full",
    help="Export mode: 'full' for all content, 'delta' for changes only"
)
@click.option(
    "--level", "-l",
    type=int,
    default=0,
    help="Community level to export (0 = most granular)"
)
@click.option(
    "--include-chunks/--no-chunks",
    default=False,
    help="Include raw document chunks in export"
)
@click.option(
    "--dedup-threshold",
    type=float,
    default=0.85,
    help="Similarity threshold for entity deduplication (0.0-1.0)"
)
@click.option(
    "--max-communities",
    type=int,
    default=None,
    help="Maximum number of communities to export"
)
def export_command(
    output: str,
    mode: str,
    level: int,
    include_chunks: bool,
    dedup_threshold: float,
    max_communities: Optional[int],
):
    """
    Export GraphRAG knowledge graph for Skill Seekers.
    
    Generates a skill_input.json file compatible with Skill Seekers
    from the current knowledge graph content.
    
    Examples:
    
        # Full export at level 0
        graphrag-skill export --output skill_input.json
        
        # Delta export (only changes)
        graphrag-skill export --mode delta
        
        # Export with chunks included
        graphrag-skill export --include-chunks --level 1
    """
    click.echo(f"Starting {mode} export at level {level}...")
    
    try:
        # Create configuration
        config = ExportConfig(
            default_level=level,
            include_chunks=include_chunks,
            dedup_threshold=dedup_threshold,
            max_communities=max_communities,
            output_path=output,
        )
        
        # Connect to graph
        graph = get_graph()
        
        # Initialize components
        exporter = GraphRAGExporter(graph, config)
        deduplicator = ContentDeduplicator(dedup_threshold)
        formatter = SkillInputFormatter()
        sync_manager = GraphRAGSkillSyncManager(graph)
        
        # Get changed communities for delta mode
        changed_ids = None
        if mode == "delta":
            changed_ids = sync_manager.get_pending_updates(level)
            if not changed_ids:
                click.echo("No pending updates found. Use --mode full to export all.")
                return
            click.echo(f"Found {len(changed_ids)} communities with pending updates")
        
        # Export
        result = exporter.export(
            mode=mode,
            level=level,
            changed_community_ids=changed_ids,
        )
        
        # Check if export returned empty data (possible query failure)
        if not result.pages and not result.entities:
            click.echo("Warning: Export returned no data. Check Neo4j connection.", err=True)
        
        # Deduplicate entities
        result.entities, _ = deduplicator.deduplicate_entities(result.entities)
        
        # Deduplicate pages
        result.pages = deduplicator.deduplicate_pages(result.pages)
        
        # Get final report AFTER all deduplication (includes page duplicates)
        result.dedup_report = deduplicator.get_report()
        
        # Format and save
        output_path = formatter.save_to_file(result, output)
        
        # Update sync state
        community_ids = [
            p["metadata"]["community_id"] 
            for p in result.pages 
            if p.get("metadata", {}).get("community_id")
        ]
        sync_manager.mark_synced(community_ids, mode, level)
        
        # Report results
        dedup_report = result.dedup_report
        click.echo(f"\n[OK] Export complete!")
        click.echo(f"   Output: {output_path}")
        click.echo(f"   Pages: {result.page_count}")
        click.echo(f"   Entities: {result.entity_count}")
        if dedup_report.get("entities_removed", 0) > 0:
            click.echo(f"   Entities deduplicated: {dedup_report['entities_removed']}")
        if dedup_report.get("duplicate_content_count", 0) > 0:
            click.echo(f"   Duplicate pages found: {dedup_report['duplicate_content_count']}")
        
    except Exception as e:
        click.echo(f"[ERROR] Export failed: {e}", err=True)
        raise click.Abort()


@skill_export.command("status")
@click.option(
    "--level", "-l",
    type=int,
    default=0,
    help="Community level to check"
)
def status_command(level: int):
    """
    Show sync status and pending updates.
    
    Displays information about the last export and any
    communities that have changed since then.
    """
    try:
        graph = get_graph()
        sync_manager = GraphRAGSkillSyncManager(graph)
        
        # Get status
        status = sync_manager.get_status()
        
        click.echo("\n📊 Sync Status")
        click.echo("=" * 40)
        
        if status["has_previous_export"]:
            click.echo(f"Last export: {status['last_export_timestamp']}")
            click.echo(f"Export mode: {status['last_export_mode']}")
            click.echo(f"Export level: {status['last_export_level']}")
            click.echo(f"Communities exported: {status['exported_community_count']}")
            click.echo(f"Total exports: {status['export_count']}")
        else:
            click.echo("No previous export found.")
        
        # Get pending updates
        pending = sync_manager.get_pending_updates(level)
        
        click.echo(f"\n📝 Pending Updates (level {level})")
        click.echo("-" * 40)
        
        if pending:
            click.echo(f"Communities with changes: {len(pending)}")
            if len(pending) <= 10:
                for cid in pending:
                    click.echo(f"  - {cid}")
            else:
                for cid in pending[:5]:
                    click.echo(f"  - {cid}")
                click.echo(f"  ... and {len(pending) - 5} more")
        else:
            click.echo("No pending updates. Knowledge graph is in sync.")
        
    except Exception as e:
        click.echo(f"❌ Failed to get status: {e}", err=True)
        raise click.Abort()


@skill_export.command("reset")
@click.confirmation_option(
    prompt="This will reset sync state. Are you sure?"
)
def reset_command():
    """
    Reset sync state for fresh full export.
    
    Use this if you want to force a complete re-export
    of all knowledge graph content.
    """
    try:
        graph = get_graph()
        sync_manager = GraphRAGSkillSyncManager(graph)
        sync_manager.reset_state()
        
        click.echo("✅ Sync state reset. Next export will be a full export.")
        
    except Exception as e:
        click.echo(f"❌ Failed to reset state: {e}", err=True)
        raise click.Abort()


# For direct script execution
if __name__ == "__main__":
    skill_export()
