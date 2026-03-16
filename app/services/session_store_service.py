import json
import os
from typing import Dict, List


class SessionStoreService:
    """Simple file-backed session store.

    Each session is stored in a JSON file under `storage/sessions/<session_id>.json`.
    """

    def __init__(self, base_dir: str = "storage/sessions") -> None:
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def _session_path(self, session_id: str) -> str:
        safe_id = session_id.replace("..", "")
        return os.path.join(self.base_dir, f"{safe_id}.json")

    def _load(self, session_id: str) -> Dict[str, any]:
        path = self._session_path(session_id)
        if not os.path.exists(path):
            return {"messages": [], "document_ids": [], "user_id": None}
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Ensure structure
                if "messages" not in data:
                    data["messages"] = []
                if "document_ids" not in data:
                    data["document_ids"] = []
                if "user_id" not in data:
                    data["user_id"] = None
                return data
        except Exception:
            return {"messages": [], "document_ids": [], "user_id": None}

    def _save(self, session_id: str, data: Dict[str, any]) -> None:
        path = self._session_path(session_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_or_create_history(self, session_id: str, user_id: str) -> Dict[str, any]:
        data = self._load(session_id)
        if data["user_id"] is None:
            # New session or old without user_id, assign user_id
            data["user_id"] = user_id
            self._save(session_id, data)
        elif data["user_id"] != user_id:
            raise ValueError(f"Session {session_id} belongs to another user")
        return data

    def append_message(self, session_id: str, user_id: str, role: str, content: str) -> None:
        data = self.get_or_create_history(session_id, user_id)
        data["messages"].append({"role": role, "content": content})
        self._save(session_id, data)

    def set_document_ids(self, session_id: str, user_id: str, document_ids: List[str]) -> None:
        data = self.get_or_create_history(session_id, user_id)
        data["document_ids"] = document_ids
        self._save(session_id, data)

    def reset(self, session_id: str, user_id: str) -> None:
        data = {"messages": [], "document_ids": [], "user_id": user_id}
        self._save(session_id, data)

    def list_sessions(self, user_id: str) -> List[str]:
        files = os.listdir(self.base_dir)
        sessions = []
        for f in files:
            if f.endswith(".json"):
                session_id = os.path.splitext(f)[0]
                data = self._load(session_id)
                if data["user_id"] == user_id:
                    sessions.append(session_id)
        return sessions