## Revisión: firmware
- `volatile` y accesos atómicos en variables compartidas con interrupciones.
- Nada bloqueante ni `printf` dentro de una ISR; ISR cortas.
- Tamaño de pila y uso de flash/RAM contra el presupuesto del proyecto.
- Watchdog: se alimenta donde corresponde y no se deshabilita "para probar".
- Desbordes en enteros y punto fijo; endianness en protocolos.
- Timeouts en buses (I2C, SPI, UART) y estado seguro al arrancar y ante fallas.
- Warnings del compilador cruzado tratados como error; análisis estático si el proyecto lo define.
