# Universal MCP Orchestrator

## Documento Base de Producto y Arquitectura

Versión: 2.0 borrador

Estado: documento de trabajo para definición técnica

Propósito: sustituir el borrador inicial por una versión más precisa, útil para diseño, implementación y toma de decisiones.

## 1. Resumen Ejecutivo

Universal MCP Orchestrator es una herramienta local de infraestructura, escrita en Python, cuyo objetivo es centralizar la ejecución, supervisión y exposición de múltiples servidores MCP a uno o varios clientes de IA desde una única capa de control.

La propuesta no es construir otro cliente conversacional, sino una pieza intermedia de sistema con tres responsabilidades claras:

1. Gestionar procesos MCP de forma robusta.
2. Exponer una interfaz unificada y controlada a clientes de IA.
3. Reducir fricción operativa mediante un CLI que configure, arranque y envuelva herramientas externas.

La idea tiene valor real si consigue resolver bien cinco problemas: duplicación de procesos, dispersión de configuración, manejo inseguro de secretos, falta de aislamiento entre sesiones y respuestas MCP demasiado grandes para ventanas de contexto limitadas.

## 2. Problema que se Quiere Resolver

En el estado actual del ecosistema, muchos clientes de IA requieren configurar servidores MCP por separado. Eso genera varios costes:

- Multiplicación innecesaria de procesos para los mismos servidores.
- Configuraciones duplicadas en varios clientes.
- Gestión manual y frágil de tokens, rutas y variables de entorno.
- Falta de observabilidad sobre qué MCP está activo, fallando o consumiendo recursos.
- Riesgo de mandar respuestas demasiado grandes al cliente LLM sin control intermedio.

Además, distintos clientes y proveedores no siempre esperan exactamente el mismo dialecto de herramientas ni el mismo mecanismo de transporte, lo que complica la compatibilidad.

## 3. Objetivo del Producto

El producto debe permitir que un usuario:

- Instale y configure una sola vez un catálogo de servidores MCP.
- Arranque un daemon local que los supervise.
- Lance clientes de IA compatibles mediante un wrapper sin modificar de forma permanente sus configuraciones personales.
- Consulte el estado del sistema desde un CLI simple.
- Aplique controles mínimos de seguridad, aislamiento y tamaño de respuesta.

## 4. No Objetivos

Para contener el alcance, esta primera versión no debe intentar:

- Reemplazar a los clientes de IA existentes.
- Resolver autenticación empresarial compleja o multiusuario remoto.
- Implementar sincronización en nube.
- Ofrecer una plataforma completa de permisos por organización.
- Soportar todos los transportes y dialectos imaginables desde el primer día.

## 5. Propuesta de Valor

La herramienta aporta valor si consigue lo siguiente:

- Reducir el coste de ejecución al reutilizar procesos MCP cuando sea seguro hacerlo.
- Mejorar la experiencia de uso con onboarding guiado y arranque rápido.
- Unificar configuración de credenciales y catálogo de servidores.
- Proteger al cliente de IA frente a respuestas gigantes, ruido o esquemas incompatibles.
- Hacer observable el sistema local: qué está corriendo, qué falla y por qué.

## 6. Arquitectura Propuesta

El sistema se divide en dos capas principales y un conjunto de servicios auxiliares.

### 6.1 Daemon local

Responsabilidades:

- Arrancar procesos MCP registrados.
- Monitorizar salud, reinicios y estados.
- Exponer una interfaz local unificada.
- Aplicar filtros y traducciones antes de reenviar datos al cliente.

Componentes previstos:

- `daemon/process_router.py`
- `daemon/multiplexer.py`
- `daemon/memory_filter.py`
- `daemon/translator.py`

### 6.2 CLI y wrapper

Responsabilidades:

- Guiar la configuración inicial.
- Gestionar el daemon.
- Lanzar clientes externos con entorno inyectado.
- Mostrar estado y errores de forma legible.

Componentes previstos:

- `cli/main.py`
- `cli/wrapper.py`
- `cli/views.py`

### 6.3 Configuración y catálogo

Responsabilidades:

- Definir servidores disponibles.
- Resolver variables de entorno y secretos necesarios.
- Mantener perfiles o contextos de ejecución.

Componente previsto:

- `config/settings.py`

## 7. Principios Técnicos

### 7.1 Asincronía estricta

El daemon debe ser no bloqueante. La gestión de subprocesos, transporte y lectura de streams debe construirse con `asyncio`.

### 7.2 Un punto de entrada local

El daemon debe exponer un único endpoint local lógico para el cliente. Internamente podrá enrutar a varios procesos, pero externamente debe comportarse como una única superficie de integración.

### 7.3 Fallo aislado

La caída de un servidor MCP no debe tumbar el daemon completo ni corromper sesiones activas no relacionadas.

### 7.4 Compatibilidad pragmática

El sistema debe soportar primero un conjunto pequeño y útil de clientes y flujos, antes de intentar compatibilidad universal completa.

### 7.5 Seguridad por defecto

Las capacidades más sensibles deben arrancar con el menor privilegio razonable.

## 8. Decisiones Técnicas de V1

Estas decisiones quedan fijadas para la primera versión. Podrán revisarse más adelante, pero la implementación inicial debe asumirlas como base.

### 8.1 Transporte expuesto por el daemon

Decisión V1:

- El daemon expondrá una interfaz local basada en HTTP.
- El streaming de respuestas y eventos se resolverá con SSE.
- WebSocket no formará parte del núcleo de la V1.
- Si en el futuro hiciera falta compatibilidad adicional, se añadirá como adaptador y no como diseño base.

Motivo:

- HTTP y SSE simplifican la depuración local.
- Reducen complejidad frente a una arquitectura centrada en WebSocket.
- Son suficientes para una primera versión enfocada en control local y respuestas progresivas.

### 8.2 Modelo de aislamiento

Decisión V1:

- El aislamiento se definirá por perfil y por workspace.
- No existirá una sesión global compartida entre clientes.
- No se compartirá contexto conversacional entre clientes.
- Las credenciales serán propias de cada perfil.
- Los procesos sensibles o dependientes de credenciales no se compartirán entre perfiles.

Requisito operativo:

- No mezclar contexto ni secretos entre perfiles, workspaces o clientes distintos.

### 8.3 Gestión de secretos

Decisión V1:

- Los secretos persistentes se almacenarán en el keyring del sistema cuando esté disponible.
- La inyección a clientes externos o procesos MCP se hará solo en tiempo de ejecución.
- La inyección se limitará al entorno del subproceso hijo.
- Los secretos no deben escribirse en logs, vistas de estado ni trazas de error.
- El CLI deberá permitir rotación y revocación por perfil.

Fallback aceptable:

- Si no existe integración de keyring en el entorno del usuario, podrá habilitarse un almacenamiento local controlado como solución temporal, claramente marcado como opción de compatibilidad y no como postura ideal.

### 8.4 Política de truncado y paginación

Decisión V1:

- Se aplicarán límites duros de tamaño a las respuestas reenviadas al cliente.
- Logs y diffs se truncarán por bytes y por número de líneas.
- Listados o tablas extensas se servirán mediante paginación.
- Toda respuesta parcial deberá indicarlo explícitamente.

Metadatos mínimos:

- `truncated`
- `next_cursor` cuando aplique
- `original_size_estimate`
- `returned_size`
- `policy_applied`

Umbrales concretos V1:

- respuesta genérica máxima: `64 KB`
- log textual máximo: `32 KB` o `400 líneas`, lo que ocurra primero
- diff textual máximo: `48 KB` o `600 líneas`, lo que ocurra primero
- lista tabular máxima por página: `100 elementos`
- texto por campo individual: `8 KB` antes de truncado puntual

Reglas de comportamiento:

- Si una respuesta cabe dentro del umbral general, se entrega completa.
- Si una respuesta excede el umbral general y no es paginable, se trunca con marca explícita.
- Si una respuesta es una colección, el sistema debe preferir paginar antes que truncar todo el bloque.
- Si un solo campo textual domina la respuesta, se permite truncado puntual del campo antes de truncar el objeto completo.

Formato recomendado para respuestas parciales:

- mantener la estructura original si es posible
- añadir un bloque de metadatos de truncado al nivel superior
- no mezclar silenciosamente datos completos con datos recortados sin indicación

### 8.5 Traducción de esquemas de herramientas

Decisión V1:

- La traducción existirá, pero con alcance limitado.
- La V1 priorizará compatibilidad con el cliente objetivo inicial en lugar de perseguir compatibilidad universal completa.
- Entradas y salidas se validarán con Pydantic v2.
- Las incompatibilidades deberán reportarse de forma explícita y legible.

### 8.6 Reutilización de procesos

Decisión V1:

- Solo se compartirán procesos sin estado sensible o de bajo riesgo operativo.
- Los procesos ligados a credenciales, conexiones externas o acceso sensible no se compartirán por defecto.

Compartibles en principio:

- `filesystem` limitado al mismo workspace
- `git` en el mismo repositorio o workspace
- `ast-grep`
- `sequential-thinking`

No compartibles por defecto:

- `github`
- `postgres`
- `docker`
- `sentry`
- `notion`
- cualquier MCP con token, conexión privilegiada o estado sensible

### 8.7 Cliente objetivo inicial

Decisión V1:

- El cliente objetivo principal será Codex CLI.
- La arquitectura no se cerrará a otros clientes, pero la compatibilidad inicial se optimizará para ese flujo.
- No se considerará éxito de V1 soportar muchos clientes con calidad mediocre.

## 9. Flujo de Usuario

### 9.1 Primera ejecución

Si no existe configuración:

1. El CLI detecta ausencia de perfil.
2. Presenta catálogo inicial de MCP soportados.
3. Solicita solo las credenciales necesarias.
4. Permite escoger cliente objetivo.
5. Guarda la configuración.
6. Arranca el daemon.
7. Lanza el cliente seleccionado mediante wrapper.

### 9.2 Ejecuciones posteriores

El usuario debe poder ejecutar:

- `mcp-cli start`
- `mcp-cli stop`
- `mcp-cli restart`
- `mcp-cli status`
- `mcp-cli run <comando>`
- `mcp-cli config`

### 9.3 Estado observable

`mcp-cli status` debería mostrar al menos:

- daemon activo o caído
- uptime
- procesos MCP activos
- reinicios recientes
- uso aproximado de memoria
- errores recientes

## 10. Catálogo Inicial de MCP

El catálogo inicial debe considerarse provisional hasta validación real. Cada entrada debe tener:

- nombre
- comando
- argumentos
- variables requeridas
- nivel de riesgo
- estado de validación

Catálogo aprobado para V1:

- Filesystem local
- Git
- GitHub
- PostgreSQL
- AST-Grep
- Sequential Thinking

Servidores explícitamente fuera de V1:

- Docker
- Sentry
- Notion
- Playwright
- Chrome DevTools
- Firecrawl
- Postman
- Context7
- Linear

### 10.1 Matriz operativa del catálogo V1

#### Filesystem local

- Rol: lectura e inspección del workspace
- Credenciales: no requiere
- Riesgo: medio
- Compartición: compartible dentro del mismo workspace
- Motivo de inclusión: capacidad base para cualquier flujo de desarrollo

#### Git

- Rol: historial, diffs y contexto del repositorio
- Credenciales: no requiere para repositorios locales
- Riesgo: medio
- Compartición: compartible dentro del mismo repositorio o workspace
- Motivo de inclusión: capacidad base de análisis de cambios y evolución del código

#### GitHub

- Rol: issues, pull requests y contexto remoto del desarrollo
- Credenciales: token por perfil
- Riesgo: alto
- Compartición: no compartible entre perfiles
- Motivo de inclusión: aporta valor directo a flujos modernos de ingeniería

#### PostgreSQL

- Rol: acceso a datos y validación operativa contra base de datos
- Credenciales: host, puerto, base de datos, usuario y contraseña por perfil
- Riesgo: alto
- Compartición: no compartible entre perfiles
- Motivo de inclusión: caso de uso técnico frecuente y de alto valor

#### AST-Grep

- Rol: análisis estructural de código y apoyo a refactorización segura
- Credenciales: no requiere
- Riesgo: bajo
- Compartición: compartible por workspace
- Motivo de inclusión: diferenciador técnico con baja superficie de riesgo

#### Sequential Thinking

- Rol: herramienta auxiliar de razonamiento paso a paso
- Credenciales: no requiere
- Riesgo: bajo
- Compartición: compartible
- Motivo de inclusión: añade utilidad sin complejidad operativa alta

### 10.2 Núcleo mínimo de arranque

Si fuera necesario reducir alcance todavía más durante la implementación, el subconjunto mínimo recomendado sería:

- Filesystem local
- Git
- GitHub
- PostgreSQL

AST-Grep y Sequential Thinking pueden tratarse como extensiones tempranas de la misma V1 si el calendario lo exige.

Nota importante:

No debe asumirse que todos estos servidores son igual de estables, seguros o adecuados para compartir proceso. El catálogo definitivo debe salir de una validación técnica real, no solo de disponibilidad pública.

## 11. Modelo de Perfiles y Configuración

La V1 debe introducir perfiles explícitos. El perfil es la unidad base de configuración, secretos y aislamiento.

### 11.1 Definición de perfil

Un perfil representa un contexto operativo independiente que agrupa:

- catálogo de MCP habilitados
- credenciales y variables asociadas
- preferencias de cliente objetivo
- políticas de aislamiento
- parámetros locales de ejecución

Ejemplos razonables:

- `personal`
- `work`
- `cliente-a`
- `staging`

### 11.2 Reglas del modelo de perfiles

- Cada perfil tiene sus propios secretos.
- Cada perfil tiene su propio catálogo habilitado.
- Un proceso sensible no puede reutilizar credenciales de otro perfil.
- El CLI debe permitir elegir perfil de forma explícita o usar uno predeterminado.
- El wrapper debe lanzar el cliente dentro del perfil activo, no sobre un estado global ambiguo.

### 11.3 Relación entre perfil y workspace

El perfil no sustituye al workspace. Ambos conceptos deben coexistir.

- El perfil define credenciales, catálogo y política.
- El workspace define el ámbito local de archivos y repositorio.

Regla V1:

- `filesystem`, `git` y `ast-grep` se vinculan al workspace activo.
- `github` y `postgres` se vinculan al perfil activo.
- No debe mezclarse un workspace con procesos sensibles de otro perfil salvo configuración explícita futura.

### 11.4 Configuración mínima por perfil

Cada perfil debería incluir al menos:

- nombre del perfil
- cliente objetivo por defecto
- MCP habilitados
- referencias a secretos requeridos
- parámetros de conexión no secretos
- política de puertos o socket local si aplica

### 11.5 Propuesta de estructura de configuración

La configuración persistente puede modelarse con una estructura semejante a esta:

```yaml
default_profile: work
profiles:
  work:
    client: codex-cli
    enabled_mcps:
      - filesystem
      - git
      - github
      - postgres
      - ast-grep
    workspace_policy:
      mode: explicit
    services:
      github:
        secret_ref: github_token
      postgres:
        host: db.internal
        port: 5432
        database: app
        user: app_user
        secret_ref: postgres_password
  personal:
    client: codex-cli
    enabled_mcps:
      - filesystem
      - git
      - github
```

Los secretos reales no deben almacenarse en esta estructura si existe keyring disponible. Solo deben guardarse referencias lógicas.

### 11.6 Operativa esperada del CLI

Ejemplos de uso esperados:

- `mcp-cli profile list`
- `mcp-cli profile use work`
- `mcp-cli profile create`
- `mcp-cli config`
- `mcp-cli run --profile work claude`

### 11.7 Decisión V1

La V1 implementará:

- un perfil por defecto
- posibilidad de múltiples perfiles
- selección explícita de perfil en CLI
- separación de secretos por perfil
- separación de MCP habilitados por perfil

## 12. Requisitos de Seguridad

El producto debe nacer con una postura de seguridad explícita.

Requisitos mínimos:

- Aislamiento entre perfiles o sesiones.
- Allowlist de servidores habilitados.
- Permisos mínimos por defecto.
- Protección de secretos.
- Logs sin exponer tokens.
- Timeouts configurables.
- Posibilidad de modo read-only para conectores de datos o sistema.

Riesgos a mitigar:

- Fuga de secretos entre procesos.
- Exposición accidental de archivos fuera del workspace.
- Acceso excesivo a Docker, bases de datos o herramientas de observabilidad.
- Persistencia de configuraciones temporales más allá del proceso envuelto.

## 13. Requisitos Operativos

El daemon debe incluir al menos:

- health checks por proceso
- reinicio con backoff
- límites de tiempo
- captura de stderr y stdout
- clasificación de errores
- apagado limpio
- telemetría local básica

### 13.1 Puerto y endpoint local

Decisión V1:

- El daemon expondrá un único puerto local configurable.
- Existirá un valor por defecto razonable, por ejemplo `localhost:8765`.
- El binding será únicamente local en V1, no público.
- El perfil podrá influir en configuración operativa, pero no se levantarán múltiples daemons por perfil en la primera versión salvo necesidad futura.

Requisito:

- El CLI debe poder descubrir de forma determinista en qué puerto está escuchando el daemon.

### 13.2 Detección de instancia activa

Decisión V1:

- El sistema mantendrá un mecanismo local de descubrimiento de instancia viva.
- La opción recomendada es un archivo PID y estado en tiempo de ejecución, acompañado de verificación activa del puerto.
- `mcp-cli start` no debe levantar una segunda instancia silenciosamente si la primera ya está sana.
- `mcp-cli status` debe distinguir entre:
  - daemon realmente activo
  - PID huérfano
  - puerto ocupado por proceso no reconocido

### 13.3 Ciclo de vida de procesos MCP

Decisión V1:

- Cada MCP gestionado tendrá un ciclo de vida supervisado por el daemon.
- El daemon será responsable de arrancar, parar y reiniciar subprocesos.
- El CLI no gestionará directamente los MCP una vez arrancado el daemon.

Estados mínimos por proceso:

- `starting`
- `healthy`
- `degraded`
- `failed`
- `stopped`

Semántica mínima:

- `starting`: proceso lanzado pero aún no verificado
- `healthy`: responde dentro de los criterios esperados
- `degraded`: sigue vivo, pero con errores recientes o chequeos inestables
- `failed`: no responde o no puede mantenerse operativo
- `stopped`: detenido de forma intencional o por apagado global

### 13.4 Política de reinicio

Decisión V1:

- El daemon aplicará reinicio automático a MCP que fallen durante operación normal.
- Se usará backoff exponencial con límite.
- Debe existir un número máximo de reintentos consecutivos antes de marcar el proceso como `failed`.
- El sistema debe registrar la última causa de fallo y el número de reinicios recientes.

Recomendación inicial:

- backoff corto en primeros intentos
- tope de ventana para evitar loops agresivos
- paso a `failed` cuando se supera el umbral configurado

### 13.5 Health checks

Decisión V1:

- Cada MCP tendrá health checks básicos definidos por tipo de proceso.
- Todo health check tendrá timeout explícito.
- El resultado del chequeo actualizará el estado observable del proceso.

Información mínima por MCP:

- estado actual
- último arranque
- último health check correcto
- último error
- número de reinicios recientes

Criterio práctico:

- si el proceso existe pero no responde a tiempo, pasa a `degraded` o `failed`
- si responde de nuevo tras reinicio, vuelve a `healthy`

### 13.6 Qué debe mostrar `mcp-cli status`

Decisión V1:

`mcp-cli status` debe mostrar al menos:

- estado global del daemon
- puerto activo
- uptime
- perfil por defecto
- lista de MCP registrados
- estado de cada MCP
- reinicios recientes por MCP
- último error resumido por MCP

### 13.7 Arranque y apagado limpio

Decisión V1:

- `mcp-cli start` debe comprobar primero si el daemon ya está operativo.
- `mcp-cli stop` debe solicitar apagado ordenado y esperar cierre de hijos.
- `mcp-cli restart` debe evitar dejar procesos huérfanos.
- En apagado, el daemon debe cerrar subprocesos y limpiar su estado efímero local.

## 14. Stack Tecnológico Propuesto

- Python 3.10+
- `asyncio` para concurrencia
- FastAPI o capa HTTP equivalente si el transporte elegido lo requiere
- Pydantic v2 para validación de mensajes y configuración
- Typer para CLI
- Rich para vistas de estado

Dependencias opcionales:

- Questionary para onboarding interactivo
- soporte de keyring del sistema para secretos

## 15. Estructura Inicial del Proyecto

```text
universal_mcp/
├── daemon/
│   ├── multiplexer.py
│   ├── process_router.py
│   ├── memory_filter.py
│   └── translator.py
├── cli/
│   ├── main.py
│   ├── wrapper.py
│   └── views.py
├── config/
│   └── settings.py
├── pyproject.toml
└── README.md
```

## 16. Criterios de Aceptación de una Primera Versión

Una V1 sería razonable si cumple lo siguiente:

- Arranca y supervisa un conjunto pequeño de MCP validados.
- Expone un punto local unificado basado en HTTP y SSE.
- Permite lanzar al menos un cliente externo mediante wrapper.
- Aísla perfiles y workspaces de forma clara.
- Trunca o pagina respuestas grandes de forma predecible.
- Gestiona errores sin colapsar el daemon completo.
- Muestra estado operativo útil desde el CLI.

## 17. Riesgos del Proyecto

- Complejidad de compatibilidad entre clientes.
- Ambigüedad del ecosistema MCP y evolución del protocolo.
- Riesgo de sobreprometer compatibilidad universal demasiado pronto.
- Riesgo de seguridad si el wrapper y la inyección de entorno no están bien contenidos.
- Complejidad real de compartir procesos con credenciales distintas.

## 18. Recomendación de Enfoque

La herramienta merece desarrollarse, pero con disciplina de alcance.

Recomendación:

1. Empezar por una V1 pequeña y defendible.
2. Soportar pocos MCP bien elegidos.
3. Diseñar aislamiento y secretos antes de ampliar catálogo.
4. Validar compatibilidad primero con Codex CLI.
5. Medir consumo, estabilidad y experiencia antes de prometer universalidad.

## 19. Próximos Pasos de Diseño

Las decisiones base de producto y arquitectura para la V1 han quedado definidas en este documento.

Los siguientes pasos recomendados ya no son de descubrimiento, sino de ejecución:

1. Traducir estas decisiones a un plan técnico de desarrollo por módulos y fases.
2. Crear la estructura inicial del proyecto.
3. Implementar primero la base operativa del daemon y del CLI.
4. Añadir después el catálogo inicial de MCP aprobado para V1.
5. Validar el flujo completo con Codex CLI como cliente objetivo inicial.

## 20. Estrategia de Observabilidad y Recuperación

La V1 debe ser observable y depurable sin depender de infraestructura externa. La observabilidad en esta fase será local, orientada a operación y diagnóstico.

### 20.1 Objetivos de observabilidad

La estrategia debe permitir responder al menos a estas preguntas:

- ¿Está vivo el daemon?
- ¿Qué MCP están sanos, degradados o caídos?
- ¿Qué proceso ha fallado y por qué?
- ¿Cuántas veces se ha reiniciado un MCP?
- ¿Qué política de truncado o filtrado se aplicó a una respuesta?
- ¿Qué perfil y workspace estaban activos durante un error?

### 20.2 Logs estructurados

Decisión V1:

- El daemon emitirá logs estructurados en formato JSON.
- El CLI podrá presentar una vista humana resumida, pero la fuente canónica será estructurada.
- Cada evento relevante debe incluir marca temporal y nivel de severidad.

Campos mínimos recomendados:

- `timestamp`
- `level`
- `component`
- `event`
- `profile`
- `workspace`
- `mcp_name`
- `process_state`
- `message`
- `error_type` cuando aplique

Regla de seguridad:

- Los logs nunca deben incluir secretos, tokens ni contraseñas.

### 20.3 Eventos operativos mínimos

La V1 debe registrar al menos:

- arranque del daemon
- apagado del daemon
- arranque de MCP
- transición de estado de MCP
- reinicio de MCP
- fallo de health check
- error de traducción
- truncado o paginación aplicada
- lanzamiento de cliente por wrapper

### 20.4 Métricas locales mínimas

Decisión V1:

- No se integrará una pila externa de métricas en la primera versión.
- El daemon mantendrá métricas locales consultables desde `mcp-cli status` o endpoint interno.

Métricas mínimas:

- uptime del daemon
- número de MCP activos
- número de MCP en `healthy`
- número de MCP en `degraded`
- número de MCP en `failed`
- reinicios por MCP
- timestamp del último error por MCP
- número de respuestas truncadas o paginadas

### 20.5 Trazabilidad mínima por petición

Decisión V1:

- Cada operación reenviada por el daemon debe poder asociarse a un identificador local de correlación.
- Ese identificador debe aparecer en logs relevantes de la misma operación.
- No hace falta trazado distribuido completo en V1, pero sí correlación local suficiente para depuración.

Campos mínimos:

- `request_id`
- `profile`
- `workspace`
- `client_name`
- `mcp_name`

### 20.6 Estrategia de recuperación

Decisión V1:

- La recuperación será automática en fallos transitorios y conservadora en fallos repetidos.
- El sistema intentará reiniciar procesos MCP según la política de backoff definida.
- Si un MCP supera el umbral de fallo, quedará en estado `failed` hasta intervención o nuevo ciclo de arranque.
- El daemon no debe entrar en bucles agresivos de reinicio.

### 20.7 Recuperación en arranque

Decisión V1:

- Al arrancar, el daemon debe reconstruir su estado operativo básico.
- Si encuentra PID o estado efímero antiguo, debe validarlo antes de reutilizarlo.
- Si detecta residuos inconsistentes de una ejecución anterior, debe limpiarlos de forma segura y continuar.

### 20.8 Superficie de inspección para el usuario

La V1 debe ofrecer inspección simple desde CLI:

- `mcp-cli status`
- `mcp-cli logs`
- `mcp-cli logs --mcp github`
- `mcp-cli logs --level error`

Objetivo:

- permitir diagnóstico local sin obligar al usuario a abrir archivos manualmente

### 20.9 Retención de logs

Decisión V1:

- La retención será local y acotada.
- Debe existir rotación básica para evitar crecimiento sin control.
- La política exacta puede ser simple en V1, por ejemplo por tamaño total o número de archivos.

Requisito:

- La observabilidad no debe convertirse en una fuente de consumo descontrolado de disco.

### 20.10 Criterio de suficiencia para V1

La observabilidad de V1 será suficiente si permite:

- detectar procesos caídos
- entender por qué fallaron
- saber qué reinicios ocurrieron
- ver qué perfil y workspace estaban implicados
- saber cuándo una respuesta fue truncada o paginada
- depurar el sistema sin herramientas externas

## 21. Conclusión

Universal MCP Orchestrator es una idea sólida de infraestructura local, con potencial real para mejorar la operativa de herramientas de IA que dependen de servidores MCP. Su valor no depende de tener una lista enorme de conectores, sino de resolver bien las bases: procesos, aislamiento, compatibilidad, seguridad y control del contexto.

El documento debe usarse como base de definición de producto y arquitectura. No cierra todavía todas las decisiones. Las expone de forma explícita para que puedan resolverse con criterio antes de construir.
