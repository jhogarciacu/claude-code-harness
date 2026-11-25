# Plan del arnés

## Tareas

| ID | Tarea | Estado | Verificación |
|---|---|---|---|
| A-01 | Reglas de hardware y optimización en el CLAUDE.md global + hook que protege el hardware al grabar | Hecha, falta probarla en Claude Code | `python3 -m unittest discover -s hooks -v`: 10 pruebas en verde con 66 casos bloqueados, 77 con confirmación, 50 permitidos y 6 entradas inválidas. Incluyen los hallazgos del verificador, del simplificador y de las dos pasadas del revisor: bucles, `timeout`, `sudo -u`, `bash -lc`, `ssh`, `docker`, `git bisect run`, `option_write`, fuses UPDI, `make fuses`, y commits con heredoc o comillas invertidas que no deben bloquearse. Además: prueba de mutación (al quitar el tope de "texto que nadie ejecuta" fallan 8 casos), fuzz de 30 000 entradas sin excepciones y 2 000 segmentos en menos de 0.1 s. **No probado** dentro de Claude Code: el plugin no está instalado en este equipo |
| A-02 | Estructura por áreas y plugin `nucleo` | Hecha, falta probarla en Claude Code | `./pruebas.sh` en verde con 35 pruebas: 18 del validador de estructura y 17 del hook de hardware y el anuncio de sesión, más la sintaxis de scripts. Comprobado que `pruebas.sh` sale con 1 si falla una prueba o si no se ejecuta ninguna. Cierre con verificador, simplificador (en paralelo con el revisor, porque solo propone) y revisor. Corregido lo que encontraron: comando de activación que la documentación no respalda, `reglas.md` que no está en UTF-8, validador frente a entradas mal formadas, plugins sin registrar, dependencias de otro marketplace, rutas con comillas en los hooks, tamaño de `reglas.md`, y `pruebas.sh` con cero pruebas. **No probado** dentro de Claude Code: instalar `nucleo`, ver los 3 agentes en `/agents` y ver la línea "Arnés activo" |
| A-03 | Plugin `firmware` | Pendiente | — |
| A-04 | Skill `/nuevo-proyecto` | Pendiente | — |
| A-05 | Plugin `hardware` | Pendiente | — |
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

| Caso | Qué se activa en el proyecto | Cómo |
|---|---|---|
| Solo firmware | `firmware` (arrastra `nucleo`) | `/nuevo-proyecto firmware`, o `/plugin` → `firmware` → Install → alcance *project* |
| Firmware + app de escritorio | `firmware` + `software` | `/nuevo-proyecto firmware software` |
| Servidor MCP | `ia` | `/nuevo-proyecto ia` |
| Producto completo | `sistema` (arrastra todas) | `/nuevo-proyecto sistema` |

- La activación queda en el `.claude/settings.json` del proyecto (`enabledPlugins`), que se versiona con el proyecto. Al clonarlo en otro computador se activan las mismas áreas.
- A nivel de usuario (en todos los proyectos) solo se instala `nucleo`.
- Las áreas se instalan siempre **por proyecto**, nunca a nivel de usuario.
- Agregar un área después a un proyecto existente es un solo paso: `/plugin` → el área → Install → alcance *project*.

## Cómo activar el arnés en un proyecto

### Una sola vez por computador
1. Clonar el arnés y enlazar el CLAUDE.md global:
   ```bash
   git clone git@github.com:jhogarciacu/claude-code-harness.git ~/Escritorio/proyectos/claude-arnes
   ~/Escritorio/proyectos/claude-arnes/instalar.sh
   ```
2. Dentro de Claude Code (terminal o VSCode), registrar el marketplace e instalar el núcleo para todos los proyectos:
   ```
   /plugin marketplace add ~/Escritorio/proyectos/claude-arnes
   /plugin install nucleo@claude-code-harness
   ```
   Desde aquí, cualquier carpeta tiene el núcleo: reglas generales, los 3 agentes, `/nuevo-proyecto` y la protección de hardware. Las áreas todavía no.

### Cada proyecto nuevo
1. Crear la carpeta y abrirla con Claude Code:
   ```bash
   mkdir ~/Escritorio/proyectos/mi-sensor && cd ~/Escritorio/proyectos/mi-sensor
   git init
   code .        # o `claude` en la terminal
   ```
   Cuando pregunte si confías en la carpeta, responder que sí. Sin eso, Claude Code ignora la configuración del proyecto.
2. Elegir las áreas con `/nuevo-proyecto`:
   ```
   /nuevo-proyecto firmware             ← solo firmware
   /nuevo-proyecto firmware software    ← firmware + app
   /nuevo-proyecto ia                   ← servidor MCP
   /nuevo-proyecto sistema              ← producto completo (las cinco áreas)
   ```
   Pregunta el nombre y una descripción corta del proyecto, y crea estos archivos:
   - `.claude/settings.json`, con las áreas activas y de dónde sale el marketplace.
   - `CLAUDE.md`, con las listas de revisión de cada área y las secciones del proyecto: comandos, definición de terminado y carpetas protegidas.
   - `Docs/`, con visión, requisitos, plan y decisiones.
   - `.gitignore`, con lo propio de cada área.
3. Ejecutar `/reload-plugins`, o abrir una sesión nueva.
4. Comprobar. Al empezar la sesión, cada plugin activo anuncia una línea como `Arnés activo: firmware 0.1.0`. También se puede ver con `/plugin`.

Ejemplo del `.claude/settings.json` que queda en un proyecto de firmware:
```json
{
  "extraKnownMarketplaces": {
    "claude-code-harness": { "source": { "source": "github", "repo": "jhogarciacu/claude-code-harness" } }
  },
  "enabledPlugins": { "firmware@claude-code-harness": true }
}
```
El marketplace se declara por GitHub y no por una ruta local, para que el proyecto funcione igual en otro computador.

### Cambiar las áreas después
| Quiero | Cómo |
|---|---|
| Agregar un área | `/plugin` → el área → Install → alcance *project* (o, en la terminal, `claude plugin install software@claude-code-harness --scope project`) |
| Pasar a proyecto completo | Instalar `sistema` en el proyecto: trae las cinco áreas |
| Quitar un área | `/plugin` → deshabilitar, o poner `false` en `enabledPlugins` |
| Saber qué tengo | Las líneas "Arnés activo" al empezar la sesión, o `/plugin` |

### Proyecto que ya existe
Se usa el mismo `/nuevo-proyecto <áreas>`. **No sobrescribe nada.**
- Si ya hay un `CLAUDE.md`, propone las secciones que le faltan y espera el OK.
- Si ya hay un `.claude/settings.json`, solo agrega las áreas.

### Clonar un proyecto en otro computador
1. Hacer una vez la instalación por computador.
2. Clonar el proyecto, abrirlo y confiar en la carpeta.
3. Si un área no aparece en el anuncio ni en `/plugin`, instalarla en ese computador: `/plugin` → el área → Install → alcance *project*. Según la documentación oficial, un plugin activado solo en el `.claude/settings.json` del proyecto **no se carga hasta instalarlo en el computador**. Lo que sí hace Claude Code solo, después de confiar en la carpeta, es clonar el marketplace declarado. En A-04, `/nuevo-proyecto` dirá exactamente qué falta.

## Qué trae cada plugin

| Plugin | Depende de | Contenido |
|---|---|---|
| `nucleo` | — | Agentes verificador, simplificador y revisor. Skill `/nuevo-proyecto`. Hook de protección de hardware (ver decisión D-2) |
| `firmware` | `nucleo` | Reglas: no grabar ni tocar fuses sin OK, archivos generados de CubeMX, `sdkconfig` y Kconfig. Lista de revisión: `volatile`, ISR, pila, watchdog, endianness, timeouts de buses y estado seguro. Verificación: warnings como error, análisis estático y presupuesto de flash/RAM. El simplificador no toca drivers ni ISR sin OK |
| `hardware` | `nucleo` | Reglas: ERC/DRC con `kicad-cli`, no editar `.kicad_*` a mano salvo que se pida, BOM con fuentes y límites eléctricos tomados del datasheet. Lista de revisión de esquemático y PCB |
| `software` | `nucleo` | Reglas: sin medición no hay optimización (antes y después, mismas condiciones, números) y benchmarks reproducibles. Lista de revisión: concurrencia, memoria, complejidad y portabilidad x86/ARM64 |
| `ia` | `nucleo` | Reglas: seguridad MCP (prompt injection, permisos mínimos de herramientas, secretos), evals aparte de las pruebas con mocks, no versionar pesos ni datasets, costo de las llamadas |
| `sistema` | las cinco | Solo lo que une las capas: el protocolo entre capas tiene una única fuente (esquema) y se versiona; cambiar un lado obliga a cambiar el otro en la misma tarea; matriz de compatibilidad de versiones; pruebas de integración y HIL; trazabilidad de requisitos entre capas |

`sistema` **no copia** las reglas de las áreas: las activa con `dependencies`. Así cada regla vive en un solo lugar.

## Cómo llegan las reglas a Claude
Según la documentación oficial de plugins, el `CLAUDE.md` que está dentro de un plugin no se carga.

- **Reglas que deben estar siempre activas:** cada área tiene un `reglas.md`, y el hook `SessionStart` (`hooks/anunciar.py`, el mismo en todos los plugins) lo inyecta al empezar la sesión y después de cada compactación. Solo se carga si el área está activa en el proyecto.
- **Listas de revisión para los agentes:** `/nuevo-proyecto` las copia al `CLAUDE.md` del proyecto.
- **Confirmado en la documentación (A-02):** los subagentes cargan toda la jerarquía de `CLAUDE.md` (usuario y proyecto). No está documentado que reciban el contexto del `SessionStart`. Por eso las listas de revisión **van al `CLAUDE.md` del proyecto**, y el plugin no las inyecta.

## Estructura del repo

```
.claude-plugin/marketplace.json     # lista los 6 plugins
plugins/
  nucleo/     .claude-plugin/plugin.json · agents/ · skills/nuevo-proyecto/ · hooks/ (protección de hardware)
  firmware/   .claude-plugin/plugin.json · reglas.md · revision.md · hooks/hooks.json (SessionStart)
  hardware/   ...igual que firmware
  software/   ...
  ia/         ...
  sistema/    .claude-plugin/plugin.json (dependencies: las cinco) · reglas.md · revision.md · hooks/
global/CLAUDE.md                    # solo reglas generales (sale la sección de hardware)
plantillas/                         # CLAUDE.md, .gitignore y Docs/ que usa /nuevo-proyecto
pruebas.sh                          # corre las pruebas de todos los plugins
```

## Tareas, en orden

| ID | Qué | Verificación |
|---|---|---|
| A-02 | Pasar a `plugins/`. Convertir `arnes` en `nucleo`. Listar los plugins en el marketplace. Sacar la sección de hardware del CLAUDE.md global y dejar reglas generales: datos técnicos con fuente citada y nada irreversible sin OK. Agregar `pruebas.sh` y `herramientas/validar.py`. Anuncio "Arnés activo" con `SessionStart`. Consultar la documentación para saber si los subagentes ven el contexto de `SessionStart` | Pruebas del hook en verde desde su nueva ubicación. JSON válidos. Prueba manual del responsable: instalar `nucleo` y ver los 3 agentes en `/agents` |
| A-03 | Plugin `firmware`: `reglas.md`, `revision.md` y `SessionStart`, con la línea "Arnés activo: …" | Prueba del `SessionStart` (imprime las reglas). En un proyecto de prueba con `firmware` activo, las reglas aparecen; en uno sin `firmware`, no |
| A-04 | Skill `/nuevo-proyecto <áreas>`: escribe `.claude/settings.json` con `enabledPlugins` y `extraKnownMarketplaces`, `CLAUDE.md` con las listas de revisión y las secciones del proyecto (comandos, definición de terminado, carpetas protegidas), `Docs/` (visión, requisitos, plan, decisiones) y el `.gitignore` de cada área | Pruebas del generador con una sola área, con varias y con `sistema`. No sobrescribe archivos que ya existen |
| A-05 | Plugin `hardware` | Igual que A-03 |
| A-06 | Plugin `software` | Igual que A-03 |
| A-07 | Plugin `ia` | Igual que A-03 |
| A-08 | Plugin `sistema` con `dependencies` | Activar `sistema` en un proyecto de prueba activa las cinco áreas y sus reglas |

Hago A-04 justo después de firmware para que puedas empezar a usar proyectos de un área cuanto antes.

## Decisiones propuestas (las confirmas al aprobar)
- **D-1. Un solo repo y un solo marketplace, con un plugin por área.** Así hay una sola versión, una sola instalación y pruebas compartidas.
- **D-2. El hook de protección de hardware se queda en `nucleo`, no en `firmware`.** Solo actúa cuando aparece una herramienta de grabación, así que en un proyecto de software no molesta. Si estuviera en `firmware`, dejaría de proteger justo en el proyecto donde alguien graba una placa "de paso". El área `firmware` aporta las reglas y la lista de revisión.
- **D-3. `sistema` arrastra las áreas con `dependencies`, sin copiarlas.**
- **D-4. Las áreas se instalan siempre por proyecto. A nivel de usuario va solo `nucleo`.**

## Riesgos
- **Cambio de nombre.** El plugin `arnes` pasa a llamarse `nucleo`. Hay que desinstalar `arnes` e instalar `nucleo`. Como `arnes` nunca se llegó a instalar, hoy esto no cuesta nada.
- **Activar no es instalar.** `enabledPlugins` no instala nada. En cada computador hay que agregar el marketplace una vez. Además, Claude Code solo respeta el `.claude/settings.json` de un proyecto después de aceptar el diálogo de confianza de la carpeta.
- **Prueba real pendiente.** `claude` no está en el PATH de esta terminal, así que la prueba dentro de Claude Code la haces tú en cada tarea. Te dejo los pasos exactos.
- **Listas copiadas.** Las listas de revisión se copian al proyecto (ver arriba). Si después cambian en el arnés, hará falta un comando para sincronizarlas (queda como propuesta).
- **Fuente del marketplace (A-04, posible).** En este computador el marketplace se agregó desde la carpeta local. Si el `extraKnownMarketplaces` que escribe `/nuevo-proyecto` lo declara desde GitHub con el mismo nombre, la documentación dice que Claude Code "lo vuelve a traer desde la nueva fuente", y podría reemplazar el marketplace local por un clon. Hay que probarlo en A-04 antes de elegir qué declarar.
- **`/plugin install … --scope project` dentro de la sesión.** La documentación no respalda la bandera `--scope` ahí. Por eso el README usa el panel `/plugin` o la CLI `claude plugin install`.
- **`systemMessage` en `SessionStart`.** La documentación dice que `systemMessage` se muestra al usuario, pero no confirma que funcione en `SessionStart`. Si no aparece, la línea igual llega a Claude por `additionalContext`, y basta con preguntarle qué arnés está activo.

## Propuestas (sin aprobar)
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
| 2026-11-25 | La regla "sin medición no hay optimización" se queda en el CLAUDE.md global hasta que exista el área `software` (A-06) | Para no dejar un hueco mientras se construyen las áreas |
| 2026-11-25 | `hooks/anunciar.py` es igual en todos los plugins; la copia canónica está en `nucleo` y `validar.py` comprueba que las demás coincidan | Los plugins se instalan aislados y no pueden leer archivos fuera de su carpeta |
| 2026-11-25 | El validador solo acepta plugins con `source` local (`./…`) y versión x.y.z (con sufijo opcional) | Todos los plugins del arnés viven en este repo. Claude Code admite más formas, pero aquí no hacen falta |
| 2026-11-25 | El arnés se divide por áreas: `nucleo` + `firmware`, `hardware`, `software`, `ia`, y `sistema` para el proyecto completo | El responsable quiere poder trabajar con un área sola y, cuando haga falta, con el arnés completo. El nombre `sistema` lo eligió el responsable |
