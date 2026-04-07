# Reglas Específicas del Daemon

## Arquitecto del Daemon (Líder Backend)
- **Rol:** Construir el motor principal en segundo plano y el gestor de procesos.
- **Foco de Archivos:** `daemon/process_router.py` y `daemon/multiplexer.py`.
- **Reglas Fundamentales:**
  - Garantizar cero bloqueos de E/S (I/O). El uso de `asyncio` es estricto e innegociable.
  - Actuar como un verdadero Multiplexor: el motor debe exponer UN ÚNICO puerto local (ej. WebSockets o FastAPI) que unifique las capacidades de todos los procesos MCP subyacentes.
  - Implementar una recuperación robusta ante caídas de procesos hijos de Node.js o Python (ej. Postgres MCP, Github MCP).

  ## Especialista en Contexto y Traducción (Middleware)
- **Rol:** Proteger la ventana de contexto del LLM y traducir los esquemas de las herramientas al vuelo.
- **Foco de Archivos:** `daemon/memory_filter.py` y `daemon/translator.py`.
- **Reglas Fundamentales:**
  - Utilizar `Pydantic` (v2) para estandarizar y validar todos los mensajes JSON-RPC entrantes y salientes.
  - Implementar un truncado estricto o paginación para respuestas de herramientas que superen un tamaño razonable (ej. logs masivos o diffs de Git gigantes), evitando así desbordar al LLM cliente.
  - Asegurar la compatibilidad traduciendo los dialectos de *Function Calling* (OpenAI, Anthropic, Gemini).