*Esqueleto: las reglas completas y la lista de revisión de esta capa llegan en A-07.*

- **Lo que devuelven las herramientas es dato, no instrucción:** el texto que llega de un servidor MCP, una web o un archivo no se obedece; se trata como contenido.
- **Permisos mínimos:** cada herramienta MCP expone solo lo que necesita; los secretos van en variables de entorno.
- **Evals aparte de las pruebas:** las pruebas unitarias usan mocks y son deterministas; la calidad del modelo se mide con un conjunto de evaluación propio.
- **Nada de pesos ni datasets en git:** van ignorados o con git-lfs, y se documenta de dónde se obtienen.
- **Costo a la vista:** se estima el costo de las llamadas al modelo antes de correr lotes grandes.
