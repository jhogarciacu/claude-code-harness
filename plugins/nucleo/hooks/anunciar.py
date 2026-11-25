#!/usr/bin/env python3
"""Hook SessionStart del arnés: anuncia qué plugin del arnés está activo.

- A Claude le inyecta (additionalContext) una línea "Arnés activo: <plugin> <versión>"
  y, si el plugin tiene `reglas.md` en su raíz, esas reglas.
- Al usuario le muestra la misma línea (systemMessage).

Cada plugin del arnés lleva una copia idéntica de este archivo (los plugins se
instalan aislados y no pueden leer archivos fuera de su carpeta). La copia
canónica está en plugins/nucleo/hooks/; `herramientas/validar.py` comprueba que
todas sean iguales.

Si algo falla no imprime nada y sale con 0: un anuncio no debe trabar la sesión.
Solo usa la biblioteca estándar.
"""

from __future__ import annotations

import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def construir(raiz: str = RAIZ) -> dict | None:
    """Devuelve la salida JSON del hook, o None si el plugin no se puede leer."""
    try:
        with open(os.path.join(raiz, ".claude-plugin", "plugin.json"), encoding="utf-8") as f:
            manifiesto = json.load(f)
        nombre, version = manifiesto["name"], manifiesto.get("version", "?")
    except (OSError, ValueError, KeyError, TypeError):
        return None
    linea = f"Arnés activo: {nombre} {version}"
    contexto = linea + " (plugin del arnés claude-code-harness)."
    try:
        with open(os.path.join(raiz, "reglas.md"), encoding="utf-8") as f:
            reglas = f.read().strip()
    except (OSError, ValueError):  # ValueError: reglas.md que no está en UTF-8
        reglas = ""
    if reglas:
        contexto += f"\n\nReglas del área `{nombre}`:\n\n{reglas}"
    return {
        "systemMessage": linea,
        "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": contexto},
    }


def main() -> int:
    salida = construir()
    if salida is not None:
        print(json.dumps(salida, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
