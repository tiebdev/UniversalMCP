# Universal MCP Orchestrator

## Bitácora de Desarrollo V1

Propósito: registrar de forma cronológica las fases, decisiones ejecutadas, estado actual y bloqueos para poder retomar el trabajo sin pérdida de contexto.

## Decisión vigente de cliente principal

- Cliente objetivo principal de la V1: `Codex CLI`
- `Claude Code` pasa a considerarse integración futura o módulo opcional
- Motivo: reducir dependencia de políticas cambiantes de suscripción de terceros y mantener foco en una ruta de integración más estable

## Estado actual

- Fase en curso: bootstrap inicial del proyecto
- Fecha base registrada: 2026-04-04
- Estado general: esqueleto del proyecto creado, dependencias aún no instaladas en el entorno local

## Registro

### 2026-04-04 | Fase 0 | Bootstrap inicial

Trabajo realizado:

- creación de la estructura del paquete `universal_mcp`
- creación de `pyproject.toml`
- creación de `README.md`
- creación de módulos base para `daemon`, `cli`, `config`, `runtime` y `observability`
- definición inicial del catálogo V1
- definición inicial de `Settings`, perfiles y estado del daemon
- creación de CLI base con comandos stub
- creación de `.gitignore`
- creación de test básico de catálogo

Archivos principales incorporados:

- `pyproject.toml`
- `README.md`
- `universal_mcp/config/catalog.py`
- `universal_mcp/config/settings.py`
- `universal_mcp/daemon/state.py`
- `universal_mcp/daemon/process_router.py`
- `universal_mcp/cli/main.py`
- `tests/test_catalog.py`

Verificaciones ejecutadas:

- `python3 -m compileall universal_mcp tests` -> correcto
- `python3 -m pytest -q` -> falla por entorno incompleto

Resultado de la última ejecución de tests:

- `pytest` sí está disponible ahora en el entorno
- la colección falla por `ModuleNotFoundError: No module named 'pydantic'`
- conclusión: faltan dependencias del proyecto en el Python actual

Bloqueos actuales:

- entorno sin dependencias instaladas
- no se puede validar la suite mientras falten `pydantic` y el resto de librerías base

Siguiente paso recomendado:

- instalar dependencias del proyecto
- relanzar tests
- pasar a implementación real de runtime local, PID/estado y comandos `start`, `stop` y `status`

### 2026-04-04 | Fase 0.1 | Preparación de entorno y validación base

Trabajo realizado:

- reintento de ejecución de `pytest`
- diagnóstico del fallo de importación por ausencia de dependencias
- intento de creación de entorno virtual local
- instalación de dependencias del proyecto en modo editable
- nueva ejecución de tests tras instalación

Incidencias observadas:

- `python3 -m venv .venv` falló porque el sistema no dispone de `ensurepip` ni `python3.12-venv`
- `pip install --user -e '.[dev]'` falló primero por política de entorno administrado externamente
- el siguiente intento con `--break-system-packages` falló dentro del sandbox por falta de red

Resolución aplicada:

- instalación con `python3 -m pip install --user --break-system-packages -e '.[dev]'`
- ejecución fuera del sandbox para permitir descarga de dependencias

Verificaciones ejecutadas:

- `python3 -m pytest -q` -> correcto

Resultado:

- entorno funcional para desarrollo local
- dependencias base instaladas
- suite actual en verde: `1 passed`

Bloqueos actuales:

- no hay bloqueo inmediato de entorno

Siguiente paso recomendado:

- iniciar Fase 1 y Fase 2 de implementación real
- añadir persistencia de configuración
- implementar runtime local del daemon con PID y archivo de estado
- hacer funcionales `mcp-cli start`, `mcp-cli stop` y `mcp-cli status`

### 2026-04-04 | Fase 1-2 | Configuración persistente y runtime local del daemon

Trabajo realizado:

- persistencia de configuración con `save_settings`
- almacenamiento local de estado del daemon
- helpers de PID con limpieza y verificación de proceso
- helpers de control del daemon para arranque, parada y diagnóstico
- creación de `universal_mcp.daemon.server` como entrypoint real de proceso en segundo plano
- activación funcional de `mcp-cli start`
- activación funcional de `mcp-cli stop`
- activación funcional de `mcp-cli status`
- persistencia funcional de cambio de perfil con `mcp-cli profile use`
- mejora de detección de puerto ocupado antes del arranque

Archivos principales afectados:

- `universal_mcp/config/settings.py`
- `universal_mcp/runtime/pid.py`
- `universal_mcp/runtime/paths.py`
- `universal_mcp/runtime/state_store.py`
- `universal_mcp/runtime/daemon_control.py`
- `universal_mcp/daemon/server.py`
- `universal_mcp/cli/main.py`
- `tests/test_runtime_state.py`

Verificaciones ejecutadas:

- `python3 -m compileall universal_mcp tests` -> correcto
- `python3 -m pytest -q` -> correcto
- smoke test real de CLI:
  - `python3 -m universal_mcp.cli.main start`
  - `python3 -m universal_mcp.cli.main status`
  - `python3 -m universal_mcp.cli.main stop`

Resultado:

- suite actual en verde: `5 passed`
- runtime local básico operativo
- el daemon arranca como proceso separado
- el CLI ya puede detectar daemon activo, detenido o inconsistente
- el estado se persiste en runtime local

Incidencias observadas:

- en el workspace principal el puerto por defecto `8765` estaba ocupado por otro proceso ajeno
- dentro del sandbox no fue fiable validar el bind local del daemon, por lo que la smoke test real se ejecutó fuera del sandbox

Conclusión de la fase:

- la base operativa mínima ya existe
- falta todavía conectar supervisión real de MCP, health checks efectivos y superficie HTTP útil más allá de `healthz` y `status`

Siguiente paso recomendado:

- iniciar Fase 3 y Fase 4
- implementar supervisor real de procesos MCP en `process_router.py`
- conectar `server.py` con estados reales de procesos
- ampliar `multiplexer.py` con superficie HTTP + SSE útil

### 2026-04-04 | Fase 3-4 | Supervisor real de procesos y superficie HTTP + SSE

Trabajo realizado:

- sustitución del `ProcessRouter` stub por supervisión real de subprocesos
- arranque de procesos por entrada de catálogo habilitada
- detección explícita de comandos no disponibles
- refresco periódico de estado de procesos
- filtrado del catálogo según el perfil activo
- persistencia periódica de `daemon-state.json`
- ampliación del multiplexer con endpoint `/events` por SSE
- conexión del daemon a estados reales en tiempo de ejecución

Archivos principales afectados:

- `universal_mcp/config/catalog.py`
- `universal_mcp/daemon/process_router.py`
- `universal_mcp/daemon/multiplexer.py`
- `universal_mcp/daemon/server.py`
- `tests/test_process_router.py`

Verificaciones ejecutadas:

- `python3 -m compileall universal_mcp tests` -> correcto
- `python3 -m pytest -q` -> correcto
- smoke test real ordenada fuera del sandbox:
  - `python3 -m universal_mcp.cli.main start`
  - `python3 -m universal_mcp.cli.main status`
  - inspección de `.universal_mcp_runtime/daemon-state.json`
  - `python3 -m universal_mcp.cli.main stop`

Resultado:

- suite actual en verde: `7 passed`
- el daemon ya refleja estados reales de procesos supervisados
- el perfil activo limita qué MCP se intentan levantar
- el estado persistido muestra errores auténticos de disponibilidad del entorno
- el endpoint SSE básico queda preparado para consumo futuro

Hallazgos relevantes:

- en la smoke test con perfil mínimo, `filesystem` arrancó y salió con código `0`, quedando marcado como `failed`
- `git` quedó marcado como `failed` por ausencia real de `uvx` en el entorno
- esto confirma que la supervisión ya no es simulada: el daemon está reportando comportamiento real del sistema

Limitaciones actuales:

- todavía no hay restart automático con backoff efectivo por MCP
- todavía no hay health checks específicos por tipo de servidor
- el multiplexor aún no reenvía tráfico MCP útil, solo expone estado y SSE básico
- la semántica de “healthy” sigue basada en vida del proceso, no en handshake MCP

Siguiente paso recomendado:

- iniciar Fase 5 y 6
- implementar `memory_filter.py` con políticas completas de truncado y paginación
- ampliar `translator.py` con normalización real de payloads
- añadir tests de truncado, paginación y traducción

### 2026-04-04 | Fase 5-6 | Filtro de memoria y traducción mínima de payloads

Trabajo realizado:

- implementación completa de políticas de truncado de texto
- soporte de truncado por líneas para logs y diffs
- soporte de paginación para listas
- truncado selectivo de campos grandes en objetos
- política general `apply_response_policy` para strings, listas y diccionarios
- normalización mínima de payloads de herramientas
- traducción específica inicial para `claude-code`
- traducción inicial a formato de función para `openai`
- ruta genérica con avisos para clientes no especializados

Archivos principales afectados:

- `universal_mcp/daemon/memory_filter.py`
- `universal_mcp/daemon/translator.py`
- `tests/test_memory_filter.py`
- `tests/test_translator.py`

Verificaciones ejecutadas:

- `python3 -m compileall universal_mcp tests` -> correcto
- `python3 -m pytest -q` -> correcto

Resultado:

- suite actual en verde: `15 passed`
- `memory_filter.py` ya no es un stub, sino una librería reutilizable con políticas concretas de V1
- `translator.py` ya aplica normalización y traducción útil en vez de solo encapsular payloads

Limitaciones actuales:

- las políticas de truncado todavía no están integradas en el flujo HTTP del daemon
- la traducción aún no participa en una ruta end-to-end de multiplexación MCP
- faltan health checks específicos por tipo de servidor
- falta implementar restart con backoff efectivo y contadores reales de reinicio
- el wrapper aún es básico

Siguiente paso recomendado:

- iniciar Fase 7 y 8
- convertir el CLI en una capa operativa más completa
- implementar `mcp-cli run` con inyección real de entorno
- desarrollar onboarding inicial
- empezar a conectar `memory_filter` y `translator` al camino de request/response del daemon

### 2026-04-04 | Fase 7-8 | CLI operativo, onboarding y wrapper funcional

Trabajo realizado:

- creación de `ensure_settings` para autocreación de configuración
- onboarding capaz de bootstrapear `.universal_mcp.json`
- mejora del comando `run` para aceptar argumentos arbitrarios del proceso hijo
- construcción de entorno inyectado para clientes externos
- implementación real de `run_wrapped_command` con `subprocess.Popen`
- persistencia automática del perfil por defecto
- ampliación de pruebas de CLI con `CliRunner`

Archivos principales afectados:

- `universal_mcp/config/settings.py`
- `universal_mcp/cli/onboarding.py`
- `universal_mcp/cli/wrapper.py`
- `universal_mcp/cli/main.py`
- `tests/test_cli_wrapper.py`

Verificaciones ejecutadas:

- `python3 -m compileall universal_mcp tests` -> correcto
- `python3 -m pytest -q` -> correcto

Resultado:

- suite actual en verde: `19 passed`
- `mcp-cli onboarding` ya crea configuración inicial usable
- `mcp-cli run` ya inyecta variables de entorno reales al subproceso hijo
- el CLI acepta flags del proceso envuelto sin confundirlos con opciones propias
- el wrapper ya cumple el diseño base de lanzamiento efímero con entorno acotado

Limitaciones actuales:

- el wrapper aún no traduce configuración a formatos específicos de clientes externos
- onboarding sigue siendo básico y no pide credenciales interactivamente
- `run` no consume todavía secretos por perfil ni los proyecta sobre MCP reales
- el daemon aún no integra `memory_filter` y `translator` en un flujo request/response real
- faltan logs consultables desde CLI

Siguiente paso recomendado:

- iniciar Fase 9 y 10
- integrar observabilidad consultable desde CLI
- conectar `memory_filter` y `translator` al flujo del daemon
- avanzar en integración efectiva del catálogo V1 sobre rutas de multiplexación reales

### 2026-04-04 | Fase 9-10 | Observabilidad consultable e integración inicial del flujo del daemon

Trabajo realizado:

- ampliación de runtime con `events.jsonl`
- persistencia de eventos estructurados JSON-lines
- lectura filtrable de eventos por nivel y por MCP
- incorporación del comando `mcp-cli logs`
- registro de eventos de arranque, parada y cambio de estado de procesos
- incorporación de la ruta `/tool-preview` en el daemon
- integración inicial de `translator` y `memory_filter` dentro de un flujo real de preview

Archivos principales afectados:

- `universal_mcp/runtime/paths.py`
- `universal_mcp/observability/logging.py`
- `universal_mcp/daemon/multiplexer.py`
- `universal_mcp/daemon/server.py`
- `universal_mcp/cli/main.py`
- `tests/test_observability.py`
- `tests/test_cli_logs.py`

Verificaciones ejecutadas:

- `python3 -m compileall universal_mcp tests` -> correcto
- `python3 -m pytest -q` -> correcto
- smoke test real fuera del sandbox:
  - `python3 -m universal_mcp.cli.main start`
  - `python3 -m universal_mcp.cli.main logs`
  - `python3 -m universal_mcp.cli.main stop`

Resultado:

- suite actual en verde: `21 passed`
- `mcp-cli logs` ya muestra eventos estructurados útiles para operación
- el daemon registra transiciones reales de estado por MCP
- existe una primera ruta HTTP que ya usa traducción y filtrado en el mismo flujo

Hallazgos relevantes de la smoke test:

- el flujo de logs mostró eventos reales como:
  - `daemon_started`
  - cambios de estado de `filesystem`
  - fallo real de `git` por entorno
  - `daemon_stopped`
- esto confirma que la observabilidad ya no es teórica ni puramente documental

Limitaciones actuales:

- la ruta `/tool-preview` es una integración inicial, no una multiplexación MCP completa
- faltan endpoints y routing reales hacia herramientas MCP
- el supervisor aún no aplica restart con backoff real
- no hay health checks específicos por tipo de servidor
- el manejo de secretos por perfil todavía no está conectado al arranque efectivo de MCP externos

Siguiente paso recomendado:

- iniciar Fase 11 y la integración efectiva del catálogo V1
- diseñar y construir rutas reales de multiplexación hacia MCP gestionados
- incorporar health checks específicos y restart con backoff
- empezar a conectar secretos y configuración por perfil al lanzamiento de procesos reales

### 2026-04-04 | Fase 11 | Integración operativa del catálogo V1 y supervisión reforzada

Trabajo realizado:

- implementación de health checks básicos orientados a proceso
- incorporación de restart programado con backoff y límite de reintentos
- incorporación de reinicio manual por MCP desde el daemon
- ampliación del `ProcessRouter` para aceptar entorno por proceso
- proyección de configuración de perfil hacia variables de entorno por servicio
- incorporación de rutas `/mcps` y `/mcps/{name}/restart`
- ampliación de pruebas de helpers de servidor y health checks

Archivos principales afectados:

- `universal_mcp/daemon/health.py`
- `universal_mcp/daemon/process_router.py`
- `universal_mcp/daemon/multiplexer.py`
- `universal_mcp/daemon/server.py`
- `tests/test_health.py`
- `tests/test_server_helpers.py`

Verificaciones ejecutadas:

- `python3 -m compileall universal_mcp tests` -> correcto
- `python3 -m pytest -q` -> correcto
- smoke test real fuera del sandbox:
  - `python3 -m universal_mcp.cli.main start`
  - consulta HTTP a `http://127.0.0.1:8876/mcps`
  - `python3 -m universal_mcp.cli.main logs --level info`
  - `python3 -m universal_mcp.cli.main stop`

Resultado:

- suite actual en verde: `25 passed`
- el daemon expone ya un inventario operativo de MCP gestionados
- el supervisor aplica degradación y fallo tras reintentos
- el sistema proyecta configuración por perfil al proceso hijo
- los eventos de observabilidad ya reflejan también la transición `healthy -> degraded -> failed`

Hallazgos relevantes de la smoke test:

- `/mcps` devolvió estado real por MCP, incluyendo `filesystem` y `git`
- `filesystem` progresó de `healthy` a `degraded` y después a `failed`
- `git` reflejó fallo del entorno por ausencia de `uvx`
- la secuencia quedó reflejada en `mcp-cli logs`

Limitaciones actuales:

- sigue sin existir multiplexación MCP completa a nivel de protocolo
- el restart con backoff está orientado a proceso, no a handshake MCP real
- los secrets por perfil se proyectan desde entorno, pero todavía sin backend seguro dedicado
- faltan endpoints de ejecución o passthrough real hacia herramientas MCP gestionadas

Siguiente paso recomendado:

- construir una primera capa de passthrough real o proxy controlado hacia MCP gestionados
- definir el contrato interno de request/response para herramientas
- conectar `translator`, `memory_filter` y observabilidad a ese flujo end-to-end
- decidir si la siguiente iteración prioriza un MCP concreto de referencia para integración real

### 2026-04-04 | MCP 1 | Integración real de `filesystem`

Objetivo de la iteración:

- tomar `filesystem` como primer MCP integrado extremo a extremo
- no pasar al siguiente MCP hasta que el patrón base quede sólido

Trabajo realizado:

- creación de `filesystem_adapter.py` como adaptador interno seguro
- resolución de rutas restringida al workspace raíz del daemon
- implementación de listado de directorios
- implementación de lectura parcial de archivos
- exposición de rutas:
  - `/filesystem/list`
  - `/filesystem/read`
- integración de `memory_filter` sobre respuestas de filesystem
- integración de eventos de observabilidad específicos de filesystem
- cobertura de tests para adaptador y handlers

Archivos principales afectados:

- `universal_mcp/daemon/filesystem_adapter.py`
- `universal_mcp/daemon/multiplexer.py`
- `universal_mcp/daemon/server.py`
- `tests/test_filesystem_adapter.py`
- `tests/test_server_filesystem.py`

Verificaciones ejecutadas:

- `python3 -m compileall universal_mcp tests` -> correcto
- `python3 -m pytest -q` -> correcto
- smoke test real fuera del sandbox:
  - creación de `fs_demo.txt` en `tmp_smoke`
  - `python3 -m universal_mcp.cli.main start`
  - consulta HTTP a `GET /filesystem/list?path=.`
  - consulta HTTP a `POST /filesystem/read`
  - `python3 -m universal_mcp.cli.main logs --mcp filesystem`
  - `python3 -m universal_mcp.cli.main stop`

Resultado:

- suite actual en verde: `29 passed`
- `filesystem` ya es el primer MCP integrado con utilidad real
- el daemon puede listar el workspace y leer archivos concretos
- las respuestas pasan por filtrado y quedan observadas en logs
- la integración ya no depende de un servidor externo para ofrecer valor

Resultado observado en la smoke test:

- `GET /filesystem/list?path=.` devolvió el inventario real del workspace
- `POST /filesystem/read` devolvió el contenido de `fs_demo.txt`
- `mcp-cli logs --mcp filesystem` mostró eventos de `filesystem_list` y `filesystem_read`

Conclusión:

- `filesystem` queda aceptado como primer MCP de referencia de la arquitectura
- el patrón base de integración real ya existe y servirá para los siguientes MCP

Limitaciones pendientes antes de pasar al siguiente MCP:

- revisar si `filesystem` debe dejar de depender del supervisor de procesos externo en paralelo
- definir una capa común para MCP internos frente a MCP externos
- decidir el contrato definitivo de ejecución de herramientas, no solo rutas específicas

Siguiente paso recomendado:

- consolidar la abstracción entre MCP internos y externos
- usar `filesystem` como patrón para el siguiente MCP candidato
- mi recomendación siguiente es `git`, pero solo después de cerrar esa abstracción común

### 2026-04-04 | Consolidación de arquitectura | MCP internos vs MCP externos

Objetivo de la iteración:

- evitar que `filesystem` quede como una excepción aislada
- separar el modelo de MCP internos del de MCP externos supervisados por proceso

Trabajo realizado:

- incorporación de `IntegrationKind` en el catálogo
- clasificación explícita entre entradas `internal` y `external`
- separación del catálogo en tiempo de arranque del daemon
- exclusión de MCP internos del supervisor de procesos externos
- consolidación de un patrón común de handlers internos dentro de `server.py`

Archivos principales afectados:

- `universal_mcp/config/catalog.py`
- `universal_mcp/daemon/server.py`

Resultado:

- la arquitectura ya distingue correctamente entre:
  - MCP internos integrados en el daemon
  - MCP externos lanzados y supervisados como procesos

Conclusión:

- esta consolidación era necesaria antes de añadir el siguiente MCP
- evita arrastrar una mezcla confusa al resto de integraciones

### 2026-04-04 | MCP 2 | Integración real de `git`

Objetivo de la iteración:

- integrar `git` como segundo MCP real siguiendo el mismo criterio que `filesystem`
- no avanzar a otro MCP sin dejar `git` probado extremo a extremo

Trabajo realizado:

- creación de `git_adapter.py` como adaptador interno
- implementación de `git status`
- implementación de `git diff`
- soporte de repos recién inicializados sin commits previos
- exposición de rutas:
  - `GET /git/status`
  - `POST /git/diff`
- integración de `memory_filter` sobre respuestas de diff
- integración de observabilidad específica de git

Archivos principales afectados:

- `universal_mcp/daemon/git_adapter.py`
- `universal_mcp/daemon/multiplexer.py`
- `universal_mcp/daemon/server.py`
- `tests/test_git_adapter.py`
- `tests/test_server_git.py`

Verificaciones ejecutadas:

- `python3 -m compileall universal_mcp tests` -> correcto
- `python3 -m pytest -q` -> correcto
- smoke test real fuera del sandbox:
  - inicialización de repo git en `tmp_smoke`
  - `python3 -m universal_mcp.cli.main start`
  - consulta HTTP a `GET /git/status`
  - modificación real del repositorio
  - consulta HTTP a `POST /git/diff`
  - `python3 -m universal_mcp.cli.main logs --mcp git`
  - `python3 -m universal_mcp.cli.main stop`

Resultado:

- suite actual en verde: `32 passed`
- `git` queda integrado como MCP interno real
- el daemon puede devolver estado de repo y diff real del workspace
- `git` ya genera eventos específicos en observabilidad

Resultado observado en la smoke test:

- `GET /git/status` devolvió rama y salida `porcelain`
- `POST /git/diff` devolvió un diff real tras modificar `git_demo.txt`
- `mcp-cli logs --mcp git` mostró eventos `git_status` y `git_diff`

Conclusión:

- `git` queda aceptado como MCP 2 siguiendo el patrón correcto
- el patrón interno ya está probado con dos MCP reales distintos

Limitaciones pendientes antes del siguiente MCP:

- aún falta una capa más general de contrato de herramientas, no solo rutas por MCP
- los MCP externos siguen en un nivel de integración inferior al de los internos
- la gestión de secretos seguros sigue pendiente para conectores como `github` o `postgres`

Siguiente paso recomendado:

- no saltar todavía a `github` o `postgres`
- primero conviene extraer una capa común de “tool execution” para MCP internos
- después elegir entre:
  - `github` como primer MCP externo con secreto
  - `postgres` como primer MCP externo con conexión sensible
- mi recomendación es `github` primero, porque su validación funcional y observabilidad serán más controlables que `postgres`

### 2026-04-04 | Decisión de producto | Cambio de cliente principal a `Codex CLI`

Motivo:

- reducir dependencia de restricciones cambiantes en herramientas de terceros apoyadas sobre suscripciones Claude
- concentrar la V1 en un cliente principal más estable para el desarrollo del orquestador

Trabajo realizado:

- actualización del documento base de arquitectura
- actualización del plan técnico
- actualización de `README.md`
- cambio del cliente por defecto en configuración de perfiles a `codex-cli`
- actualización del target por defecto de traducción y preview a `codex-cli`
- conservación de compatibilidad alias para `claude-code` en la capa de traducción

Archivos principales afectados:

- `Investigación de Servidores MCP para Desarrollo - v2.md`
- `Plan Técnico de Desarrollo - V1.md`
- `README.md`
- `Bitácora de Desarrollo - V1.md`
- `universal_mcp/config/profiles.py`
- `universal_mcp/daemon/translator.py`
- `universal_mcp/daemon/multiplexer.py`
- `universal_mcp/daemon/server.py`

Verificaciones ejecutadas:

- `python3 -m compileall universal_mcp tests` -> correcto
- `python3 -m pytest -q` -> correcto

Resultado:

- suite actual en verde: `32 passed`
- la V1 queda alineada con `Codex CLI` como cliente principal
- `Claude Code` queda relegado a compatibilidad futura u opcional

Siguiente paso recomendado:

- retomar el desarrollo desde la arquitectura ya consolidada
- mantener `Codex CLI` como cliente principal de validación
- elegir el siguiente MCP externo con el mismo criterio incremental

### 2026-04-04 | Consolidación técnica | Capa común de ejecución para MCP internos

Objetivo de la iteración:

- extraer una abstracción común para MCP internos antes de introducir conectores externos más complejos
- evitar que `filesystem` y `git` sigan implementados como casos especiales dispersos en `server.py`

Trabajo realizado:

- creación de `internal_tools.py`
- extracción de resolución común de workspace
- extracción de construcción de `request_id`
- extracción de aplicación de `memory_filter`
- extracción de formateo común de `filter_metadata`
- extracción del patrón común de observabilidad para herramientas internas
- refactorización de handlers de `filesystem` y `git` para usar la nueva capa

Archivos principales afectados:

- `universal_mcp/daemon/internal_tools.py`
- `universal_mcp/daemon/server.py`

Verificaciones ejecutadas:

- `python3 -m compileall universal_mcp tests` -> correcto
- `python3 -m pytest -q` -> correcto

Resultado:

- suite actual en verde: `32 passed`
- `filesystem` y `git` siguen funcionando igual, pero sobre una base común más limpia
- `server.py` queda menos acoplado a la implementación concreta de cada MCP interno

Conclusión:

- esta consolidación sí era necesaria
- ahora sí tiene sentido pasar al primer MCP externo serio sin arrastrar deuda de forma

Siguiente paso recomendado:

- iniciar MCP 3 con un conector externo real
- mantener el criterio incremental y la validación completa
- mi recomendación sigue siendo `github` antes que `postgres`

### 2026-04-04 | MCP 3 | Integración externa inicial de `github`

Objetivo de la iteración:

- tomar `github` como primer MCP externo serio
- cerrar primero configuración, preflight, proyección de entorno y observabilidad antes de prometer uso completo del servidor externo

Trabajo realizado:

- ampliación del estado con `ExternalMcpPreflight`
- incorporación de preflight específica para MCP externos
- proyección correcta del secreto GitHub a `GITHUB_PERSONAL_ACCESS_TOKEN`
- incorporación de validación previa para secretos requeridos
- incorporación de fallo temprano en el supervisor si faltan requisitos previos
- exposición de ruta:
  - `GET /github/preflight`

Archivos principales afectados:

- `universal_mcp/daemon/state.py`
- `universal_mcp/daemon/process_router.py`
- `universal_mcp/daemon/multiplexer.py`
- `universal_mcp/daemon/server.py`
- `tests/test_github_preflight.py`
- `tests/test_server_helpers.py`

Verificaciones ejecutadas:

- `python3 -m compileall universal_mcp tests` -> correcto
- `python3 -m pytest -q` -> correcto
- smoke test real fuera del sandbox:
  - actualización de `tmp_smoke/.universal_mcp.json` para habilitar `github`
  - arranque del daemon con `UNIVERSAL_MCP_SECRET_GITHUB_TOKEN`
  - consulta HTTP a `GET /github/preflight`
  - consulta HTTP a `GET /mcps`
  - `python3 -m universal_mcp.cli.main logs --mcp github`
  - `python3 -m universal_mcp.cli.main stop`

Resultado:

- suite actual en verde: `34 passed`
- `github` ya está integrado como MCP externo a nivel de:
  - configuración
  - validación previa
  - proyección de entorno
  - observabilidad
  - estado de proceso

Resultado observado en la smoke test:

- `GET /github/preflight` devolvió:
  - `enabled: true`
  - `executable_available: true`
  - `required_env_present: true`
  - `env_keys: [\"GITHUB_PERSONAL_ACCESS_TOKEN\"]`
- `GET /mcps` reflejó el estado real del proceso `github`
- `mcp-cli logs --mcp github` mostró la transición:
  - `healthy`
  - `degraded`
  - `failed`

Conclusión:

- `github` queda aceptado como MCP 3 en integración externa inicial
- la parte cerrada es la de preflight, arranque y observabilidad
- todavía no puede considerarse una integración funcional completa de herramientas GitHub

Limitaciones pendientes antes de considerarlo “perfecto”:

- no existe aún passthrough MCP real de herramientas GitHub a nivel de protocolo
- no hay validación contra operaciones concretas del servidor GitHub
- sigue faltando una capa común de ejecución para MCP externos comparable a la que ya existe para internos

Siguiente paso recomendado:

- no pasar todavía a `postgres`
- consolidar ahora la abstracción común de MCP externos
- después decidir si se completa `github` con passthrough real o si se abre ese patrón con un proxy/protocolo común

### 2026-04-04 | Consolidación técnica | Capa común de ejecución para MCP externos

Objetivo de la iteración:

- dejar de tratar el primer MCP externo como un mero proceso supervisado
- crear una base común real para sesiones MCP externas sobre stdio

Trabajo realizado:

- creación de `external_mcp.py`
- implementación de sesión stdio JSON-RPC mínima
- soporte de:
  - `initialize`
  - `tools/list`
  - `tools/call`
- conexión de `ProcessRouter` con sesiones MCP externas
- exposición de rutas genéricas:
  - `GET /external/{name}/tools`
  - `POST /external/{name}/tools/{tool_name}`
- incorporación de test con servidor MCP falso controlado

Archivos principales afectados:

- `universal_mcp/daemon/external_mcp.py`
- `universal_mcp/daemon/process_router.py`
- `universal_mcp/daemon/multiplexer.py`
- `universal_mcp/daemon/server.py`
- `tests/test_external_mcp.py`

Verificaciones ejecutadas:

- `python3 -m compileall universal_mcp tests` -> correcto
- `python3 -m pytest -q` -> correcto

Resultado:

- suite actual en verde: `35 passed`
- ya existe una capa común de MCP externos comparable a la que se creó antes para MCP internos

### 2026-04-04 | MCP 3 | Cierre real de `github`

Objetivo de la iteración:

- completar `github` más allá del preflight
- verificar que el daemon puede hablar con el servidor MCP real y descubrir herramientas

Trabajo realizado:

- uso de la nueva capa común de MCP externos sobre el proceso `github`
- validación de `initialize` real del servidor
- validación de `tools/list` real del servidor GitHub MCP
- observabilidad del listado de herramientas

Verificaciones ejecutadas:

- arranque del daemon con `UNIVERSAL_MCP_SECRET_GITHUB_TOKEN`
- consulta HTTP a `GET /external/github/tools`
- `python3 -m universal_mcp.cli.main logs --mcp github`
- `python3 -m universal_mcp.cli.main stop`

Resultado:

- `github` ya no está solo en preflight
- el daemon pudo descubrir herramientas reales del servidor GitHub MCP
- la respuesta incluyó un inventario amplio de herramientas GitHub reales
- se registró en observabilidad el evento `external_tools_list`

Resultado observado en la smoke test:

- `GET /external/github/tools` devolvió herramientas reales como:
  - `create_or_update_file`
  - `search_repositories`
  - `create_issue`
  - `create_pull_request`
  - `get_pull_request`
- `mcp-cli logs --mcp github` reflejó el evento de listado real

Conclusión:

- `github` queda ya cerrado como MCP 3 funcional a nivel de:
  - preflight
  - arranque
  - sesión MCP real
  - descubrimiento de herramientas
  - observabilidad

Pendiente para considerar la integración totalmente madura:

- probar `tools/call` con una llamada real y controlada
- decidir si se usa token real del usuario para validación final de una operación segura

Siguiente paso recomendado:

- antes de pasar a otro MCP, validar al menos una `tools/call` inocua sobre `github`
- si esa llamada sale bien, `github` podrá considerarse suficientemente cerrado para pasar a `postgres`

### 2026-04-04 | MCP 3 | Validación de `tools/call` segura sobre `github`

Objetivo de la iteración:

- comprobar que el passthrough MCP externo no solo lista herramientas, sino que también puede ejecutar una llamada segura de solo lectura

Trabajo realizado:

- arranque del daemon con `github` habilitado
- intento de llamada segura a:
  - `POST /external/github/tools/search_repositories`

Verificaciones ejecutadas:

- arranque real del daemon con `UNIVERSAL_MCP_SECRET_GITHUB_TOKEN`
- llamada HTTP real al endpoint externo de tools call
- inspección de `daemon.log`
- parada ordenada del daemon

Resultado:

- la integración de passthrough llegó hasta el servidor MCP real
- la llamada falló con error de autenticación del propio servidor GitHub MCP

Diagnóstico confirmado:

- el error real fue:
  - `Authentication Failed: Bad credentials`
- esto confirma que:
  - el routing hacia `tools/call` funciona
  - la sesión MCP externa funciona
  - el bloqueo actual no es arquitectónico
  - el bloqueo es la falta de credenciales GitHub válidas para una validación final

Conclusión:

- `github` queda técnicamente cerrado hasta el punto en que el siguiente paso depende de un token real
- para considerar el MCP completamente validado falta una última prueba con credenciales válidas del usuario

Siguiente paso recomendado:

- si quieres cerrar `github` de forma definitiva, usar un token real de tu cuenta para una `tools/call` segura de lectura
- si prefieres no hacerlo aún, la integración puede considerarse cerrada a nivel técnico y seguir después con el siguiente frente

### 2026-04-05 | MCP 3 | Cierre real de `github` con credenciales válidas

Objetivo de la iteración:

- completar la validación final de `github` con una llamada MCP real, segura y de solo lectura

Trabajo realizado:

- preparación de `tmp_smoke/.universal_mcp.json` con:
  - puerto `8891`
  - perfil `work`
  - MCP habilitados: `filesystem`, `git`, `github`
  - `services.github.secret_ref = github_token`
- arranque real del daemon con secreto GitHub proyectado al proceso hijo
- ejecución de:
  - `GET /github/preflight`
  - `GET /external/github/tools`
  - `POST /external/github/tools/search_repositories`

Verificaciones ejecutadas:

- espera activa de `GET /healthz`
- validación de preflight del MCP `github`
- listado real de herramientas MCP
- llamada real segura de lectura a `search_repositories`
- parada ordenada del daemon al final de la prueba

Resultado:

- `github/preflight` devolvió:
  - `enabled: true`
  - `executable_available: true`
  - `required_env_present: true`
  - `process_state: healthy`
- `GET /external/github/tools` devolvió `26` herramientas
- la llamada a `search_repositories` devolvió resultados reales y válidos
- quedaron confirmados extremo a extremo:
  - arranque
  - proyección de secretos
  - sesión MCP externa
  - `tools/list`
  - `tools/call`

Conclusión:

- `github` queda cerrado como MCP 3 funcional y validado de extremo a extremo
- la arquitectura para MCP externos queda confirmada con una integración real, no solo con preflight

Nota operativa:

- como el token GitHub se compartió en el canal de trabajo y se usó para validación, conviene rotarlo al cerrar esta fase

Siguiente paso recomendado:

- pasar a `postgres` como MCP 4 siguiendo el mismo criterio
- mantener la disciplina de integración incremental: preflight, sesión, llamada segura, observabilidad y cierre antes de pasar al siguiente

### 2026-04-05 | MCP 4 | Integración operativa inicial de `postgres`

Objetivo de la iteración:

- llevar `postgres` al mismo nivel operativo base que `github`
- validar preflight real, sesión MCP real y manejo correcto de errores de conexión

Trabajo realizado:

- generalización del preflight externo en:
  - `GET /external/{name}/preflight`
  - alias de compatibilidad:
    - `GET /github/preflight`
    - `GET /postgres/preflight`
- alineación del preflight de `postgres` con el contrato real del servidor `mcp-postgres-server`
- validación de requisitos mínimos de `postgres`:
  - `PG_HOST`
  - `PG_PORT`
  - `PG_USER`
  - `PG_PASSWORD`
  - `PG_DATABASE`
- normalización de errores de MCP externos para evitar `500` genéricos y devolver `502` con detalle estructurado

Archivos afectados:

- `universal_mcp/daemon/multiplexer.py`
- `universal_mcp/daemon/server.py`
- `tests/test_github_preflight.py`

Verificaciones ejecutadas:

- `python3 -m compileall universal_mcp tests`
- `python3 -m pytest -q` -> `38 passed`
- smoke test real fuera del sandbox con `postgres` habilitado:
  - `GET /postgres/preflight`
  - `GET /external/postgres/tools`
  - `POST /external/postgres/tools/connect_db`

Resultado:

- `postgres/preflight` devolvió:
  - `enabled: true`
  - `executable_available: true`
  - `required_env_present: true`
  - `process_state: healthy`
- `GET /external/postgres/tools` devolvió `6` herramientas reales:
  - `connect_db`
  - `query`
  - `execute`
  - `list_schemas`
  - `list_tables`
  - `describe_table`
- `POST /external/postgres/tools/connect_db` devolvió un `502` estructurado
- el error confirmado fue del servidor MCP de Postgres al intentar conectar con una BD inexistente local:
  - `connect ECONNREFUSED 127.0.0.1:5432`

Conclusión:

- `postgres` queda cerrado a nivel de:
  - preflight
  - arranque
  - sesión MCP real
  - `tools/list`
  - `tools/call`
  - propagación de errores útil para CLI y debugging
- falta solo una validación final con una base PostgreSQL real para considerarlo completamente cerrado de extremo a extremo

Siguiente paso recomendado:

- si quieres cerrar `postgres` del todo, usar una base PostgreSQL real con credenciales válidas y probar una lectura segura como:
  - `connect_db`
  - `list_schemas`
  - `list_tables`
- si no quieres abrir todavía ese frente, el siguiente MCP razonable sería `ast-grep`, porque no introduce secretos ni conectividad externa

### 2026-04-05 | MCP 4 | Cierre real de `postgres` con base local de usuario

Objetivo de la iteración:

- cerrar `postgres` de extremo a extremo con una base PostgreSQL real y lecturas válidas
- no pasar al siguiente MCP hasta comprobar datos reales, no solo preflight o errores controlados

Trabajo realizado:

- detección de que el enfoque inicial con Docker y `127.0.0.1:5432` no era fiable en este entorno por interferencias del host
- descubrimiento de binarios locales de PostgreSQL 16:
  - `/usr/lib/postgresql/16/bin/initdb`
  - `/usr/lib/postgresql/16/bin/pg_ctl`
  - `/usr/lib/postgresql/16/bin/postgres`
- creación de un clúster PostgreSQL temporal de usuario en:
  - `/tmp/universal_mcp_pg_cluster`
- arranque del servidor local en:
  - host `127.0.0.1`
  - puerto `55432`
  - socket dir `/tmp`
- creación de la base `umcp_test`
- creación y carga de tabla de prueba:
  - `widgets(id, name, qty)`
  - filas:
    - `alpha, 3`
    - `beta, 7`

Verificaciones ejecutadas:

- verificación directa con `psql` sobre `127.0.0.1:55432`
- validación real del daemon en `8896`
- llamadas MCP reales:
  - `GET /postgres/preflight`
  - `GET /external/postgres/tools`
  - `POST /external/postgres/tools/connect_db`
  - `POST /external/postgres/tools/list_tables`
  - `POST /external/postgres/tools/query`

Resultado:

- `preflight` correcto con entorno completo:
  - `PG_HOST`
  - `PG_PORT`
  - `PG_USER`
  - `PG_PASSWORD`
  - `PG_DATABASE`
- `tools/list` devolvió las `6` herramientas reales del servidor `postgres`
- `connect_db` devolvió:
  - `Successfully connected to PostgreSQL database`
- `list_tables` devolvió la tabla real:
  - `widgets`
- `query` devolvió datos reales:
  - `id=1, name=alpha, qty=3`
  - `id=2, name=beta, qty=7`

Conclusión:

- `postgres` queda cerrado como MCP 4 funcional y validado de extremo a extremo
- la arquitectura externa queda confirmada también para un MCP con estado de conexión real y consultas sobre datos reales

Siguiente paso recomendado:

- pasar al siguiente MCP sin secretos ni conectividad compleja:
  - `ast-grep`
- mantener el mismo criterio:
  - integración
  - prueba real
  - bitácora
  - cierre antes del siguiente

### 2026-04-05 | MCP 5 | Cierre real de `ast-grep`

Objetivo de la iteración:

- integrar `ast-grep` como MCP externo de bajo riesgo
- validar descubrimiento de herramientas y una búsqueda estructural real sobre el repositorio

Trabajo realizado:

- corrección del catálogo para usar el servidor MCP oficial desde `uvx`:
  - `uvx --from git+https://github.com/ast-grep/ast-grep-mcp ast-grep-server`
- endurecimiento del preflight para exigir el binario local `ast-grep`
- instalación en espacio de usuario de:
  - `uv` / `uvx`
  - `ast-grep`

Archivos afectados:

- `universal_mcp/config/catalog.py`
- `universal_mcp/daemon/server.py`
- `tests/test_github_preflight.py`

Verificaciones ejecutadas:

- `python3 -m compileall universal_mcp tests`
- `python3 -m pytest -q` -> `39 passed`
- comprobación de binarios:
  - `uvx 0.11.3`
  - `ast-grep 0.42.1`
- smoke test real del daemon con `ast-grep` habilitado:
  - `GET /external/ast-grep/preflight`
  - `GET /external/ast-grep/tools`
  - `POST /external/ast-grep/tools/find_code`

Resultado:

- `preflight` correcto:
  - `enabled: true`
  - `executable_available: true`
  - `required_env_present: true`
  - `process_state: healthy`
- `tools/list` devolvió `4` herramientas reales:
  - `dump_syntax_tree`
  - `test_match_code_rule`
  - `find_code`
  - `find_code_by_rule`
- `find_code` funcionó sobre el repositorio real con patrón estructural Python
- búsqueda validada con patrón:
  - `return $EXPR`
- resultado real:
  - `Found 3 matches (showing first 3 of 154)`
  - coincidencias reales en `universal_mcp/cli/onboarding.py`

Conclusión:

- `ast-grep` queda cerrado como MCP 5 funcional y validado de extremo a extremo
- la arquitectura externa queda ya probada también con un MCP de análisis estructural local, sin secretos ni dependencias de servicio

Nota operativa:

- en algunos workspaces temporales de smoke test, el comando `stop` no pudo confirmar el apagado porque el PID ya no estaba activo
- no quedó ningún daemon vivo al cierre de la fase

Siguiente paso recomendado:

- pasar a `sequential-thinking` como siguiente MCP ligero de validación
- si prefieres priorizar valor práctico en vez de ligereza, reabrir `filesystem`/`git` para ampliar surface de herramientas antes de seguir añadiendo MCPs

### 2026-04-05 | Capacidad práctica | Ampliación de `filesystem`

Objetivo de la iteración:

- ampliar el valor práctico del orquestador antes de seguir añadiendo más MCP
- reforzar `filesystem` con operaciones útiles para revisión, depuración y navegación de código

Trabajo realizado:

- ampliación del adaptador de `filesystem` con nuevas operaciones:
  - `exists`
  - `stat`
  - `glob`
  - `search_text`
  - `read_many`
- ampliación de la capa común de herramientas internas para soportar asignación explícita del campo filtrado
- exposición de nuevas rutas HTTP:
  - `GET /filesystem/exists`
  - `GET /filesystem/stat`
  - `GET /filesystem/glob`
  - `POST /filesystem/search-text`
  - `POST /filesystem/read-many`

Archivos afectados:

- `universal_mcp/daemon/internal_tools.py`
- `universal_mcp/daemon/filesystem_adapter.py`
- `universal_mcp/daemon/multiplexer.py`
- `universal_mcp/daemon/server.py`
- `tests/test_filesystem_adapter.py`
- `tests/test_server_filesystem.py`

Verificaciones ejecutadas:

- `python3 -m compileall universal_mcp tests`
- `python3 -m pytest -q` -> `43 passed`
- smoke test real de `filesystem` en workspace temporal con:
  - `notes.txt`
  - `script.py`
  - `nested/more.txt`

Resultado:

- `exists` devolvió existencia correcta de `notes.txt`
- `stat` devolvió tamaño correcto de `notes.txt`
- `glob` devolvió coincidencias reales para `*.txt`
- `search-text` encontró la línea real con `needle`
- `read-many` devolvió contenido parcial de varios archivos en una sola llamada

Conclusión:

- `filesystem` queda ampliado y claramente más útil para trabajo diario sobre código
- el patrón de herramientas internas adicionales queda ya asentado para repetirlo en `git`

Siguiente paso recomendado:

- ampliar `git` con el mismo criterio práctico:
  - `changed_files`
  - `log`
  - `show`
  - `diff_file`
  - `branch`
- solo después decidir si volvemos a añadir otro MCP

### 2026-04-05 | Capacidad práctica | Ampliación de `git`

Objetivo de la iteración:

- ampliar `git` para cubrir operaciones de revisión y navegación de cambios más útiles en flujos reales con `Codex CLI`
- igualar el criterio práctico aplicado antes a `filesystem`

Trabajo realizado:

- ampliación del adaptador de `git` con nuevas operaciones:
  - `changed_files`
  - `branch`
  - `log`
  - `show`
  - `diff_file`
- exposición de nuevas rutas HTTP:
  - `GET /git/changed-files`
  - `GET /git/branch`
  - `POST /git/log`
  - `POST /git/show`
  - `POST /git/diff-file`

Archivos afectados:

- `universal_mcp/daemon/git_adapter.py`
- `universal_mcp/daemon/multiplexer.py`
- `universal_mcp/daemon/server.py`
- `tests/test_git_adapter.py`
- `tests/test_server_git.py`

Verificaciones ejecutadas:

- `python3 -m compileall universal_mcp tests`
- `python3 -m pytest -q` -> `46 passed`
- smoke test real con repo git temporal:
  - commit inicial `demo init`
  - cambio posterior en `demo.txt`
  - archivo sin track `notes.txt`

Resultado:

- `changed-files` devolvió archivos modificados y sin track del workspace
- `branch` devolvió la rama activa real
- `log` devolvió el commit real:
  - `demo init`
- `show` devolvió el patch real del commit
- `diff-file` devolvió el diff real y acotado de `demo.txt`

Conclusión:

- `git` queda ampliado y claramente más útil para análisis, revisión y debugging local
- el producto gana bastante más valor práctico con `filesystem + git` reforzados que con añadir MCPs ligeros sin superficie operativa real

Siguiente paso recomendado:

- decidir entre:
  - volver al plan de nuevos MCP y continuar con `sequential-thinking`
  - o hacer una fase corta de consolidación para exponer estas capacidades mejor desde CLI y onboarding

### 2026-04-05 | Consolidación | Exposición de capacidades en CLI y onboarding

Objetivo de la iteración:

- hacer visible desde CLI el estado real del producto sin tener que inspeccionar código, tests o bitácora
- consolidar onboarding y comandos de inspección antes de seguir con más MCP

Trabajo realizado:

- ampliación del onboarding para mostrar:
  - perfil por defecto
  - MCP habilitados
  - capacidades prácticas ya expuestas en `filesystem` y `git`
- nuevo comando:
  - `mcp-cli catalog`
- nuevo comando:
  - `mcp-cli doctor`
- nuevo comando:
  - `mcp-cli profile show`
- actualización del `README.md` para reflejar el estado actual real del proyecto

Archivos afectados:

- `universal_mcp/cli/onboarding.py`
- `universal_mcp/cli/views.py`
- `universal_mcp/cli/main.py`
- `tests/test_cli_wrapper.py`
- `README.md`

Verificaciones ejecutadas:

- `python3 -m compileall universal_mcp tests`
- `python3 -m pytest -q` -> `48 passed`
- smoke test real del CLI en workspace temporal:
  - `mcp-cli onboarding --force`
  - `mcp-cli catalog`
  - `mcp-cli profile show`
  - `mcp-cli doctor`

Resultado:

- `onboarding` ya informa de capacidades prácticas reales de `filesystem` y `git`
- `catalog` muestra el catálogo MCP con:
  - kind
  - risk
  - sharing
  - secrets
- `profile show` muestra el perfil activo y sus MCP habilitados
- `doctor` detecta prerequisitos faltantes de forma útil y legible

Conclusión:

- la base ya no solo funciona; también se puede inspeccionar y entender mejor desde CLI
- la consolidación reduce fricción para retomar trabajo y para diagnosticar entornos incompletos

Siguiente paso recomendado:

- volver al plan de MCP y continuar con `sequential-thinking`
- alternativa secundaria:
  - añadir una fase corta de CLI para invocar desde terminal algunas rutas internas ya existentes sin usar `curl`

### 2026-04-05 | MCP 6 | Cierre real de `sequential-thinking`

Objetivo de la iteración:

- validar `sequential-thinking` como MCP ligero sin secretos ni servicios externos
- comprobar que el passthrough externo funciona también para una tool orientada a razonamiento estructurado

Trabajo realizado:

- arranque real del daemon con `sequential-thinking` habilitado
- validación de:
  - `GET /external/sequential-thinking/preflight`
  - `GET /external/sequential-thinking/tools`
  - `POST /external/sequential-thinking/tools/sequentialthinking`

Verificaciones ejecutadas:

- discovery real del servidor MCP
- inspección del esquema real de la tool `sequentialthinking`
- llamada segura mínima con:
  - `thought`
  - `nextThoughtNeeded`
  - `thoughtNumber`
  - `totalThoughts`

Resultado:

- `preflight` correcto:
  - `enabled: true`
  - `executable_available: true`
  - `required_env_present: true`
  - `process_state: healthy`
- `tools/list` devolvió `1` tool real:
  - `sequentialthinking`
- `tools/call` devolvió respuesta válida del servidor:
  - `thoughtNumber: 1`
  - `totalThoughts: 1`
  - `nextThoughtNeeded: false`
  - `branches: []`
  - `thoughtHistoryLength: 1`

Conclusión:

- `sequential-thinking` queda cerrado como MCP 6 funcional y validado de extremo a extremo
- no fue necesario modificar código de integración porque la arquitectura existente ya lo soportaba correctamente

Siguiente paso recomendado:

- revisar si el catálogo V1 debe considerarse ya suficientemente cubierto para una primera entrega usable
- si seguimos ampliando, priorizar conectores con valor operativo claro antes que MCPs puramente accesorios

## Próximos pasos pendientes de V1

1. gestión real de secretos
   - backend de keyring cuando esté disponible
   - fallback local controlado
   - rotación y borrado desde CLI
2. onboarding guiado real
   - selección de MCP
   - configuración inicial de servicios
   - solicitud guiada de credenciales
3. gestión completa de perfiles
   - alta y edición de perfiles desde CLI
   - configuración de `services` por perfil sin editar JSON a mano
4. experiencia de integración final con Codex CLI
   - revisar wrapper, mensajes y flujo real de uso
5. endurecimiento de reutilización y compartición
   - explotar mejor `sharing_mode`
   - revisar política de reutilización entre perfiles y sesiones
6. endurecimiento final de UX operativa
   - mensajes más claros
   - documentación de uso diario
   - pulido de comandos y errores

### 2026-04-05 | Hueco 1 | Gestión real de secretos y servicios por perfil

Objetivo de la iteración:

- empezar a cerrar el hueco principal de V1 en torno a secretos y configuración operativa de servicios
- dejar de depender solo de variables de entorno y edición manual del JSON

Trabajo realizado:

- creación de almacén de secretos reusable en:
  - `universal_mcp/config/secrets.py`
- soporte de dos backends:
  - `keyring` si está disponible
  - fallback local controlado en `.universal_mcp.secrets.json`
- integración del almacén de secretos en la resolución del daemon:
  - `_resolve_secret`
  - `_service_env`
  - `_env_by_name`
  - `_preflight_errors_by_name`
- nuevos comandos CLI:
  - `mcp-cli secret list`
  - `mcp-cli secret set <ref> [value]`
  - `mcp-cli secret delete <ref>`
- nuevos comandos CLI para servicios por perfil:
  - `mcp-cli profile service show`
  - `mcp-cli profile service set`
  - `mcp-cli profile service remove`

Archivos afectados:

- `universal_mcp/config/secrets.py`
- `universal_mcp/daemon/server.py`
- `universal_mcp/cli/views.py`
- `universal_mcp/cli/main.py`
- `tests/test_secrets.py`
- `tests/test_server_helpers.py`
- `tests/test_cli_wrapper.py`

Verificaciones ejecutadas:

- `python3 -m compileall universal_mcp tests`
- `python3 -m pytest -q` -> `52 passed`
- validación manual en workspace temporal con:
  - `mcp-cli onboarding --force`
  - `mcp-cli secret set postgres_password demo-pw`
  - `mcp-cli profile service set work postgres --host 127.0.0.1 --port 55432 --database umcp_test --user postgres --secret-ref postgres_password`
  - `mcp-cli secret list`
  - `mcp-cli profile service show`
  - `mcp-cli doctor`

Resultado:

- el secreto queda persistido y visible desde CLI
- la configuración de servicio `postgres` se puede dar de alta desde CLI
- `doctor` ya reconoce correctamente:
  - `PG_DATABASE`
  - `PG_HOST`
  - `PG_PASSWORD`
  - `PG_PORT`
  - `PG_USER`
- se elimina la necesidad de editar `.universal_mcp.json` a mano para este caso

Conclusión:

- el hueco 1 queda parcialmente cubierto y la base ya es útil de verdad
- todavía falta para cerrar del todo este bloque:
  - keyring real probado en entorno con backend disponible
  - comandos de rotación y experiencia más guiada
  - integración más profunda con onboarding

Siguiente paso recomendado:

- seguir dentro del hueco 1 con una segunda fase:
  - mejorar onboarding para pedir y registrar secretos/servicios de forma guiada
  - revisar si añadimos comando explícito de rotación o actualización asistida

### 2026-04-05 | Diseño UX/CLI | Onboarding guiado real de V1

Objetivo de la iteración:

- aterrizar el diseño detallado del onboarding guiado antes de implementarlo
- definir una experiencia con identidad visual clara, pero apoyada en comprobaciones reales del sistema
- dejar decidido el flujo de prompts, checks, persistencia y resumen final para cerrar el hueco 1

Trabajo realizado:

- definición del tono visual del onboarding:
  - banner ASCII con `Universal MCP`
  - panel principal de identidad con estilo de consola operativa
  - enfoque "cinemático sobrio" sin checks falsos ni animaciones vacías
- definición de la secuencia del onboarding en cuatro bloques:
  - `Boot / Identity`
  - `Preflight`
  - `Guided setup`
  - `Final summary`
- definición del bloque `Boot / Identity`:
  - mostrar banner ASCII al inicio
  - renderizar un panel grande con:
    - `System: Universal Model Context Protocol (MCP) [1.0]`
    - `Mode: First-Run Onboarding`
    - `Workspace`
    - `Settings path`
    - `Default profile`
    - `Client target`
- definición del bloque `Preflight` con comprobaciones reales:
  - existencia o creación de `.universal_mcp.json`
  - validación del esquema `Settings` con Pydantic
  - resolución de workspace actual
  - carga del catálogo MCP
  - detección del backend de secretos:
    - `keyring`
    - fallback local
  - inspección del perfil por defecto
  - detección de secretos requeridos ausentes
  - detección de servicios parcialmente configurados
  - detección de binarios necesarios para MCP habilitados cuando aplique
- decisión de formato visual para el preflight:
  - cada check debe corresponder a una verificación real
  - estados permitidos:
    - `OK`
    - `WARN`
    - `INFO`
    - `FAIL`
  - ejemplos de salida esperada:
    - `OK  Settings schema validated`
    - `OK  MCP catalog loaded`
    - `WARN github_token missing`
    - `INFO keyring unavailable, using local fallback`
- definición del bloque `Guided setup`:
  - preguntar si se reutiliza el perfil por defecto o se ajusta sobre él
  - permitir seleccionar MCP habilitados del catálogo V1
  - para cada MCP con requisitos operativos:
    - pedir solo los datos necesarios
    - saltar MCP sin secretos ni servicios obligatorios
  - reglas iniciales por MCP:
    - `github`:
      - pedir `github_token`
      - opcionalmente permitir `host` para `GITHUB_API_URL`
    - `postgres`:
      - pedir `host`
      - pedir `port`
      - pedir `database`
      - pedir `user`
      - pedir contraseña y guardarla como secreto
      - guardar o reutilizar `secret_ref`
    - `filesystem`, `git`, `ast-grep`, `sequential-thinking`:
      - no pedir secretos
      - solo informar de que quedan habilitados
- definición de reglas de persistencia:
  - reutilizar la lógica ya existente en lugar de duplicarla
  - secretos:
    - persistir mediante `set_secret`
  - servicios:
    - persistir en `settings.profiles[profile].services`
  - perfiles:
    - actualizar `enabled_mcps` del perfil activo
    - guardar con `save_settings`
- definición de comportamiento para secretos ya existentes:
  - si un `secret_ref` ya existe, ofrecer:
    - reutilizar valor actual
    - reemplazarlo
    - posponer configuración
  - esta interacción cubre la primera versión de rotación/actualización asistida sin crear todavía un comando independiente
- definición de validación dentro del propio onboarding:
  - validar campos requeridos antes de persistir
  - impedir guardar `postgres` con configuración claramente incompleta si el MCP queda habilitado
  - permitir posponer un secreto, pero marcar el resultado final como incompleto con `WARN`
- definición del bloque `Final summary`:
  - tabla o panel con:
    - perfil activo
    - MCP habilitados
    - servicios configurados
    - secretos registrados
    - backend de secretos en uso
    - huecos pendientes detectados
  - cierre con siguientes comandos sugeridos:
    - `mcp-cli doctor`
    - `mcp-cli start`
    - `mcp-cli run codex`
- definición de alcance de implementación inmediata:
  - `universal_mcp/cli/onboarding.py`:
    - mover aquí el flujo guiado y los checks
  - `universal_mcp/cli/views.py`:
    - banner ASCII
    - panel de identidad
    - render de checks y resumen final
  - `universal_mcp/cli/main.py`:
    - delegar el comando `onboarding` en el flujo nuevo
  - `tests/test_cli_wrapper.py`:
    - cubrir primera ejecución
    - cubrir reutilización de configuración existente
    - cubrir captura guiada de secretos y servicios

Archivos afectados:

- `Bitácora de Desarrollo - V1.md`

Verificaciones ejecutadas:

- lectura del estado actual de:
  - plan técnico
  - bitácora
  - `universal_mcp/cli/onboarding.py`
  - `universal_mcp/cli/main.py`
  - `universal_mcp/config/secrets.py`
  - `universal_mcp/config/settings.py`
  - `universal_mcp/config/profiles.py`
- validación del estado actual del repositorio:
  - `python3 -m pytest -q` -> `52 passed`

Bloqueos detectados:

- no hay bloqueos técnicos para implementar esta fase
- queda pendiente comprobar `keyring` real en un entorno que disponga de backend operativo

Siguiente paso recomendado:

- implementar el nuevo onboarding guiado sobre la base ya existente
- empezar por:
  - componentes visuales en `views.py`
  - checks reales en `onboarding.py`
  - flujo guiado para `github` y `postgres`
  - tests del recorrido interactivo principal

### 2026-04-05 | Hueco 1 | Implementación del onboarding guiado real

Objetivo de la iteración:

- implementar la primera versión real del onboarding guiado definido en la fase de diseño
- convertir `mcp-cli onboarding` en un flujo visual e interactivo con checks reales y persistencia operativa

Trabajo realizado:

- ampliación de `views.py` con componentes visuales específicos de onboarding:
  - banner ASCII `Universal MCP`
  - panel `Boot / Identity`
  - tabla `Preflight`
  - panel `Final Summary`
- ampliación de `onboarding.py` con flujo guiado real:
  - bootstrap de configuración reutilizable
  - checks reales previos a la configuración
  - selección interactiva de MCP habilitados
  - configuración guiada de `github`
  - configuración guiada de `postgres`
  - reutilización o reemplazo de secretos existentes
  - cálculo de huecos pendientes tras la configuración
- integración del comando `mcp-cli onboarding` con el nuevo flujo:
  - render del bloque visual inicial
  - render de preflight antes de pedir datos
  - persistencia de cambios al finalizar
  - resumen final de perfil, MCP, servicios, secretos y pendientes
- ampliación del sistema de secretos con helper explícito para detectar backend:
  - `secret_backend_name`
- ampliación de tests CLI para cubrir:
  - nueva salida visual del onboarding
  - onboarding interactivo mínimo con defaults
  - onboarding guiado completo con `github` y `postgres`

Archivos afectados:

- `universal_mcp/cli/views.py`
- `universal_mcp/cli/onboarding.py`
- `universal_mcp/cli/main.py`
- `universal_mcp/config/secrets.py`
- `tests/test_cli_wrapper.py`

Verificaciones ejecutadas:

- `python3 -m compileall universal_mcp tests`
- `python3 -m pytest -q` -> `53 passed`

Resultado:

- `mcp-cli onboarding` ya no es solo bootstrap + resumen
- el comando ahora muestra identidad visual clara y checks reales del entorno
- el usuario puede habilitar MCP y configurar `github` y `postgres` sin editar JSON a mano
- los secretos quedan persistidos reutilizando la infraestructura ya existente
- el cierre del onboarding deja visible qué está listo y qué sigue pendiente

Bloqueos detectados:

- no hay bloqueos para esta fase
- sigue pendiente la validación real de `keyring` en un entorno con backend operativo

Siguiente paso recomendado:

- endurecer la UX del onboarding:
  - selección múltiple más cómoda que una cascada de confirmaciones
  - mensajes de validación más precisos en campos incompletos
  - posibilidad de posponer configuración por MCP con resumen más explícito
- después continuar con:
  - gestión completa de perfiles desde CLI
  - pulido final del flujo `mcp-cli run codex`

### 2026-04-06 | UX visual | Pulido de cabecera y checks del onboarding

Objetivo de la iteración:

- refinar la presentación visual del onboarding tras probarlo en terminal real
- acercar el banner ASCII al estilo visual objetivo sin reintroducir cajas innecesarias
- simplificar el bloque de checks para que el arranque se vea más limpio

Trabajo realizado:

- sustitución del banner ASCII inicial por una versión más grande y ornamental inspirada en la referencia visual aprobada
- eliminación del texto redundante `Universal MCP` que aparecía debajo del banner
- integración de la cabecera visual y los datos de identidad en un único bloque sin paneles adicionales
- eliminación de la línea separadora situada encima de la tabla de checks
- eliminación del título `Preflight` para dejar el bloque de comprobaciones más limpio
- actualización de la línea de sistema a:
  - `System: Universal Model Context Protocol (MCP) [1.0.0]`
- mantenimiento del enfoque visual minimalista:
  - sin cuadros extra alrededor del ASCII
  - sin panel intermedio para `Boot / Identity`
  - sin duplicación de títulos

Archivos afectados:

- `universal_mcp/cli/views.py`
- `tests/test_cli_wrapper.py`

Verificaciones ejecutadas:

- `python3 -m compileall universal_mcp/cli/views.py tests/test_cli_wrapper.py`
- `python3 -m pytest -q tests/test_cli_wrapper.py` -> `9 passed`

Resultado:

- el onboarding arranca con una cabecera más cercana a la estética deseada
- el encabezado ya no repite `Universal MCP` fuera del propio ASCII
- el bloque de checks queda visualmente más integrado y menos cargado
- la línea de sistema refleja ya la versión `1.0.0`

Bloqueos detectados:

- no hay bloqueos para este ajuste

Siguiente paso recomendado:

- continuar con mejoras funcionales del onboarding y la CLI
- evitar más complejidad decorativa salvo que aporte legibilidad real en terminal

### 2026-04-07 | Higiene de repositorio | Endurecimiento de `.gitignore`

Objetivo de la iteración:

- reducir el riesgo de commits accidentales de artefactos locales
- endurecer la higiene básica del repositorio antes de seguir iterando

Trabajo realizado:

- ampliación de `.gitignore` para cubrir:
  - caches adicionales de Python
  - artefactos de cobertura
  - salidas locales de build
  - configuraciones comunes de IDE
  - logs
  - fichero local `.universal_mcp.secrets.json`
- actualización de `README.md` para reflejar que el repositorio ya protege mejor secretos locales y artefactos de trabajo

Archivos afectados:

- `.gitignore`
- `README.md`
- `Bitácora de Desarrollo - V1.md`

Verificaciones ejecutadas:

- revisión manual del `.gitignore` resultante
- comprobación del estado git local antes de preparar commit

Resultado:

- el repositorio queda mejor protegido frente a commits accidentales de secretos locales, cobertura, logs y configuraciones de editor
- se reduce la necesidad de limpieza manual antes de futuros commits

Bloqueos detectados:

- no hay bloqueos para este ajuste

Siguiente paso recomendado:

- continuar con mejoras funcionales de perfiles, secretos y wrapper
- mantener el `.gitignore` corto y centrado en artefactos realmente locales

### 2026-04-07 | CLI de perfiles | Gestión completa básica desde terminal

Objetivo de la iteración:

- cubrir el hueco principal que quedaba tras validar el onboarding
- permitir gestionar perfiles desde CLI sin editar JSON a mano

Trabajo realizado:

- ampliación de `profile` con nuevos comandos:
  - `mcp-cli profile create`
  - `mcp-cli profile clone`
  - `mcp-cli profile delete`
  - `mcp-cli profile set-mcps`
- validación de MCP contra el catálogo V1 antes de persistir cambios
- protección frente al borrado del perfil por defecto activo
- mantenimiento del comportamiento existente de:
  - `profile list`
  - `profile show`
  - `profile use`
- ampliación de tests CLI para cubrir:
  - creación de perfil con MCP explícitos
  - clonado profundo de perfil
  - reasignación de MCP habilitados
  - rechazo del borrado del perfil por defecto

Archivos afectados:

- `universal_mcp/cli/main.py`
- `tests/test_cli_wrapper.py`
- `README.md`
- `Bitácora de Desarrollo - V1.md`

Verificaciones ejecutadas:

- `python3 -m compileall universal_mcp/cli/main.py tests/test_cli_wrapper.py`
- `python3 -m pytest -q tests/test_cli_wrapper.py` -> `11 passed`
- `python3 -m pytest -q` -> `55 passed`

Resultado:

- ya se pueden crear, clonar, borrar y reconfigurar perfiles desde CLI
- el usuario ya no depende de editar `.universal_mcp.json` para la gestión básica de perfiles
- el bloque de perfiles queda suficientemente cubierto para flujos diarios de trabajo en V1

Bloqueos detectados:

- no hay bloqueos para esta fase
- queda pendiente solo la edición más fina del perfil si hiciera falta:
  - `client`
  - `workspace_policy`

Siguiente paso recomendado:

- volver al cierre del hueco 1:
  - rotación/actualización asistida de secretos
  - validación real de `keyring` cuando el entorno lo permita
- después revisar el flujo final de `mcp-cli run codex`

### 2026-04-07 | CLI de perfiles | Activación real de `workspace_policy`

Objetivo de la iteración:

- cerrar la parte pendiente de edición fina de perfiles
- hacer que `workspace_policy` deje de ser solo un dato mostrado y pase a afectar al flujo real de `run`

Trabajo realizado:

- ampliación del modelo `WorkspacePolicy` para soportar de forma explícita:
  - `explicit`
  - `fixed`
- validación del modelo para garantizar:
  - `explicit` sin `path`
  - `fixed` con `path` obligatorio
- ampliación de `profile` con nuevos comandos:
  - `mcp-cli profile set-client <name> <client>`
  - `mcp-cli profile set-workspace-policy <name> <explicit|fixed> [--path ...]`
- integración de `workspace_policy` en `mcp-cli run`:
  - `explicit` usa `--workspace` si se indica
  - `explicit` usa `cwd` si no se indica workspace
  - `fixed` usa la ruta persistida del perfil
  - error claro si el workspace fijo no existe
- ampliación de la vista de perfil para mostrar también:
  - `Workspace path`
- ampliación de tests CLI para cubrir:
  - cambio de `client`
  - configuración de `workspace_policy`
  - validaciones de argumentos inválidos
  - resolución real del workspace fijo durante `run`

Archivos afectados:

- `universal_mcp/config/profiles.py`
- `universal_mcp/cli/main.py`
- `universal_mcp/cli/views.py`
- `tests/test_cli_wrapper.py`
- `Readme.md`
- `Bitácora de Desarrollo - V1.md`

Verificaciones ejecutadas:

- `python3 -m compileall universal_mcp tests`
- `python3 -m pytest -q tests/test_cli_wrapper.py` -> `15 passed`
- `python3 -m pytest -q` -> `59 passed`

Resultado:

- ya se pueden editar desde CLI los dos atributos finos del perfil que faltaban:
  - `client`
  - `workspace_policy`
- `workspace_policy` ya no es decorativo:
  - condiciona la resolución real del workspace en `mcp-cli run`
- la V1 gana una política de workspace mínima, clara y usable sin introducir modos ambiguos

Bloqueos detectados:

- no hay bloqueos para esta fase
- sigue pendiente validar si en una fase posterior compensa añadir más modos además de:
  - `explicit`
  - `fixed`

Siguiente paso recomendado:

- volver al cierre del hueco 1:
  - rotación/actualización asistida de secretos
  - validación real de `keyring` cuando el entorno lo permita
- después continuar con:
  - pulido final del flujo `mcp-cli run codex`
  - mejoras de ergonomía y validación específicas por cliente

### 2026-04-07 | Hueco 1 | Rotación y actualización asistida de secretos

Objetivo de la iteración:

- cerrar la parte práctica pendiente de la gestión de secretos
- exponer desde CLI una rotación explícita y hacer más visible dónde se usa cada secreto

Trabajo realizado:

- ampliación de `secret list` para mostrar también:
  - qué perfil/servicio referencia cada secreto
- incorporación de un nuevo comando:
  - `mcp-cli secret rotate <ref> [value]`
- mejora del flujo de onboarding para secretos existentes:
  - validación robusta de `reuse/replace/skip`
  - mensaje claro cuando la configuración se pospone
  - reintento guiado si la acción introducida es inválida
- mantenimiento de la persistencia existente:
  - `set_secret`
  - fallback local
  - proyección posterior al daemon

Archivos afectados:

- `universal_mcp/cli/main.py`
- `universal_mcp/cli/onboarding.py`
- `universal_mcp/cli/views.py`
- `tests/test_cli_wrapper.py`

Verificaciones ejecutadas:

- `python3 -m compileall universal_mcp tests`
- `python3 -m pytest -q tests/test_secrets.py tests/test_cli_wrapper.py` -> `18 passed`
- `python3 -m pytest -q` -> `61 passed`

Resultado:

- la rotación de secretos ya no depende de reutilizar `set` de forma implícita
- el usuario puede ver mejor el impacto operativo de cada secreto antes de cambiarlo
- el onboarding ya cubre con mejor UX la actualización de credenciales existentes

Bloqueos detectados:

- no hay bloqueos para esta fase

Siguiente paso recomendado:

- validar de forma real el backend de `keyring`
- después continuar con el pulido del wrapper de `mcp-cli run`

### 2026-04-07 | Hueco 1 | Validación real de `keyring`

Objetivo de la iteración:

- dejar de considerar `keyring` disponible solo por poder importarlo
- hacer que la detección del backend refleje si realmente puede usarse

Trabajo realizado:

- incorporación de un estado explícito de backend de secretos:
  - `SecretBackendStatus`
- cambio de criterio para `secret_backend_name`:
  - `keyring` solo se reporta si el backend es utilizable
- detección de escenarios degradados:
  - módulo ausente
  - backend no resoluble
  - backend `fail`
  - backend sin métodos necesarios o con prioridad inválida
- mantenimiento del fallback local como ruta segura por defecto
- actualización del preflight del onboarding para mostrar el detalle real del backend

Archivos afectados:

- `universal_mcp/config/secrets.py`
- `universal_mcp/cli/onboarding.py`
- `tests/test_secrets.py`

Verificaciones ejecutadas:

- `python3 -m compileall universal_mcp tests`
- `python3 -m pytest -q tests/test_secrets.py tests/test_cli_wrapper.py` -> `24 passed`
- `python3 -m pytest -q` -> `67 passed`

Resultado:

- la detección de backend de secretos ya no es superficial
- el sistema cae a fallback de forma explícita cuando `keyring` no es realmente operativo
- el preflight informa mejor al usuario sobre el estado de almacenamiento seguro disponible

Bloqueos detectados:

- no hay bloqueos para esta fase

Siguiente paso recomendado:

- revisar el wrapper de `mcp-cli run`
- endurecer validaciones y mensajes según cliente objetivo

### 2026-04-07 | Wrapper | Endurecimiento del flujo `mcp-cli run`

Objetivo de la iteración:

- reforzar el wrapper de lanzamiento del cliente para que deje de ser un `Popen` mínimo con pocas variables
- añadir validaciones previas y señales más claras para el usuario

Trabajo realizado:

- incorporación de un plan explícito de lanzamiento:
  - `WrapperLaunchPlan`
- validación previa del comando externo:
  - existencia del ejecutable
  - resolución de ruta real
- validación previa del workspace:
  - existencia
  - comprobación de directorio
- ampliación del entorno inyectado al subproceso hijo:
  - `UNIVERSAL_MCP_TARGET_CLIENT`
  - `UNIVERSAL_MCP_TRANSLATION_TARGET`
  - `UNIVERSAL_MCP_CLIENT_EXECUTABLE`
  - `UNIVERSAL_MCP_CLIENT_EXECUTABLE_PATH`
- incorporación de warnings útiles cuando:
  - el `profile.client` no encaja con el ejecutable lanzado
  - el cliente usa la ruta genérica del wrapper
- integración de estas validaciones y warnings en `mcp-cli run`

Archivos afectados:

- `universal_mcp/cli/wrapper.py`
- `universal_mcp/cli/main.py`
- `tests/test_cli_wrapper.py`

Verificaciones ejecutadas:

- `python3 -m compileall universal_mcp tests`
- `python3 -m pytest -q tests/test_cli_wrapper.py tests/test_translator.py` -> `25 passed`
- `python3 -m pytest -q` -> `72 passed`

Resultado:

- `mcp-cli run` falla antes y mejor cuando el comando o el workspace son inválidos
- el cliente hijo recibe más contexto interno útil para futuras integraciones
- el wrapper ya ofrece una base más seria para pulido posterior por cliente

Bloqueos detectados:

- no hay bloqueos para esta fase

Siguiente paso recomendado:

- seguir afinando la integración específica con `codex-cli`
- revisar si hace falta proyectar más metadatos o convenciones por cliente

### 2026-04-07 | Wrapper | Afinado específico de `codex-cli`

Objetivo de la iteración:

- convertir `codex-cli` en el camino principal y más cuidado del wrapper
- mejorar la UX del flujo `mcp-cli run codex` con mensajes y hints más concretos

Trabajo realizado:

- ampliación del plan de lanzamiento con:
  - `display_name`
  - `launch_message`
- tratamiento explícito de `codex-cli` como cliente principal en el wrapper
- mejora de warnings por desajuste entre perfil y ejecutable:
  - hint concreto a `mcp-cli run codex`
- mejora del error de comando ausente para `codex-cli`:
  - sugerencia de instalar `codex`
  - sugerencia de añadirlo al `PATH`
- impresión de mensaje de lanzamiento visible antes de ejecutar el subproceso:
  - `Launching Codex CLI via ...`
- ampliación de tests para cubrir:
  - caso feliz con ejecutable `codex`
  - hint específico en comando ausente
  - warning mejorado por desajuste
  - presencia del mensaje de lanzamiento

Archivos afectados:

- `universal_mcp/cli/wrapper.py`
- `universal_mcp/cli/main.py`
- `tests/test_cli_wrapper.py`
- `README.md`
- `Bitácora de Desarrollo - V1.md`

Verificaciones ejecutadas:

- `python3 -m compileall universal_mcp tests`
- `python3 -m pytest -q tests/test_cli_wrapper.py` -> `24 passed`
- `python3 -m pytest -q` -> `74 passed`

Resultado:

- `mcp-cli run codex` ya no depende de mensajes genéricos del wrapper
- el flujo principal para `Codex CLI` queda más claro y más fácil de depurar
- los errores y warnings del camino principal ya orientan mejor al usuario

Bloqueos detectados:

- no hay bloqueos para esta fase

Siguiente paso recomendado:

- revisar si `codex-cli` necesita variables o convenciones adicionales además de las ya inyectadas
- después seguir con pulido general de V1 y UX operativa

### 2026-04-07 | Wrapper | Validación previa y `dry-run` para `mcp-cli run`

Objetivo de la iteración:

- cerrar mejor el flujo real de uso de `mcp-cli run codex`
- permitir validar el contexto exacto de lanzamiento sin arrancar ni el cliente ni el daemon

Trabajo realizado:

- incorporación de `--dry-run` al comando `mcp-cli run`
- render previo de un resumen operativo:
  - `Run Context`
- exposición visible antes del lanzamiento de:
  - perfil
  - cliente objetivo
  - ejecutable
  - workspace
  - daemon URL
  - estado de `ensure_daemon`
  - estado de `dry_run`
- comportamiento explícito para `dry-run`:
  - valida comando y workspace
  - construye el entorno de wrapper
  - no arranca el daemon
  - no lanza el proceso hijo
  - cierra con mensaje claro de validación completada
- ampliación de tests para cubrir:
  - render del contexto
  - ausencia de lanzamiento real del proceso hijo
  - ausencia de arranque del daemon en `dry-run`

Archivos afectados:

- `universal_mcp/cli/main.py`
- `universal_mcp/cli/views.py`
- `tests/test_cli_wrapper.py`
- `README.md`
- `Bitácora de Desarrollo - V1.md`

Verificaciones ejecutadas:

- `python3 -m compileall universal_mcp tests`
- `python3 -m pytest -q tests/test_cli_wrapper.py` -> `26 passed`
- `python3 -m pytest -q` -> `76 passed`

Resultado:

- el usuario ya puede inspeccionar el contexto real de `mcp-cli run codex` antes de ejecutar nada
- el flujo principal de uso gana una validación operativa útil para depuración y soporte
- el wrapper queda más cerca de un cierre real de V1 en términos de experiencia diaria

Bloqueos detectados:

- no hay bloqueos para esta fase

Siguiente paso recomendado:

- validar manualmente el flujo completo:
  - `mcp-cli onboarding`
  - `mcp-cli doctor`
  - `mcp-cli start`
  - `mcp-cli run --dry-run codex`
  - `mcp-cli run codex`
- decidir después si `codex-cli` necesita alguna convención adicional de entorno

## Regla de mantenimiento

Cada nueva fase o avance relevante debe añadir una nueva entrada con:

- fecha
- fase
- trabajo realizado
- archivos afectados
- verificaciones ejecutadas
- bloqueos detectados
- siguiente paso recomendado
