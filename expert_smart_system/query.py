import os
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def search(question, model, client, top_k=5):
    vector = model.encode(f"query: {question}").tolist()
    # qdrant-client 1.7+ uses query_points instead of search
    try:
        response = client.query_points(
            collection_name='egypt_estate',
            query=vector,
            limit=top_k,
            with_payload=True,
        )
        hits = response.points
    except Exception:
        hits = client.search(collection_name='egypt_estate', query_vector=vector, limit=top_k)
    return [h.payload for h in hits]


def build_prompt(question, results):
    lines = [
        f"- {r['loc']}: {r['pr']:,} جنيه | {r['ar']} م²  "
        f"({r['pr'] // r['ar']:,} جنيه/م²)"
        for r in results
    ]
    context = "\n".join(lines)
    return (
        f"أنت خبير عقاري متخصص في السوق المصري.\n"
        f"استخدم البيانات التالية فقط للإجابة بدقة.\n\n"
        f"البيانات:\n{context}\n\n"
        f"السؤال: {question}\n"
        f"الإجابة:"
    )


def ask_llm(prompt):
    # --- Option A: Ollama (local, free) ---
    try:
        import ollama
        response = ollama.chat(
            model='qwen2.5:7b',
            messages=[{'role': 'user', 'content': prompt}]
        )
        return response['message']['content']
    except Exception:
        pass

    # --- Option B: Claude API (set ANTHROPIC_API_KEY env var) ---
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if api_key:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model='claude-sonnet-4-6',
            max_tokens=1024,
            messages=[{'role': 'user', 'content': prompt}]
        )
        return response.content[0].text

    # --- Fallback: print raw results ---
    return f"(لا يوجد LLM متاح)\n\n{prompt}"


def main():
    print("جارٍ تحميل النموذج...")
    model = SentenceTransformer('intfloat/multilingual-e5-large')
    client = QdrantClient(path=os.path.join(BASE_DIR, 'vector_db'))
    print("النظام جاهز. اكتب سؤالك أو 'exit' للخروج.\n")

    while True:
        question = input("السؤال: ").strip()
        if not question or question.lower() == 'exit':
            break
        results = search(question, model, client)
        prompt = build_prompt(question, results)
        answer = ask_llm(prompt)
        print(f"\n{answer}\n{'─' * 50}\n")


if __name__ == '__main__':
    main()
