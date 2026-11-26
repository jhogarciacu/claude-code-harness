# Plan del arnés

## Tareas

| ID | Tarea | Estado | Verificación |
|---|---|---|---|
| A-01 | Reglas de hardware y optimización en el CLAUDE.md global + hook que protege el hardware al grabar | Terminada (PR #1). Hook probado en sesión (ver A-02) | `python3 -m unittest discover -s hooks -v`: 10 pruebas en verde con 66 casos bloqueados, 77 con confirmación, 50 permitidos y 6 entradas inválidas. Incluyen los hallazgos del verificador, del simplificador y de las dos pasadas del revisor: bucles, `timeout`, `sudo -u`, `bash -lc`, `ssh`, `docker`, `git bisect run`, `option_write`, fuses UPDI, `make fuses`, y commits con heredoc o comillas invertidas que no deben bloquearse. Además: prueba de mutación (al quitar el tope de "texto que nadie ejecuta" fallan 8 casos), fuzz de 30 000 entradas sin excepciones y 2 000 segmentos en menos de 0.1 s. Probado en una sesión real de Claude Code en A-02 (bloqueo de `burn_efuse` en VSCode y confirmación de `idf.py flash` con `claude -p`) |
| A-02 | Estructura por áreas y plugin `nucleo` | Terminada (PR #2) | `./pruebas.sh` en verde con 35 pruebas: 18 del validador de estructura y 17 del hook de hardware y el anuncio de sesión, más la sintaxis de scripts. Comprobado que `pruebas.sh` sale con 1 si falla una prueba o si no se ejecuta ninguna. Cierre con verificador, simplificador (en paralelo con el revisor, porque solo propone) y revisor. Corregido lo que encontraron: comando de activación que la documentación no respalda, `reglas.md` que no está en UTF-8, validador frente a entradas mal formadas, plugins sin registrar, dependencias de otro marketplace, rutas con comillas en los hooks, tamaño de `reglas.md`, y `pruebas.sh` con cero pruebas. **Probado en Claude Code 2.1.332 (2026-11-25):** `nucleo` instalado con `claude plugin install`. Una sesión nueva (`claude -p`) recibe "Arnés activo: nucleo 0.3.0" y tiene los agentes `nucleo:revisor`, `nucleo:simplificador` y `nucleo:verificador`. `claude plugin validate` pasa para el marketplace y para `nucleo`; solo avisa que falta un ícono. **Hook en sesión real (2026-11-26):** en VSCode, `true espefuse.py burn_efuse JTAG_DISABLE` quedó bloqueado con el mensaje del arnés. Con `claude -p`, modo `default` y permiso general a Bash, `true idf.py -p /dev/ttyUSB0 flash` no se ejecutó: el arnés pidió confirmación. **Límite:** en modo automático, la misma confirmación se resolvió sin preguntar. Lo irreversible sigue bloqueado; la grabación normal puede pasar (ver propuestas) |
| A-03 | Capa `firmware` completa y hook de archivos generados | Hecha, falta el merge | `./pruebas.sh` en verde con 91 pruebas (12 del hook nuevo, con prueba de mutación). **Probado con `claude -p` en un proyecto con `firmware` activa:** la sesión recibe las reglas de la capa; editar `sdkconfig` con Edit, con permiso general a Edit y Write, no se aplicó porque el arnés pidió confirmación; editar dentro de un bloque `USER CODE` de CubeMX se aplicó sin preguntar. Cierre con los agentes del arnés (`arnes:verificador`, `arnes:simplificador`, `arnes:revisor`). Corregido lo que encontraron: con `replace_all` se escapaban ediciones fuera de `USER CODE`, y escribir en un bloque vacío pedía confirmación siempre. Ahora la edición se simula en memoria y se compara lo que queda fuera de los bloques. También: rutas relativas al proyecto y symlinks, bloques sin cerrar, más archivos generados (`build-*/`, `Middlewares/`, arranque y linker de CubeMX, `dependencies.lock`, `*.pb-c.c`, `*.pb.cc`) y precisiones en las reglas. 99 pruebas en verde, con pruebas de mutación de `replace_all` y de los bloques |
| A-04 | Comandos `/arnes:capas` y atajos por capa, y esqueleto de las cinco capas (va antes que A-03) | Terminada (PR #3) | `./pruebas.sh` en verde con 78 pruebas (43 de `arnes.py`). **Cambio de nombres, pedido por el responsable:** el plugin del núcleo pasa de `nucleo` a `arnes`, el menú es `/arnes:capas` y hay un atajo por capa; reinstalado en este equipo (`arnes` 0.5.0, 6 skills). Probado con `claude -p`: la sesión ve los seis comandos `arnes:…`, `/arnes:firmware` y luego `/arnes:software` dejan las dos capas activas, y la sesión siguiente anuncia arnes 0.5.0, firmware y software. Cierre con verificador, simplificador y revisor (en paralelo, porque ninguno modifica). Corregido lo que encontraron: `/arnes:capas` en la carpeta personal escribía el `settings.json` de usuario; aviso de capa que puede no cargar; escritura que rompía symlinks y permisos; errores de archivo con traceback; `Docs` como archivo; `completar` para no editar a mano; pasos del SKILL más claros. `claude plugin validate` pasa para el marketplace y las seis carpetas (solo avisos de ícono y licencia). **Probado con Claude Code 2.1.332 (`claude -p`) en una carpeta vacía:** `/arnes firmware software` activó las dos capas y preguntó antes de crear archivos; con el OK creó `CLAUDE.md` (con las secciones de revisión de las dos capas), `Docs/` y `.gitignore`; una sesión nueva en esa carpeta anunció nucleo 0.4.0, firmware 0.1.0 y software 0.1.0. Comprobado también: anotar `sistema` solo no carga nada, y anotar las cinco sí carga las cinco. **Probado en VSCode por el responsable (2026-11-26):** el plugin carga en la extensión (anuncio "Arnés activo: arnes 0.5.0", agentes y los seis comandos); en el repo del arnés `/arnes:capas` se niega, como se espera; en una carpeta de prueba muestra el selector de modo (proyecto completo o elegir capas) |
| A-05 | Capa `hardware` completa y hook de archivos de KiCad | Hecha, falta el merge | `./pruebas.sh` en verde con 107 pruebas (8 del hook nuevo; las dos pruebas de plantilla de firmware y hardware quedan en una). Prueba de mutación: 8 mutaciones del hook (quitar `.kicad_pcb`, la carpeta de respaldos, las mayúsculas, la decisión `ask`, la ruta relativa al proyecto, las capas Protel `.gN`, el manejo del byte nulo y el de `tool_name` que no es texto) hacen fallar las pruebas. **Probado con `claude -p` (Claude Code 2.1.332):** en un proyecto con `hardware` activa, la sesión anuncia arnes 0.5.2 y hardware 0.2.0 y cita el comando de DRC de las reglas; con permiso general a Edit, editar `placa.kicad_sch` no se aplicó porque el arnés pidió confirmación, y editar `placa.kicad_dru` sí. En un proyecto sin la capa, solo está el núcleo y la edición del `.kicad_sch` se aplica. `claude plugin validate` pasa para el marketplace y para `plugins/hardware`. Cierre con verificador, simplificador y revisor (en paralelo, porque el simplificador solo propone). Corregido lo que encontraron: `-backups` se medía en la ruta absoluta (un proyecto dentro de `viejos-backups/` preguntaba por todo) y ahora se mide relativa al proyecto; tracebacks con `tool_name` que no es texto o con byte nulo en la ruta; capas Protel `.g3`+ y `.pos` sin cubrir; `--save-board` también es solo de KiCad 10; la plantilla ya no afirma qué norma usa la calculadora de KiCad; pruebas de plantilla unidas en una con `subTest`. **No verificado:** `kicad-cli` no está instalado aquí, así que los comandos de ERC, DRC y BOM se tomaron de la documentación oficial (docs.kicad.org, manual CLI 9.0 y 10.0, secciones "Schematic ERC", "PCB DRC" y "Schematic export: bill of materials") sin ejecutarlos. Las opciones de `sch erc` y `sch export bom` vinieron de un resumen de esas páginas: conviene confirmarlas con `kicad-cli sch erc -h` al instalar KiCad |
| A-06 | Plugin `software` | Pendiente | — |
| A-07 | Plugin `ia` | Pendiente | — |
| A-08 | Plugin `sistema` (todas las áreas + contrato entre capas) | Pendiente | — |

---

# Plan A-02 a A-08: arnés por áreas

## Objetivo
Que cada proyecto cargue **solo lo que necesita**:

- **Un área sola.** Un proyecto de firmware carga el núcleo y `firmware`. No ve reglas de KiCad ni de MCP.
- **Varias áreas.** Por ejemplo, un servidor MCP con algo de optimización activa `ia` y `software`.
- **Proyecto completo.** Se activa `sistema` y se carga todo el arnés: las cinco áreas más las reglas que unen las capas (placa ↔ firmware ↔ host ↔ IA).

## Cómo se usa

En cualquier proyecto se escribe **`/arnes:capas`** en el chat de Claude Code (VSCode o terminal). Muestra qué capas están activas, deja marcar las que se necesitan y aplica el cambio solo para ese proyecto.

| Caso | Qué marcar en `/arnes:capas` |
|---|---|
| Solo firmware | `firmware` |
| Firmware + app de escritorio | `firmware` y `software` |
| Servidor MCP | `ia` |
| Producto completo | `sistema` (trae las cinco) |

- La activación queda en el `.claude/settings.json` del proyecto (`enabledPlugins`), que se versiona con el proyecto.
- A nivel de usuario (en todos los proyectos) solo se instala `arnes` (núcleo).
- Las áreas se activan siempre **por proyecto**, nunca a nivel de usuario.
- Sin `/arnes:capas` también se puede, desde la terminal y en la carpeta del proyecto: `claude plugin install <área>@claude-code-harness --scope project`. El panel `/plugin` sirve en la terminal, pero no en la extensión de VSCode.

## Cómo activar el arnés en un proyecto

### Una sola vez por computador
1. Clonar el arnés y enlazar el CLAUDE.md global:
   ```bash
   git clone git@github.com:jhogarciacu/claude-code-harness.git ~/Escritorio/proyectos/claude-arnes
   ~/Escritorio/proyectos/claude-arnes/instalar.sh
   ```
2. Instalar Claude Code para terminal (si no está) y el núcleo, desde bash:
   ```bash
   curl -fsSL https://claude.ai/install.sh | bash
   claude plugin marketplace add ~/Escritorio/proyectos/claude-arnes
   claude plugin install arnes@claude-code-harness
   claude plugin list            # arnes@claude-code-harness debe salir ✔ enabled
   ```
   Desde aquí, cualquier carpeta tiene el núcleo: reglas generales, los 3 agentes, `/arnes:capas` y la protección de hardware.

### Activar capas con `/arnes:capas`
1. Abrir la carpeta del proyecto con Claude Code (`code .` o `claude`) y aceptar que se confía en ella. Sin eso, Claude Code ignora la configuración del proyecto.
2. Escribir `/arnes:capas`. El comando:
   1. **muestra el estado:** qué capas están activas en este proyecto;
   2. **muestra la lista de capas** para marcar (selección múltiple). La lista sale del marketplace, así que cada capa nueva aparece sola;
   3. **aplica la selección:** activa y desactiva capas solo en este proyecto;
   4. **si la carpeta es nueva o le faltan piezas**, ofrece crear el `CLAUDE.md` (con las listas de revisión de cada capa y las secciones del proyecto: comandos, definición de terminado y carpetas protegidas), `Docs/` (visión, requisitos, plan y decisiones) y el `.gitignore` de cada capa. **Nunca sobrescribe:** si algo ya existe, propone lo que falta y espera el OK;
   5. **recuerda el último paso:** abrir una conversación nueva para que las capas carguen. `/arnes:capas` no puede recargar la conversación en la que se ejecuta.
3. En la conversación nueva, cada capa activa anuncia "Arnés activo: <capa> <versión>". Basta con preguntar "¿qué arnés está activo?".

Para cambiar las capas después, o para quitar alguna, se vuelve a escribir `/arnes:capas`.

### Clonar un proyecto en otro computador
1. Hacer una vez la instalación por computador.
2. Clonar el proyecto, abrirlo y confiar en la carpeta.
3. Escribir `/arnes:capas`. Muestra las capas que el proyecto tiene anotadas. Si en ese computador el marketplace no viene de una carpeta local, avisa que una capa anotada puede no cargar y da el comando para instalarla (`claude plugin install <capa>@claude-code-harness --scope project`, en la terminal). Según la documentación oficial, un plugin anotado solo en el `.claude/settings.json` del proyecto no siempre se carga hasta instalarlo en el computador.

## Qué trae cada plugin

| Plugin | Depende de | Contenido |
|---|---|---|
| `arnes` (núcleo) | — | Agentes verificador, simplificador y revisor. Comandos `/arnes:capas` (menú) y `/arnes:firmware`, `/arnes:hardware`, `/arnes:software`, `/arnes:ia`, `/arnes:sistema` (atajos). Hook de protección de hardware (ver decisión D-2) |
| `firmware` | `arnes` (núcleo) | Reglas: no grabar ni tocar fuses sin OK, archivos generados de CubeMX, `sdkconfig` y Kconfig. Lista de revisión: `volatile`, ISR, pila, watchdog, endianness, timeouts de buses y estado seguro. Verificación: warnings como error, análisis estático y presupuesto de flash/RAM. El simplificador no toca drivers ni ISR sin OK |
| `hardware` | `arnes` (núcleo) | Reglas: límites eléctricos, huellas y capacidades del fabricante con fuente; no editar `.kicad_*` a mano salvo que se pida (un hook pide confirmación); ERC, DRC con paridad y BOM con `kicad-cli`; ERC/DRC en verde no es "funciona"; fabricación desde una versión con commit; seguridad física. Lista de revisión de esquemático y PCB y reglas para los agentes |
| `software` | `arnes` (núcleo) | Reglas: sin medición no hay optimización (antes y después, mismas condiciones, números) y benchmarks reproducibles. Lista de revisión: concurrencia, memoria, complejidad y portabilidad x86/ARM64 |
| `ia` | `arnes` (núcleo) | Reglas: seguridad MCP (prompt injection, permisos mínimos de herramientas, secretos), evals aparte de las pruebas con mocks, no versionar pesos ni datasets, costo de las llamadas |
| `sistema` | las cinco | Solo lo que une las capas: el protocolo entre capas tiene una única fuente (esquema) y se versiona; cambiar un lado obliga a cambiar el otro en la misma tarea; matriz de compatibilidad de versiones; pruebas de integración y HIL; trazabilidad de requisitos entre capas |

`sistema` **no copia** las reglas de las áreas: las activa con `dependencies`. Así cada regla vive en un solo lugar.

## Cómo llegan las reglas a Claude
Según la documentación oficial de plugins, el `CLAUDE.md` que está dentro de un plugin no se carga.

- **Reglas que deben estar siempre activas:** cada área tiene un `reglas.md`, y el hook `SessionStart` (`hooks/anunciar.py`, el mismo en todos los plugins) lo inyecta al empezar la sesión y después de cada compactación. Solo se carga si el área está activa en el proyecto.
- **Listas de revisión para los agentes:** `/arnes:capas` las copia al `CLAUDE.md` del proyecto.
- **Confirmado en la documentación (A-02):** los subagentes cargan toda la jerarquía de `CLAUDE.md` (usuario y proyecto). No está documentado que reciban el contexto del `SessionStart`. Por eso las listas de revisión **van al `CLAUDE.md` del proyecto**, y el plugin no las inyecta.

## Estructura del repo

```
.claude-plugin/marketplace.json     # lista los 6 plugins
plugins/
  arnes/      .claude-plugin/plugin.json · agents/ · skills/capas/ y un skill por capa · hooks/ (protección de hardware)
  firmware/   .claude-plugin/plugin.json · reglas.md · revision.md · hooks/hooks.json (SessionStart)
  hardware/   ...igual que firmware
  software/   ...
  ia/         ...
  sistema/    .claude-plugin/plugin.json (dependencies: las cinco) · reglas.md · revision.md · hooks/
global/CLAUDE.md                    # solo reglas generales (sale la sección de hardware)
plantillas/                         # CLAUDE.md, .gitignore y Docs/ que usa /arnes
pruebas.sh                          # corre las pruebas de todos los plugins
```

## Tareas, en orden

| ID | Qué | Verificación |
|---|---|---|
| A-02 | Pasar a `plugins/`. Convertir `arnes` en `nucleo`. Listar los plugins en el marketplace. Sacar la sección de hardware del CLAUDE.md global y dejar reglas generales: datos técnicos con fuente citada y nada irreversible sin OK. Agregar `pruebas.sh` y `herramientas/validar.py`. Anuncio "Arnés activo" con `SessionStart`. Consultar la documentación para saber si los subagentes ven el contexto de `SessionStart` | Pruebas del hook en verde desde su nueva ubicación. JSON válidos. Prueba manual del responsable: instalar `nucleo` y ver los 3 agentes en `/agents` |
| A-03 | Plugin `firmware`: `reglas.md`, `revision.md` y `SessionStart`, con la línea "Arnés activo: …" | Prueba del `SessionStart` (imprime las reglas). En un proyecto de prueba con `firmware` activo, las reglas aparecen; en uno sin `firmware`, no |
| A-04 | Comando `/arnes:capas` (skill del núcleo) y **esqueleto de las cinco capas**, para poder elegir capas desde ya. Ver "Detalle de A-04" | Ver "Detalle de A-04" |
| A-05 | Plugin `hardware` | Igual que A-03 |
| A-06 | Plugin `software` | Igual que A-03 |
| A-07 | Plugin `ia` | Igual que A-03 |
| A-08 | Plugin `sistema` con `dependencies` | Activar `sistema` en un proyecto de prueba activa las cinco áreas y sus reglas |

**Orden actualizado (decisión del responsable):** A-04 va primero. Crea `/arnes:capas` y el esqueleto de las cinco capas, y después A-03, A-05, A-06, A-07 y A-08 completan el contenido de cada capa sin cambiar cómo se activan.

## Detalle de A-04

### Flujo de `/arnes:capas`
1. **Estado.** Ejecuta `arnes.py estado` y muestra: "Capas activas en este proyecto: …" y qué falta. Si el marketplace no viene de una carpeta local, avisa que una capa anotada puede no cargar y da el comando para instalarla. Se niega a trabajar en la carpeta personal, en `/` y en el repo del arnés, porque allí un cambio afectaría a todos los proyectos.
2. **Primera pregunta** (una sola opción):
   - **Proyecto completo (sistema)**
   - **Elegir capas**
   - **Quitar todas las capas**
   - **Dejarlo como está**
3. **Segunda pregunta**, solo si se elige "Elegir capas" (selección múltiple): `firmware`, `hardware`, `software`, `ia`. El texto de la pregunta dice cuáles están activas hoy; el selector de Claude Code no permite dejarlas marcadas. `sistema` va aparte porque el selector admite como máximo 4 opciones por pregunta. Si no se marca ninguna, no se aplica nada.
4. **Aplicar.** Ejecuta `arnes.py aplicar <capas>`: activa las elegidas y desactiva las que se quitaron, solo en el `.claude/settings.json` del proyecto, sin tocar el resto de ese archivo. Después muestra el resultado.
5. **Preparar el proyecto.** Si faltan `CLAUDE.md`, `Docs/` o `.gitignore`, pregunta si se crean desde las plantillas y ejecuta `arnes.py preparar`. **Nunca sobrescribe.** Lo que ya existe se deja intacto; si le faltan secciones de capa o líneas de `.gitignore`, se informan y, con el OK, `arnes.py completar` las agrega al final.
6. **Cierre.** Pide abrir una conversación nueva para que las capas carguen, y preguntar ahí "¿qué arnés está activo?".

### Esqueleto de cada capa
Cada una de `firmware`, `hardware`, `software`, `ia` y `sistema` lleva:
- `plugin.json`, versión 0.1.0. Las cuatro primeras dependen de `arnes` (núcleo); `sistema` depende de las cuatro.
- `hooks/hooks.json` con `SessionStart` y una copia de `anunciar.py`, idéntica a la del núcleo. `validar.py` comprueba que lo sea.
- `reglas.md` mínimo, con las reglas ya acordadas para esa capa y la nota "se completa en A-0x". La regla "sin medición no hay optimización" sale del CLAUDE.md global y pasa a `software`.

### Archivos
| Archivo | Qué es |
|---|---|
| `plugins/arnes/skills/capas/SKILL.md` | El comando: los pasos que sigue Claude y las preguntas que hace |
| `plugins/arnes/skills/capas/arnes.py` | La lógica: `estado`, `aplicar`, `agregar`, `preparar`, `completar` y `seccion`. Biblioteca estándar |
| `plugins/arnes/skills/capas/test_arnes.py` | Pruebas de la lógica |
| `plugins/arnes/skills/{firmware,hardware,software,ia,sistema}/SKILL.md` | Atajos `/arnes:<capa>`: activan su capa con `arnes.py agregar` sin quitar las demás |
| `plugins/arnes/skills/capas/plantillas/` | `CLAUDE.md`, `Docs/` (visión, requisitos, plan, decisiones) y `.gitignore` base, más una sección por capa |
| `plugins/{firmware,hardware,software,ia,sistema}/` | El esqueleto de cada capa |
| `.claude-plugin/marketplace.json` | Registra las cinco capas |
| `global/CLAUDE.md`, `README.md`, `Docs/plan.md` | Mover la regla de medición, explicar el uso de `/arnes:capas` y registrar estado y decisiones |

### Verificación
- `test_arnes.py`:
  - estado de un proyecto sin `.claude/`, con capas y con un `settings.json` que tiene otras claves;
  - aplicar una capa, varias, `sistema`, y quitar todas;
  - no tocar las otras claves del `settings.json`;
  - `preparar` en una carpeta vacía y en una con archivos que ya existen (no los sobrescribe);
  - JSON roto en el proyecto (error claro, sin destruir nada).
- `./pruebas.sh` en verde, y `claude plugin validate` para el marketplace y las seis carpetas.
- **Prueba real con `claude -p`** en una carpeta de prueba del scratchpad: aplicar `firmware` con `arnes.py` y comprobar que la sesión nueva anuncia "Arnés activo: firmware 0.1.0". Después, lo mismo con `sistema`, que debe anunciar las cinco capas.
- **Prueba del responsable:** en VSCode y en la terminal, escribir `/arnes:capas`, elegir capas y abrir una conversación nueva.

### Lo que se resolvió al construirla (comprobado con `claude -p`)
- **Nombre:** Claude Code antepone el nombre del plugin a sus comandos. Por eso el plugin del núcleo se llama `arnes` y los comandos son `/arnes:capas` y `/arnes:<capa>`.
- **Cómo aplicar:** basta con anotar la capa en el `.claude/settings.json` del proyecto. Con el marketplace agregado desde la carpeta local, la sesión siguiente la carga. No hace falta `claude plugin install`.
- **`sistema`:** si se anota solo, Claude Code no carga nada (ni siquiera `sistema`), porque sus dependencias no están activas. Por eso `/arnes:sistema` (o `/arnes:capas sistema`) anota las cinco capas.
- **Ruta del marketplace:** `arnes.py` lo encuentra en `~/.claude/plugins/known_marketplaces.json` y, si no está ahí, en la carpeta del repo donde vive el skill.

### Fuera de alcance
- `extraKnownMarketplaces` no se escribe en esta tarea, para no arriesgar que Claude Code reemplace la copia local por un clon de GitHub. Se resuelve cuando haga falta usar el arnés en otro computador.
- El contenido completo de las listas de revisión de cada capa: va en A-03 y de A-05 a A-08.

## Decisiones propuestas (las confirmas al aprobar)
- **D-1. Un solo repo y un solo marketplace, con un plugin por área.** Así hay una sola versión, una sola instalación y pruebas compartidas.
- **D-2. El hook de protección de hardware se queda en `arnes` (núcleo), no en `firmware`.** Solo actúa cuando aparece una herramienta de grabación, así que en un proyecto de software no molesta. Si estuviera en `firmware`, dejaría de proteger justo en el proyecto donde alguien graba una placa "de paso". El área `firmware` aporta las reglas y la lista de revisión.
- **D-3. `sistema` arrastra las áreas con `dependencies`, sin copiarlas.**
- **D-4. Las áreas se instalan siempre por proyecto. A nivel de usuario va solo `arnes` (núcleo).**

## Riesgos
- **Cambio de nombre.** En A-02 el plugin pasó de `arnes` a `nucleo`, y en A-04 volvió a `arnes` para que los comandos se lean `/arnes:…`. En cada computador donde estuviera `nucleo` hay que ejecutar `claude plugin uninstall nucleo@claude-code-harness` y `claude plugin install arnes@claude-code-harness`. En este equipo ya está hecho.
- **Activar no es instalar.** `enabledPlugins` no instala nada. En cada computador hay que agregar el marketplace una vez. Además, Claude Code solo respeta el `.claude/settings.json` de un proyecto después de aceptar el diálogo de confianza de la carpeta.
- **Prueba real pendiente.** `claude` no está en el PATH de esta terminal, así que la prueba dentro de Claude Code la haces tú en cada tarea. Te dejo los pasos exactos.
- **Listas copiadas.** Las listas de revisión se copian al proyecto (ver arriba). Si después cambian en el arnés, hará falta un comando para sincronizarlas (queda como propuesta).
- **Fuente del marketplace (A-04, posible).** En este computador el marketplace se agregó desde la carpeta local. Si el `extraKnownMarketplaces` que escribe `/arnes:capas` lo declara desde GitHub con el mismo nombre, la documentación dice que Claude Code "lo vuelve a traer desde la nueva fuente", y podría reemplazar el marketplace local por un clon. Hay que probarlo en A-04 antes de elegir qué declarar.
- **`/plugin install … --scope project` dentro de la sesión.** La documentación no respalda la bandera `--scope` ahí. Por eso el README usa el panel `/plugin` o la CLI `claude plugin install`.
- **`systemMessage` en `SessionStart`.** La documentación dice que `systemMessage` se muestra al usuario, pero no confirma que funcione en `SessionStart`. Si no aparece, la línea igual llega a Claude por `additionalContext`, y basta con preguntarle qué arnés está activo.

## Propuestas (sin aprobar)
- **Estrategia de pruebas estandarizada (pedida por el responsable, 2026-11-26):** un agente `probador` que diseña y escribe las pruebas de cada tarea; una plantilla `Docs/pruebas.md` con los niveles, los comandos, las convenciones de pruebas robustas y la matriz requisito → prueba; y una sección de pruebas por capa. Propuesta detallada en la conversación; pendiente de aprobar como A-09.
- **Modo automático y grabación:** en modo automático, la confirmación del hook al grabar firmware se resuelve sola. Opción: que el hook detecte el modo (`permission_mode` en la entrada del hook) y, en modo automático, bloquee la grabación en vez de pedir confirmación. Lo decide el responsable.
- **Hook de firmware frente a entradas raras (encontrado en A-05):** `proteger_generados.py` sale con traceback si `tool_name` no es texto (`herramienta not in HERRAMIENTAS` con una lista) o si la ruta trae un byte nulo. No deja pasar nada (Claude Code toma la salida 1 como error no bloqueante), pero no cumple su docstring. Arreglo de 2 líneas más pruebas, como en `proteger_kicad.py`.
- **Archivos generados por Bash:** el hook de la capa firmware no ve un `sed -i sdkconfig` ni un `echo > x.pb.c`. Se podría extender el hook de hardware del núcleo para pedir confirmación en esos casos.
- Hook global: bloquear `git push` a la rama principal y el commit de `.env` o llaves.
- Simplificador: revertir solo sus propias ediciones (nunca `git checkout`/`restore`/`stash`) y no tocar drivers, interrupciones ni secciones críticas sin OK.
- Revisor: detectar la rama principal con `git symbolic-ref refs/remotes/origin/HEAD`.
- Volver a pasar el verificador si el simplificador aplicó cambios.
- Comandos `/tarea <ID>`, `/cerrar-tarea` y `/sincronizar`.

## Decisiones

| Fecha | Decisión | Motivo |
|---|---|---|
| 2026-11-25 | Lo irreversible (eFuses, fuses, lock bits, option bytes, RDP, OTP, burn-bootloader) se **bloquea**; grabar o borrar firmware **pide confirmación** | Un "sí" por error en lo irreversible cuesta una placa. Lo decidió el responsable |
| 2026-11-25 | El hook está en Python 3 con la biblioteca estándar y viaja dentro del plugin | Es portable a x86 y ARM64, no agrega dependencias, se prueba con `unittest` y se instala junto con los agentes |
| 2026-11-25 | El hook busca la herramienta en cualquier posición del comando y analiza el texto entre comillas como otro comando, en vez de quitar prefijos uno por uno | El revisor encontró bypasses con bucles, `timeout`, `sudo -u`, `bash -lc`, `docker` y `ssh`. Quitar prefijos caso por caso no tiene fin. A cambio puede pedir confirmación de más, y eso es barato |
| 2026-11-25 | Lo irreversible que solo aparece dentro de un texto (argumento entre comillas que ningún ejecutor como `bash -c`, `ssh`, `eval`, `git bisect`, ni `$(…)`, va a correr) baja a **pedir confirmación** | Así los commits, PR y documentos que mencionan `make fuses` o `espefuse burn_efuse` no se bloquean, y el texto sospechoso igual pide confirmación |
| 2026-11-25 | `make lock` pide confirmación; `make fuses`, `lockbits` y `burn-*` se bloquean | `lock` también es un objetivo común en proyectos Python (pip-compile, poetry). Criterio mío: el responsable puede pedir que se bloquee |
| 2026-11-25 | `sed … e` y `awk system()` piden confirmación en vez de bloquear | Si se trataran como ejecutores, `sed -i 's/make fuses/…/' doc.md` quedaría bloqueado |
| 2026-11-25 | Si la entrada no es válida, el hook deja pasar el comando (no lo bloquea) | Un error del hook no debe trabar todo el trabajo. La regla escrita en el CLAUDE.md sigue vigente |
| 2026-11-25 | Regla en el CLAUDE.md global: los datos de hardware se toman de una fuente citada, y no hay optimización sin medición | Los proyectos son de electrónica, firmware y optimización |
| 2026-11-25 | Las listas de revisión de cada área van al `CLAUDE.md` del proyecto; las reglas, por `SessionStart` | La documentación confirma que los subagentes cargan `CLAUDE.md`, pero no que reciban el contexto de `SessionStart` |
| 2026-11-25 | La regla "sin medición no hay optimización" sale del CLAUDE.md global y pasa a `plugins/software/reglas.md` en A-04 (antes se había previsto para A-06) | Con el esqueleto de `software` ya existe dónde ponerla |
| 2026-11-25 | `hooks/anunciar.py` es igual en todos los plugins; la copia canónica está en `nucleo` y `validar.py` comprueba que las demás coincidan | Los plugins se instalan aislados y no pueden leer archivos fuera de su carpeta |
| 2026-11-25 | El validador solo acepta plugins con `source` local (`./…`) y versión x.y.z (con sufijo opcional) | Todos los plugins del arnés viven en este repo. Claude Code admite más formas, pero aquí no hacen falta |
| 2026-11-25 | El punto de entrada es un solo comando, `/arnes`, que reemplaza a `/nuevo-proyecto`: muestra las capas, se marcan y se aplican, y prepara el proyecto si hace falta | El responsable quiere elegir capas desde el chat con una lista. Además, el panel `/plugin` no existe en la extensión de VSCode |
| 2026-11-26 | La capa `hardware` pide **confirmación**, sin bloquear, antes de editar con Edit, Write o MultiEdit `.kicad_sch`, `.kicad_pcb`, `.kicad_sym`, `.kicad_mod`, `.kicad_pro`, Gerber (también extensiones Protel), taladro, posiciones (`.pos`) y la carpeta `*-backups/` del proyecto. `.kicad_dru`, `fp-lib-table` y `sym-lib-table` quedan libres | Editar el texto de KiCad puede romper UUIDs o la sincronía esquemático-PCB, pero a veces el responsable lo pide. Las reglas de diseño y las tablas de librerías sí se escriben a mano. Lo aprobó el responsable |
| 2026-11-26 | Los comandos de `kicad-cli` de la capa `hardware` usan solo opciones presentes en KiCad 9.0 y 10.0; `--refill-zones` y `--save-board` se mencionan como exclusivas de la 10 | `kicad-cli` no está instalado aquí; se tomaron de la documentación oficial de las dos versiones |
| 2026-11-26 | La capa `firmware` pide **confirmación**, sin bloquear, antes de editar archivos generados: `sdkconfig`, `.ioc`, `*.pb.c`/`*.pb.h`, `managed_components/`, HAL/CMSIS y carpetas de build. En archivos de CubeMX solo pregunta si la edición sale de los bloques `USER CODE` | Editar a mano un generado se pierde al regenerar, pero a veces es legítimo. Lo aprobó el responsable |
| 2026-11-26 | Las reglas para los agentes de cada capa van en su sección del `CLAUDE.md` del proyecto ("Reglas para los agentes") | Los subagentes leen `CLAUDE.md`, no el contexto de `SessionStart` |
| 2026-11-25 | El plugin del núcleo se llama `arnes`; el menú es `/arnes:capas` y hay atajos `/arnes:firmware`, `/arnes:hardware`, `/arnes:software`, `/arnes:ia` y `/arnes:sistema` | Claude Code antepone el nombre del plugin a sus comandos. Así, al escribir `/arnes` el usuario ve todas las opciones en la lista. Lo pidió el responsable |
| 2026-11-25 | Los atajos activan su capa sin quitar las demás (`arnes.py agregar`); para quitar se usa `/arnes:capas` | Un atajo que reemplazara la selección borraría capas sin avisar |
| 2026-11-25 | `/arnes` no trabaja en la carpeta personal, en `/` ni en el repo del arnés | En la carpeta personal, `.claude/settings.json` es el de usuario (activaría las capas en todos los proyectos) y un `CLAUDE.md` ahí se cargaría en todos los proyectos. Lo encontró el revisor |
| 2026-11-25 | Todo cambio de archivos lo hace `arnes.py` (`aplicar`, `preparar`, `completar`); el modelo no edita a mano | Evita errores como pegar líneas al `.gitignore` sin salto final |
| 2026-11-25 | `/arnes` activa capas escribiendo solo el `.claude/settings.json` del proyecto; `sistema` se anota junto con las cuatro capas | Comprobado con `claude -p`: con el marketplace local, anotar basta; `sistema` solo no carga sin sus dependencias activas |
| 2026-11-25 | La plantilla de CLAUDE.md se llama `CLAUDE.plantilla.md` | Si se llamara `CLAUDE.md`, Claude Code la cargaría como instrucciones al trabajar en el repo del arnés |
| 2026-11-25 | A-04 (`/arnes` y esqueleto de las cinco capas) va antes que A-03 | El responsable quiere poder elegir capas desde ya. El esqueleto hace que `/arnes` tenga algo real que activar |
| 2026-11-25 | `/arnes` hace dos preguntas: primero el modo (sistema, elegir, quitar todo, dejar igual) y luego las capas | El selector de Claude Code admite como máximo 4 opciones por pregunta |
| 2026-11-25 | En A-04 `/arnes` no escribe `extraKnownMarketplaces` | Evita que Claude Code reemplace el marketplace local por un clon de GitHub. En otro computador, `/arnes` instala lo que falte |
| 2026-11-25 | El arnés se divide por áreas: `nucleo` + `firmware`, `hardware`, `software`, `ia`, y `sistema` para el proyecto completo | El responsable quiere poder trabajar con un área sola y, cuando haga falta, con el arnés completo. El nombre `sistema` lo eligió el responsable |
