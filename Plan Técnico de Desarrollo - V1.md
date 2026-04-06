# Universal MCP Orchestrator

## Plan Técnico de Desarrollo V1

Versión: 1.0 borrador

Estado: plan de ejecución técnica

Propósito: convertir las decisiones de producto y arquitectura ya cerradas en un plan implementable por módulos, fases y entregables.

## 1. Objetivo de la V1

Construir una primera versión funcional del orquestador que:

- arranque un daemon local
- gestione un catálogo limitado de MCP
- exponga un punto unificado local basado en HTTP + SSE
- permita lanzar Codex CLI mediante wrapper
- aplique aislamiento por perfil y workspace
- gestione secretos por perfil
- ofrezca observabilidad local suficiente para operación y depuración

## 2. Alcance de Implementación

La V1 cubrirá:

- daemon supervisor de procesos MCP
- CLI de gestión y wrapper
- perfiles y configuración base
- catálogo inicial de MCP aprobado
- filtrado y truncado de respuestas
- traducción mínima de esquemas
- logs estructurados y estado observable

La V1 no cubrirá:

- compatibilidad universal con múltiples clientes desde el primer día
- conectores avanzados fuera del catálogo aprobado
- observabilidad externa compleja
- políticas avanzadas multiusuario o remotas

## 3. Estructura del Proyecto

```text
universal_mcp/
├── daemon/
│   ├── multiplexer.py
│   ├── process_router.py
│   ├── memory_filter.py
│   ├── translator.py
│   ├── health.py
│   └── state.py
├── cli/
│   ├── main.py
│   ├── wrapper.py
│   ├── views.py
│   └── onboarding.py
├── config/
│   ├── settings.py
│   ├── profiles.py
│   └── catalog.py
├── runtime/
│   ├── pid.py
│   └── paths.py
├── observability/
│   ├── logging.py
│   └── events.py
├── tests/
├── pyproject.toml
└── README.md
```

## 4. Fases de Implementación

## Fase 0. Bootstrap del repositorio

Objetivo:

- preparar base mínima de proyecto Python mantenible

Entregables:

- `pyproject.toml`
- estructura de paquetes
- dependencias base
- configuración mínima de lint y test

Dependencias clave:

- `pydantic`
- `typer`
- `rich`
- `fastapi`
- `uvicorn`

## Fase 1. Configuración, perfiles y catálogo

Objetivo:

- definir modelo de configuración persistente y perfiles

Módulos:

- `config/settings.py`
- `config/profiles.py`
- `config/catalog.py`

Capacidades:

- cargar configuración desde archivo local
- resolver perfil por defecto
- validar perfiles con Pydantic
- definir catálogo V1 de MCP
- mapear secretos requeridos por MCP

Entregables:

- modelos de configuración
- parser y validador
- catálogo inicial formalizado

## Fase 2. Runtime local del daemon

Objetivo:

- arrancar y descubrir el daemon de forma fiable

Módulos:

- `runtime/pid.py`
- `runtime/paths.py`
- parte inicial de `daemon/state.py`

Capacidades:

- gestión de PID
- archivos de estado efímero
- puerto configurable con valor por defecto
- detección de daemon activo
- limpieza de estado huérfano

Entregables:

- utilidades de runtime local
- contrato de estado del daemon

## Fase 3. Supervisor de procesos MCP

Objetivo:

- lanzar, observar y reiniciar procesos MCP

Módulos:

- `daemon/process_router.py`
- `daemon/state.py`
- `daemon/health.py`

Capacidades:

- arranque asíncrono de subprocesos
- asignación de proceso por MCP
- estados `starting`, `healthy`, `degraded`, `failed`, `stopped`
- restart con backoff
- health checks con timeout
- separación entre procesos compartibles y sensibles

Entregables:

- supervisor operativo
- registro de estados por MCP
- políticas de reinicio

## Fase 4. Multiplexor y superficie HTTP + SSE

Objetivo:

- exponer un punto unificado local

Módulos:

- `daemon/multiplexer.py`
- soporte de integración con `daemon/process_router.py`

Capacidades:

- endpoint HTTP local
- stream SSE
- routing básico hacia MCP registrados
- IDs de correlación por petición
- errores estructurados

Entregables:

- servidor local funcional
- contrato interno de request/response

## Fase 5. Filtro de memoria y truncado

Objetivo:

- proteger al cliente frente a respuestas excesivas

Módulos:

- `daemon/memory_filter.py`

Capacidades:

- truncado por tamaño
- truncado por líneas
- paginación de colecciones
- metadatos de parcialidad
- aplicación de políticas según tipo de respuesta

Entregables:

- filtro reusable
- tests de límites y formatos parciales

## Fase 6. Traducción mínima de esquemas

Objetivo:

- adaptar herramientas y payloads al cliente objetivo inicial

Módulos:

- `daemon/translator.py`

Capacidades:

- validación de entrada y salida con Pydantic
- normalización básica de esquemas
- errores legibles en incompatibilidades

Entregables:

- traductor mínimo orientado a Codex CLI

## Fase 7. CLI de operación

Objetivo:

- exponer control de usuario sobre el daemon

Módulos:

- `cli/main.py`
- `cli/views.py`

Comandos mínimos:

- `mcp-cli start`
- `mcp-cli stop`
- `mcp-cli restart`
- `mcp-cli status`
- `mcp-cli config`
- `mcp-cli profile list`
- `mcp-cli profile use <name>`

## 5. Estado actual de implementación

Actualmente ya están cubiertos:

- daemon local con HTTP + SSE
- supervisor de MCP y estados de proceso
- wrapper para `Codex CLI`
- observabilidad local y logs estructurados
- filtro de truncado y paginación
- traducción mínima de payloads
- MCP validados de extremo a extremo:
  - `filesystem`
  - `git`
  - `github`
  - `postgres`
  - `ast-grep`
  - `sequential-thinking`
- ampliación práctica de capacidades internas:
  - `filesystem`: `list`, `read`, `exists`, `stat`, `glob`, `search-text`, `read-many`
  - `git`: `status`, `diff`, `changed-files`, `branch`, `log`, `show`, `diff-file`
- consolidación inicial de CLI:
  - `catalog`
  - `doctor`
  - `profile show`

## 6. Punto actual de trabajo

El foco actual ya no es ampliar el catálogo V1, sino cerrar huecos de producto pendientes.

Siguiente bloque activo:

- hueco 1: gestión real de secretos y servicios por perfil

Estado del hueco 1:

- ya implementado:
  - almacén de secretos con fallback local
  - comandos `secret list/set/delete`
  - comandos `profile service show/set/remove`
  - resolución de secretos integrada en el daemon
- pendiente para cerrarlo:
  - onboarding guiado para secretos y servicios
  - rotación/actualización asistida
  - prueba real de backend `keyring` cuando el entorno lo permita

Orden recomendado para retomar:

1. cerrar hueco 1
2. pasar a onboarding guiado completo
3. completar gestión de perfiles
4. revisar preparación real de entrega V1

Entregables:

- CLI funcional con vistas Rich

## Fase 8. Wrapper y lanzamiento de cliente

Objetivo:

- lanzar Codex CLI con entorno inyectado y efímero

Módulos:

- `cli/wrapper.py`
- `cli/onboarding.py`

Capacidades:

- resolución de perfil activo
- inyección de variables solo al subproceso hijo
- selección de workspace
- first-run onboarding
- lanzamiento de cliente objetivo

Entregables:

- `mcp-cli run <comando>`
- onboarding mínimo usable

## Fase 9. Observabilidad local

Objetivo:

- hacer el sistema depurable y operable

Módulos:

- `observability/logging.py`
- `observability/events.py`
- integración con `daemon/state.py` y CLI

Capacidades:

- logs JSON estructurados
- eventos operativos mínimos
- retención local acotada
- consulta desde CLI

Comandos mínimos:

- `mcp-cli logs`
- `mcp-cli logs --mcp <name>`
- `mcp-cli logs --level error`

## Fase 10. Integración del catálogo V1

Objetivo:

- conectar el catálogo aprobado a la infraestructura común

Orden recomendado:

1. `filesystem`
2. `git`
3. `github`
4. `postgres`
5. `ast-grep`
6. `sequential-thinking`

Criterio:

- empezar por el núcleo mínimo de arranque
- añadir después los MCP complementarios

## Fase 11. Validación end-to-end

Objetivo:

- demostrar que la V1 es usable en flujo real

Casos mínimos:

- arranque del daemon sin configuración previa
- creación de perfil
- almacenamiento de secretos
- lanzamiento de Codex CLI con wrapper
- uso de al menos un MCP sin credenciales y uno con credenciales
- visualización de estado y logs
- recuperación tras caída de un MCP

## 5. Orden de construcción recomendado

Orden pragmático:

1. bootstrap
2. configuración y perfiles
3. runtime local
4. supervisor de procesos
5. multiplexor
6. memory filter
7. CLI base
8. wrapper
9. observabilidad
10. integración de MCP
11. validación end-to-end

Motivo:

- el wrapper y los MCP dependen de una base operativa ya estable
- la observabilidad debe aparecer antes de la integración final para poder depurar bien

## 6. Riesgos Técnicos Principales

- diferencias reales entre transportes esperados por clientes
- comportamiento inconsistente de servidores MCP de terceros
- dificultades en health checks genéricos
- gestión segura de secretos en distintos sistemas operativos
- riesgo de acoplar demasiado pronto la arquitectura a un solo cliente

## 7. Criterios de “hecho” para la V1

La V1 puede considerarse lista si:

- el daemon arranca y se detecta correctamente
- el CLI opera sin estados ambiguos
- el wrapper lanza Codex CLI con entorno efímero
- el catálogo mínimo funciona de forma estable
- los procesos se reinician de manera controlada
- el estado del sistema se puede inspeccionar localmente
- las respuestas grandes no desbordan al cliente

## 8. Recomendación para la ejecución inmediata

La implementación debería empezar por:

1. crear el esqueleto del proyecto
2. fijar `pyproject.toml`
3. modelar perfiles y catálogo con Pydantic
4. implementar el runtime local del daemon
5. construir el supervisor de procesos antes de intentar integrar MCP reales
