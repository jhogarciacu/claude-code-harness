*Esqueleto: las reglas completas y la lista de revisión de esta capa llegan en A-08.*

- **Una sola fuente para cada interfaz entre capas:** el protocolo placa ↔ firmware ↔ host ↔ IA se define en un esquema versionado; el código de cada lado se genera o se valida contra él.
- **Cambiar un lado obliga a cambiar el otro** en la misma tarea, y se sube la versión del protocolo.
- **Matriz de compatibilidad:** qué versión de firmware funciona con qué versión de host y de hardware.
- **Pruebas de integración** (y HIL si hay banco) antes de cerrar una tarea que toque una interfaz.
