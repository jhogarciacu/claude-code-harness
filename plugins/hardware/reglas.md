## Datos eléctricos y de componentes
- **Con fuente, siempre.** Tensiones, corrientes, potencias, temperaturas, tiempos, pinouts y encapsulados salen del datasheet del componente (o de la nota de aplicación del fabricante), citando documento, revisión y sección o tabla. Si no aparecen ahí, se pregunta. Nunca se inventa un límite, un pinout ni un número de parte.
- **Máximos absolutos no son condiciones de operación:** se diseña con las "recommended operating conditions" y se dice qué margen se dejó. El criterio de margen lo fija el proyecto; si no lo dice, se pregunta.
- **La huella se compara con el dibujo mecánico** del datasheet: pin 1, paso, pad expuesto, y si el dibujo es vista superior o inferior. Una huella de librería no se da por buena sin esa comparación.
- **Capacidades del fabricante de PCB** (pista y separación mínimas, taladro, anillo, capas, espesor de cobre): de su documento o página, citada. No de memoria.
- **BOM:** cada componente con fabricante y número de parte del fabricante (MPN). Disponibilidad, precio y estado de ciclo de vida solo si se consultaron en la fuente; si no, se dice "no consultado".

## Archivos de KiCad
- `.kicad_sch`, `.kicad_pcb`, `.kicad_sym`, `.kicad_mod` y `.kicad_pro` se cambian en KiCad (o con sus herramientas y scripts oficiales), no editando el texto a mano: un cambio manual puede romper UUIDs, referencias o la sincronía entre esquemático y PCB. Solo se editan a mano si el responsable lo pide.
- Gerbers, archivos de taladro, posiciones y demás salidas de fabricación se regeneran desde el PCB; nunca se editan.
- El hook de esta capa pide confirmación antes de editar con Edit, Write o MultiEdit los archivos de diseño de arriba, los Gerber (`.gbr`, `.gbrjob` y extensiones Protel como `.gtl` o `.g1`), el taladro (`.drl`), las posiciones (`.pos`) y lo que esté en carpetas `*-backups/`. No ve lo que se hace por Bash (`sed -i`, `echo >`): la regla aplica igual.
- `.kicad_dru` (reglas de diseño propias), `fp-lib-table` y `sym-lib-table` sí se pueden editar como texto.

## Verificar
- Antes de dar por terminado un cambio de esquemático o PCB se corren ERC y DRC y se reportan los conteos de errores y advertencias. Comandos de `kicad-cli` (docs.kicad.org, manual CLI de KiCad 9.0 y 10.0, secciones "Schematic ERC" y "PCB DRC"), si el `CLAUDE.md` no dice otra cosa:
  - ERC: `kicad-cli sch erc --severity-all --exit-code-violations --format json -o erc.json <proyecto>.kicad_sch`
  - DRC: `kicad-cli pcb drc --schematic-parity --severity-all --exit-code-violations --format json -o drc.json <proyecto>.kicad_pcb`
  - Con `--exit-code-violations` salen con 0 si no hay violaciones y con 5 si hay alguna.
  - BOM: `kicad-cli sch export bom -o bom.csv <proyecto>.kicad_sch`, con `--fields` para incluir el MPN si el proyecto lo usa.
- `--refill-zones` y `--save-board` existen solo desde KiCad 10. `--save-board` modifica el PCB: solo con OK.
- Con `--severity-all` las advertencias también cuentan como violaciones (código 5).
- Una violación excluida o aceptada se justifica por escrito (en el esquemático o en `Docs/`), no se silencia.
- **ERC y DRC en verde no prueban que el circuito funcione.** Lo que necesita banco (tensiones, consumo, señales, temperatura) se reporta como "no verificado en placa", con lo que falta medir.
- Si `kicad-cli` no está instalado, se dice; no se da el ERC o el DRC por pasados.

## Fabricación
- Las salidas de fabricación (Gerber, taladro, posiciones, BOM) se generan desde una versión con commit, y se anota esa versión.
- Las reglas del fabricante se cargan como reglas de diseño del proyecto antes del DRC final.

## Seguridad física
- Con tensión de red, baterías de litio, supercondensadores o corrientes altas se avisa del riesgo y no se proponen pruebas sin protección (fusible, fuente con límite de corriente, aislamiento).
- Encender, medir o conectar una placa lo hace el responsable. Claude no da por hecha una medición que no vio.
