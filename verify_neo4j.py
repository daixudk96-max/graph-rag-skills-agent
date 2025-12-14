"""验证 Neo4j 中的知识图谱数据"""
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv
load_dotenv()

uri = os.getenv('NEO4J_URI', 'neo4j://localhost:7687')
user = os.getenv('NEO4J_USERNAME', 'neo4j')
password = os.getenv('NEO4J_PASSWORD', '12345678')

driver = GraphDatabase.driver(uri, auth=(user, password))
with driver.session() as session:
    # 统计节点
    result = session.run('MATCH (n:KGEntity) RETURN count(n) as count')
    node_count = result.single()['count']
    print(f'节点数: {node_count}')
    
    # 统计关系
    result = session.run('MATCH ()-[r:RELATES]->() RETURN count(r) as count')
    rel_count = result.single()['count']
    print(f'关系数: {rel_count}')
    
    # 显示部分实体
    print('\n实体示例:')
    result = session.run('MATCH (n:KGEntity) RETURN n.name as name, n.type as type LIMIT 10')
    for record in result:
        print(f'  - {record["name"]} ({record["type"]})')
    
driver.close()
print('\n验证完成!')
