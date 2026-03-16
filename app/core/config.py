from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    upload_dir: str = "data"
    chroma_db_path: str = "./chroma_db"
    embedding_model: str = "embeddinggemma"
    rag_collection_name: str = "pdf_knowledge_base"
    chat_model: str = "qwen2.5:1.5b"
    logs_dir: str = "logs"
    chat_logs_file: str = "chat_interactions.jsonl"
    knowledge_base_dir: str = "knowledge_base"
    knowledge_base_docs_dir: str = "knowledge_base/docs"
    knowledge_base_faq_dir: str = "knowledge_base/faq"
    knowledge_base_structured_dir: str = "knowledge_base/structured"
    system_prompt: str = """Eres un asistente especializado en análisis de documentos.

Reglas obligatorias:
- Responde siempre en español.
- Usa únicamente la información del contexto proporcionado.
- Si la respuesta no está explícitamente en el contexto, responde exactamente:
  "No puedo responderlo con certeza usando el contexto disponible."
- No uses conocimiento general.
- No inventes información.
- No reformatees números.
- No agregues ceros, comas, puntos o espacios a los números.
- No redondees ni interpretes los números; transcríbelos exactamente como están.
- Si hay duda sobre un valor numérico, indícalo en lugar de asumir.
- Sé claro, breve y práctico.
- Responde en un máximo de 60 palabras, salvo que el usuario pida más detalle."""


    model_config = {
        "extra": "ignore",
        "env_file": ".env",
    }


settings = Settings()
