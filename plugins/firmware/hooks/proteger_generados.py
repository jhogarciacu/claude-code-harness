#!/usr/bin/env python3
"""Hook PreToolUse de la capa firmware: pide confirmación antes de editar archivos generados.

Un archivo generado se pierde al regenerar: lo correcto es cambiar su fuente.
Este hook no bloquea (a veces editar `sdkconfig` a mano es legítimo); pide
confirmación con el motivo y la fuente que habría que cambiar.

Archivos de STM32CubeMX (los que tienen bloques `USER CODE BEGIN … END`): la
edición se simula en memoria (respetando `replace_all` y el orden de MultiEdit)
y se compara todo lo que queda **fuera** de los bloques antes y después. Si solo
cambia el contenido de los bloques, no pregunta.

Cubre Edit, Write, MultiEdit y NotebookEdit. Límite conocido: un `sed -i` o un
`echo >` por Bash no pasan por aquí.

Si la entrada no es válida, no dice nada y sale con 0: un error del hook no
debe trabar el trabajo. Solo usa la biblioteca estándar.
"""

from __future__ import annotations

import json
import os
import re
import sys

HERRAMIENTAS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
_HAL = re.compile(r"^(STM32\w*_HAL_Driver|CMSIS)$", re.IGNORECASE)
_BUILD = re.compile(r"^(build|\.pio|cmake-build-.*|build[-_].*)$")
_MARCA = re.compile(r"USER CODE (BEGIN|END)\b[^\n]*")


def _relativa(ruta: str, base: str | None) -> list[str]:
    """Partes de la ruta real, relativas al proyecto si está dentro de él."""
    real = os.path.realpath(ruta)
    if base:
        base = os.path.realpath(base)
        if real == base or real.startswith(base + os.sep):
            real = os.path.relpath(real, base)
    return [p for p in real.split(os.sep) if p]


def motivo_por_ruta(ruta: str, base: str | None = None) -> str | None:
    """Motivo para pedir confirmación según la ruta, o None."""
    partes = _relativa(ruta, base)
    nombre = partes[-1] if partes else ""
    carpetas = partes[:-1]
    if nombre == "sdkconfig":
        return "`sdkconfig` lo genera menuconfig; cámbialo con `idf.py menuconfig` o en `sdkconfig.defaults`"
    if nombre == "dependencies.lock":
        return "`dependencies.lock` lo escribe el gestor de componentes de ESP-IDF"
    if nombre.endswith(".ioc"):
        return f"`{nombre}` es el proyecto de STM32CubeMX; se edita con CubeMX, que regenera el código"
    if nombre.endswith((".pb.c", ".pb.h", ".pb-c.c", ".pb-c.h", ".pb.cc")):
        return f"`{nombre}` lo genera protobuf/nanopb; cambia el `.proto` o el `.options` y regenera"
    if re.match(r"^startup_stm32\w*\.s$", nombre, re.IGNORECASE) or re.search(r"_(FLASH|RAM)\.ld$", nombre):
        return f"`{nombre}` lo genera STM32CubeMX/CubeIDE (arranque o linker script); cambiarlo requiere OK y se pierde al regenerar"
    if "managed_components" in carpetas:
        return "`managed_components/` lo descarga el gestor de componentes de ESP-IDF; no se edita"
    if "Drivers" in carpetas and any(_HAL.match(c) for c in carpetas):
        return "es código del fabricante (HAL/CMSIS); un parche se propone y se documenta aparte"
    if "Middlewares" in carpetas and any(c in {"Third_Party", "ST"} for c in carpetas):
        return "es middleware que agrega CubeMX (FreeRTOS, USB de ST…); un parche se propone y se documenta aparte"
    if any(_BUILD.match(c) for c in carpetas):
        return "está en una carpeta de compilación; se regenera en cada build"
    return None


def esqueleto(texto: str) -> str:
    """El texto sin el contenido de los bloques USER CODE (los marcadores se conservan).

    Solo cuenta como bloque un BEGIN seguido directamente de un END. Un BEGIN sin
    cerrar no vuelve editable el código generado que le sigue.
    """
    marcas = list(_MARCA.finditer(texto))
    partes, posicion, i = [], 0, 0
    while i < len(marcas):
        inicio = marcas[i]
        fin = marcas[i + 1] if i + 1 < len(marcas) else None
        if inicio.group(1) == "BEGIN" and fin is not None and fin.group(1) == "END":
            partes.append(texto[posicion:inicio.end()])
            partes.append(texto[fin.start():fin.end()])
            posicion = fin.end()
            i += 2
        else:
            i += 1
    partes.append(texto[posicion:])
    return "\u0000".join(partes)


def _aplicar(texto: str, edicion: dict) -> str | None:
    """Simula una edición de Claude Code. None si no se puede aplicar (Claude Code la rechazará)."""
    viejo, nuevo = edicion.get("old_string"), edicion.get("new_string", "")
    if not isinstance(viejo, str) or not viejo or not isinstance(nuevo, str) or viejo not in texto:
        return None
    return texto.replace(viejo, nuevo) if edicion.get("replace_all") is True else texto.replace(viejo, nuevo, 1)


def motivo_cubemx(ruta: str, herramienta: str, entrada: dict) -> str | None:
    """En archivos de CubeMX, pregunta solo si la edición cambia algo fuera de los bloques USER CODE."""
    try:
        with open(ruta, encoding="utf-8", errors="replace") as f:
            texto = f.read()
    except OSError:
        return None  # archivo nuevo o ilegible: no es código de CubeMX existente
    if "USER CODE BEGIN" not in texto:
        return None
    if herramienta == "Write":
        despues = entrada.get("content")
        if not isinstance(despues, str):
            return None
    else:
        ediciones = entrada.get("edits") if herramienta == "MultiEdit" else [entrada]
        if not isinstance(ediciones, list):
            return None
        despues = texto
        for edicion in ediciones:
            despues = _aplicar(despues, edicion) if isinstance(edicion, dict) else None
            if despues is None:
                return None
    if esqueleto(despues) == esqueleto(texto):
        return None
    return f"`{os.path.basename(ruta)}` lo genera STM32CubeMX y esta edición cambia algo fuera de los bloques USER CODE, que se pierde al regenerar"


def evaluar(herramienta: str, entrada: dict, base: str | None = None) -> str | None:
    if herramienta not in HERRAMIENTAS or not isinstance(entrada, dict):
        return None
    ruta = entrada.get("notebook_path") if herramienta == "NotebookEdit" else entrada.get("file_path")
    if not isinstance(ruta, str) or not ruta:
        return None
    motivo = motivo_por_ruta(ruta, base)
    if motivo is None and herramienta != "NotebookEdit":
        motivo = motivo_cubemx(ruta, herramienta, entrada)
    return motivo


def main() -> int:
    try:
        datos = json.load(sys.stdin)
    except ValueError:
        return 0
    if not isinstance(datos, dict):
        return 0
    base = os.environ.get("CLAUDE_PROJECT_DIR") or datos.get("cwd")
    motivo = evaluar(datos.get("tool_name"), datos.get("tool_input"), base if isinstance(base, str) else None)
    if motivo:
        salida = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "ask",
                "permissionDecisionReason": f"El arnés (capa firmware) pide confirmación: {motivo}.",
            }
        }
        print(json.dumps(salida, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
