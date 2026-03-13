import json
import os
import datetime
from typing import List


class ObservabilityService:
    def __init__(self, config):
        self.logs_dir = config.logs_dir
        self.chat_logs_file = config.chat_logs_file
        os.makedirs(self.logs_dir, exist_ok=True)
        self.file_path = os.path.join(self.logs_dir, self.chat_logs_file)

    def log_chat_interaction(
        self,
        session_id: str,
        question: str,
        document_ids: List[str],
        context_used: str,
        response: str,
        latency_ms: int
    ):
        timestamp = datetime.datetime.now().isoformat()
        data = {
            "session_id": session_id,
            "question": question,
            "document_ids": document_ids,
            "context_used": context_used,
            "response": response,
            "latency_ms": latency_ms,
            "timestamp": timestamp
        }
        try:
            with open(self.file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(data, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"Error logging: {e}")  # don't fail the response