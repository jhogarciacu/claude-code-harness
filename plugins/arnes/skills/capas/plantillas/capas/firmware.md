## Revisión: firmware

### Comandos de firmware
<!-- Rellenar: los usa el agente verificador. Grabar solo con OK del responsable. -->
- Compilar para la placa: `...`
- Tamaño (flash/RAM): `...`
- Pruebas en el host: `...`
- Grabar (solo con OK): `...`
- Presupuesto: flash `... KB` de `... KB`, RAM `... KB` de `... KB`

### Lista de revisión
- **Concurrencia e interrupciones:** `volatile` y accesos atómicos en lo que comparte una ISR con el resto; ISR cortas, sin bloqueos, `printf` ni reservas de memoria; secciones críticas mínimas.
- **Memoria:** pila de cada tarea con margen; sin `malloc` en tiempo de ejecución salvo que el proyecto lo permita; flash y RAM dentro del presupuesto.
- **Tiempos y buses:** timeouts en I2C, SPI, UART y esperas activas; el watchdog se alimenta donde corresponde y no se desactiva "para probar".
- **Arranque y fallas:** estado seguro de salidas al arrancar, tras un reset y ante un error; se manejan los códigos de error de HAL y SDK.
- **Datos:** desbordes en enteros y punto fijo; endianness y alineación en protocolos y estructuras empaquetadas.
- **Datos del hardware:** cada registro, pin o tiempo nuevo cita su fuente (datasheet, manual de referencia o esquemático, con sección).
- **Archivos generados:** no se editaron a mano (`sdkconfig`, código de CubeMX fuera de `USER CODE`, `*.pb.c`/`*.pb.h`); se cambió la fuente y se regeneró.
- **Compilación:** sin warnings nuevos; análisis estático si el proyecto lo define.

### Reglas para los agentes
- **Verificador:** compila, mide el tamaño y corre las pruebas en el host. Lo que necesita la placa se reporta como "no verificado en hardware". Nunca graba.
- **Simplificador:** no toca drivers, ISR, secciones críticas, arranque ni linker script, ni quita `volatile` o lecturas de registros "redundantes", sin OK del responsable.
- **Revisor:** los puntos *Datos del hardware* y *Archivos generados* de la lista se marcan como importantes.
