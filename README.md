# Universal MCP

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

### Comandos principales

El comando principal visible es `umcp`.

Alias compatible disponible:

- `mcp-cli`

- `umcp onboarding`
- `umcp doctor`
- `umcp probe-daemon`
- `umcp start`
- `umcp stop`
- `umcp restart`
- `umcp status`
- `umcp run codex`
- `umcp run --dry-run codex`
- `umcp catalog`
- `umcp logs`
- `umcp config`
- `umcp set-port <port>`

Secretos:

- `umcp secret list`
- `umcp secret set <ref> [value]`
- `umcp secret rotate <ref> [value]`
- `umcp secret delete <ref>`

Perfiles:

- `umcp profile list`
- `umcp profile create <name> [--mcp ...]`
- `umcp profile clone <source> <target>`
- `umcp profile delete <name>`
- `umcp profile show`
- `umcp profile set-client <name> <client>`
- `umcp profile set-mcps <name> <mcp...>`
- `umcp profile set-workspace-policy <name> <explicit|fixed> [--path ...]`
- `umcp profile use <name>`
- `umcp profile service show`
- `umcp profile service set <profile> <service> [options]`
- `umcp profile service remove <profile> <service>`

### Flujo recomendado

Sesión normal:

1. `umcp doctor`
2. `umcp start`
3. `umcp run codex`

Validación sin lanzar el cliente:

1. `umcp doctor`
2. `umcp probe-daemon`
3. `umcp run --dry-run codex`

### Validación runtime

El proyecto incluye un script reproducible de validación end-to-end:

- `scripts/validate_runtime.sh`

Secuencia:

- `umcp doctor`
- `umcp probe-daemon`
- `umcp start`
- `umcp status`
- `umcp run --dry-run codex -- --version`
- `umcp run codex -- --version`
- `umcp stop`

Logs por ejecución:

- `.universal_mcp_runtime/validation/<timestamp>/`

### Wrapper y daemon

La V1 está centrada en `Codex CLI`:

- `umcp run codex` es la ruta principal
- `umcp run --dry-run codex` valida contexto sin lanzar el cliente
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

`umcp onboarding` ya ofrece:

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
  - `umcp run ...` usa esa ruta por defecto
  - si la ruta no existe, la ejecución falla con error claro

### Licencia

Este proyecto está publicado bajo [PolyForm Noncommercial 1.0.0](./LICENSE.md)

Antes de usar, redistribuir o modificar el proyecto, revisa [LICENSE.md](./LICENSE.md).

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

### Main commands

The primary visible command is `umcp`.

Compatible alias still available:

- `mcp-cli`

- `umcp onboarding`
- `umcp doctor`
- `umcp probe-daemon`
- `umcp start`
- `umcp stop`
- `umcp restart`
- `umcp status`
- `umcp run codex`
- `umcp run --dry-run codex`
- `umcp catalog`
- `umcp logs`
- `umcp config`
- `umcp set-port <port>`

Secrets:

- `umcp secret list`
- `umcp secret set <ref> [value]`
- `umcp secret rotate <ref> [value]`
- `umcp secret delete <ref>`

Profiles:

- `umcp profile list`
- `umcp profile create <name> [--mcp ...]`
- `umcp profile clone <source> <target>`
- `umcp profile delete <name>`
- `umcp profile show`
- `umcp profile set-client <name> <client>`
- `umcp profile set-mcps <name> <mcp...>`
- `umcp profile set-workspace-policy <name> <explicit|fixed> [--path ...]`
- `umcp profile use <name>`
- `umcp profile service show`
- `umcp profile service set <profile> <service> [options]`
- `umcp profile service remove <profile> <service>`

### Recommended flow

Normal session:

1. `umcp doctor`
2. `umcp start`
3. `umcp run codex`

Validation without launching the client:

1. `umcp doctor`
2. `umcp probe-daemon`
3. `umcp run --dry-run codex`

### Runtime validation

The project includes a reproducible end-to-end validation script:

- `scripts/validate_runtime.sh`

Sequence:

- `umcp doctor`
- `umcp probe-daemon`
- `umcp start`
- `umcp status`
- `umcp run --dry-run codex -- --version`
- `umcp run codex -- --version`
- `umcp stop`

Per-run logs:

- `.universal_mcp_runtime/validation/<timestamp>/`

### Wrapper and daemon

V1 is centered on `Codex CLI`:

- `umcp run codex` is the main path
- `umcp run --dry-run codex` validates context without launching the client
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

`umcp onboarding` already provides:

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
  - `umcp run ...` uses that path by default
  - execution fails with a clear error if the path does not exist

### License

This project is released under [PolyForm Noncommercial 1.0.0](./LICENSE.md)

Before using, redistributing, or modifying the project, review [LICENSE.md](./LICENSE.md).
