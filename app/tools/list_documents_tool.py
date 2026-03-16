from typing import Any, Dict, Optional
from app.tools.base_tool import BaseTool


class ListDocumentsTool(BaseTool):
    """
    Herramienta para listar los documentos cargados en la base de conocimiento.
    """

    def __init__(self, chroma_repository: Optional[Any] = None):
        # chroma_repository se puede inyectar en runtime para evitar dependencias fuertes
        self.chroma_repository = chroma_repository

    @property
    def name(self) -> str:
        return "list_documents"

    @property
    def description(self) -> str:
        return "Lista los documentos disponibles en la base de conocimiento."

    def execute(self, parameters: Dict[str, Any]) -> str:
        # Implementación básica: obtener metadatos de documentos desde ChromaDB
        try:
            # Asumiendo que chroma_repository tiene un método para listar documentos
            # Esto es un placeholder; en una implementación real, ajustar según la API de ChromaDB
            documents = self.chroma_repository.list_documents()  # Método hipotético
            if not documents:
                return "No hay documentos cargados en la base de conocimiento."
            result = "Documentos disponibles:\n"
            for doc in documents:
                result += f"- {doc['name']} (ID: {doc['id']})\n"
            return result
        except Exception as e:
            return f"Error al listar documentos: {str(e)}"