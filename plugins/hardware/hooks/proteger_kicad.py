#!/usr/bin/env python3
"""Hook PreToolUse de la capa hardware: pide confirmación antes de editar archivos de KiCad a mano.

Los archivos de diseño de KiCad se cambian en KiCad: editarlos como texto puede
romper UUIDs, referencias o la sincronía entre esquemático y PCB. Las salidas de
fabricación (Gerber, taladro) se regeneran desde el PCB. El hook no bloquea
(a veces el responsable pide un cambio de texto): pide confirmación con el motivo.

No pregunta por `.kicad_dru`, `fp-lib-table` ni `sym-lib-table`, que sí se
escriben a mano.

Cubre Edit, Write y MultiEdit. Límite conocido: un `sed -i` o un `echo >` por
Bash no pasan por aquí.

Si la entrada no es válida, no dice nada y sale con 0: un error del hook no
debe trabar el trabajo. Solo usa la biblioteca estándar.
"""

from __future__ import annotations

import json
import os
import re
import sys

HERRAMIENTAS = {"Edit", "Write", "MultiEdit"}
DISENO = {
    ".kicad_sch": "un esquemático de KiCad",
    ".kicad_pcb": "un PCB de KiCad",
    ".kicad_sym": "una librería de símbolos de KiCad",
    ".kicad_mod": "una huella de KiCad",
    ".kicad_pro": "el archivo de proyecto de KiCad",
}
# Gerber X2/RS-274X (extensiones de KiCad y las de Protel que usan muchos fabricantes, con capas
# internas .g1, .g2… y mecánicas .gm1, .gm2…), taladro Excellon y archivo de posiciones.
FABRICACION = {".gbr", ".gbrjob", ".drl", ".gtl", ".gbl", ".gts", ".gbs", ".gto", ".gbo", ".gtp", ".gbp",
               ".gko", ".pos"}
_CAPA_PROTEL = re.compile(r"^\.gm?\d+$")


def _relativa(ruta: str, base: str | None) -> list[str]:
    """Partes de la ruta real, relativas al proyecto si está dentro de él."""
    real = os.path.realpath(ruta)
    if base:
        base = os.path.realpath(base)
        if real == base or real.startswith(base + os.sep):
            real = os.path.relpath(real, base)
    return [p for p in real.split(os.sep) if p]


def motivo(ruta: str, base: str | None = None) -> str | None:
    """Motivo para pedir confirmación según la ruta, o None."""
    partes = _relativa(ruta, base)
    nombre = partes[-1] if partes else ""
    extension = os.path.splitext(nombre)[1].lower()
    if extension in DISENO:
        return f"`{nombre}` es {DISENO[extension]}; se cambia en KiCad, y editarlo a mano puede romper UUIDs, referencias o la sincronía esquemático-PCB"
    if extension in FABRICACION or _CAPA_PROTEL.match(extension):
        return f"`{nombre}` es una salida de fabricación; se regenera desde el PCB, no se edita"
    if any(carpeta.endswith("-backups") for carpeta in partes[:-1]):
        return f"`{nombre}` está en una carpeta de respaldos de KiCad; se restaura desde KiCad"
    return None


def evaluar(herramienta: str, entrada: dict, base: str | None = None) -> str | None:
    if not isinstance(herramienta, str) or herramienta not in HERRAMIENTAS or not isinstance(entrada, dict):
        return None
    ruta = entrada.get("file_path")
    if not isinstance(ruta, str) or not ruta:
        return None
    try:
        return motivo(ruta, base)
    except ValueError:  # por ejemplo, un byte nulo en la ruta
        return None


def main() -> int:
    try:
        datos = json.load(sys.stdin)
    except ValueError:
        return 0
    if not isinstance(datos, dict):
        return 0
    base = os.environ.get("CLAUDE_PROJECT_DIR") or datos.get("cwd")
    razon = evaluar(datos.get("tool_name"), datos.get("tool_input"), base if isinstance(base, str) else None)
    if razon:
        salida = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "ask",
                "permissionDecisionReason": f"El arnés (capa hardware) pide confirmación: {razon}.",
            }
        }
        print(json.dumps(salida, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
