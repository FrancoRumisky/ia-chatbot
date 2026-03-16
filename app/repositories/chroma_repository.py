import chromadb
from chromadb.config import Settings

from typing import List, Dict, Any


class ChromaRepository:
    def __init__(self, db_path: str, collection_name: str):
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(name=collection_name)

    def add(
        self,
        ids: List[str],
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]],
    ) -> None:
        self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def query(self, **kwargs) -> Dict[str, Any]:
        return self.collection.query(**kwargs)

    def list_documents(self, limit: int = 100) -> List[Dict[str, str]]:
        """Lista documentos únicos presentes en la colección."""
        result = self.collection.get(limit=limit, include=["metadatas"])

        metadatas = result.get("metadatas", [])

        # Normalizar a lista de metadatos (cada elemento corresponde a un registro)
        if metadatas and isinstance(metadatas[0], list):
            # Chroma puede devolver [[...]] estructura
            metadatas = metadatas[0]

        documents = {}
        for meta in metadatas:
            if not isinstance(meta, dict):
                continue
            doc_id = meta.get("documentId") or meta.get("document_id")
            doc_name = meta.get("documentName") or meta.get("document_name")
            if doc_id and doc_id not in documents:
                documents[doc_id] = doc_name or doc_id

        return [{"id": did, "name": name} for did, name in documents.items()]
