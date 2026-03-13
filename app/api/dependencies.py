from fastapi import Depends

from app.core.config import settings
from app.services.observability_service import ObservabilityService
from app.services.rag_service import RagService
from app.services.session_service import SessionService


# simple singleton instances for now; could be replaced by a DI container
rag_service_instance = RagService(settings)
session_service_instance = SessionService()
observability_service_instance = ObservabilityService(settings)


def get_rag_service() -> RagService:
    return rag_service_instance


def get_session_service() -> SessionService:
    return session_service_instance


def get_observability_service() -> ObservabilityService:
    return observability_service_instance
