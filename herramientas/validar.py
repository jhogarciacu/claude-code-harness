#!/usr/bin/env python3
"""Valida la estructura del arnés: marketplace, plugins, hooks y copias compartidas.

Comprueba lo que Claude Code exige según su documentación y lo que el arnés
necesita para no romperse en silencio:

- marketplace.json con `name`, `owner` y `plugins`;
- cada `source` es relativo (`./...`), sin `..`, y la carpeta existe. Decisión del
  arnés: todos sus plugins viven en este repo, así que no se aceptan fuentes
  remotas (GitHub, npm...), aunque Claude Code sí las admite;
- cada carpeta de `plugins/` está registrada en el marketplace;
- el `name` del marketplace coincide con el de `plugin.json`, que tiene versión;
- las `dependencies` apuntan a plugins de este mismo marketplace;
- `hooks/hooks.json` es válido y los archivos que usa con `${CLAUDE_PLUGIN_ROOT}` existen;
- no hay `CLAUDE.md` en la raíz de un plugin (Claude Code no lo carga);
- `reglas.md` cabe en el contexto que inyecta un hook (Claude Code corta a 10 000 caracteres);
- todas las copias de `hooks/anunciar.py` son idénticas a la del núcleo.

Uso: python3 herramientas/validar.py [raíz del repo]
Sale con 1 y lista los errores si encuentra alguno.
"""

from __future__ import annotations

import glob
import json
import os
import re
import sys
from pathlib import Path

# Claude Code no valida semver; el arnés pide al menos x.y.z (con sufijo opcional).
_VERSION = re.compile(r"^\d+\.\d+\.\d+([-+][0-9A-Za-z.-]+)?$")
# `${CLAUDE_PLUGIN_ROOT}/x`, `"${CLAUDE_PLUGIN_ROOT}"/x` y `$CLAUDE_PLUGIN_ROOT/x`.
_RUTA_EN_COMANDO = re.compile(r"\$\{?CLAUDE_PLUGIN_ROOT\}?\"?/([^\"'\s;|&()]+)")
ANUNCIAR_CANONICO = os.path.join("plugins", "arnes", "hooks", "anunciar.py")
# Claude Code guarda en un archivo lo que pase de 10 000 caracteres; se deja margen
# para la línea de anuncio que agrega anunciar.py.
MAX_REGLAS = 9000


def _leer_json(ruta: str, errores: list[str], tipo=dict):
    try:
        with open(ruta, encoding="utf-8") as f:
            datos = json.load(f)
    except OSError:
        errores.append(f"{ruta}: no existe")
        return None
    except ValueError as error:
        errores.append(f"{ruta}: JSON no válido ({error})")
        return None
    if not isinstance(datos, tipo):
        errores.append(f"{ruta}: debe ser un objeto JSON")
        return None
    return datos


def _validar_hooks(carpeta: str, errores: list[str]) -> None:
    ruta = os.path.join(carpeta, "hooks", "hooks.json")
    if not os.path.exists(ruta):
        return  # un plugin puede no tener hooks
    datos = _leer_json(ruta, errores)
    if datos is None:
        return
    if not isinstance(datos.get("hooks"), dict):
        errores.append(f"{ruta}: falta el objeto `hooks` en el primer nivel")
        return
    for evento, grupos in datos["hooks"].items():
        if not isinstance(grupos, list):
            errores.append(f"{ruta}: el evento {evento} debe ser una lista")
            continue
        for grupo in grupos:
            hooks = grupo.get("hooks") if isinstance(grupo, dict) else None
            if not isinstance(hooks, list):
                errores.append(f"{ruta}: un grupo de {evento} no tiene la lista `hooks`")
                continue
            for hook in hooks:
                comando = hook.get("command") if isinstance(hook, dict) else None
                if not isinstance(comando, str):
                    continue
                for relativa in _RUTA_EN_COMANDO.findall(comando):
                    if not os.path.isfile(os.path.join(carpeta, relativa)):
                        errores.append(f"{ruta}: el hook {evento} usa `{relativa}`, que no existe")


def _validar_dependencias(nombre: str, manifiesto: dict, marketplace: str, nombres: set, errores: list[str]):
    dependencias = manifiesto.get("dependencies", [])
    if not isinstance(dependencias, list):
        errores.append(f"plugin `{nombre}`: `dependencies` debe ser una lista")
        return
    for dep in dependencias:
        if isinstance(dep, dict):
            dep_nombre, dep_market = dep.get("name"), dep.get("marketplace", marketplace)
        else:
            dep_nombre, _, dep_market = str(dep).partition("@")
            dep_market = dep_market or marketplace
        if dep_market != marketplace:
            errores.append(f"plugin `{nombre}`: depende de `{dep_nombre}` de otro marketplace (`{dep_market}`)")
        elif dep_nombre not in nombres:
            errores.append(f"plugin `{nombre}`: depende de `{dep_nombre}`, que no está en el marketplace")


def _validar_copias(raiz: str, errores: list[str]) -> None:
    canonico = os.path.join(raiz, ANUNCIAR_CANONICO)
    if not os.path.isfile(canonico):
        return
    contenido = Path(canonico).read_bytes()
    for copia in sorted(glob.glob(os.path.join(raiz, "plugins", "*", "hooks", "anunciar.py"))):
        if Path(copia).read_bytes() != contenido:
            errores.append(f"{os.path.relpath(copia, raiz)} difiere de la copia del núcleo")


def validar(raiz: str) -> list[str]:
    errores: list[str] = []
    marketplace = _leer_json(os.path.join(raiz, ".claude-plugin", "marketplace.json"), errores)
    if marketplace is None:
        return errores
    for campo in ("name", "owner", "plugins"):
        if campo not in marketplace:
            errores.append(f"marketplace.json: falta `{campo}`")
    plugins = marketplace.get("plugins", [])
    if not isinstance(plugins, list):
        errores.append("marketplace.json: `plugins` debe ser una lista")
        return errores
    entradas = [p for p in plugins if isinstance(p, dict)]
    if len(entradas) != len(plugins):
        errores.append("marketplace.json: cada elemento de `plugins` debe ser un objeto")
    nombres = {p.get("name") for p in entradas}
    registradas = set()

    for entrada in entradas:
        nombre, source = entrada.get("name"), entrada.get("source", "")
        if not isinstance(source, str) or not source.startswith("./") or ".." in source.split("/"):
            errores.append(f"plugin `{nombre}`: `source` debe ser una ruta de este repo: empezar con ./ y sin ..")
            continue
        carpeta = os.path.join(raiz, source)
        if not os.path.isdir(carpeta):
            errores.append(f"plugin `{nombre}`: la carpeta {source} no existe")
            continue
        registradas.add(os.path.realpath(carpeta))
        manifiesto = _leer_json(os.path.join(carpeta, ".claude-plugin", "plugin.json"), errores)
        if manifiesto is None:
            continue
        if manifiesto.get("name") != nombre:
            errores.append(f"plugin `{nombre}`: plugin.json se llama `{manifiesto.get('name')}`")
        if not _VERSION.match(str(manifiesto.get("version", ""))):
            errores.append(f"plugin `{nombre}`: falta una versión x.y.z en plugin.json")
        _validar_dependencias(nombre, manifiesto, marketplace.get("name"), nombres, errores)
        if os.path.exists(os.path.join(carpeta, "CLAUDE.md")):
            errores.append(f"plugin `{nombre}`: tiene CLAUDE.md en su raíz; Claude Code no lo carga (usa reglas.md)")
        reglas = os.path.join(carpeta, "reglas.md")
        if os.path.isfile(reglas) and len(Path(reglas).read_text(encoding="utf-8", errors="replace")) > MAX_REGLAS:
            errores.append(f"plugin `{nombre}`: reglas.md pasa de {MAX_REGLAS} caracteres; Claude Code lo cortaría")
        _validar_hooks(carpeta, errores)

    for carpeta in sorted(glob.glob(os.path.join(raiz, "plugins", "*", ""))):
        if os.path.realpath(carpeta) not in registradas:
            errores.append(f"{os.path.relpath(carpeta, raiz)} no está registrado en marketplace.json")

    _validar_copias(raiz, errores)
    return errores


def main(argv: list[str]) -> int:
    raiz = argv[1] if len(argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    errores = validar(raiz)
    for error in errores:
        print(f"✗ {error}")
    if not errores:
        print("✓ estructura del arnés válida")
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
