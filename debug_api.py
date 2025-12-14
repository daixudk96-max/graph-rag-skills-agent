
import os
from openai import OpenAI
from dotenv import load_dotenv

# Load .env explicitly
load_dotenv(".env")

api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_BASE_URL")
model = os.getenv("OPENAI_LLM_MODEL", "qwen-flash")

print(f"Loaded config:")
print(f"API Key: {api_key[:8]}...{api_key[-4:] if api_key else 'None'}")
print(f"Base URL: {base_url}")
print(f"Model: {model}")

if not api_key:
    print("Error: OPENAI_API_KEY is empty!")
    exit(1)

client = OpenAI(api_key=api_key, base_url=base_url)

try:
    print("\nAttempting to call API...")
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Hello, are you working?"}],
        max_tokens=10
    )
    print("Success! Response:")
    print(response.choices[0].message.content)

    print("\nAttempting to call Embeddings...")
    embedding_model = os.getenv("OPENAI_EMBEDDINGS_MODEL", "text-embedding-v1")
    print(f"Embedding Model: {embedding_model}")
    emb_response = client.embeddings.create(
        model=embedding_model,
        input="Hello embedding"
    )
    print("Success! Embedding generated.")
    print(f"Dimension: {len(emb_response.data[0].embedding)}")

    print("\nAttempting to call Embeddings with LIST input...")
    try:
        emb_response_list = client.embeddings.create(
            model=embedding_model,
            input=["Hello list 1", "Hello list 2"]
        )
        print("Success! List Embedding generated.")
    except Exception as e_list:
        print(f"List Input Failed: {e_list}")

except Exception as e:
    print(f"\nAPI Call Failed: {e}")
