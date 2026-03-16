from typing import Any, Dict, List

from app.core.config import settings
from app.repositories.chroma_repository import ChromaRepository
from app.tools.tool_registry import tool_registry


class ToolService:
    """Servicio que expone herramientas (tools) para el asistente."""

    def __init__(self):
        # Dependencias que pueden ser inyectadas en las herramientas
        self.chroma_repository = ChromaRepository(
            db_path=settings.chroma_db_path,
            collection_name=settings.rag_collection_name,
        )

    def list_tools(self) -> List[Dict[str, str]]:
        """Lista las herramientas registradas con nombre y descripción."""
        return [
            {"name": name, "description": desc}
            for name, desc in tool_registry.list_tools().items()
        ]

    def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> str:
        """Ejecuta una herramienta registrada y retorna su resultado."""
        tool_class = tool_registry.get_tool(tool_name)
        if not tool_class:
            raise ValueError(f"Tool '{tool_name}' no encontrada.")

        tool = tool_class(chroma_repository=self.chroma_repository)
        return tool.execute(parameters)
