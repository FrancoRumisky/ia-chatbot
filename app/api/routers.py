from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Form
from fastapi.responses import StreamingResponse
from typing import List
import json
import os
import shutil
import time

from app.api import schemas
from app.api.dependencies import get_rag_service, get_session_service, get_observability_service, get_tool_service
from app.core.config import settings
from app.services.observability_service import ObservabilityService
from app.services.rag_service import RagService
from app.services.session_service import SessionService
from app.services.tool_service import ToolService

router = APIRouter()


@router.post("/ingest")
def ingest_pdf(
    file: UploadFile = File(...),
    type: str = Form("docs"),
    user_id: str = Form(...),
    rag_service: RagService = Depends(get_rag_service),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Solo se permiten archivos PDF.")

    # Determinar el directorio basado en el tipo
    if type == "docs":
        upload_dir = settings.knowledge_base_docs_dir
    elif type == "faq":
        upload_dir = settings.knowledge_base_faq_dir
    elif type == "structured":
        upload_dir = settings.knowledge_base_structured_dir
    else:
        upload_dir = settings.knowledge_base_docs_dir  # default

    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        result = rag_service.ingest_pdf(file_path, user_id)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al ingerir PDF: {str(e)}"
        )


@router.post("/chat", response_model=schemas.ChatResponse)
def chat(
    request: schemas.ChatRequest,
    rag_service: RagService = Depends(get_rag_service),
    session_service: SessionService = Depends(get_session_service),
    observability_service: ObservabilityService = Depends(get_observability_service),
):
    total_start = time.perf_counter()

    if not request.document_ids:
        raise HTTPException(
            status_code=400,
            detail="Debes enviar al menos un document_id."
        )

    session_history = session_service.get_or_create_history(request.session_id, request.user_id)
    session_service.set_document_ids(request.session_id, request.user_id, request.document_ids)

    context_start = time.perf_counter()
    retrieved_context = rag_service.build_context(
        query=request.message,
        user_id=request.user_id,
        document_ids=request.document_ids,
        n_results=5
    )
    context_end = time.perf_counter()

    chat_ms = 0.0

    if not rag_service.is_context_useful(retrieved_context):
        assistant_reply = "No puedo responderlo con certeza usando el contexto disponible."
    else:
        user_prompt = f"""
Contexto recuperado:
{retrieved_context}

Pregunta del usuario:
{request.message}
"""

        messages = [{"role": "system", "content": rag_service.system_prompt}]
        messages.extend(session_history[-4:])  # últimas interacciones
        messages.append({"role": "user", "content": user_prompt})

        chat_start = time.perf_counter()
        response = rag_service.chat(messages)
        chat_end = time.perf_counter()

        chat_ms = (chat_end - chat_start) * 1000
        assistant_reply = response.strip()

    session_service.append_message(request.session_id, request.user_id, "user", request.message)
    session_service.append_message(request.session_id, request.user_id, "assistant", assistant_reply)

    total_end = time.perf_counter()

    build_context_ms = (context_end - context_start) * 1000
    total_ms = (total_end - total_start) * 1000

    timing_info = {
        "build_context_ms": round(build_context_ms, 2),
        "chat_ms": round(chat_ms, 2),
        "total_ms": round(total_ms, 2),
    }

    print(timing_info)

    observability_service.log_chat_interaction(
        session_id=request.session_id,
        question=request.message,
        document_ids=request.document_ids,
        context_used=retrieved_context,
        response=assistant_reply,
        latency_ms=int(total_ms)
    )

    return schemas.ChatResponse(
        response=assistant_reply,
        context_used=retrieved_context,
        session_id=request.session_id,
        document_ids=request.document_ids,
    )


@router.post("/chat/stream")
def chat_stream(
    request: schemas.ChatRequest,
    rag_service: RagService = Depends(get_rag_service),
    session_service: SessionService = Depends(get_session_service),
    observability_service: ObservabilityService = Depends(get_observability_service),
):
    start_time = time.time()
    if not request.document_ids:
        raise HTTPException(
            status_code=400,
            detail="Debes enviar al menos un document_id."
        )

    session_history = session_service.get_or_create_history(request.session_id, request.user_id)
    session_service.set_document_ids(request.session_id, request.user_id, request.document_ids)

    retrieved_context = rag_service.build_context(
        query=request.message,
        user_id=request.user_id,
        document_ids=request.document_ids,
        n_results=5
    )
    if not rag_service.is_context_useful(retrieved_context):
        assistant_reply = "No puedo responderlo con certeza usando el contexto disponible."
        # Log and return as SSE
        latency_ms = int((time.time() - start_time) * 1000)
        observability_service.log_chat_interaction(
            session_id=request.session_id,
            question=request.message,
            document_ids=request.document_ids,
            context_used=retrieved_context,
            response=assistant_reply,
            latency_ms=latency_ms
        )
        session_service.append_message(request.session_id, request.user_id, "user", request.message)
        session_service.append_message(request.session_id, request.user_id, "assistant", assistant_reply)
        def generate_no_context():
            yield f"data: {json.dumps({'token': assistant_reply})}\n\n"
        return StreamingResponse(generate_no_context(), media_type="text/event-stream")
    else:
        user_prompt = f"""
        Contexto recuperado:
        {retrieved_context}

        Pregunta del usuario:
        {request.message}
        """

        messages = [{"role": "system", "content": rag_service.system_prompt}]
        messages.extend(session_history[-4:])
        messages.append({"role": "user", "content": user_prompt})

        def generate():
            full_response = ""
            for chunk in rag_service.chat_stream(messages):
                if 'message' in chunk and 'content' in chunk['message']:
                    token = chunk['message']['content']
                    full_response += token
                    yield f"data: {json.dumps({'token': token})}\n\n"
            # After streaming, log and save
            latency_ms = int((time.time() - start_time) * 1000)
            observability_service.log_chat_interaction(
                session_id=request.session_id,
                question=request.message,
                document_ids=request.document_ids,
                context_used=retrieved_context,
                response=full_response,
                latency_ms=latency_ms
            )
            session_service.append_message(request.session_id, request.user_id, "user", request.message)
            session_service.append_message(request.session_id, request.user_id, "assistant", full_response)

        return StreamingResponse(generate(), media_type="text/event-stream")
    
def reset_session(
    request: schemas.ResetSessionRequest,
    session_service: SessionService = Depends(get_session_service),
):
    session_service.reset(request.session_id, request.user_id)
    return {"message": "Sesión reiniciada correctamente", "session_id": request.session_id}


@router.get("/sessions")
def list_sessions(
    user_id: str,
    session_service: SessionService = Depends(get_session_service),
):
    sessions = session_service.list_sessions(user_id)
    return {"sessions": sessions, "total_sessions": len(sessions)}


@router.get("/tools", response_model=List[schemas.ToolDescription])
def list_tools(
    tool_service: ToolService = Depends(get_tool_service),
):
    return tool_service.list_tools()


@router.post("/tools/execute", response_model=schemas.ToolExecuteResponse)
def execute_tool(
    request: schemas.ToolExecuteRequest,
    tool_service: ToolService = Depends(get_tool_service),
):
    try:
        output = tool_service.execute_tool(request.tool_name, request.parameters)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return schemas.ToolExecuteResponse(tool_name=request.tool_name, output=output)


@router.get("/documents")
def list_documents(
    user_id: str,
    rag_service: RagService = Depends(get_rag_service),
):
    results = rag_service.collection.get(include=["metadatas"])
    metadatas = results.get("metadatas", [])

    unique_docs = {}
    for metadata in metadatas:
        if metadata.get("user_id") == user_id:
            doc_id = metadata["documentId"]
            if doc_id not in unique_docs:
                unique_docs[doc_id] = {
                    "document_id": doc_id,
                    "filename": metadata.get("filename"),
                    "source": metadata.get("source")
                }

    return {"documents": list(unique_docs.values()), "total_documents": len(unique_docs)}


@router.get("/health")
def health():
    return {
        "status": "ok",
        "chat_model": settings.chat_model,
        "embedding_model": settings.embedding_model,
        "collection": settings.rag_collection_name
    }


@router.get("/logs/recent")
def get_recent_logs(limit: int = 20):
    file_path = os.path.join(settings.logs_dir, settings.chat_logs_file)
    if not os.path.exists(file_path):
        return {"logs": []}
    
    logs = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for line in lines[-limit:]:
                if line.strip():
                    logs.append(json.loads(line.strip()))
    except Exception as e:
        return {"error": str(e)}
    
    return {"logs": logs}


@router.get("/sessions")
def list_sessions(session_service: SessionService = Depends(get_session_service)):
    sessions = session_service.list_sessions()
    return {"sessions": sessions}


@router.get("/sessions/{session_id}")
def get_session_history(session_id: str, user_id: str, session_service: SessionService = Depends(get_session_service)):
    data = session_service.get_full_session_data(session_id, user_id)
    return {"session_id": session_id, "messages": data["messages"], "document_ids": data["document_ids"]}
