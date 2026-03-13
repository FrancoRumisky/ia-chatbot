# Roadmap AI Engineer — instrucciones paso a paso para ejecutar cambios en el código

Este documento está pensado para que un asistente de IA pueda trabajar **directamente sobre el código** de este proyecto, de forma **incremental**, con cambios chicos, probables y fáciles de validar.

## Contexto del proyecto actual

Estructura relevante detectada:

- `main.py`
- `app/api/routers.py`
- `app/api/schemas.py`
- `app/core/config.py`
- `app/services/rag_service.py`
- `app/services/session_service.py`
- `app/repositories/chroma_repository.py`
- `data/`
- `chroma_db/`

Estado actual del proyecto:

- Ya existe un chatbot RAG funcional.
- Usa `FastAPI`.
- Usa `Ollama` para embeddings y chat.
- Usa `ChromaDB` como vector store.
- La memoria de sesión es en memoria (`SessionService`).
- Ya existe ingesta de PDFs y recuperación de contexto.
- El siguiente objetivo ya no es “hacer que funcione”, sino **hacerlo medible, trazable y más seguro**.

---

# Reglas de trabajo para el asistente de IA

## Objetivo general

Aplicar los cambios **por etapas**, sin romper el flujo actual del bot.

## Restricciones obligatorias

1. **No refactorizar masivamente de una sola vez.**
2. **Hacer un solo bloque funcional por iteración.**
3. **Mantener compatibilidad con la API actual.**
4. **No eliminar endpoints existentes salvo indicación explícita.**
5. **No cambiar nombres públicos de request/response sin necesidad.**
6. **Priorizar simplicidad, legibilidad y principios SOLID.**
7. **Antes de tocar código, leer los archivos involucrados.**
8. **Después de cada cambio, dejar claro qué probar manualmente.**
9. **Si una mejora requiere librerías nuevas, agregarlas de forma mínima y justificada.**
10. **Cada etapa debe quedar utilizable aunque la siguiente todavía no exista.**

## Forma de ejecución

En cada etapa, el asistente debe seguir este formato:

1. Explicar brevemente qué va a cambiar.
2. Modificar solo los archivos necesarios.
3. Mostrar el código final completo de cada archivo modificado.
4. Indicar cómo correr y validar el cambio.
5. Esperar validación humana antes de pasar a la siguiente etapa.

---

# Orden de implementación recomendado

La prioridad correcta para este proyecto es:

1. **Observabilidad y logs de IA**
2. **Evaluación básica del bot**
3. **Guardrails mínimos**
4. **Mejora del retrieval**
5. **Persistencia de sesiones**
6. **Streaming**
7. **Tools / agents**

---

# ETAPA 1 — Observabilidad básica del chatbot

## Objetivo

Registrar cada interacción importante para poder auditar:

- pregunta
- contexto recuperado
- respuesta final
- latencia
- documentos usados
- session_id
- timestamp

## Resultado esperado

Crear una primera capa de logging local en archivo JSONL.

## Cambios a implementar

### 1. Crear un servicio nuevo

Crear archivo:

- `app/services/observability_service.py`

Responsabilidad:

- guardar logs de interacción en un archivo, por ejemplo:
  - `logs/chat_interactions.jsonl`

Cada línea del archivo debe ser un JSON independiente.

Campos mínimos por log:

- `session_id`
- `question`
- `document_ids`
- `context_used`
- `response`
- `latency_ms`
- `timestamp`

### 2. Agregar configuración

Modificar `app/core/config.py` para agregar:

- `logs_dir: str = "logs"`
- `chat_logs_file: str = "chat_interactions.jsonl"`

### 3. Integrar el logger al flujo `/chat`

Modificar `app/api/routers.py` para:

- medir tiempo de ejecución del flujo de chat
- invocar el nuevo servicio de observabilidad al final
- no romper el response actual

### 4. Dependencias

Si hace falta, crear provider en:

- `app/api/dependencies.py`

## Criterios de aceptación

- El endpoint `/chat` sigue funcionando.
- Después de una consulta, se crea el archivo de logs si no existe.
- Cada request agrega una nueva línea JSON válida.
- Si el logging falla, el chatbot igual responde.

## Qué probar manualmente

1. Levantar el proyecto.
2. Ejecutar una consulta al endpoint `/chat`.
3. Verificar que exista `logs/chat_interactions.jsonl`.
4. Verificar que la línea tenga pregunta, contexto, respuesta y latencia.

## Prompt recomendado para el asistente

> Implementa la ETAPA 1 de observabilidad básica en este proyecto FastAPI RAG. Crea `app/services/observability_service.py`, agrega la configuración necesaria en `app/core/config.py`, conecta el servicio en `app/api/dependencies.py` si corresponde, e integra el logging dentro de `app/api/routers.py` sin romper el contrato actual del endpoint `/chat`. Usa un archivo JSONL local en `logs/chat_interactions.jsonl`. Muestra el contenido final completo de cada archivo modificado y al final indícame cómo probarlo manualmente.

---

# ETAPA 2 — Endpoint de health y endpoint de revisión de logs

## Objetivo

Tener visibilidad rápida del estado del sistema sin entrar al código.

## Cambios a implementar

### 1. Crear endpoint `/health`

Debe devolver algo como:

```json
{
  "status": "ok",
  "chat_model": "...",
  "embedding_model": "...",
  "collection": "..."
}
```

### 2. Crear endpoint `/logs/recent`

Debe devolver las últimas N interacciones desde el archivo JSONL.

Parámetro sugerido:

- `limit: int = 20`

### 3. Reglas

- No devolver todo el archivo completo.
- Manejar el caso en que todavía no exista el archivo.

## Criterios de aceptación

- `/health` responde correctamente.
- `/logs/recent` devuelve las últimas interacciones.
- No rompe el resto de la API.

## Qué probar manualmente

1. Hacer GET a `/health`.
2. Generar algunos chats.
3. Hacer GET a `/logs/recent?limit=5`.

## Prompt recomendado

> Implementa la ETAPA 2 sobre el proyecto actual. Agrega un endpoint `/health` y un endpoint `/logs/recent` en FastAPI, reutilizando el servicio de observabilidad creado antes. Mantén la API existente intacta. Muestra el código final completo de los archivos modificados y explícame cómo probarlo.

---

# ETAPA 3 — Evaluación básica offline del bot

## Objetivo

Poder medir respuestas del bot contra un dataset controlado.

## Resultado esperado

Agregar una carpeta de evaluación que permita correr pruebas offline.

## Cambios a implementar

### 1. Crear estructura

Crear:

- `evaluation/`
- `evaluation/dataset.json`
- `evaluation/evaluator.py`

### 2. Dataset inicial

El dataset debe tener ejemplos como:

```json
[
  {
    "question": "¿Qué experiencia tiene Franco Rumisky?",
    "document_ids": ["..."],
    "expected_keywords": ["software", "developer", "full stack"]
  }
]
```

### 3. Evaluador simple

El evaluador debe:

- leer el dataset
- consultar al `RagService`
- generar respuesta
- medir si contiene ciertas keywords esperadas
- emitir un reporte simple por consola

### 4. Alcance

No hace falta meter aún `ragas` ni `deepeval`.
Primero hacer una versión mínima, práctica y local.

## Criterios de aceptación

- Existe un script ejecutable de evaluación.
- Se puede correr localmente sin tocar la API.
- Devuelve un resumen con total de casos, aprobados y fallidos.

## Qué probar manualmente

1. Completar al menos 3 casos en `evaluation/dataset.json`.
2. Ejecutar `python evaluation/evaluator.py`.
3. Confirmar que imprime resultados claros.

## Prompt recomendado

> Implementa la ETAPA 3 de evaluación offline en este proyecto. Crea la carpeta `evaluation`, un `dataset.json` inicial y un `evaluator.py` que use el `RagService` actual para ejecutar preguntas de prueba y validar respuestas con `expected_keywords`. No cambies el contrato de la API. Muestra el código final completo y cómo correrlo.

---

# ETAPA 4 — Guardrail mínimo antes de responder

## Objetivo

Reducir respuestas dudosas cuando el contexto recuperado sea pobre.

## Idea

Si el contexto recuperado está vacío, demasiado corto o no tiene contenido suficiente, responder con el mensaje seguro ya definido.

## Cambios a implementar

### 1. Encapsular validación

Agregar dentro de `RagService` o en un servicio separado una validación tipo:

- contexto vacío
- contexto demasiado corto
- retrieval sin resultados

### 2. Integrar en `/chat`

Antes de llamar al modelo, validar el contexto.

Si no pasa la validación, devolver directamente:

```text
No puedo responderlo con certeza usando el contexto disponible.
```

### 3. Mantener compatibilidad

No cambiar la estructura de `ChatResponse`.

## Criterios de aceptación

- Cuando no haya contexto útil, no consulta al modelo.
- Devuelve la respuesta segura.
- El flujo normal sigue funcionando con contexto válido.

## Qué probar manualmente

1. Preguntar algo no relacionado al documento.
2. Validar que devuelva el mensaje seguro.
3. Preguntar algo sí relacionado y verificar que responda normal.

## Prompt recomendado

> Implementa la ETAPA 4 agregando un guardrail mínimo al flujo de chat. Si el contexto recuperado está vacío, es muy corto o no hay resultados relevantes, el endpoint debe devolver directamente el mensaje seguro definido por el sistema, sin invocar al modelo. Mantén la respuesta actual de la API. Muestra el código final completo de los archivos modificados y cómo probarlo.

---

# ETAPA 5 — Mejorar estructura del RAG sin romper el proyecto

## Objetivo

Separar mejor responsabilidades en el `RagService`, que hoy concentra demasiada lógica.

## Propuesta

Desacoplar en piezas pequeñas.

## Cambios a implementar

### 1. Crear servicios nuevos

Separar gradualmente:

- `app/services/document_ingestion_service.py`
- `app/services/embedding_service.py`
- `app/services/retrieval_service.py`

### 2. Reglas

- No rehacer todo desde cero.
- Mover lógica en pequeñas partes.
- `RagService` puede quedar como fachada/orquestador.

### 3. Alcance inicial

Primero mover solo lo más claro:

- generación de embeddings
- build de contexto
- lectura/chunking si aplica

## Criterios de aceptación

- El proyecto sigue funcionando.
- `RagService` queda más liviano.
- La lógica queda más mantenible y testeable.

## Qué probar manualmente

1. Ingestar un PDF.
2. Hacer chat con documento.
3. Verificar que todo siga igual funcionalmente.

## Prompt recomendado

> Implementa la ETAPA 5 refactorizando de manera incremental el `RagService` actual para separar responsabilidades en servicios más pequeños, sin romper el comportamiento público actual. Usa principios SOLID. Mantén `RagService` como fachada si te resulta útil. Muestra el código final completo de cada archivo modificado y explícame cómo validarlo manualmente.

---

# ETAPA 6 — Persistencia de memoria de sesión

## Objetivo

Dejar de depender solo de memoria RAM para las conversaciones.

## Cambios a implementar

### Opción inicial simple

Persistir sesiones en archivo JSON.

Crear por ejemplo:

- `app/services/session_store_service.py`

Y guardar en:

- `storage/sessions/{session_id}.json`

### Alcance

- `get_or_create_history`
- `append_message`
- `reset`
- mantener compatibilidad con `SessionService`

### Importante

Primero hacerlo simple. Más adelante puede migrarse a Redis o DB.

## Criterios de aceptación

- Reiniciar el servidor no borra la sesión.
- El historial sigue existiendo por `session_id`.
- Reset sigue funcionando.

## Qué probar manualmente

1. Crear una conversación.
2. Reiniciar el backend.
3. Volver a usar el mismo `session_id`.
4. Confirmar que recuerda el historial.

## Prompt recomendado

> Implementa la ETAPA 6 agregando persistencia simple de sesiones a disco para reemplazar o complementar el almacenamiento en memoria del `SessionService`. Usa archivos JSON por `session_id` en una carpeta `storage/sessions`. Mantén la interfaz pública del servicio actual para no romper el resto del proyecto. Muestra el código final completo y cómo probarlo.

---

# ETAPA 7 — Streaming de respuestas

## Objetivo

Mejorar UX devolviendo tokens parciales.

## Cambios a implementar

### 1. Nuevo endpoint opcional

Agregar un endpoint nuevo, por ejemplo:

- `/chat/stream`

### 2. Reglas

- No romper `/chat` actual.
- Mantener ambas opciones convivendo.
- Si `ollama` soporta streaming en la librería instalada, usarlo.

## Criterios de aceptación

- `/chat` sigue igual.
- `/chat/stream` entrega respuesta incremental.

## Qué probar manualmente

1. Consumir el endpoint desde curl o frontend.
2. Ver que lleguen chunks progresivos.

## Prompt recomendado

> Implementa la ETAPA 7 agregando streaming de respuestas en un nuevo endpoint `/chat/stream`, manteniendo intacto el endpoint `/chat` existente. Usa la capacidad de streaming del cliente de `ollama` si está disponible en este proyecto. Muestra el código final completo de los archivos modificados y cómo probarlo.

---

# ETAPA 8 — Ingesta más profesional de documentos

## Objetivo

Pasar de una carpeta `data/` genérica a una base de conocimiento mejor organizada.

## Cambios a implementar

### 1. Proponer estructura nueva

```text
knowledge_base/
  docs/
  faq/
  structured/
```

### 2. Adaptar configuración

Agregar parámetros nuevos en config para esta estructura.

### 3. No romper lo existente

Mantener compatibilidad temporal con `data/`.

## Criterios de aceptación

- Puede ingerir archivos desde la nueva estructura.
- Sigue funcionando con la estructura anterior durante transición.

## Prompt recomendado

> Implementa la ETAPA 8 para profesionalizar la organización de la base documental, agregando soporte para `knowledge_base/docs`, `knowledge_base/faq` y `knowledge_base/structured`, manteniendo compatibilidad con `data/` durante la transición. Muestra el código final completo y los pasos de validación.

---

# ETAPA 9 — Mejorar retrieval con metadatos y filtros

## Objetivo

Hacer más preciso el contexto recuperado.

## Cambios a implementar

### 1. Guardar mejores metadatos al ingerir

Metadatos sugeridos por chunk:

- `document_id`
- `document_name`
- `chunk_index`
- `source_type`
- `ingested_at`

### 2. Mejorar el query a Chroma

Permitir filtros por:

- `document_id`
- potencialmente `document_name`

### 3. Exponer el contexto más claro

Que el contexto incluya referencias legibles al documento y chunk.

## Criterios de aceptación

- Los metadatos se guardan correctamente.
- El retrieval sigue funcionando.
- El contexto usado es más entendible para debug.

## Prompt recomendado

> Implementa la ETAPA 9 mejorando la ingesta y recuperación para incluir metadatos más ricos por chunk y filtros más claros en Chroma, sin romper el funcionamiento actual. Muestra el código final completo y cómo probarlo.

---

# ETAPA 10 — Tools / acciones externas

## Objetivo

Preparar el proyecto para pasar de chatbot RAG a asistente con acciones.

## Primera versión sugerida

Crear una carpeta:

- `app/tools/`

Y definir una interfaz simple para herramientas.

Ejemplos futuros:

- consultar estado del sistema
- listar documentos cargados
- borrar sesión
- reingestar documentos

## Alcance inicial

No hacer un agente complejo todavía.
Primero preparar arquitectura.

## Prompt recomendado

> Implementa la ETAPA 10 creando una base arquitectónica para tools dentro de `app/tools`, con una interfaz o convención clara para futuras acciones del asistente. No construyas todavía un agente autónomo complejo; enfócate en dejar la estructura lista y coherente con SOLID. Muestra el código final completo y cómo validarlo.

---

# Orden real de ejecución sugerido para trabajar con el asistente

Usar este orden exacto en las conversaciones:

1. ETAPA 1 — Observabilidad básica
2. ETAPA 2 — Health + recent logs
3. ETAPA 3 — Evaluación offline
4. ETAPA 4 — Guardrail mínimo
5. ETAPA 5 — Refactor incremental de `RagService`
6. ETAPA 6 — Persistencia de sesiones
7. ETAPA 7 — Streaming
8. ETAPA 8 — Estructura nueva de knowledge base
9. ETAPA 9 — Retrieval con mejores metadatos
10. ETAPA 10 — Base para tools

---

# Instrucción maestra para pegarle al asistente de IA

Puedes usar este prompt base en cada iteración:

> Quiero que trabajes como AI Engineer sobre mi proyecto FastAPI + Ollama + Chroma RAG. Debes hacer cambios incrementales, seguros y compatibles con la API actual. No hagas refactors gigantes ni cambies varias capas sin necesidad. Primero lee los archivos involucrados, luego modifica solo los necesarios, muestra el código final completo de cada archivo editado y al final indícame exactamente cómo probar manualmente el cambio. Aplica principios SOLID. Vamos a ejecutar una sola etapa por vez. Empecemos por la ETAPA X.

---

# Nota final de estrategia

En este proyecto, el mayor salto de madurez no está en “otro modelo” ni en “más prompts”, sino en esto:

- medir
- observar
- registrar
- aislar responsabilidades
- controlar errores
- mejorar retrieval

Ese es el camino correcto para pasar de **bot funcional** a **producto de IA serio**.
