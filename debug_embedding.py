
import os
import asyncio
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings

load_dotenv(".env")

async def test_embeddings():
    print("Initializing Embeddings...")
    model_name = os.getenv("OPENAI_EMBEDDINGS_MODEL")
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    
    print(f"Model: {model_name}")
    print(f"Base URL: {base_url}")

    embeddings = OpenAIEmbeddings(
        model=model_name,
        openai_api_key=api_key,
        openai_api_base=base_url
    )

    tests = [
        ("Single string", "hello"),
        ("List of strings", ["hello", "world"]),
        ("List with empty string", ["hello", ""]),
        ("List with None (simulated as empty string)", [""]),
        ("Empty list", [])
    ]

    for name, input_data in tests:
        print(f"\nTesting: {name}")
        print(f"Input: {input_data}")
        try:
            if isinstance(input_data, str):
                res = await embeddings.aembed_query(input_data)
            else:
                res = await embeddings.aembed_documents(input_data)
            print("SUCCESS")
        except Exception as e:
            print(f"FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(test_embeddings())
