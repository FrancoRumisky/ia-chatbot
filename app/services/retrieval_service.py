from typing import Any, Dict, List

import chromadb
import re
import time

from app.services.embedding_service import EmbeddingService


class RetrievalService:
    def __init__(self, settings, metrics_service=None) -> None:
        self.config = settings
        self.collection_name = settings.rag_collection_name

        self.embedding_service = EmbeddingService(settings.embedding_model)
        self.metrics_service = metrics_service

        self.chroma_client = chromadb.PersistentClient(path=settings.chroma_db_path)
        self.collection = self.chroma_client.get_or_create_collection(
            name=self.collection_name
        )

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
        n_results: int = 8,
        source_types: List[str] = None  # Nuevo filtro opcional
    ) -> List[Dict[str, Any]]:
        start_time = time.time()
        try:
            query_embedding = self.embedding_service.get_embedding(query)

            # Construir filtros where
            where_conditions = {"documentId": {"$in": document_ids}}
            if source_types:
                where_conditions["sourceType"] = {"$in": source_types}

            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where_conditions,
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

            # Record metrics
            if self.metrics_service:
                duration = time.time() - start_time
                self.metrics_service.observe_histogram("vector_search_duration_seconds", duration)
                self.metrics_service.observe_histogram("search_results_count", len(output))

                if output:
                    avg_distance = sum(item["distance"] for item in output) / len(output)
                    self.metrics_service.set_gauge("search_avg_distance", avg_distance)

            return output
        except Exception as e:
            if self.metrics_service:
                self.metrics_service.increment_counter("search_errors_total")
            raise e

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
        n_results: int = 10,
        source_types: List[str] = None
    ) -> str:
        start_time = time.time()
        try:
            results = self.search(
                query=query,
                document_ids=document_ids,
                n_results=n_results,
                source_types=source_types
            )

            if not results:
                return "NO_CONTEXT"

            if not self.has_reliable_context(results):
                return "NO_CONTEXT"

            context_parts: List[str] = []

            for item in results[:10]:
                metadata = item["metadata"] or {}
                filename = metadata.get("documentName", "documento_desconocido")
                source_type = metadata.get("sourceType", "desconocido")
                page_number = metadata.get("pageNumber", "?")
                chunk_index = metadata.get("chunkIndex", "?")
                ingested_at = metadata.get("ingestedAt", None)
                document = item["document"]
                distance = item["distance"]
                keyword_score = item["keyword_score"]

                # Formato mejorado del contexto
                ingested_date = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ingested_at)) if ingested_at else "desconocido"

                context_parts.append(
                    (
                        f"[Fuente: {filename} | Tipo: {source_type} | Página: {page_number} | "
                        f"Chunk: {chunk_index} | Ingestado: {ingested_date} | "
                        f"Distancia: {distance:.4f} | KeywordScore: {keyword_score}]\n"
                        f"{document}"
                    )
                )

            # Record metrics
            if self.metrics_service:
                duration = time.time() - start_time
                self.metrics_service.observe_histogram("retrieval_duration_seconds", duration)

                has_context = len(context_parts) > 0
                self.metrics_service.record_response_type(has_context)

                if has_context:
                    quality_score = min(1.0, len("\n\n".join(context_parts)) / 2000.0)
                    chunks_used = len(context_parts)
                    self.metrics_service.record_context_quality(quality_score, chunks_used)

            return "\n\n".join(context_parts)
        except Exception as e:
            if self.metrics_service:
                self.metrics_service.increment_counter("retrieval_errors_total")
            raise e
