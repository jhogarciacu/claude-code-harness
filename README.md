# claude-code-harness

Arnés de trabajo propio para Claude Code. Tiene un **núcleo** que se instala una vez y vale para todos los proyectos, y **áreas** que se activan solo en los proyectos que las necesitan.

| Plugin | Estado | Qué trae |
|---|---|---|
| `arnes` (el núcleo) | ✅ 0.5.2 | Comandos `/arnes:capas` y atajos por capa, agentes verificador, simplificador y revisor, protección de hardware al grabar firmware y anuncio "Arnés activo" |
| `firmware` | ✅ 0.2.0 | Reglas y lista de revisión de firmware: datasheet, grabación segura, archivos generados, código sensible y verificación según la herramienta (ESP-IDF, PlatformIO, Zephyr, CMake/Make). Pide confirmación antes de editar archivos generados (`sdkconfig`, `.ioc`, `*.pb.c`, HAL, build) y, en CubeMX, solo fuera de `USER CODE` |
| `hardware` | ✅ 0.2.0 | Reglas y lista de revisión de hardware: límites eléctricos y huellas con fuente, ERC/DRC y BOM con `kicad-cli`, fabricación y seguridad física. Pide confirmación antes de editar a mano archivos de KiCad (`.kicad_sch`, `.kicad_pcb`, librerías, `.kicad_pro`) y salidas de fabricación |
| `software` | 🟡 esqueleto 0.1.0 (A-06) | Optimización con medición, benchmarks y portabilidad |
| `ia` | 🟡 esqueleto 0.1.0 (A-07) | Seguridad MCP, evals, datasets y costos |
| `sistema` | 🟡 esqueleto 0.1.0 (A-08) | Proyecto completo: activa las cuatro capas y agrega el contrato entre capas |

"Esqueleto" significa que la capa ya se puede activar, se anuncia y trae sus reglas principales; su lista de revisión completa llega en su tarea.

Las reglas generales están en `global/CLAUDE.md`, enlazado a `~/.claude/CLAUDE.md`: español, tareas aprobadas, git por ramas, honestidad al reportar y seguridad. Los agentes leen además el `CLAUDE.md` de cada proyecto, y **las reglas del proyecto mandan** sobre las globales.

## Instalación (una vez por computador)
```bash
git clone git@github.com:jhogarciacu/claude-code-harness.git ~/Escritorio/proyectos/claude-arnes
~/Escritorio/proyectos/claude-arnes/instalar.sh      # enlaza el CLAUDE.md global (respalda el que exista)
curl -fsSL https://claude.ai/install.sh | bash        # Claude Code para terminal, si no está
claude plugin marketplace add ~/Escritorio/proyectos/claude-arnes
claude plugin install arnes@claude-code-harness
claude plugin list                                    # arnes@claude-code-harness debe salir ✔ enabled
```
El núcleo queda activo en **todos** los proyectos, tanto en la terminal como en VSCode. Los comandos `claude plugin …` se escriben en bash: la extensión de VSCode no tiene el panel `/plugin`.

## Elegir las capas de un proyecto: `/arnes:…`
Abre la carpeta del proyecto con Claude Code (`code .` o `claude`), **acepta que confías en ella** y escribe `/arnes` en el chat. Aparecen estos comandos:

| Comando | Qué hace |
|---|---|
| `/arnes:capas` | **Menú.** Muestra las capas activas y pregunta qué quieres: proyecto completo, elegir capas (marcas varias), quitarlas todas o dejarlo como está |
| `/arnes:firmware` | Activa la capa firmware, sin quitar las demás |
| `/arnes:hardware` | Activa la capa hardware |
| `/arnes:software` | Activa la capa software |
| `/arnes:ia` | Activa la capa ia |
| `/arnes:sistema` | Activa el proyecto completo: las cinco capas |

- Para **quitar** capas, usa `/arnes:capas`. También acepta todo de una vez: `/arnes:capas firmware software` o `/arnes:capas ninguna`.
- Si faltan `CLAUDE.md`, `Docs/` o `.gitignore`, cualquiera de los comandos te ofrece crearlos desde las plantillas. **Nunca sobrescribe**: de lo que ya existe, te propone lo que falta y espera tu OK.
- **Abre una conversación nueva** para que las capas carguen y pregunta "¿qué arnés está activo?".
- No trabajan en tu carpeta personal, en `/` ni en el repo del arnés, porque ahí un cambio afectaría a todos los proyectos.
- *Probado en la terminal (`claude -p`) y en VSCode, incluido el selector de `/arnes:capas`.*

Las capas quedan anotadas en el `.claude/settings.json` del proyecto, que se versiona con él. Con el marketplace agregado desde la carpeta local, anotarlas basta para que carguen. Para cambiarlas o quitarlas, usa `/arnes:capas`.

## Uso de los agentes
Pídelos en lenguaje natural o con `@`:
- "usa el **verificador** antes de cerrar la tarea"
- "pásale el **simplificador** a la rama" (o "...y aplica los cambios")
- "que el **revisor** revise la rama antes del PR"

Orden recomendado al cerrar una tarea: **verificador → simplificador → revisor**.

## Hook de protección de hardware
Viene con el núcleo (plugin `arnes`), así que protege en **todos** los proyectos (decisión D-2); no hay que configurar nada. Requiere `python3` (solo biblioteca estándar).

| Decisión | Ejemplos |
|---|---|
| **Bloquea** (lo ejecutas tú a mano) | `espefuse burn_*`, `idf.py efuse-burn*`, `avrdude` escribiendo fuses o lock (incluye UPDI: `syscfg0`, `bodcfg`…, y `-T "write lfuse…"`), `STM32_Programmer_CLI -ob/-optionbytes RDP=…`, `-lockRDP1/2`, `-otp write`, `-ssp/-sfi`, `st-flash --area=option\|otp\|optcr`, `openocd … lock`/`option_write`/`options_write`, `nrfjprog --rbp`, `pio run -t fuses\|bootloader`, `picotool otp set`, `arduino-cli burn-bootloader`, `bossac -s/-l`, `stm32flash -j`, `flashrom --wp-*`, `dfu-programmer setsecure`, `minipro -c config -w`, `pymcuprog write -m fuses`, `blhost efuse-program-once`, `commander device lock`, `fastboot … lock`, `make/cmake fuses\|lockbits\|burn-fuses\|burn-lock`, y `git bisect run`/`rebase -x`/`submodule foreach` que lancen cualquiera de los anteriores |
| **Pide confirmación** | `idf.py flash`, `esptool write_flash`, `espflash flash`, `pio run -t upload`, `pio test` en una placa, `west flash`, `st-flash write`, `STM32_Programmer_CLI -w/-e/-rdu`, `openocd … program`/`program_esp`/`unlock`, `pyocd flash`, `probe-rs download`, `cargo flash/embed`, `nrfjprog --program/--eraseuicr`, `nrfutil dfu`, `avrdude -U flash:w`, `dfu-util -D`, `picotool load`, `flashrom -w`, J-Link, J-Flash, openFPGALoader, iceprog, ipecmd, pk2cmd, fastboot, bmaptool, `make/ninja/cmake flash\|upload\|program\|erase\|lock`, copiar `.uf2/.bin/.hex` a `/media/…`, `dd of=/dev/…` o `cat img > /dev/sdX`, `mkfs`/`wipefs` sobre `/dev/…`. También lo irreversible cuando solo aparece **dentro de un texto** que nadie ejecuta de forma evidente (`sed … e`, `awk system()`, `curl -d '…'`) |

**Cómo detecta:**
- Busca la herramienta en **cualquier posición** del comando. Por eso no importan los prefijos ni la forma de lanzarla: `sudo -u x`, `timeout 30`, `nice -n 10`, `xargs`, `docker run`, `ssh host`, bucles `for/while/if`, `python3 ruta/espefuse.py`, `python -m`, `pio pkg exec --`.
- Analiza el texto entre comillas como otro comando: `bash -lc "…"`, `ssh host "…"`, `eval "…"`, `"$(…)"`, comillas invertidas.
- Ignora los programas que solo muestran texto (`echo`, `grep`, `gh`, y `git` con subcomandos como `commit`, `log` o `push` sin `-c`), salvo lo que vaya dentro de `$(…)` o de comillas invertidas fuera de comillas simples, igual que hace bash.
- Descarta el cuerpo de los heredocs (`<<'EOF' … EOF`), salvo que los reciba una shell (`bash <<EOF`, `ssh host <<EOF`).
- Así, los commits y PR que **mencionan** estos comandos no se bloquean: `git commit -m "$(cat <<'EOF' … make fuses … EOF)"`, `git commit -m '… `espefuse burn_efuse` …'`, `gh pr create --body '…'`.

**Límites:**
- Analiza el texto del comando. Un script propio (`./grabar.sh`), un `Makefile` con un nombre de objetivo raro o un programa que llame a estas herramientas por dentro **no se detecta**. Por eso la regla también está escrita en el CLAUDE.md global.
- `cargo run` con un runner de `probe-rs` o `espflash` en `.cargo/config.toml` graba la placa y **no se detecta**.
- Puede pedir confirmación de más: con `make flash_test` o `make lock` (en Python también es un objetivo común), con un `python -c` o `curl -d` cuyo texto incluya "make fuses", o con más de 4 niveles de comandos anidados.

Código y pruebas: `plugins/arnes/hooks/`.

## Estructura y pruebas
```
.claude-plugin/marketplace.json   # lista los plugins del arnés
plugins/<plugin>/                 # cada plugin: .claude-plugin/plugin.json, agents/, hooks/, reglas.md
global/CLAUDE.md                  # reglas generales (enlazado a ~/.claude/CLAUDE.md)
herramientas/validar.py           # valida marketplace, manifiestos, hooks y copias compartidas
pruebas.sh                        # corre todas las verificaciones
Docs/plan.md                      # tareas, verificación y decisiones
```
Antes de cada commit: `./pruebas.sh`

## Actualizar
- El CLAUDE.md global es un enlace: basta con `git pull` en este repo.
- Los plugins: `git pull` y después, en bash, `claude plugin update <plugin>@claude-code-harness` (por ejemplo `arnes`). Abre una conversación nueva para que cargue. Sube la `version` del `plugin.json` del plugin que cambie.
- **Cuidado con las ramas:** el marketplace se lee de esta carpeta, así que los plugins cargan desde la rama que tengas activa.

## Plan
Las tareas y decisiones del arnés están en [Docs/plan.md](Docs/plan.md).
