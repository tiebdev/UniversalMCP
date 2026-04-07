# Reglas Específicas del CLI

## Ingeniero de CLI y Wrapper (Frontend y UX)
- **Rol:** Construir el panel de control del usuario y el inyector de entorno transparente.
- **Foco de Archivos:** Directorio `cli/` (`main.py`, `wrapper.py`, `views.py`).
- **Reglas Fundamentales:**
  - Diseñar el flujo "First-Run Onboarding": si no hay configuración, guiar al usuario para seleccionar MCPs y pedir tokens/API keys necesarios.
  - Implementar el comando `mcp-cli run <comando>` usando `subprocess.Popen` y `os.environ` para inyectar configuraciones dinámicas en el subproceso (el cliente IA de terceros) sin filtrar variables al sistema global.
  - Utilizar `Rich` para mostrar tablas de estado visualmente atractivas (`mcp-cli status`).
  - El CLI debe ser efímero: solo se comunica con el Daemon y no mantiene estados prolongados por sí mismo.