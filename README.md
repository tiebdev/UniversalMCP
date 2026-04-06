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
- gestión de secretos con `keyring` opcional y fallback local
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
- `mcp-cli stop`
- `mcp-cli restart`
- `mcp-cli status`
- `mcp-cli config`
- `mcp-cli catalog`
- `mcp-cli doctor`
- `mcp-cli logs`
- `mcp-cli secret list`
- `mcp-cli secret set <ref> [value]`
- `mcp-cli secret delete <ref>`
- `mcp-cli profile list`
- `mcp-cli profile show`
- `mcp-cli profile use <name>`
- `mcp-cli profile service show`
- `mcp-cli profile service set <profile> <service> [options]`
- `mcp-cli profile service remove <profile> <service>`
- `mcp-cli run codex`

## Onboarding actual

`mcp-cli onboarding` ya ofrece:

- banner ASCII y cabecera visual de arranque
- checks reales del entorno antes de pedir configuración
- selección interactiva de MCP habilitados
- configuración guiada de `github` y `postgres`
- alta o reutilización de secretos
- resumen final con estado y siguientes comandos recomendados

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

- seguir cerrando el hueco 1 de V1:
  - rotación/actualización asistida de secretos
  - validación de keyring real cuando el entorno lo permita
- después continuar con:
  - gestión completa de perfiles desde CLI
  - pulido final del flujo `mcp-cli run codex`
  - mejora de UX del onboarding sin añadir complejidad visual innecesaria
