*Esqueleto: las reglas completas y la lista de revisión de esta capa llegan en A-05.*

- **ERC y DRC** con `kicad-cli` antes de dar por terminado un cambio de esquemático o PCB; se reportan los resultados.
- **Archivos de KiCad** (`.kicad_sch`, `.kicad_pcb`, `.kicad_pro`): no se editan a mano salvo que se pida; los cambios se hacen en KiCad o con sus herramientas.
- **Límites eléctricos con fuente:** tensiones, corrientes, potencias y temperaturas salen del datasheet del componente, citando documento y sección.
- **BOM:** cada componente con número de parte del fabricante; no se inventan referencias.
