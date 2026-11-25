# Plan del arnés

## Tareas

| ID | Tarea | Estado | Verificación |
|---|---|---|---|
| A-01 | Reglas de hardware y optimización en el CLAUDE.md global + hook que protege el hardware al grabar | Hecha, falta probarla en Claude Code | `python3 -m unittest discover -s hooks -v`: 10 pruebas en verde con 66 casos bloqueados, 77 con confirmación, 50 permitidos y 6 entradas inválidas. Incluyen los hallazgos del verificador, del simplificador y de las dos pasadas del revisor: bucles, `timeout`, `sudo -u`, `bash -lc`, `ssh`, `docker`, `git bisect run`, `option_write`, fuses UPDI, `make fuses`, y commits con heredoc o comillas invertidas que no deben bloquearse. Además: prueba de mutación (al quitar el tope de "texto que nadie ejecuta" fallan 8 casos), fuzz de 30 000 entradas sin excepciones y 2 000 segmentos en menos de 0.1 s. **No probado** dentro de Claude Code: el plugin no está instalado en este equipo |

## Propuestas (sin aprobar)
- Plantillas por perfil (`firmware`, `hardware`, `software`, `ia-mcp`) con `/nuevo-proyecto`: CLAUDE.md, `settings.json`, `.gitignore` y la lista de revisión del dominio.
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
