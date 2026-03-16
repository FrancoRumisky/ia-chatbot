from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseTool(ABC):
    """
    Interfaz base para herramientas externas que el asistente puede ejecutar.
    Cada herramienta debe implementar el método execute.
    """

    @abstractmethod
    def execute(self, parameters: Dict[str, Any]) -> str:
        """
        Ejecuta la acción de la herramienta con los parámetros dados.

        Args:
            parameters: Diccionario con los parámetros necesarios para la herramienta.

        Returns:
            str: Resultado de la ejecución de la herramienta.
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Nombre de la herramienta."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Descripción de la herramienta."""
        pass