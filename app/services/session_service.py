from typing import List, Dict, Any

from app.services.session_store_service import SessionStoreService


class SessionService:
    def __init__(self, store: SessionStoreService = None):
        self._store = store or SessionStoreService()

    def get_or_create_history(self, session_id: str, user_id: str) -> List[Dict[str, str]]:
        data = self._store.get_or_create_history(session_id, user_id)
        return data["messages"]

    def append_message(self, session_id: str, user_id: str, role: str, content: str) -> None:
        self._store.append_message(session_id, user_id, role, content)

    def set_document_ids(self, session_id: str, user_id: str, document_ids: List[str]) -> None:
        self._store.set_document_ids(session_id, user_id, document_ids)

    def get_document_ids(self, session_id: str, user_id: str) -> List[str]:
        data = self._store.get_or_create_history(session_id, user_id)
        return data["document_ids"]

    def reset(self, session_id: str, user_id: str) -> None:
        self._store.reset(session_id, user_id)

    def list_sessions(self, user_id: str) -> List[str]:
        return self._store.list_sessions(user_id)

    def get_full_session_data(self, session_id: str, user_id: str) -> Dict[str, Any]:
        return self._store.get_or_create_history(session_id, user_id)
