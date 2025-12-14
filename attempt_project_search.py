
import os
import sys
import asyncio
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加项目根目录到路径
sys.path.append(os.getcwd())

try:
    from graphrag_agent.models.get_models import get_llm, get_embeddings
    from graphrag_agent.search.local_search import LocalSearch
    from langchain_core.messages import HumanMessage
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

def test_local_search():
    print("Initializing Models...")
    try:
        llm = get_llm("gpt-3.5-turbo") # 使用一个便宜的模型或者默认的
        embeddings = get_embeddings()
    except Exception as e:
        print(f"Failed to initialize models: {e}")
        return

    print("Initializing LocalSearch...")
    try:
        # 实例化 LocalSearch
        searcher = LocalSearch(llm=llm, embeddings=embeddings)
        
        query = "国家奖学金的要求是什么？"
        print(f"Running query: {query}")
        
        # 尝试查询
        # 注意：这可能会因为缺少向量索引而失败或返回空
        result = searcher.search(query)
        
        print("\n=== Search Result ===")
        print(result)
        print("=====================")
        
    except Exception as e:
        print(f"\n❌ Search failed as expected (likely due to missing indices): {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_local_search()
