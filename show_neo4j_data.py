"""查看 Neo4j 中的所有数据"""
from neo4j import GraphDatabase
import warnings
warnings.filterwarnings('ignore')

driver = GraphDatabase.driver('neo4j://localhost:7687', auth=('neo4j', '12345678'))

with driver.session() as session:
    print("=" * 50)
    print("Neo4j 数据库内容")
    print("=" * 50)
    
    # 1. 所有节点标签
    print("\n1. 所有节点标签:")
    result = session.run("CALL db.labels() YIELD label RETURN label")
    labels = [r["label"] for r in result]
    for label in labels:
        count_result = session.run(f"MATCH (n:`{label}`) RETURN count(n) as cnt")
        cnt = count_result.single()["cnt"]
        print(f"   - {label}: {cnt} 个节点")
    
    # 2. KGEntity 节点详情
    print("\n2. KGEntity 节点:")
    result = session.run("MATCH (n:KGEntity) RETURN n.entity_id, n.name, n.type ORDER BY n.type")
    for r in result:
        print(f"   - [{r['n.type']}] {r['n.name']}")
    
    # 3. 关系
    print("\n3. 关系:")
    result = session.run("MATCH (a:KGEntity)-[r:RELATES]->(b:KGEntity) RETURN a.name, r.type, b.name LIMIT 10")
    for r in result:
        print(f"   {r['a.name']} --[{r['r.type']}]--> {r['b.name']}")
    
    print("\n" + "=" * 50)
    print("查看完整图谱请访问: http://localhost:7474")
    print("Cypher: MATCH (n:KGEntity)-[r]->(m) RETURN n,r,m")
    print("=" * 50)

driver.close()
