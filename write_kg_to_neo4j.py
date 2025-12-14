"""
将知识图谱数据写入 Neo4j 数据库

从 output/kg_build/*.json 读取提取的实体和关系，写入 Neo4j。
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

console = Console()

# ============================================================
# Neo4j 写入函数
# ============================================================

def write_to_neo4j(data: Dict[str, Any], neo4j_uri: str, neo4j_user: str, neo4j_password: str):
    """将知识图谱数据写入 Neo4j"""
    from neo4j import GraphDatabase
    
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    
    entities = data.get("entities", [])
    relations = data.get("relations", [])
    
    console.print(f"[cyan]连接 Neo4j: {neo4j_uri}[/cyan]")
    
    with driver.session() as session:
        # 清理旧数据（可选）
        console.print("[yellow]清理旧的知识图谱节点...[/yellow]")
        session.run("MATCH (n:KGEntity) DETACH DELETE n")
        
        # 创建约束和索引
        console.print("[yellow]创建索引...[/yellow]")
        try:
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (n:KGEntity) REQUIRE n.entity_id IS UNIQUE")
        except Exception as e:
            console.print(f"[dim]索引可能已存在: {e}[/dim]")
        
        # 写入实体
        console.print(f"[green]写入 {len(entities)} 个实体...[/green]")
        for entity in entities:
            cypher = """
            MERGE (n:KGEntity {entity_id: $entity_id})
            SET n.name = $name,
                n.type = $type,
                n.properties = $properties,
                n.created_at = datetime()
            """
            session.run(cypher, 
                entity_id=entity["id"],
                name=entity["name"],
                type=entity["type"],
                properties=json.dumps(entity.get("properties", {}), ensure_ascii=False)
            )
        
        # 写入关系
        console.print(f"[green]写入 {len(relations)} 个关系...[/green]")
        for relation in relations:
            cypher = """
            MATCH (source:KGEntity {entity_id: $source_id})
            MATCH (target:KGEntity {entity_id: $target_id})
            MERGE (source)-[r:RELATES {type: $rel_type}]->(target)
            SET r.properties = $properties,
                r.created_at = datetime()
            """
            try:
                session.run(cypher,
                    source_id=relation["source"],
                    target_id=relation["target"],
                    rel_type=relation["type"],
                    properties=json.dumps(relation.get("properties", {}), ensure_ascii=False)
                )
            except Exception as e:
                # 跳过无法创建的关系（源或目标节点不存在）
                pass
        
        # 统计结果
        result = session.run("MATCH (n:KGEntity) RETURN count(n) as node_count")
        node_count = result.single()["node_count"]
        
        result = session.run("MATCH ()-[r:RELATES]->() RETURN count(r) as rel_count")
        rel_count = result.single()["rel_count"]
        
        console.print(f"[green]✓ 写入完成: {node_count} 个节点, {rel_count} 个关系[/green]")
    
    driver.close()
    return node_count, rel_count


def main():
    """主函数"""
    console.print(Panel.fit(
        "[bold cyan]Neo4j 知识图谱写入[/bold cyan]",
        border_style="cyan"
    ))
    
    # 读取最新的知识图谱数据
    output_dir = project_root / "output" / "kg_build"
    json_files = list(output_dir.glob("*.json"))
    
    if not json_files:
        console.print("[red]未找到知识图谱数据文件！请先运行 build_kg_demo.py[/red]")
        return
    
    latest_file = max(json_files, key=lambda x: x.stat().st_mtime)
    console.print(f"[cyan]读取数据文件: {latest_file.name}[/cyan]")
    
    with open(latest_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # 显示数据统计
    stats = data.get("statistics", {})
    table = Table(title="数据统计")
    table.add_column("指标", style="cyan")
    table.add_column("数量", style="green")
    table.add_row("文档数", str(stats.get("documents", 0)))
    table.add_row("文本块", str(stats.get("chunks", 0)))
    table.add_row("实体数", str(stats.get("entities", 0)))
    table.add_row("关系数", str(stats.get("relations", 0)))
    console.print(table)
    
    # 读取 Neo4j 配置
    from dotenv import load_dotenv
    load_dotenv()
    
    neo4j_uri = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "12345678")
    
    console.print(f"\n[yellow]Neo4j 配置:[/yellow]")
    console.print(f"  URI: {neo4j_uri}")
    console.print(f"  User: {neo4j_user}")
    
    # 写入 Neo4j
    try:
        node_count, rel_count = write_to_neo4j(data, neo4j_uri, neo4j_user, neo4j_password)
        
        console.print(Panel.fit(
            f"[bold green]✓ 知识图谱写入成功！[/bold green]\n\n"
            f"节点数: {node_count}\n"
            f"关系数: {rel_count}\n\n"
            f"您可以在 Neo4j Browser (http://localhost:7474) 中查看图谱",
            border_style="green"
        ))
        
    except Exception as e:
        console.print(f"[red]写入失败: {e}[/red]")
        console.print("[yellow]请确保 Neo4j 数据库正在运行[/yellow]")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
