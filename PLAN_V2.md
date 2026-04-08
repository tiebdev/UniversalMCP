# Plan V2

Documento inicial para líneas de evolución post-V1.

## Objetivo principal

Desacoplar la instalación del comando de la ubicación física del proyecto y mejorar la ergonomía de uso diario.

Hoy `umcp` puede instalarse como comando global, pero su configuración y runtime siguen dependiendo del directorio actual. En V2 se propone soportar un modelo más cercano a una herramienta típica de Linux, con estado global de usuario y selección explícita de proyecto o workspace cuando haga falta.

## Línea prioritaria

### Configuración y runtime globales

Propuesta de evolución:

- configuración de usuario bajo rutas XDG
- runtime y logs en rutas globales de usuario
- selección explícita de proyecto o workspace sin depender siempre de `cwd`

Dirección propuesta:

- config:
  - `~/.config/umcp/`
- state:
  - `~/.local/state/umcp/`
- cache o runtime efímero:
  - `~/.cache/umcp/`

## Comportamiento objetivo

Ejemplos deseados:

- ejecutar `umcp doctor` desde cualquier directorio
- ejecutar `umcp start` sin depender de que `.universal_mcp.json` viva en el `cwd`
- seleccionar proyecto explícitamente cuando sea necesario:
  - `umcp --project <path> doctor`
  - `umcp --project <path> run codex`

## Compatibilidad

La migración debería ser progresiva.

Propuesta:

- mantener compatibilidad con el modo actual por directorio durante una fase
- soportar prioridad de resolución:
  1. `--project`
  2. variable de entorno específica
  3. configuración global de usuario
  4. fallback al modo local actual

## Cambios técnicos previsibles

- refactor de `default_settings_path`
- refactor de `runtime_dir`, `pid_file`, `state_file`, `log_file`, `events_file`
- introducción de un concepto explícito de:
  - project root
  - user config root
  - runtime root
- revisión de onboarding, `doctor`, `start`, `status`, `run` y scripts auxiliares
- actualización de tests para cubrir:
  - modo global
  - modo local por directorio
  - precedencia de `--project`

## Riesgos

- mezclar estado global y estado local sin reglas claras
- romper flujos existentes basados en el `cwd`
- generar confusión si `workspace` y `project root` no se distinguen bien

## Criterio de diseño

V2 debería conseguir esto:

- instalación y ejecución cómodas desde cualquier sitio
- estado predecible
- aislamiento razonable por proyecto
- compatibilidad transitoria con V1
