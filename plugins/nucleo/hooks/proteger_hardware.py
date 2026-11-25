#!/usr/bin/env python3
"""Hook PreToolUse del arnés: protege el hardware de comandos que graban o dañan.

Lee del stdin el JSON que envía Claude Code antes de ejecutar una herramienta
`Bash` y decide:

- "deny": acciones irreversibles (eFuses, fuses, lock bits, option bytes,
  protección de lectura, OTP). Se bloquean siempre; las ejecuta el responsable
  a mano.
- "ask": grabar o borrar firmware o memorias. Claude Code pide confirmación.
- sin salida: el comando sigue el flujo normal de permisos.

Cómo analiza: separa el comando en segmentos (`;`, `&&`, `|`, `(`...) y busca
una herramienta conocida en **cualquier posición** del segmento, no solo al
inicio. Así no importan los prefijos (`sudo -u x`, `timeout 30`, `nice -n 10`,
`docker run img`, `ssh host`, `then`, `do`, `{`, `python3 ruta/espefuse.py`).
Cada texto entre comillas que tenga espacios se analiza como otro comando
(`bash -lc "..."`, `ssh host "..."`, `eval "..."`). Los programas que solo
muestran texto (`echo`, `grep`, `git`...) se ignoran, salvo lo que tengan
dentro de `$(...)` o comillas invertidas.

Límite conocido: analiza el texto del comando. Un script propio que llame a
estas herramientas por dentro (por ejemplo `./grabar.sh`) no se detecta; por eso
la regla también está escrita en el CLAUDE.md global.

Solo usa la biblioteca estándar (portable a Linux x86 y ARM64).
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys

DENY = "deny"
ASK = "ask"
_GRAVEDAD = {None: 0, ASK: 1, DENY: 2}
_NADA = (None, None)  # (decisión, motivo) cuando no hay nada que decir
_PROFUNDIDAD_MAX = 4

# Caracteres que separan comandos. shlex junta los seguidos (`;(`, `&&(`), así
# que cualquier token formado solo por ellos cuenta como separador.
_PUNTUACION = "();<>|&\n"
_CONTROL = set(";&|()\n")

# Programas que solo muestran o buscan texto: sus argumentos no se ejecutan.
# (sed, awk, less y man NO están: pueden ejecutar comandos.)
_SOLO_TEXTO = {
    "echo", "printf", "grep", "egrep", "fgrep", "rg", "ag", "gh", "more",
    "head", "tail", "which", "type", "whereis", "ls", "wc", "diff",
}
# git solo cuenta como texto con estos subcomandos y sin `-c` (bisect run,
# rebase -x, submodule foreach y los alias sí ejecutan).
_GIT_SEGUROS = {
    "commit", "log", "tag", "show", "status", "diff", "add", "push", "pull", "fetch", "switch",
    "checkout", "branch", "merge", "stash", "notes", "blame", "grep", "restore", "rm", "mv",
    "init", "clone", "remote", "config", "reset", "revert", "cherry-pick", "am", "apply",
}
# Programas que ejecutan el texto que reciben como argumento.
# git llega aquí solo con subcomandos que ejecutan (bisect run, rebase -x, submodule
# foreach, alias con -c). sed `e` y awk `system()` quedan en ASK a propósito: si
# ejecutaran, un `sed -i 's/make fuses/.../' doc.md` quedaría bloqueado.
_EJECUTORES = {"sh", "bash", "zsh", "dash", "ksh", "fish", "busybox", "ssh", "eval", "su",
               "runuser", "watch", "script", "parallel", "git"}
_SHELL_EN_LINEA = re.compile(r"(^|[\s;&|(/])(ba|z|da|k)?sh\b|\bssh\b|\bfish\b")
_HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")


# ---------------------------------------------------------------------------
# Separar el comando


def _tokens(comando: str) -> list[str]:
    lex = shlex.shlex(comando, posix=True, punctuation_chars=_PUNTUACION)
    lex.whitespace = " \t\r"
    lex.whitespace_split = True
    lex.commenters = ""
    return list(lex)


def _comillas_invertidas(comando: str) -> str:
    """Trata las comillas invertidas como `$(`, salvo dentro de comillas simples (como bash)."""
    salida, simples, dobles = [], False, False
    for c in comando:
        if c == "'" and not dobles:
            simples = not simples
        elif c == '"' and not simples:
            dobles = not dobles
        elif c == "`" and not simples:
            c = " $( "
        salida.append(c)
    return "".join(salida)


def _quitar_heredocs(comando: str) -> str:
    """Quita el cuerpo de los heredocs: es texto, salvo que lo reciba una shell (`bash <<EOF`)."""
    lineas, salida, i = comando.split("\n"), [], 0
    while i < len(lineas):
        linea = lineas[i]
        salida.append(linea)
        i += 1
        for marca in _HEREDOC.finditer(linea):
            fin = marca.group(2)
            cuerpo = []
            while i < len(lineas) and lineas[i].strip() != fin:
                cuerpo.append(lineas[i])
                i += 1
            if i < len(lineas):
                cuerpo.append(lineas[i])  # la línea de cierre
                i += 1
            if _SHELL_EN_LINEA.search(linea[: marca.start()]):
                salida.extend(cuerpo)
            elif cuerpo:
                salida.append(cuerpo[-1])  # conserva el cierre, por ejemplo `EOF\n)"`
    return "\n".join(salida)


def _segmentos(comando: str) -> list[list[str]]:
    comando = _comillas_invertidas(_quitar_heredocs(comando))
    try:
        tokens = _tokens(comando)
    except ValueError:
        # Comillas sin cerrar: se analiza de forma aproximada, sin perder nada.
        tokens = re.split(r"\s+|(?<=[;&|()])|(?=[;&|()])", comando)
    segmentos, actual = [], []
    for token in tokens:
        if token and set(token) <= _CONTROL:
            if actual:
                segmentos.append(actual)
            actual = []
        elif token:
            actual.append(token)
    if actual:
        segmentos.append(actual)
    return segmentos


def _programa(nombre: str) -> str:
    # `alias.x=!espefuse.py`: el programa va después del último `=` o `!`.
    base = os.path.basename(re.split(r"[=!]", nombre)[-1]).lower()
    for sufijo in (".py", ".exe", ".sh"):
        if base.endswith(sufijo):
            base = base[: -len(sufijo)]
    return base


# ---------------------------------------------------------------------------
# Reglas por herramienta. Cada una recibe los argumentos que siguen al programa.


def _hay(args, *opciones: str) -> bool:
    """True si alguna opción aparece, sola o pegada a su valor (`-w`, `-wfile`, `--write=x`)."""
    return any(
        arg == op or arg.startswith(op + "=") or (len(op) == 2 and arg.startswith(op))
        for arg in args
        for op in opciones
    )


def _espefuse(args):
    for arg in args:
        a = arg.replace("-", "_")
        if a.startswith("burn") or a in {
            "write_protect_efuse",
            "read_protect_efuse",
            "set_flash_voltage",
            "execute_scripts",
        }:
            return DENY, f"espefuse `{arg}` quema eFuses (irreversible)"
    return _NADA


def _esptool(args):
    for arg in args:
        if arg.replace("-", "_") in {"write_flash", "erase_flash", "erase_region", "write_mem", "write_flash_status"}:
            return ASK, f"esptool `{arg}` graba o borra la memoria del dispositivo"
    return _NADA


_IDF_PEDIR = {
    "flash", "app-flash", "bootloader-flash", "partition-table-flash", "encrypted-flash",
    "encrypted-app-flash", "erase-flash", "erase-otadata", "dfu-flash", "write-otadata",
}


def _idf(args):
    for arg in args:
        a = arg.replace("_", "-")
        if a.startswith("efuse-burn") or a in {"efuse-read-protect", "efuse-write-protect"}:
            return DENY, f"idf.py `{arg}` quema eFuses (irreversible)"
    for arg in args:
        if arg.replace("_", "-") in _IDF_PEDIR:
            return ASK, f"idf.py `{arg}` graba o borra el dispositivo"
    return _NADA


def _espflash(args):
    for arg in args:
        if arg.replace("_", "-") in {"flash", "erase-flash", "erase-region", "erase-parts", "write-bin"}:
            return ASK, f"espflash `{arg}` graba o borra el dispositivo"
    return _NADA


# Fuses clásicos (lfuse, hfuse, efuse, fuseN, lock) y los de UPDI (megaAVR-0, tinyAVR, AVR-Dx).
_AVR_FUSIBLES = re.compile(
    r"^((l|h|e)?fuses?\d*|lock(bits)?|syscfg\d|bodcfg|bootend|bootsize|codesize|osccfg|wdtcfg|tcd\dcfg|append|pdicfg)$"
)


def _avrdude(args):
    operaciones = []
    for i, arg in enumerate(args):
        if arg == "-U" and i + 1 < len(args):
            operaciones.append(args[i + 1])
        elif arg.startswith("-U") and len(arg) > 2:
            operaciones.append(arg[2:])
    for i, arg in enumerate(args):
        # Modo terminal no interactivo (avrdude 7.1+): -T "write lfuse 0 0xff"
        if arg == "-T" and i + 1 < len(args):
            pedir = False
            for orden in args[i + 1].lower().split(";"):
                palabras = orden.split()
                if not palabras:
                    continue
                es_escritura = "write".startswith(palabras[0])
                if es_escritura and len(palabras) > 1 and _AVR_FUSIBLES.match(palabras[1]):
                    return DENY, f"avrdude `-T {args[i + 1]}` escribe fuses o lock bits"
                pedir = pedir or es_escritura or "erase".startswith(palabras[0])
            if pedir:
                return ASK, "avrdude escribe o borra la memoria del microcontrolador"
    # `-U archivo.hex` sin `memoria:op` escribe la flash.
    escrituras = [op for op in operaciones if op.split(":")[1:2] == ["w"] or ":" not in op]
    for op in escrituras:
        if _AVR_FUSIBLES.match(op.split(":")[0].lower()):
            return DENY, f"avrdude `-U {op}` escribe fuses o lock bits"
    if escrituras:
        return ASK, "avrdude escribe la memoria del microcontrolador"
    if _hay(args, "-e", "-t"):
        return ASK, "avrdude borra el chip o abre el modo terminal"
    return _NADA


_STM32_NEGAR = {"-lockrdp1", "-lockrdp2", "-ssp", "-sfi", "-sfix", "-smi", "-sfu"}
_STM32_PEDIR = {"-w", "-w8", "-w16", "-w32", "-w64", "--write", "-d", "--download", "-e", "--erase",
                "-rdu", "-setdefaultob", "-hardrst"}


def _stm32_programmer(args):
    bajos = [a.lower() for a in args]
    for i, arg in enumerate(bajos):
        if arg in _STM32_NEGAR:
            return DENY, f"STM32_Programmer_CLI `{args[i]}` fija protección de lectura o instalación segura"
        if arg == "-otp" and any(v in {"write", "program", "lock"} for v in bajos[i + 1 : i + 3]):
            return DENY, "STM32_Programmer_CLI escribe OTP (irreversible)"
        if arg in {"-ob", "--optionbytes", "-optionbytes"}:
            valores = []
            for siguiente in bajos[i + 1 :]:
                if siguiente.startswith("-"):
                    break
                valores.append(siguiente)
            if any("=" in v for v in valores):
                return DENY, "STM32_Programmer_CLI cambia option bytes (RDP/WRP pueden ser irreversibles)"
    for arg in bajos:
        if arg in _STM32_PEDIR or arg.startswith(("--write=", "--download=", "--erase=")):
            return ASK, "STM32_Programmer_CLI graba o borra el microcontrolador"
    return _NADA


_ST_AREAS_NEGAR = re.compile(r"^(option|otp|optcr\d?)$")


def _st_flash(args):
    for i, arg in enumerate(args):
        area = arg.split("=", 1)[1] if arg.startswith("--area=") else None
        if arg == "--area" and i + 1 < len(args):
            area = args[i + 1]
        if area and _ST_AREAS_NEGAR.match(area.lower()) and "write" in args:
            return DENY, f"st-flash escribe el área `{area}` (option bytes u OTP)"
    if any(a in {"write", "erase"} for a in args):
        return ASK, "st-flash graba o borra el microcontrolador"
    return _NADA


def _openocd(args):
    # Solo los comandos (-c y texto suelto), no los nombres de archivos de configuración.
    comandos = [a for i, a in enumerate(args) if not (i > 0 and args[i - 1] in {"-f", "-s", "--file", "--search"})]
    texto = " ".join(comandos).lower()
    if re.search(
        r"\b\w+x lock\b|\boptions?_write\b|\brdp\b|\bflash protect\b(?![^;]*\boff\b)|\botp\b[^;]*\b(write|enable)\b",
        texto,
    ):
        return DENY, "openocd bloquea, protege o cambia option bytes/OTP"
    if re.search(r"\bprogram(_esp\w*)?\b|\bflash (write|erase)|\bmass_erase\b|\bflash_write\b|\bunlock\b", texto):
        return ASK, "openocd graba o borra la flash"
    return _NADA


def _subcomando(nombre, pedir: set[str], negar: set[str] = frozenset()):
    def regla(args):
        for arg in args:
            if arg in negar:
                return DENY, f"{nombre} `{arg}` es irreversible"
        for arg in args:
            if arg in pedir:
                return ASK, f"{nombre} `{arg}` graba o borra el dispositivo"
        return _NADA

    return regla


def _nrfjprog(args):
    if _hay(args, "--rbp"):
        return DENY, "nrfjprog `--rbp` activa la protección de lectura"
    if _hay(args, "--program", "--eraseall", "--erasepage", "--eraseuicr", "--recover", "--memwr",
            "--sectorerase", "--chiperase", "--qspieraseall", "--sectoranduicrerase"):
        return ASK, "nrfjprog graba o borra el dispositivo"
    return _NADA


def _nrfutil(args):
    if "protection-set" in args:
        return DENY, "nrfutil `protection-set` activa la protección del dispositivo"
    if any(a in {"program", "erase", "recover", "fw-update", "dfu"} for a in args):
        return ASK, "nrfutil graba o borra el dispositivo"
    return _NADA


_PIO_NEGAR = {"fuses", "bootloader"}
_PIO_PEDIR = {"upload", "uploadfs", "uploadfsota", "program", "erase", "uploadeep", "upload_eeprom"}


def _platformio(args):
    objetivos = []
    for i, arg in enumerate(args):
        if arg in {"-t", "--target"} and i + 1 < len(args):
            objetivos.append(args[i + 1])
        elif arg.startswith("--target="):
            objetivos.append(arg.split("=", 1)[1])
        elif arg.startswith("-t") and len(arg) > 2 and not arg.startswith("--"):
            objetivos.append(arg[2:])
    for obj in objetivos:
        if obj in _PIO_NEGAR:
            return DENY, f"platformio `-t {obj}` escribe fuses o bootloader"
    for obj in objetivos:
        if obj in _PIO_PEDIR:
            return ASK, f"platformio `-t {obj}` graba o borra el dispositivo"
    # `pio test` sube el firmware a la placa salvo en entornos nativos.
    if args[:1] == ["test"] and "--without-uploading" not in args:
        entornos = [args[i + 1] for i, a in enumerate(args[:-1]) if a in {"-e", "--environment"}]
        if not entornos or not all("native" in e for e in entornos):
            return ASK, "platformio `test` sube el firmware a la placa"
    return _NADA


def _picotool(args):
    if args and args[0] == "otp" and any(a in {"set", "load", "write", "permissions"} for a in args[1:]):
        return DENY, "picotool `otp` escribe memoria OTP (irreversible)"
    if args and args[0] in {"load", "erase"}:
        return ASK, f"picotool `{args[0]}` graba o borra el dispositivo"
    return _NADA


def _arduino_cli(args):
    if "burn-bootloader" in args:
        return DENY, "arduino-cli `burn-bootloader` escribe bootloader y fuses"
    if "upload" in args or (args and args[0] == "compile" and _hay(args, "-u", "--upload")):
        return ASK, "arduino-cli graba el dispositivo"
    return _NADA


def _bossac(args):
    if _hay(args, "-l", "--lock", "-s", "--security"):
        return DENY, "bossac bloquea regiones o activa el bit de seguridad"
    if _hay(args, "-w", "--write", "-e", "--erase"):
        return ASK, "bossac graba o borra el dispositivo"
    return _NADA


def _stm32flash(args):
    if _hay(args, "-j"):
        return DENY, "stm32flash `-j` activa la protección de lectura"
    if _hay(args, "-w", "-o", "-e", "-k", "-u"):
        return ASK, "stm32flash graba, borra o cambia protecciones"
    return _NADA


def _flashrom(args):
    if _hay(args, "--wp-enable", "--wp-range", "--wp-region", "--wp-mode"):
        return DENY, "flashrom cambia la protección de escritura (puede ser permanente)"
    if _hay(args, "-w", "--write", "-E", "--erase"):
        return ASK, "flashrom graba o borra un chip de memoria"
    return _NADA


def _dfu_util(args):
    if _hay(args, "-D", "--download"):
        return ASK, "dfu-util graba el dispositivo"
    return _NADA


def _minipro(args):
    escribe = _hay(args, "-w", "--write")
    for i, arg in enumerate(args[:-1]):
        if arg in {"-c", "--page"} and args[i + 1] == "config" and escribe:
            return DENY, "minipro escribe la configuración (fuses) del chip"
    if escribe or _hay(args, "-E", "--erase"):
        return ASK, "minipro graba o borra un chip"
    return _NADA


def _mspdebug(args):
    if re.search(r"\b(prog|erase|load)\b", " ".join(args)):
        return ASK, "mspdebug graba o borra el microcontrolador"
    return _NADA


def _pymcuprog(args):
    if "write" in args and any(re.match(r"^(fuses?|lockbits?|lock)$", a) for a in args):
        return DENY, "pymcuprog escribe fuses o lock bits"
    if any(a in {"write", "erase"} for a in args):
        return ASK, "pymcuprog graba o borra el microcontrolador"
    return _NADA


def _commander(args):
    if any(a in {"lock", "protect"} for a in args):
        return DENY, "commander bloquea o protege el dispositivo"
    if any(a in {"flash", "masserase", "pageerase", "recover"} for a in args):
        return ASK, "commander graba o borra el dispositivo"
    return _NADA


def _fastboot(args):
    if "lock" in args or "lock_critical" in args:
        return DENY, "fastboot `lock` bloquea el bootloader"
    if any(a in {"flash", "erase", "flashall", "update", "format", "unlock"} for a in args):
        return ASK, "fastboot graba o borra particiones"
    return _NADA


def _siempre_pedir(nombre):
    return lambda args: (ASK, f"{nombre} puede grabar el dispositivo")


# `lock` suelto solo pide confirmación: también es un objetivo común en Python (pip-compile, poetry).
_OBJETIVOS_NEGAR = re.compile(r"^((burn|write|set|program)[-_]?)?(e?fuses?|lockbits)$|^(burn|write|set|program)[-_]?lock$")
_OBJETIVOS_PEDIR = re.compile(r"^(flash|upload|program|erase|lock)([-_].*)?$")


def _build(args):
    # Cualquier argumento puede ser un objetivo (`make flash`, `--target flash`, `--target=flash`).
    objetivos = [a.split("=", 1)[1] if a.startswith("--target=") else a for a in args]
    for obj in objetivos:
        if _OBJETIVOS_NEGAR.match(obj.lower()):
            return DENY, f"el objetivo de compilación `{obj}` escribe fuses o lock bits"
    for obj in objetivos:
        if _OBJETIVOS_PEDIR.match(obj.lower()):
            return ASK, f"el objetivo de compilación `{obj}` graba o borra el dispositivo"
    return _NADA


def _cargo(args):
    resto = [a for a in args if not a.startswith("+")]  # `cargo +nightly flash`
    if resto and resto[0] in {"flash", "embed"}:
        return ASK, f"cargo `{resto[0]}` graba el dispositivo"
    return _NADA


# Unidades que montan los bootloaders UF2 y las sondas tipo ST-Link/micro:bit.
_MONTAJES = re.compile(r"(^|[=\s])(/media/|/run/media/|/mnt/)|RPI-RP2|RP2350|NODE_|MICROBIT|DAPLINK")
_FIRMWARE = re.compile(r"\.(uf2|bin|hex)$", re.IGNORECASE)


_DISCOS = re.compile(r"^/dev/(sd[a-z]|mmcblk|nvme|disk|hd[a-z])")


def _copiar(args):
    if any(_MONTAJES.search(a) for a in args) and any(_FIRMWARE.search(a) for a in args):
        return ASK, "copiar firmware a la unidad del bootloader o de la sonda graba el dispositivo"
    if any(_DISCOS.match(a) for a in args):
        return ASK, "escribe directo sobre un disco o tarjeta SD"
    return _NADA


_DEV_INOFENSIVOS = re.compile(r"^of=/dev/(null|zero|stdout|stderr|fd/)")


def _dd(args):
    if any(a.startswith("of=/dev/") and not _DEV_INOFENSIVOS.match(a) for a in args):
        return ASK, "dd escribe directo sobre un dispositivo de bloques (tarjeta SD, memoria)"
    return _copiar(args)


def _sobre_dispositivo(nombre):
    def regla(args):
        if any(a.startswith("/dev/") for a in args):
            return ASK, f"{nombre} escribe sobre un dispositivo de bloques"
        return _NADA

    return regla


REGLAS = {
    "espefuse": _espefuse,
    "esptool": _esptool,
    "idf": _idf,
    "espflash": _espflash,
    "avrdude": _avrdude,
    "stm32_programmer_cli": _stm32_programmer,
    "st-flash": _st_flash,
    "openocd": _openocd,
    "pyocd": _subcomando("pyocd", {"flash", "load", "erase"}),
    "probe-rs": _subcomando("probe-rs", {"download", "run", "erase", "flash"}),
    "nrfjprog": _nrfjprog,
    "nrfutil": _nrfutil,
    "west": _subcomando("west", {"flash"}),
    "pio": _platformio,
    "platformio": _platformio,
    "dfu-util": _dfu_util,
    "dfu-programmer": _subcomando("dfu-programmer", {"flash", "erase", "configure"}, {"setsecure"}),
    "picotool": _picotool,
    "arduino-cli": _arduino_cli,
    "bossac": _bossac,
    "stm32flash": _stm32flash,
    "flashrom": _flashrom,
    "minipro": _minipro,
    "mspdebug": _mspdebug,
    "pymcuprog": _pymcuprog,
    "blhost": _subcomando(
        "blhost",
        {"write-memory", "flash-erase-all", "flash-erase-region", "flash-erase-all-unsecure",
         "receive-sb-file", "fill-memory"},
        {"efuse-program-once", "flash-program-once", "fuse-program"},
    ),
    "commander": _commander,
    "fastboot": _fastboot,
    "bmaptool": _subcomando("bmaptool", {"copy"}),
    "teensy_loader_cli": _siempre_pedir("teensy_loader_cli"),
    "jlinkexe": _siempre_pedir("JLinkExe"),
    "jlink": _siempre_pedir("JLink"),
    "jflashexe": _siempre_pedir("JFlashExe"),
    "jflash": _siempre_pedir("JFlash"),
    "openfpgaloader": _siempre_pedir("openFPGALoader"),
    "iceprog": _siempre_pedir("iceprog"),
    "ipecmd": _siempre_pedir("ipecmd"),
    "pk2cmd": _siempre_pedir("pk2cmd"),
    "make": _build,
    "ninja": _build,
    "cmake": _build,
    "cargo": _cargo,
    "cp": _copiar,
    "mv": _copiar,
    "rsync": _copiar,
    "cat": _copiar,
    "dd": _dd,
    "wipefs": _sobre_dispositivo("wipefs"),
    "mkfs": _sobre_dispositivo("mkfs"),
}


# ---------------------------------------------------------------------------
# Decisión


def _peor(a, b):
    return b if _GRAVEDAD[b[0]] > _GRAVEDAD[a[0]] else a


def _regla(token: str):
    programa = _programa(token)
    if programa.startswith("mkfs."):
        programa = "mkfs"
    return REGLAS.get(programa)


def _es_solo_texto(segmento: list[str]) -> bool:
    args = [t for t in segmento if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", t)]
    if not args:
        return False
    programa = _programa(args[0])
    if programa == "git":
        sub = next((a for a in args[1:] if not a.startswith("-")), "")
        return "-c" not in args and sub in _GIT_SEGUROS
    return programa in _SOLO_TEXTO


def _texto_interno(token: str, ejecutado: bool, profundidad: int):
    """Analiza el texto de un argumento. Si nadie lo ejecuta, como mucho pide confirmación."""
    resultado = evaluar(token, profundidad + 1)
    if resultado[0] == DENY and not ejecutado:
        return ASK, resultado[1] + " (aparece dentro de un texto)"
    return resultado


def evaluar(comando: str, _profundidad: int = 0) -> tuple[str | None, str | None]:
    """Devuelve (decisión, motivo) para el comando más grave, o (None, None)."""
    peor = _NADA
    if _profundidad > _PROFUNDIDAD_MAX:
        return ASK, "comando con demasiados niveles anidados para analizarlo"
    for segmento in _segmentos(comando):
        solo_texto = _es_solo_texto(segmento)
        ejecutor_antes = False
        for i, token in enumerate(segmento):
            # Texto con espacios: puede ser un comando dentro de otro (`bash -lc "..."`).
            # En los programas de solo texto, únicamente lo que se ejecuta: `$(...)`.
            if (" " in token or "\t" in token or "\n" in token) and (not solo_texto or "$(" in token):
                ejecutado = ejecutor_antes or "$(" in token
                peor = _peor(peor, _texto_interno(token, ejecutado, _profundidad))
            ejecutor_antes = ejecutor_antes or _programa(token) in _EJECUTORES
            if solo_texto:
                continue
            regla = _regla(token)
            if regla:
                peor = _peor(peor, regla(segmento[i + 1 :]))
    return peor


def main() -> int:
    try:
        entrada = json.load(sys.stdin)
    except ValueError as error:  # incluye JSONDecodeError
        print(f"proteger_hardware: entrada no válida ({error}); no se evalúa", file=sys.stderr)
        return 0
    if not isinstance(entrada, dict) or entrada.get("tool_name") != "Bash":
        return 0
    tool_input = entrada.get("tool_input")
    comando = tool_input.get("command") if isinstance(tool_input, dict) else None
    if not isinstance(comando, str):
        return 0
    decision, motivo = evaluar(comando)
    if decision is None:
        return 0
    if decision == DENY:
        motivo = f"Bloqueado por el arnés: {motivo}. Si de verdad hay que hacerlo, lo ejecuta el responsable a mano."
    else:
        motivo = f"El arnés pide confirmación: {motivo}. ¿Está conectado el dispositivo correcto?"
    salida = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": motivo,
        }
    }
    print(json.dumps(salida, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
