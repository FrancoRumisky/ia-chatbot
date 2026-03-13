import os
import re
import time
import uuid
from typing import Any, Dict, List

import chromadb
import ollama
from pypdf import PdfReader

from app.services.embedding_service import EmbeddingService
from app.services.retrieval_service import RetrievalService


class RagService:
    def __init__(self, settings) -> None:
        self.config = settings
        self.collection_name = settings.rag_collection_name
        self.chat_model = settings.chat_model
        self.system_prompt = settings.system_prompt

        self.embedding_service = EmbeddingService(settings.embedding_model)

        self.retrieval_service = RetrievalService(settings)

        self.chroma_client = chromadb.PersistentClient(path=settings.chroma_db_path)
        self.collection = self.chroma_client.get_or_create_collection(
            name=self.collection_name
        )

    def _clean_text(self, text: str) -> str:
        text = text.replace("\r", "\n")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" +\n", "\n", text)
        text = re.sub(r"\n +", "\n", text)
        text = re.sub(r'(\d)\s+(\d)', r'\1\2', text)  # Merge digits separated by spaces
        return text.strip()

    def _split_into_paragraphs(self, text: str) -> List[str]:
        raw_paragraphs = text.split("\n\n")
        paragraphs: List[str] = []

        for paragraph in raw_paragraphs:
            cleaned = paragraph.strip()
            if len(cleaned) >= 25:
                paragraphs.append(cleaned)

        return paragraphs

    def _chunk_paragraphs(
        self,
        paragraphs: List[str],
        max_chunk_length: int = 900,
        overlap_paragraphs: int = 1
    ) -> List[str]:
        if not paragraphs:
            return []

        chunks: List[str] = []
        current_chunk: List[str] = []
        current_length = 0

        for paragraph in paragraphs:
            paragraph_length = len(paragraph)

            if current_chunk and current_length + paragraph_length > max_chunk_length:
                chunks.append("\n\n".join(current_chunk))

                overlap = current_chunk[-overlap_paragraphs:] if overlap_paragraphs > 0 else []
                current_chunk = overlap.copy()
                current_length = sum(len(p) for p in current_chunk)

            current_chunk.append(paragraph)
            current_length += paragraph_length

        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        return chunks

    def _extract_pages(self, pdf_path: str) -> List[Dict[str, Any]]:
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"No se encontró el PDF en: {pdf_path}")

        reader = PdfReader(pdf_path)
        pages_output: List[Dict[str, Any]] = []

        for page_index, page in enumerate(reader.pages):
            raw_text = page.extract_text() or ""
            cleaned_text = self._clean_text(raw_text)

            if not cleaned_text.strip():
                continue

            paragraphs = self._split_into_paragraphs(cleaned_text)
            chunks = self._chunk_paragraphs(paragraphs)

            for chunk_index, chunk in enumerate(chunks):
                pages_output.append(
                    {
                        "page_number": page_index + 1,
                        "chunk_index_in_page": chunk_index,
                        "text": chunk
                    }
                )

        return pages_output

    def ingest_pdf(self, pdf_path: str) -> Dict[str, Any]:
        chunk_entries = self._extract_pages(pdf_path)

        if not chunk_entries:
            raise ValueError("No se pudo extraer texto útil del PDF.")

        filename = os.path.basename(pdf_path)
        document_id = os.path.splitext(filename)[0]

        # Determinar source_type basado en el path
        if "knowledge_base/docs" in pdf_path:
            source_type = "docs"
        elif "knowledge_base/faq" in pdf_path:
            source_type = "faq"
        elif "knowledge_base/structured" in pdf_path:
            source_type = "structured"
        else:
            source_type = "data"  # para compatibilidad con data/

        ingested_at = int(time.time())

        ids: List[str] = []
        documents: List[str] = []
        embeddings: List[List[float]] = []
        metadatas: List[Dict[str, Any]] = []

        for global_index, entry in enumerate(chunk_entries):
            chunk_text = entry["text"]
            page_number = entry["page_number"]
            chunk_index_in_page = entry["chunk_index_in_page"]

            ids.append(str(uuid.uuid4()))
            documents.append(chunk_text)
            embeddings.append(self.embedding_service.get_embedding(chunk_text))
            metadatas.append(
                {
                    "source": pdf_path,
                    "documentId": document_id,
                    "documentName": filename,
                    "sourceType": source_type,
                    "filename": filename,
                    "pageNumber": page_number,
                    "chunkIndex": global_index,
                    "chunkIndexInPage": chunk_index_in_page,
                    "chunkPreview": chunk_text[:180],
                    "ingestedAt": ingested_at
                }
            )

        self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )

        return {
            "message": "PDF ingerido correctamente",
            "chunks_added": len(documents),
            "source": pdf_path,
            "document_id": document_id
        }

    def _tokenize_for_keyword_score(self, text: str) -> List[str]:
        return re.findall(r"\w+", text.lower(), flags=re.UNICODE)

    def _keyword_overlap_score(self, query: str, document: str) -> int:
        query_tokens = set(self._tokenize_for_keyword_score(query))
        document_tokens = set(self._tokenize_for_keyword_score(document))
        return len(query_tokens.intersection(document_tokens))

    def search(
        self,
        query: str,
        document_ids: List[str],
        n_results: int = 8
    ) -> List[Dict[str, Any]]:
        query_embedding = self.embedding_service.get_embedding(query)

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where={
                "documentId": {
                    "$in": document_ids
                }
            },
            include=["documents", "metadatas", "distances"]
        )

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        output: List[Dict[str, Any]] = []

        for document, metadata, distance in zip(documents, metadatas, distances):
            keyword_score = self._keyword_overlap_score(query, document)

            output.append(
                {
                    "document": document,
                    "metadata": metadata,
                    "distance": distance,
                    "keyword_score": keyword_score
                }
            )

        output.sort(
            key=lambda item: (-item["keyword_score"], item["distance"])
        )

        return output

    def has_reliable_context(
        self,
        results: List[Dict[str, Any]],
        max_distance: float = 1.7,
        min_keyword_score: int = 1
    ) -> bool:
        if not results:
            return False

        best = results[0]

        if best["distance"] <= max_distance:
            return True

        return False

    def build_context(
        self,
        query: str,
        document_ids: List[str],
        n_results: int = 10
    ) -> str:
        results = self.search(
            query=query,
            document_ids=document_ids,
            n_results=n_results
        )

        if not results:
            return "NO_CONTEXT"

        if not self.has_reliable_context(results):
            return "NO_CONTEXT"

        context_parts: List[str] = []

        for item in results[:10]:
            metadata = item["metadata"] or {}
            print(f"Metadata: {metadata}")  # Debug
            filename = metadata.get("filename", "documento_desconocido")
            page_number = metadata.get("pageNumber", "?")
            chunk_index = metadata.get("chunkIndex", "?")
            document = item["document"]
            distance = item["distance"]
            keyword_score = item["keyword_score"]

            context_parts.append(
                (
                    f"[Fuente: {filename} | Página: {page_number} | Chunk: {chunk_index} "
                    f"| Distancia: {distance:.4f} | KeywordScore: {keyword_score}]\n"
                    f"{document}"
                )
            )

        return "\n\n".join(context_parts)

    def is_context_useful(self, context: str) -> bool:
        if context == "NO_CONTEXT":
            return False
        if len(context.strip()) < 50:  # Too short to be useful
            return False
        return True

    def build_context(
        self,
        query: str,
        document_ids: List[str],
        n_results: int = 10,
        source_types: List[str] = None
    ) -> str:
        return self.retrieval_service.build_context(query, document_ids, n_results, source_types)

    def chat(self, messages: List[Dict[str, str]]) -> str:
        response = ollama.chat(
            model=self.chat_model,
            messages=messages
        )
        return response["message"]["content"]

    def chat_stream(self, messages: List[Dict[str, str]]):
        return ollama.chat(
            model=self.chat_model,
            messages=messages,
            stream=True
        )