# Universal MCP Orchestrator

Base operativa de la V1 del orquestador Universal MCP.

## Estado

Este repositorio contiene una base funcional del proyecto:

- paquetes Python principales
- CLI operativa
- modelos de configuración y perfiles
- catálogo V1 de MCP
- daemon local con supervisión, observabilidad y wrapper
- onboarding guiado con flujo visual en terminal
- gestión de secretos con validación real de `keyring` y fallback local seguro
- configuración de servicios por perfil desde CLI
- MCP ya validados:
  - `filesystem`
  - `git`
  - `github`
  - `postgres`
  - `ast-grep`
  - `sequential-thinking`

## Comandos disponibles

- `mcp-cli onboarding`
- `mcp-cli start`
- `mcp-cli start --port <port>`
- `mcp-cli stop`
- `mcp-cli restart`
- `mcp-cli restart --port <port>`
- `mcp-cli status`
- `mcp-cli config`
- `mcp-cli set-port <port>`
- `mcp-cli catalog`
- `mcp-cli doctor`
- `mcp-cli logs`
- `mcp-cli secret list`
- `mcp-cli secret set <ref> [value]`
- `mcp-cli secret rotate <ref> [value]`
- `mcp-cli secret delete <ref>`
- `mcp-cli profile list`
- `mcp-cli profile create <name> [--mcp ...]`
- `mcp-cli profile clone <source> <target>`
- `mcp-cli profile delete <name>`
- `mcp-cli profile show`
- `mcp-cli profile set-client <name> <client>`
- `mcp-cli profile set-mcps <name> <mcp...>`
- `mcp-cli profile set-workspace-policy <name> <explicit|fixed> [--path ...]`
- `mcp-cli profile use <name>`
- `mcp-cli profile service show`
- `mcp-cli profile service set <profile> <service> [options]`
- `mcp-cli profile service remove <profile> <service>`
- `mcp-cli run codex`

## Wrapper y `codex-cli`

El flujo principal de V1 ya está orientado a `codex-cli`:

- `mcp-cli run codex` se trata como camino feliz del wrapper
- `mcp-cli run --dry-run codex` permite validar el contexto antes de lanzar nada
- el lanzamiento muestra un mensaje explícito para `Codex CLI`
- el CLI renderiza un resumen `Run Context` antes de ejecutar
- si el perfil espera `codex-cli` pero el ejecutable no encaja, el CLI emite un warning con hint concreto
- si falta el binario `codex`, el error ya sugiere instalarlo o añadirlo al `PATH`

## Arranque del daemon

El control del daemon ya diagnostica mejor los fallos de arranque:

- si el puerto configurado está ocupado, `mcp-cli start` lo reporta de forma explícita
- el CLI sugiere puertos libres alternativos cuando detecta conflicto
- el puerto runtime ya puede actualizarse desde CLI con `set-port` o con `start --port`
- si el boot falla por otra causa, el CLI incorpora el último extracto útil de `daemon.log`
- esto reduce el caso genérico de "no respondió tras arrancar" cuando el proceso muere al iniciar

Estado actual del arranque real:

- la ergonomía de puerto ya está resuelta en la CLI
- en este entorno de validación el daemon siguió sin poder bindear incluso usando puertos alternativos altos
- eso apunta a una restricción del entorno de ejecución o a un problema más profundo del transporte, no ya a una falta de configuración del producto
- la investigación adicional confirmó que en este sandbox no se pueden crear sockets locales desde Python (`PermissionError: [Errno 1] Operation not permitted`)
- además se endureció la limpieza del PID para que sea idempotente en shutdown

## Onboarding actual

`mcp-cli onboarding` ya ofrece:

- banner ASCII y cabecera visual de arranque
- checks reales del entorno antes de pedir configuración
- selección interactiva de MCP habilitados
- configuración guiada de `github` y `postgres`
- alta, reutilización o reemplazo guiado de secretos
- resumen final con estado y siguientes comandos recomendados

## Secretos

La gestión de secretos ya permite:

- `set`, `list`, `rotate` y `delete` desde CLI
- mostrar en `secret list` qué perfil/servicio referencia cada secreto
- usar `keyring` solo cuando el backend es realmente utilizable
- caer a fallback local cuando `keyring` no está disponible o no tiene backend operativo

## Perfiles y workspace policy

Los perfiles ya permiten gestionar desde CLI:

- cliente objetivo del perfil
- MCP habilitados
- servicios por perfil
- política de workspace

La `workspace_policy` de V1 soporta dos modos:

- `explicit`
  - usa `--workspace` si se indica
  - si no, usa el directorio actual solo para esa ejecución
- `fixed`
  - persiste una ruta en el perfil
  - `mcp-cli run ...` usa esa ruta por defecto
  - si la ruta no existe, la ejecución falla con error claro

## Hygiene

El repositorio ya ignora artefactos locales comunes para evitar commits accidentales de:

- entornos virtuales y caches de Python
- archivos de cobertura y builds locales
- configuraciones de IDE
- logs locales
- configuración runtime y secretos locales de Universal MCP
- carpetas temporales `tmp_*`

## Capacidades internas ya expuestas

- `filesystem`
  - `list`
  - `read`
  - `exists`
  - `stat`
  - `glob`
  - `search-text`
  - `read-many`
- `git`
  - `status`
  - `diff`
  - `changed-files`
  - `branch`
  - `log`
  - `show`
  - `diff-file`

## Siguientes pasos recomendados

- continuar con el cierre operativo de V1:
  - integración más afinada por cliente si hiciera falta
  - mejora de UX del onboarding sin añadir complejidad visual innecesaria
  - seguir endureciendo validaciones y mensajes del wrapper
  - revisar si `codex-cli` necesita más convenciones de entorno específicas
  - priorizar validaciones manuales end-to-end del flujo real de uso
  - investigar por qué el daemon no puede bindear en este entorno aunque el puerto cambie

## Plan de análisis del daemon

Para cerrar la incidencia real de arranque del daemon, el plan inmediato es:

1. aislar si el problema es del entorno o del servidor
2. probar `universal_mcp.daemon.server` directamente, sin pasar por el wrapper del CLI
3. revisar el lifecycle de PID y shutdown si vuelven a aparecer errores de limpieza
4. instrumentar mejor el arranque para distinguir fallo de bind, fallo de `uvicorn` y fallo de la app
