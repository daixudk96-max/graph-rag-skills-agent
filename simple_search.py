
"""
Simple Knowledge Graph Search Tool
用于验证 Neo4j 数据库中的数据是否可检索。
"""
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

# 加载环境变量
load_dotenv()

URI = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
PASSWORD = os.getenv("NEO4J_PASSWORD", "12345678")

def simple_search(keyword):
    print(f"\n🔍 Searching for keyword: '{keyword}'...")
    
    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
    
    query = """
    MATCH (n:KGEntity)
    WHERE toLower(n.name) CONTAINS toLower($keyword) 
       OR toLower(n.description) CONTAINS toLower($keyword)
    RETURN n.name as name, n.type as type, n.description as description, elementId(n) as id
    LIMIT 5
    """
    
    rel_query = """
    MATCH (n:KGEntity)-[r]->(m:KGEntity)
    WHERE toLower(n.name) CONTAINS toLower($keyword)
    RETURN n.name as source, type(r) as rel_type, m.name as target
    LIMIT 10
    """
    
    try:
        with driver.session() as session:
            # 1. Search Entities
            print("\n[Entities Found]")
            result = session.run(query, keyword=keyword)
            nodes = list(result)
            if not nodes:
                print("  No entities found.")
            for record in nodes:
                print(f"  - [{record['type']}] {record['name']}")
            
            # 2. Search Relations
            print("\n[Related Information]")
            result = session.run(rel_query, keyword=keyword)
            rels = list(result)
            if not rels:
                print("  No relationships found for these entities.")
            for record in rels:
                print(f"  - {record['source']} --[{record['rel_type']}]--> {record['target']}")
                
    except Exception as e:
        print(f"Query failed: {e}")
    finally:
        driver.close()

if __name__ == "__main__":
    search_terms = ["奖学金", "华东理工"]
    for term in search_terms:
        simple_search(term)
