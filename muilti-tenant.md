# Multi-tenant Security Tasks
Proyecto: AI Document Assistant

Objetivo:
Implementar aislamiento por usuario para documentos, sesiones y consultas RAG.

Estado actual:
- El sistema maneja sesiones globales.
- Los documentos y chunks en Chroma no están asociados a un usuario.
- Los endpoints `/sessions`, `/sessions/{id}`, `/documents`, `/chat` y `/chat/stream` no filtran por usuario.
- Esto implica riesgo de acceso cruzado entre usuarios.

El objetivo de esta tarea es preparar el proyecto para un entorno multiusuario básico y más seguro.

---

# 1. Objetivo funcional

Cada usuario debe acceder únicamente a:

- sus sesiones
- sus documentos
- sus chunks/indexaciones
- sus respuestas de chat

---

# 2. Estrategia general

Agregar `user_id` a todas las entidades relevantes:

- sesiones
- documentos
- metadata de Chroma
- requests de chat

El backend debe usar ese `user_id` para:

- listar sesiones del usuario
- devolver detalles solo de sesiones del usuario
- listar documentos del usuario
- consultar Chroma solo sobre chunks del usuario

---

# 3. Fase inicial recomendada

Como el proyecto aún es demo / portfolio, no implementar auth completa todavía.

Primera fase:
usar un `user_id` temporal enviado desde el frontend.

Ejemplo:
- `demo-user-1`
- o session-based user id

Más adelante eso se reemplazará por:
- JWT
- Auth provider
- Clerk / Auth.js / Firebase Auth

---

# 4. Backend – Schemas

Actualizar los schemas de request para incluir `user_id`.

## ChatRequest

Agregar:

```python
user_id: str

Ejemplo esperado:

{
  "user_id": "demo-user-1",
  "session_id": "abc123",
  "document_ids": ["doc_1"],
  "message": "¿Cuál es el presupuesto?"
}
5. Backend – SessionService

Modificar SessionService para que cada sesión tenga ownership por usuario.

Estructura sugerida
{
  "session_id": "...",
  "user_id": "...",
  "messages": [...],
  "document_ids": [...]
}
Reglas

get_or_create_history(session_id, user_id) debe crear o recuperar solo sesiones del usuario correcto.

si una sesión existe pero pertenece a otro usuario, rechazar acceso.

/sessions debe listar solo sesiones del user_id.

/sessions/{id} debe devolver solo sesiones del user_id.

6. Backend – Ingesta de PDF

Actualizar la lógica de ingesta para asociar cada documento al usuario.

Requerimiento

El endpoint /ingest debe recibir user_id.

Cada chunk almacenado en Chroma debe guardar metadata como:

{
  "user_id": "...",
  "document_id": "...",
  "filename": "...",
  "page_number": 1,
  "chunk_index": 0
}
7. Backend – RagService

Modificar RagService para filtrar retrieval por user_id.

Search actual

Actualmente se filtra por document_id.

Debe pasar a filtrar por:

user_id

document_ids

Ejemplo conceptual:

where={
  "$and": [
    {"user_id": user_id},
    {"document_id": {"$in": document_ids}}
  ]
}
8. Backend – build_context

La función build_context() debe aceptar user_id.

Firma esperada:

build_context(query: str, user_id: str, document_ids: List[str], n_results: int = 5)

Internamente debe llamar a search() con user_id.

9. Backend – Endpoints a modificar
/chat

Debe recibir user_id y filtrar sesiones/contexto por usuario.

/chat/stream

Debe recibir user_id y filtrar sesiones/contexto por usuario.

/sessions

Debe devolver solo sesiones del usuario.

/sessions/{id}

Debe verificar que la sesión pertenezca al usuario.

/documents

Debe devolver solo documentos del usuario.

/ingest

Debe asociar el documento al usuario.

10. Importante – Unificar /chat/stream

Actualmente /chat/stream devuelve:

JSON si no hay contexto útil

SSE si sí hay contexto

Esto debe unificarse.

Requisito

/chat/stream debe responder siempre con text/event-stream.

Si no hay contexto útil, enviar un único evento SSE con el mensaje final.

Ejemplo:

yield f"data: {json.dumps({'token': 'No puedo responderlo con certeza usando el contexto disponible.'})}\n\n"

y luego terminar el stream.

Esto evita que el frontend tenga que soportar dos formatos distintos.

11. Frontend – Enviar user_id

Agregar user_id a:

upload de documentos

chat normal

chat streaming

listados de sesiones

listados de documentos

Primera fase

Generar user_id persistente en localStorage.

Ejemplo:

clave: docmind_user_id

Si no existe:

generar UUID

guardar en localStorage

Usar siempre ese valor en requests.

12. Frontend – Session Service

Actualizar llamadas a:

/sessions

/sessions/{id}

para incluir user_id.

Opciones:

query params

body

headers

Elegir un enfoque consistente en todo el backend.

13. Seguridad mínima

Incluso en demo, validar siempre:

sesión pertenece a user_id

documento pertenece a user_id

chunk consultado pertenece a user_id

Si no coincide, devolver:

403 Forbidden
o

404 Not Found

14. No romper funcionalidad existente

El refactor debe mantener funcionando:

chat

chat streaming

upload de PDFs

listado de documentos

listado de sesiones

recuperación de conversación

15. Resultado esperado

Después de este refactor:

cada usuario ve solo sus sesiones

cada usuario ve solo sus documentos

el retrieval RAG opera solo sobre chunks del usuario

/chat/stream responde de forma consistente