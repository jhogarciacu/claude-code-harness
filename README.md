# claude-code-harness

Arnés de trabajo propio para Claude Code. Tiene un **núcleo** que se instala una vez y vale para todos los proyectos, y **áreas** que se activan solo en los proyectos que las necesitan.

| Plugin | Estado | Qué trae |
|---|---|---|
| `nucleo` | ✅ disponible | Agentes verificador, simplificador y revisor. Protección de hardware al grabar firmware. Anuncio "Arnés activo" al empezar la sesión |
| `firmware` | ⏳ A-03 | Reglas y lista de revisión de firmware |
| `hardware` | ⏳ A-05 | KiCad: ERC/DRC, BOM y límites eléctricos |
| `software` | ⏳ A-06 | Optimización con medición y benchmarks |
| `ia` | ⏳ A-07 | Seguridad MCP, evals, datasets |
| `sistema` | ⏳ A-08 | Proyecto completo: las cinco áreas y el contrato entre capas |

Las reglas generales están en `global/CLAUDE.md`, enlazado a `~/.claude/CLAUDE.md`: español, tareas aprobadas, git por ramas, honestidad al reportar y seguridad. Los agentes leen además el `CLAUDE.md` de cada proyecto, y **las reglas del proyecto mandan** sobre las globales.

## Instalación (una vez por computador)
```bash
git clone git@github.com:jhogarciacu/claude-code-harness.git ~/Escritorio/proyectos/claude-arnes
~/Escritorio/proyectos/claude-arnes/instalar.sh      # enlaza el CLAUDE.md global (respalda el que exista)
```
Luego, dentro de Claude Code (terminal o VSCode):
```
/plugin marketplace add ~/Escritorio/proyectos/claude-arnes
/plugin install nucleo@claude-code-harness
```
El núcleo queda activo en **todos** los proyectos. Si prefieres instalarlo desde GitHub en vez de la carpeta local: `/plugin marketplace add jhogarciacu/claude-code-harness` (si el repo es privado, necesitas acceso).

## Activar el arnés en un proyecto
1. Crea la carpeta, ábrela con Claude Code y **acepta que confías en ella**. Sin eso, Claude Code ignora el `.claude/settings.json` del proyecto.
2. Activa las áreas que el proyecto necesite. **Solo para este proyecto**, nunca a nivel de usuario. Hay dos formas:
   - **Dentro de Claude Code:** abre `/plugin`, busca el área (por ejemplo `firmware`) en el marketplace `claude-code-harness`, elige **Install** y como alcance **project**.
   - **Desde la terminal**, en la carpeta del proyecto, si tienes el comando `claude`:
     ```bash
     claude plugin install firmware@claude-code-harness --scope project
     ```
   Para el proyecto completo, instala `sistema`: trae las cinco áreas. Desde A-04 bastará con `/nuevo-proyecto firmware` o `/nuevo-proyecto sistema`, que además crea el `CLAUDE.md`, `Docs/` y el `.gitignore` del proyecto.
3. Ejecuta `/reload-plugins`, o abre una sesión nueva.
4. Comprueba. Al empezar la sesión, cada plugin activo anuncia "Arnés activo: <nombre> <versión>". También lo ves con `/plugin`.

Las áreas quedan anotadas en el `.claude/settings.json` del proyecto, que se versiona con él. En otro computador, haz primero la instalación por computador y abre el proyecto. Si un área no aparece en el anuncio ni en `/plugin`, instálala otra vez con alcance **project**: según la documentación, un plugin anotado solo en el proyecto no siempre se carga hasta instalarlo en ese computador.

| Quiero | Cómo |
|---|---|
| Agregar un área | `/plugin` → el área → Install → alcance *project* (o `claude plugin install <área>@claude-code-harness --scope project`) |
| Pasar a proyecto completo | Instalar `sistema` en el proyecto |
| Quitar un área | `/plugin` → deshabilitar, o poner `false` en `enabledPlugins` |
| Saber qué tengo | La línea "Arnés activo" al empezar la sesión, o `/plugin` |

## Uso de los agentes
Pídelos en lenguaje natural o con `@`:
- "usa el **verificador** antes de cerrar la tarea"
- "pásale el **simplificador** a la rama" (o "...y aplica los cambios")
- "que el **revisor** revise la rama antes del PR"

Orden recomendado al cerrar una tarea: **verificador → simplificador → revisor**.

## Hook de protección de hardware
Viene con `nucleo`, así que protege en **todos** los proyectos (decisión D-2); no hay que configurar nada. Requiere `python3` (solo biblioteca estándar).

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

Código y pruebas: `plugins/nucleo/hooks/`.

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
- Los plugins: `git pull`, después `/plugin marketplace update claude-code-harness` y `/reload-plugins`. Sube la `version` del `plugin.json` del plugin que cambie.

## Plan
Las tareas y decisiones del arnés están en [Docs/plan.md](Docs/plan.md).
