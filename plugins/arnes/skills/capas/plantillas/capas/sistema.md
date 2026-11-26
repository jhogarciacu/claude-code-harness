## Revisión: sistema (contrato entre capas)
- Cada interfaz entre capas tiene una sola fuente (esquema versionado) y los dos lados se validan contra ella.
- Un cambio de interfaz sube la versión y actualiza los dos lados en la misma tarea.
- Matriz de compatibilidad de versiones al día (firmware ↔ host ↔ hardware).
- Pruebas de integración, y HIL si hay banco, antes de cerrar una tarea que toque una interfaz.
