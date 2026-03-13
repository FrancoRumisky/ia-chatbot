from typing import List
import ollama


class EmbeddingService:
    def __init__(self, model: str):
        self.model = model

    def get_embedding(self, text: str) -> List[float]:
        text = text.lower()
        response = ollama.embed(
            model=self.model,
            input=text
        )
        return response["embeddings"][0]