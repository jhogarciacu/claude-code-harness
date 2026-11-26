## Datos del hardware
- **Con fuente, siempre.** Registros, bits, pines, frecuencias, tiempos, límites eléctricos y erratas salen del datasheet, el manual de referencia, la hoja de erratas o el esquemático, citando documento, revisión y sección. Si no aparecen ahí, se pregunta. Nunca se inventa una dirección, un valor de registro ni un pinout.
- **El esquemático manda sobre el código:** si un pin o una configuración del código no coincide con el esquemático, se reporta antes de cambiar nada.

## Grabar y tocar el dispositivo
- **Grabar, borrar o reiniciar la placa solo con OK explícito**, y diciendo antes qué puerto y qué binario se usa.
- **Lo irreversible lo ejecuta el responsable a mano:** eFuses, fuses, lock bits, option bytes, protección de lectura, OTP, bootloader.
- Nada de comandos que muevan actuadores, motores, relés o fuentes sin OK: un comando por serie también puede causar daño físico.

## Archivos generados
- `sdkconfig` lo genera menuconfig: se cambia con `idf.py menuconfig` o en `sdkconfig.defaults`. Ojo: `sdkconfig.defaults` solo se aplica al crear un `sdkconfig` nuevo; si ya existe, hay que regenerarlo (por ejemplo, borrándolo antes de compilar).
- Proyectos de STM32CubeMX: la fuente es el `.ioc`. En el código generado solo se escribe dentro de los bloques `USER CODE BEGIN`/`USER CODE END`. El resto se pierde al regenerar.
- Código de protobuf o nanopb (`*.pb.c`, `*.pb.h`), la configuración que genera Kconfig (`autoconf.h`, `.config`) y todo lo que esté en carpetas de build: se cambia la fuente (`.proto`, `.options`, Kconfig, `prj.conf`) y se regenera.
- Código del fabricante (HAL, CMSIS, `managed_components/`) no se modifica. Si hace falta un parche, se propone y se documenta.
- El hook de esta capa pide confirmación antes de editar con Edit, Write o MultiEdit la mayoría de estos archivos; en CubeMX, solo si se cambia algo fuera de `USER CODE`. No ve lo que se hace por Bash (`sed -i`, `echo >`): la regla aplica igual.

## Código sensible
- Drivers, rutinas de interrupción, secciones críticas, arranque y linker script no se simplifican, reordenan ni "limpian" sin OK.
- Un `volatile`, una lectura "redundante" de un registro (por ejemplo, para limpiar una bandera) o un retardo que parece inútil suelen ser intencionales: se pregunta antes de quitarlos.
- No se cambian prioridades de interrupción, relojes, tamaño de pila ni el mapa de memoria sin OK.

## Verificar
- Se compila con los warnings del proyecto tratados como error y se reporta el tamaño: flash y RAM contra el presupuesto del `CLAUDE.md`.
- Comandos según la herramienta, si el `CLAUDE.md` no dice otra cosa:
  - ESP-IDF: `idf.py build` y `idf.py size`
  - PlatformIO: `pio run`, `pio run -t size` y `pio test -e native` para las pruebas en el host (si el `platformio.ini` define un entorno `native`)
  - Zephyr: `west build` y `west build -t rom_report` / `ram_report`
  - CMake/Make con GCC de ARM: compilar y `arm-none-eabi-size`
- La lógica que no depende del hardware se prueba en el host (Unity, Ceedling, GoogleTest o un entorno `native` de PlatformIO).
- Análisis estático (`cppcheck`, `clang-tidy`) si el proyecto lo define.
- **Sin placa no hay ✅:** lo que solo compiló o corrió en simulador se reporta como "no verificado en hardware", con lo que falta probar.
