# Universal MCP Orchestrator

Base operativa de la V1 del orquestador Universal MCP.

## Español

### Qué es

Universal MCP Orchestrator es una herramienta para unificar el arranque, validación y uso diario de clientes y herramientas basadas en MCP desde una sola CLI.

La V1 está enfocada en `Codex CLI` como camino principal, con soporte operativo para:

- daemon local
- perfiles
- servicios por perfil
- secretos
- onboarding guiado
- validación runtime
- wrapper de cliente

### Estado actual

La V1 queda operativa y validada para su flujo principal con `Codex CLI`.

MCP validados en V1:

- `filesystem`
- `git`
- `github`
- `postgres`
- `ast-grep`
- `sequential-thinking`

Resumen técnico de cierre:

- ver [ESTADO_FINAL_V1.md](/mnt/c/Users/RidO/Documents/GitHub/UniversalMCP/ESTADO_FINAL_V1.md)

Trabajo posterior no bloqueante:

- ver [POST_V1.md](/mnt/c/Users/RidO/Documents/GitHub/UniversalMCP/POST_V1.md)

### Comandos principales

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

Secretos:

- `mcp-cli secret list`
- `mcp-cli secret set <ref> [value]`
- `mcp-cli secret rotate <ref> [value]`
- `mcp-cli secret delete <ref>`

Perfiles:

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

### Flujo recomendado

Sesión normal:

1. `mcp-cli doctor`
2. `mcp-cli start`
3. `mcp-cli run codex`

Validación sin lanzar el cliente:

1. `mcp-cli doctor`
2. `mcp-cli probe-daemon`
3. `mcp-cli run --dry-run codex`

### Validación runtime

El proyecto incluye un script reproducible de validación end-to-end:

- `scripts/validate_runtime.sh`

Secuencia:

- `mcp-cli doctor`
- `mcp-cli probe-daemon`
- `mcp-cli start`
- `mcp-cli status`
- `mcp-cli run --dry-run codex -- --version`
- `mcp-cli run codex -- --version`
- `mcp-cli stop`

Logs por ejecución:

- `.universal_mcp_runtime/validation/<timestamp>/`

### Wrapper y daemon

La V1 está centrada en `Codex CLI`:

- `mcp-cli run codex` es la ruta principal
- `mcp-cli run --dry-run codex` valida contexto sin lanzar el cliente
- la CLI muestra `Run Context` antes de ejecutar
- si falta `codex`, el error indica instalarlo o añadirlo al `PATH`

El control del daemon ya distingue entre:

- puerto ocupado
- entorno sin listeners locales permitidos
- fallo genérico de boot con extracto de `daemon.log`

Además:

- `doctor` muestra binario cliente, bind local y probe ASGI
- `probe-daemon` valida el app ASGI sin abrir sockets locales
- `stop` escala a `SIGKILL` si `SIGTERM` no confirma la salida

### Onboarding, secretos y workspace

`mcp-cli onboarding` ya ofrece:

- checks reales del entorno
- selección interactiva de MCP
- configuración guiada de `github` y `postgres`
- alta, reutilización o reemplazo de secretos

`workspace_policy`:

- `explicit`
  - usa `--workspace` si se indica
  - si no, usa el directorio actual para esa ejecución
- `fixed`
  - persiste una ruta en el perfil
  - `mcp-cli run ...` usa esa ruta por defecto
  - si la ruta no existe, la ejecución falla con error claro

### Licencia

Este proyecto está publicado bajo [PolyForm Noncommercial 1.0.0](/mnt/c/Users/RidO/Documents/GitHub/UniversalMCP/LICENSE.md).

Antes de usar, redistribuir o modificar el proyecto, revisa [LICENSE.md](/mnt/c/Users/RidO/Documents/GitHub/UniversalMCP/LICENSE.md).

---

## English

### What it is

Universal MCP Orchestrator is a tool for unifying the startup, validation, and day-to-day use of MCP-based clients and tools from a single CLI.

V1 is focused on `Codex CLI` as the main path, with operational support for:

- local daemon
- profiles
- per-profile services
- secrets
- guided onboarding
- runtime validation
- client wrapper

### Current status

V1 is operational and validated for its main `Codex CLI` flow.

Validated MCPs in V1:

- `filesystem`
- `git`
- `github`
- `postgres`
- `ast-grep`
- `sequential-thinking`

Technical closeout summary:

- see [ESTADO_FINAL_V1.md](/mnt/c/Users/RidO/Documents/GitHub/UniversalMCP/ESTADO_FINAL_V1.md)

Non-blocking follow-up work:

- see [POST_V1.md](/mnt/c/Users/RidO/Documents/GitHub/UniversalMCP/POST_V1.md)

### Main commands

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

Secrets:

- `mcp-cli secret list`
- `mcp-cli secret set <ref> [value]`
- `mcp-cli secret rotate <ref> [value]`
- `mcp-cli secret delete <ref>`

Profiles:

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

### Recommended flow

Normal session:

1. `mcp-cli doctor`
2. `mcp-cli start`
3. `mcp-cli run codex`

Validation without launching the client:

1. `mcp-cli doctor`
2. `mcp-cli probe-daemon`
3. `mcp-cli run --dry-run codex`

### Runtime validation

The project includes a reproducible end-to-end validation script:

- `scripts/validate_runtime.sh`

Sequence:

- `mcp-cli doctor`
- `mcp-cli probe-daemon`
- `mcp-cli start`
- `mcp-cli status`
- `mcp-cli run --dry-run codex -- --version`
- `mcp-cli run codex -- --version`
- `mcp-cli stop`

Per-run logs:

- `.universal_mcp_runtime/validation/<timestamp>/`

### Wrapper and daemon

V1 is centered on `Codex CLI`:

- `mcp-cli run codex` is the main path
- `mcp-cli run --dry-run codex` validates context without launching the client
- the CLI renders `Run Context` before execution
- if `codex` is missing, the error tells the user to install it or add it to `PATH`

Daemon control already distinguishes between:

- port conflict
- environments where local listeners are blocked
- generic boot failure with a useful `daemon.log` excerpt

Also:

- `doctor` reports client binary, local bind, and ASGI probe
- `probe-daemon` validates the ASGI app without opening local sockets
- `stop` escalates to `SIGKILL` if `SIGTERM` does not confirm shutdown

### Onboarding, secrets, and workspace

`mcp-cli onboarding` already provides:

- real environment checks
- interactive MCP selection
- guided `github` and `postgres` setup
- secret creation, reuse, or replacement

`workspace_policy`:

- `explicit`
  - uses `--workspace` when provided
  - otherwise uses the current directory for that execution
- `fixed`
  - persists a path in the profile
  - `mcp-cli run ...` uses that path by default
  - execution fails with a clear error if the path does not exist

### License

This project is released under [PolyForm Noncommercial 1.0.0](/mnt/c/Users/RidO/Documents/GitHub/UniversalMCP/LICENSE.md).

Before using, redistributing, or modifying the project, review [LICENSE.md](/mnt/c/Users/RidO/Documents/GitHub/UniversalMCP/LICENSE.md).
