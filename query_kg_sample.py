"""
查询并展示 Neo4j 中的知识图谱数据样本
"""
from neo4j import GraphDatabase
import os
import json
from rich.console import Console
from rich.table import Table
from dotenv import load_dotenv

load_dotenv()

uri = os.getenv('NEO4J_URI', 'neo4j://localhost:7687')
user = os.getenv('NEO4J_USERNAME', 'neo4j')
password = os.getenv('NEO4J_PASSWORD', '12345678')

console = Console()

def query_sample():
    driver = GraphDatabase.driver(uri, auth=(user, password))
    session = driver.session()
    
    try:
        # 1. 总体统计
        console.print("\n[bold cyan]1. 总体统计:[/bold cyan]")
        result = session.run("MATCH (n:KGEntity) RETURN count(n) as node_count")
        node_count = result.single()["node_count"]
        
        result = session.run("MATCH ()-[r:RELATES]->() RETURN count(r) as rel_count")
        rel_count = result.single()["rel_count"]
        
        console.print(f"   节点总数 (KGEntity): [green]{node_count}[/green]")
        console.print(f"   关系总数 (RELATES):  [green]{rel_count}[/green]")
        
        if node_count == 0:
            console.print("[red]警告: 未找到任何 KGEntity 节点！请确认是否已运行写入脚本。[/red]")
            return

        # 2. 实体样本
        console.print("\n[bold cyan]2. 实体样本 (前 10 个):[/bold cyan]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("ID")
        table.add_column("名称 (Name)")
        table.add_column("类型 (Type)")
        
        result = session.run("MATCH (n:KGEntity) RETURN n.entity_id, n.name, n.type LIMIT 10")
        for record in result:
            table.add_row(
                str(record["n.entity_id"]), 
                str(record["n.name"]), 
                str(record["n.type"])
            )
        console.print(table)
        
        # 3. 关系样本
        console.print("\n[bold cyan]3. 关系样本 (前 10 个):[/bold cyan]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("源实体")
        table.add_column("关系类型")
        table.add_column("目标实体")
        
        result = session.run("""
            MATCH (a:KGEntity)-[r:RELATES]->(b:KGEntity) 
            RETURN a.name, r.type, b.name 
            LIMIT 10
        """)
        for record in result:
            table.add_row(
                str(record["a.name"]), 
                f"[yellow]{record['r.type']}[/yellow]", 
                str(record["b.name"])
            )
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]查询出错: {e}[/red]")
    finally:
        session.close()
        driver.close()

if __name__ == "__main__":
    query_sample()
