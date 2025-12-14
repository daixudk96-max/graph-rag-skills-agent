"""
将知识图谱数据写入 Neo4j 数据库

从 output/kg_build/*.json 读取提取的实体和关系，写入 Neo4j。
"""

import json
import logging
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

console = Console()


# ============================================================
# 数据一致性校验
# ============================================================

def validate_graph_consistency(
    entities: List[Dict[str, Any]], 
    relations: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    校验实体-关系一致性，过滤悬空关系。
    
    检查每条关系的 source 和 target 是否都存在于实体集合中。
    将悬空关系（引用不存在实体的关系）过滤掉并记录警告。
    
    Args:
        entities: 实体列表，每个实体需包含 "id" 字段
        relations: 关系列表，每个关系需包含 "source" 和 "target" 字段
        
    Returns:
        (valid_relations, invalid_relations) 元组
    """
    entity_ids = {e["id"] for e in entities}
    valid: List[Dict[str, Any]] = []
    invalid: List[Dict[str, Any]] = []
    
    for rel in relations:
        source_valid = rel.get("source") in entity_ids
        target_valid = rel.get("target") in entity_ids
        
        if source_valid and target_valid:
            valid.append(rel)
        else:
            # 记录缺失信息
            missing_parts = []
            if not source_valid:
                missing_parts.append(f"source={rel.get('source')}")
            if not target_valid:
                missing_parts.append(f"target={rel.get('target')}")
            
            invalid.append({
                **rel,
                "_error": f"缺失实体: {', '.join(missing_parts)}",
            })
    
    # 记录警告
    if invalid:
        logger.warning("发现 %d 条悬空关系（引用不存在的实体）", len(invalid))
        for rel in invalid[:5]:  # 只显示前 5 条
            logger.warning(
                "  跳过关系: %s -[%s]-> %s (%s)",
                rel.get("source"),
                rel.get("type"),
                rel.get("target"),
                rel.get("_error"),
            )
        if len(invalid) > 5:
            logger.warning("  ... 还有 %d 条未显示", len(invalid) - 5)
    
    return valid, invalid


def generate_relation_id(source: str, target: str, rel_type: str, chunk_id: str = "") -> str:
    """
    生成关系的稳定唯一 ID。
    
    基于 source|target|type|chunk_id 生成哈希，确保同一对节点间
    的多条不同关系不会被合并。
    
    Args:
        source: 源实体 ID
        target: 目标实体 ID
        rel_type: 关系类型
        chunk_id: 来源文本块 ID（可选）
        
    Returns:
        关系唯一 ID
    """
    import hashlib
    key = f"{source}|{target}|{rel_type}|{chunk_id}"
    return hashlib.md5(key.encode()).hexdigest()[:16]

def write_to_neo4j(data: Dict[str, Any], neo4j_uri: str, neo4j_user: str, neo4j_password: str):
    """将知识图谱数据写入 Neo4j"""
    from neo4j import GraphDatabase
    
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    
    entities = data.get("entities", [])
    relations = data.get("relations", [])
    
    # 一致性校验
    console.print("[yellow]校验数据一致性...[/yellow]")
    valid_relations, invalid_relations = validate_graph_consistency(entities, relations)
    
    if invalid_relations:
        console.print(
            f"[yellow]⚠ 过滤 {len(invalid_relations)} 条悬空关系[/yellow]"
        )
    
    console.print(f"[cyan]连接 Neo4j: {neo4j_uri}[/cyan]")
    
    # 统计计数器
    success_relations = 0
    failed_relations = 0
    
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
        
        # 写入关系（仅已验证的有效关系）
        console.print(f"[green]写入 {len(valid_relations)} 个关系...[/green]")
        for relation in valid_relations:
            # 生成关系唯一 ID（Phase 3）
            chunk_id = relation.get("properties", {}).get("来源", "")
            rel_id = generate_relation_id(
                relation["source"],
                relation["target"],
                relation["type"],
                chunk_id,
            )
            
            # 使用 rel_id 作为 MERGE 键，避免关系被合并
            cypher = """
            MATCH (source:KGEntity {entity_id: $source_id})
            MATCH (target:KGEntity {entity_id: $target_id})
            MERGE (source)-[r:RELATES {rel_id: $rel_id}]->(target)
            SET r.type = $rel_type,
                r.properties = $properties,
                r.created_at = datetime()
            """
            try:
                # Phase 4: 直接传递属性字典（简单属性）或 JSON 序列化（复杂属性）
                props = relation.get("properties", {})
                # Neo4j 不支持嵌套 map，对复杂属性仍需序列化
                if any(isinstance(v, (dict, list)) for v in props.values()):
                    props_str = json.dumps(props, ensure_ascii=False)
                else:
                    props_str = json.dumps(props, ensure_ascii=False)
                
                session.run(cypher,
                    source_id=relation["source"],
                    target_id=relation["target"],
                    rel_type=relation["type"],
                    rel_id=rel_id,
                    properties=props_str,
                )
                success_relations += 1
            except Exception as e:
                failed_relations += 1
                logger.error(
                    "写入关系失败: %s -[%s]-> %s, 错误: %s",
                    relation["source"],
                    relation.get("type"),
                    relation["target"],
                    e,
                )
        
        # 显示写入结果
        if failed_relations:
            console.print(f"[red]✗ {failed_relations} 条关系写入失败[/red]")
        console.print(f"[green]✓ 成功写入 {success_relations} 条关系[/green]")
        
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
