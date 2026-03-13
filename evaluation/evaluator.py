import json
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.services.rag_service import RagService

def main():
    rag_service = RagService(settings)
    
    with open('evaluation/dataset.json', 'r', encoding='utf-8') as f:
        dataset = json.load(f)
    
    total = len(dataset)
    passed = 0
    failed = 0
    
    for item in dataset:
        question = item['question']
        document_ids = item['document_ids']
        expected_keywords = item['expected_keywords']
        
        # Build context as in real chat
        context = rag_service.build_context(question, document_ids, n_results=10)
        
        # Build user prompt as in real chat
        user_prompt = f"""
        Contexto recuperado:
        {context}

        Pregunta del usuario:
        {question}
        """
        
        messages = [
            {"role": "system", "content": settings.system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # Get response
        response = rag_service.chat(messages)
        
        # Check if response contains any expected keyword (case insensitive)
        response_lower = response.lower()
        has_keyword = any(kw.lower() in response_lower for kw in expected_keywords)
        
        if has_keyword:
            passed += 1
            status = "PASS"
        else:
            failed += 1
            status = "FAIL"
        
        print(f"Question: {question}")
        print(f"Response: {response[:200]}...")  # Truncate for readability
        print(f"Expected keywords: {expected_keywords}")
        print(f"Status: {status}")
        print("-" * 50)
    
    print(f"Summary: Total={total}, Passed={passed}, Failed={failed}")

if __name__ == "__main__":
    main()