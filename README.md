# claude-code-harness

Arnés de trabajo propio para Claude Code, reutilizable en cualquier proyecto:

| Pieza | Dónde | Qué hace |
|---|---|---|
| **CLAUDE.md global** | `global/CLAUDE.md` → enlazado a `~/.claude/CLAUDE.md` | Reglas generales: español, tareas aprobadas, explicar antes de arrancar, git por ramas, honestidad al reportar, seguridad |
| **Agente `revisor`** | `agents/revisor.md` | Revisa el cambio de la rama **sin modificar nada**: errores, seguridad, reglas del CLAUDE.md del proyecto y definición de terminado |
| **Agente `simplificador`** | `agents/simplificador.md` | Simplifica el código cambiado **sin alterar su comportamiento**. Propone por defecto y aplica si se le pide, con las pruebas en verde |
| **Agente `verificador`** | `agents/verificador.md` | Ejecuta pruebas, lint, formato y chequeos del proyecto y reporta qué pasó y qué **no** se pudo verificar |
| **Hook `proteger_hardware`** | `hooks/` | Antes de cada comando de shell: **pide confirmación** si graba o borra firmware y **bloquea** lo irreversible (eFuses, fuses, lock bits, option bytes, RDP, OTP) |

Los agentes son genéricos: leen el `CLAUDE.md` de cada proyecto, y **las reglas del proyecto mandan** sobre las globales.

## Instalación (una vez por computador)
```bash
git clone git@github.com:jhogarciacu/claude-code-harness.git ~/Escritorio/proyectos/claude-arnes
~/Escritorio/proyectos/claude-arnes/instalar.sh      # enlaza el CLAUDE.md global (respalda el que exista)
```
Luego, dentro de Claude Code (terminal o VSCode):
```
/plugin marketplace add ~/Escritorio/proyectos/claude-arnes
/plugin install arnes@claude-code-harness
```
Para instalarlo desde GitHub en vez de la carpeta local: `/plugin marketplace add jhogarciacu/claude-code-harness` (si el repo es privado, requiere acceso).

## Uso
Pedirlo en lenguaje natural o con `@`:
- "usa el **verificador** antes de cerrar la tarea"
- "pásale el **simplificador** a la rama" (o "...y aplica los cambios")
- "que el **revisor** revise la rama antes del PR"

Orden recomendado al cerrar una tarea: **verificador → simplificador → revisor**.

## Hook de protección de hardware
Viene con el plugin; no hay que configurar nada. Requiere `python3` (solo biblioteca estándar).

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
- Analiza el texto del comando. Un script propio (`./grabar.sh`), un `Makefile` con un nombre de objetivo raro o un programa que llame a estas herramientas por dentro **no se detecta**. Por eso la regla también está en el CLAUDE.md global.
- `cargo run` con un runner de `probe-rs` o `espflash` en `.cargo/config.toml` graba la placa y **no se detecta**.
- Puede pedir confirmación de más: con `make flash_test` o `make lock` (en Python también es un objetivo común), con un `python -c` o `curl -d` cuyo texto incluya "make fuses", o con más de 4 niveles de comandos anidados.

Pruebas: `python3 -m unittest discover -s hooks -v`

## Actualizar
- El CLAUDE.md global es un enlace: basta con `git pull` en este repo.
- Los agentes: `git pull` y luego `/plugin marketplace update claude-code-harness`. Subir `version` en `.claude-plugin/plugin.json` en cada cambio.

## Plan
Las tareas y decisiones del arnés están en [Docs/plan.md](Docs/plan.md).

## Próximas piezas (propuestas, sin aprobar)
- Comandos `/tarea <ID>`, `/cerrar-tarea` y `/sincronizar` para el flujo por tareas y ramas.
- `/nuevo-proyecto`: crea la estructura `Docs/` (visión, requisitos, planes, interfaces y decisiones) y una plantilla de CLAUDE.md.
