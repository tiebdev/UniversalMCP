# Universal MCP Orchestrator

Base operativa de la V1 del orquestador Universal MCP.

## Estado actual

La V1 queda operativa y validada para su flujo principal con `Codex CLI`.

Capas ya cerradas:

- CLI operativa con `Typer` y renderizado `Rich`
- configuración persistente por perfil
- catálogo V1 de MCP
- onboarding guiado
- gestión de secretos con backend real y fallback local
- wrapper de cliente orientado a `codex-cli`
- daemon local con diagnóstico de arranque, estado y parada
- validación runtime end-to-end mediante script

MCP validados en V1:

- `filesystem`
- `git`
- `github`
- `postgres`
- `ast-grep`
- `sequential-thinking`

Resumen ejecutivo de cierre:

- ver [ESTADO_FINAL_V1.md](/mnt/c/Users/RidO/Documents/GitHub/UniversalMCP/ESTADO_FINAL_V1.md)

## Comandos principales

- `mcp-cli onboarding`
- `mcp-cli doctor`
- `mcp-cli probe-daemon`
- `mcp-cli start`
- `mcp-cli stop`
- `mcp-cli restart`
- `mcp-cli status`
- `mcp-cli run codex`
- `mcp-cli run --dry-run codex`
- `mcp-cli catalog`
- `mcp-cli logs`
- `mcp-cli config`
- `mcp-cli set-port <port>`

Gestión de secretos:

- `mcp-cli secret list`
- `mcp-cli secret set <ref> [value]`
- `mcp-cli secret rotate <ref> [value]`
- `mcp-cli secret delete <ref>`

Gestión de perfiles:

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

## Flujo recomendado

Para una sesión normal:

1. `mcp-cli doctor`
2. `mcp-cli start`
3. `mcp-cli run codex`

Para validar sin lanzar el cliente:

1. `mcp-cli doctor`
2. `mcp-cli probe-daemon`
3. `mcp-cli run --dry-run codex`

## Validación runtime

El proyecto incluye un script reproducible de validación end-to-end:

- `scripts/validate_runtime.sh`

Secuencia que ejecuta:

- `mcp-cli doctor`
- `mcp-cli probe-daemon`
- `mcp-cli start`
- `mcp-cli status`
- `mcp-cli run --dry-run codex -- --version`
- `mcp-cli run codex -- --version`
- `mcp-cli stop`

Logs por ejecución:

- `.universal_mcp_runtime/validation/<timestamp>/`

Resultado validado en entorno con sockets locales disponibles:

- bind local correcto
- arranque del daemon correcto
- `status` correcto
- wrapper `codex` correcto
- parada correcta, con escalado a `SIGKILL` cuando `SIGTERM` no basta

## Wrapper y `codex-cli`

La V1 está centrada en `Codex CLI` como camino feliz:

- `mcp-cli run codex` es la ruta principal
- `mcp-cli run --dry-run codex` valida contexto sin lanzar el cliente
- la CLI muestra `Run Context` antes de ejecutar
- si el ejecutable no encaja con el cliente esperado, aparece un warning explícito
- si falta `codex`, el error indica instalarlo o añadirlo al `PATH`

Variables que inyecta el wrapper:

- `UNIVERSAL_MCP_DAEMON_URL`
- `UNIVERSAL_MCP_PORT`
- `UNIVERSAL_MCP_PROFILE`
- `UNIVERSAL_MCP_TARGET_CLIENT`
- `UNIVERSAL_MCP_TRANSLATION_TARGET`
- `UNIVERSAL_MCP_WORKSPACE`
- `UNIVERSAL_MCP_CLIENT_EXECUTABLE`
- `UNIVERSAL_MCP_CLIENT_EXECUTABLE_PATH`

## Daemon y diagnóstico

El control del daemon ya distingue correctamente entre:

- conflicto real de puerto ocupado
- entorno sin listeners locales permitidos
- fallo genérico de boot con extracto útil de `daemon.log`

Además:

- `doctor` muestra binario cliente, bind local y probe ASGI
- `probe-daemon` valida el app ASGI sin abrir sockets locales
- la limpieza de PID y estado es idempotente
- la detección de proceso activo ignora zombies en Linux
- `stop` escala a `SIGKILL` si `SIGTERM` no confirma la salida

## Onboarding, secretos y perfiles

`mcp-cli onboarding` ya ofrece:

- checks reales del entorno
- selección interactiva de MCP
- configuración guiada de `github` y `postgres`
- alta, reutilización o reemplazo de secretos
- resumen final con siguientes comandos recomendados

Secretos:

- backend `keyring` si está disponible y es utilizable
- fallback local controlado
- `list`, `set`, `rotate` y `delete` desde CLI

Perfiles:

- cliente objetivo por perfil
- MCP habilitados
- servicios por perfil
- `workspace_policy` en modo `explicit` o `fixed`

## Workspace policy

- `explicit`
  - usa `--workspace` si se indica
  - si no, usa el directorio actual para esa ejecución
- `fixed`
  - persiste una ruta en el perfil
  - `mcp-cli run ...` usa esa ruta por defecto
  - si la ruta no existe, la ejecución falla con error claro

## Estado de cierre V1

Lo que queda fuera de este cierre:

- afinado adicional de UX si se decide pulir onboarding o mensajes
- integración futura con clientes no prioritarios
- decisión de producto sobre si el escalado a `SIGKILL` debe mantenerse tal cual o merecer investigación adicional

El estado técnico de V1 hoy es de base funcional cerrada, no de prototipo abierto.
