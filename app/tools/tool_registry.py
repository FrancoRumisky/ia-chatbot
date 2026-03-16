from typing import Dict, Type
from app.tools.base_tool import BaseTool


class ToolRegistry:
    """
    Registro de herramientas disponibles para el asistente.
    """

    def __init__(self):
        self._tools: Dict[str, Type[BaseTool]] = {}

    def register(self, tool_class: Type[BaseTool]):
        """Registra una herramienta en el registro."""
        self._tools[tool_class().name] = tool_class

    def get_tool(self, name: str) -> Type[BaseTool]:
        """Obtiene una herramienta por nombre."""
        return self._tools.get(name)

    def list_tools(self) -> Dict[str, str]:
        """Lista todas las herramientas registradas con sus descripciones."""
        return {name: tool_class().description for name, tool_class in self._tools.items()}


# Instancia global del registro
tool_registry = ToolRegistry()