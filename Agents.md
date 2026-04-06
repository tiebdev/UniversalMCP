# Roles de Agentes: Universal MCP Orchestrator

## 1. Arquitecto del Daemon (Líder Backend)
- **Rol:** Construir el motor principal en segundo plano y el gestor de procesos.
- **Foco de Archivos:** `daemon/process_router.py` y `daemon/multiplexer.py`.
- **Reglas Fundamentales:**
  - Garantizar cero bloqueos de E/S (I/O). El uso de `asyncio` es estricto e innegociable.
  - Actuar como un verdadero Multiplexor: el motor debe exponer UN ÚNICO puerto local (ej. WebSockets o FastAPI) que unifique las capacidades de todos los procesos MCP subyacentes.
  - Implementar una recuperación robusta ante caídas de procesos hijos de Node.js o Python (ej. Postgres MCP, Github MCP).

## 2. Especialista en Contexto y Traducción (Middleware)
- **Rol:** Proteger la ventana de contexto del LLM y traducir los esquemas de las herramientas al vuelo.
- **Foco de Archivos:** `daemon/memory_filter.py` y `daemon/translator.py`.
- **Reglas Fundamentales:**
  - Utilizar `Pydantic` (v2) para estandarizar y validar todos los mensajes JSON-RPC entrantes y salientes.
  - Implementar un truncado estricto o paginación para respuestas de herramientas que superen un tamaño razonable (ej. logs masivos o diffs de Git gigantes), evitando así desbordar al LLM cliente.
  - Asegurar la compatibilidad traduciendo los dialectos de *Function Calling* (OpenAI, Anthropic, Gemini).

## 3. Ingeniero de CLI y Wrapper (Frontend y UX)
- **Rol:** Construir el panel de control del usuario y el inyector de entorno transparente.
- **Foco de Archivos:** Directorio `cli/` (`main.py`, `wrapper.py`, `views.py`).
- **Reglas Fundamentales:**
  - Diseñar el flujo "First-Run Onboarding": si no hay configuración, guiar al usuario para seleccionar MCPs y pedir tokens/API keys necesarios.
  - Implementar el comando `mcp-cli run <comando>` usando `subprocess.Popen` y `os.environ` para inyectar configuraciones dinámicas en el subproceso (el cliente IA de terceros) sin filtrar variables al sistema global.
  - Utilizar `Rich` para mostrar tablas de estado visualmente atractivas (`mcp-cli status`).
  - El CLI debe ser efímero: solo se comunica con el Daemon y no mantiene estados prolongados por sí mismo.