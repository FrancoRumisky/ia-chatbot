# Tools module for external actions
from app.tools.base_tool import BaseTool
from app.tools.list_documents_tool import ListDocumentsTool
from app.tools.tool_registry import tool_registry

# Registrar herramientas disponibles
tool_registry.register(ListDocumentsTool)