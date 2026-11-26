## Revisión: hardware

### Comandos de hardware
<!-- Rellenar: los usa el agente verificador. -->
- Versión de KiCad: `...`
- ERC: `kicad-cli sch erc --severity-all --exit-code-violations --format json -o erc.json <proyecto>.kicad_sch`
- DRC: `kicad-cli pcb drc --schematic-parity --severity-all --exit-code-violations --format json -o drc.json <proyecto>.kicad_pcb`
- BOM: `kicad-cli sch export bom -o bom.csv <proyecto>.kicad_sch`
- Fabricante de PCB y documento de sus capacidades: `...`
- Margen de diseño (derating) del proyecto: `...`

### Lista de revisión
- **Límites eléctricos:** cada tensión, corriente, potencia y temperatura nueva cita su fuente (datasheet, revisión y sección); se usan las condiciones de operación recomendadas, no los máximos absolutos, con el margen del proyecto.
- **Huellas:** comparadas con el dibujo mecánico (pin 1, paso, pad expuesto, vista superior o inferior); orientación de polarizados (diodos, electrolíticos, conectores) marcada en la serigrafía.
- **Alimentación:** desacople cerca de cada pin de alimentación según el datasheet; reguladores dentro de su corriente y disipación; secuencia de arranque si el componente la exige.
- **Entradas y salidas:** pull-ups/pull-downs donde hacen falta (I2C, reset, pines de arranque); protección contra ESD, polaridad inversa y sobretensión en lo que sale de la placa.
- **PCB:** ancho de pista según la corriente, con el cálculo, la norma o herramienta usada (IPC-2221, IPC-2152, la calculadora de KiCad…) y los datos de entrada; separación según la tensión; retornos de tierra y pares diferenciales; disipación térmica; puntos de prueba en las señales que hay que medir.
- **ERC y DRC:** sin violaciones, o con cada excepción justificada; paridad esquemático-PCB.
- **BOM:** fabricante y MPN en cada componente; alternativa para los que tienen una sola fuente; DNP marcado.
- **Archivos de KiCad:** no se editaron como texto salvo pedido; las salidas de fabricación salen de una versión con commit.

### Reglas para los agentes
- **Verificador:** corre ERC, DRC y la exportación de BOM con los comandos de arriba y reporta los conteos. Si `kicad-cli` no está, lo dice y no da nada por pasado. Lo que necesita banco se reporta como "no verificado en placa".
- **Simplificador:** no toca archivos de KiCad (`.kicad_*`) ni salidas de fabricación; solo scripts y documentación del proyecto.
- **Revisor:** los puntos *Límites eléctricos* y *Huellas* de la lista se marcan como importantes.
