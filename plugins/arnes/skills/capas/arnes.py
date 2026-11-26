#!/usr/bin/env python3
"""Lógica de los comandos /arnes:capas y los atajos /arnes:<capa>: ver, activar y quitar capas del arnés en un proyecto.

Subcomandos (todos aceptan --proyecto DIR; por defecto, la carpeta actual):

  estado                     Capas disponibles, capas activas en el proyecto y avisos.
  aplicar CAPA [CAPA ...]    Deja activas exactamente esas capas en el proyecto.
                             `sistema` activa las cinco; `ninguna` las quita todas.
  agregar CAPA [CAPA ...]    Activa esas capas y conserva las que ya estaban (lo usan
                             los atajos /arnes:firmware, /arnes:software, etc.).
  preparar CAPA [CAPA ...]   Crea CLAUDE.md, Docs/ y .gitignore si faltan. Nunca
                             sobrescribe: de lo que ya existe, informa qué le falta.
  completar CAPA [CAPA ...]  Agrega al final de CLAUDE.md y .gitignore existentes solo
                             las secciones y líneas que les faltan (usar con el OK del usuario).
  seccion CAPA               Imprime la sección de CLAUDE.md de una capa.

Las capas se pueden separar con espacios o con comas.

Cómo se activa una capa: se anota `<capa>@claude-code-harness: true` en el
`enabledPlugins` del `.claude/settings.json` del proyecto. Con el marketplace
agregado desde una carpeta local, Claude Code la carga al empezar la siguiente
sesión (comprobado en A-04). `sistema` se anota junto con las otras cuatro,
porque Claude Code no lo carga si sus dependencias no están activas.

Por seguridad se niega a trabajar en la carpeta personal, en `/` y en el repo del
propio arnés: allí `.claude/settings.json` o `CLAUDE.md` afectarían a todos los proyectos.

Solo usa la biblioteca estándar.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import string
import sys
import tempfile

MARKETPLACE = "claude-code-harness"
NUCLEO = "arnes"  # el plugin del núcleo; no es una capa
SISTEMA = "sistema"
NINGUNA = "ninguna"
AQUI = os.path.dirname(os.path.abspath(__file__))
PLANTILLAS = os.path.join(AQUI, "plantillas")
DOCS = ("vision.md", "requisitos.md", "plan.md", "decisiones.md")
CONOCIDOS = os.path.expanduser("~/.claude/plugins/known_marketplaces.json")
NO_REGISTRADO = f"el marketplace {MARKETPLACE} no está registrado en este computador"


class ErrorArnes(Exception):
    """Error que se muestra al usuario tal cual, sin traceback."""


def _lista(capas: list[str]) -> str:
    return ", ".join(capas) or NINGUNA


# ---------------------------------------------------------------------------
# Marketplace y capas disponibles


def _registro(conocidos: str | None = None) -> dict | None:
    try:
        with open(conocidos or CONOCIDOS, encoding="utf-8") as f:
            registro = json.load(f)[MARKETPLACE]
        return registro if isinstance(registro, dict) else None
    except (OSError, ValueError, KeyError, TypeError):
        return None


def raiz_marketplace(conocidos: str | None = None) -> str | None:
    """Carpeta del marketplace: la registrada en Claude Code o, si no, la del repo del skill."""
    ruta = (_registro(conocidos) or {}).get("installLocation")
    if isinstance(ruta, str) and os.path.isfile(os.path.join(ruta, ".claude-plugin", "marketplace.json")):
        return ruta
    # plugins/arnes/skills/capas/arnes.py -> raíz del repo
    repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(AQUI))))
    if os.path.isfile(os.path.join(repo, ".claude-plugin", "marketplace.json")):
        return repo
    return None


def marketplace_local(conocidos: str | None = None) -> bool:
    """True si el marketplace se agregó desde una carpeta (las capas anotadas cargan sin instalar)."""
    fuente = (_registro(conocidos) or {}).get("source")
    return isinstance(fuente, dict) and fuente.get("source") == "directory"


def capas_disponibles(raiz: str) -> dict[str, str]:
    """{capa: descripción} en el orden del marketplace, sin el núcleo."""
    try:
        with open(os.path.join(raiz, ".claude-plugin", "marketplace.json"), encoding="utf-8") as f:
            plugins = json.load(f)["plugins"]
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ErrorArnes(f"no se pudo leer el marketplace en {raiz}: {error}") from None
    return {
        p["name"]: p.get("description", "")
        for p in plugins
        if isinstance(p, dict) and p.get("name") and p["name"] != NUCLEO
    }


def expandir(pedidas: list[str], disponibles: dict[str, str]) -> list[str]:
    """Valida las capas pedidas y devuelve la lista final, en el orden del marketplace."""
    pedidas = [c.strip().lower() for texto in pedidas for c in texto.replace(",", " ").split()]
    if not pedidas:
        raise ErrorArnes(f"indica al menos una capa, o `{NINGUNA}` para quitarlas todas")
    if pedidas == [NINGUNA]:
        return []
    if NINGUNA in pedidas:
        raise ErrorArnes(f"`{NINGUNA}` no se combina con otras capas")
    desconocidas = [c for c in pedidas if c not in disponibles]
    if desconocidas:
        raise ErrorArnes(f"capas desconocidas: {', '.join(desconocidas)}. Disponibles: {', '.join(disponibles)}")
    if SISTEMA in pedidas:
        return list(disponibles)  # sistema necesita las demás activas para cargar
    return [c for c in disponibles if c in pedidas]


# ---------------------------------------------------------------------------
# Configuración del proyecto


def comprobar_proyecto(proyecto: str, raiz: str | None) -> None:
    """Se niega a trabajar donde un cambio afectaría a todos los proyectos."""
    real = os.path.realpath(proyecto)
    if real in {os.path.realpath(os.path.expanduser("~")), os.path.realpath(os.sep)}:
        raise ErrorArnes(
            f"{proyecto} es tu carpeta personal o la raíz del sistema: allí .claude/settings.json "
            "y CLAUDE.md afectarían a todos los proyectos. Abre Claude Code en la carpeta del proyecto."
        )
    if raiz and real == os.path.realpath(raiz):
        raise ErrorArnes(f"{proyecto} es el repo del propio arnés; los comandos /arnes:… son para tus proyectos")
    usuario = os.path.realpath(os.path.expanduser("~/.claude/settings.json"))
    if os.path.realpath(_ruta_settings(proyecto)) == usuario:
        raise ErrorArnes("el .claude/settings.json de este proyecto es el de usuario; no se toca")


def _ruta_settings(proyecto: str) -> str:
    return os.path.join(proyecto, ".claude", "settings.json")


def leer_settings(proyecto: str) -> dict:
    ruta = _ruta_settings(proyecto)
    if not os.path.exists(ruta):
        return {}
    try:
        with open(ruta, encoding="utf-8") as f:
            datos = json.load(f)
    except ValueError as error:
        raise ErrorArnes(f"{ruta} no es JSON válido ({error}); corrígelo antes de usar /arnes:capas") from None
    if not isinstance(datos, dict) or not isinstance(datos.get("enabledPlugins", {}), dict):
        raise ErrorArnes(f"{ruta} no tiene la forma esperada; corrígelo antes de usar /arnes:capas")
    return datos


def _id(capa: str) -> str:
    return f"{capa}@{MARKETPLACE}"


def capas_activas(settings: dict, disponibles: dict[str, str]) -> list[str]:
    activos = settings.get("enabledPlugins", {})
    return [c for c in disponibles if activos.get(_id(c)) is True]


def _escribir_json(ruta: str, datos: dict) -> None:
    """Escribe de forma atómica en el destino real (sigue symlinks) y conserva los permisos."""
    ruta = os.path.realpath(ruta)
    carpeta = os.path.dirname(ruta)
    os.makedirs(carpeta, exist_ok=True)
    modo = stat.S_IMODE(os.stat(ruta).st_mode) if os.path.exists(ruta) else 0o644
    fd, temporal = tempfile.mkstemp(dir=carpeta, prefix=".settings-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.chmod(temporal, modo)
        os.replace(temporal, ruta)
    except BaseException:
        os.unlink(temporal)
        raise


def aplicar(proyecto: str, capas: list[str], disponibles: dict[str, str]) -> tuple[list[str], bool]:
    """Deja activas exactamente `capas`. Devuelve (capas activas, si hubo cambio)."""
    ruta = _ruta_settings(proyecto)
    settings = leer_settings(proyecto)
    antes = capas_activas(settings, disponibles)
    if antes == capas:
        return capas, False
    activos = dict(settings.get("enabledPlugins", {}))
    for capa in disponibles:
        activos.pop(_id(capa), None)
    for capa in capas:
        activos[_id(capa)] = True
    settings["enabledPlugins"] = activos
    _escribir_json(ruta, settings)
    return capas_activas(settings, disponibles), True


def agregar(proyecto: str, nuevas: list[str], disponibles: dict[str, str]) -> tuple[list[str], bool]:
    """Activa `nuevas` sin quitar las que ya estaban. Devuelve (capas activas, si hubo cambio)."""
    if not nuevas:
        raise ErrorArnes(f"indica qué capa agregar; para quitarlas usa `aplicar {NINGUNA}`")
    actuales = capas_activas(leer_settings(proyecto), disponibles)
    return aplicar(proyecto, expandir(actuales + nuevas, disponibles), disponibles)


# ---------------------------------------------------------------------------
# Preparar y completar el proyecto


def _leer_plantilla(*partes: str) -> str:
    with open(os.path.join(PLANTILLAS, *partes), encoding="utf-8") as f:
        return f.read()


def seccion(capa: str) -> str:
    return _leer_plantilla("capas", f"{capa}.md").strip() + "\n"


def _titulo_seccion(capa: str) -> str:
    return seccion(capa).splitlines()[0].strip()


def lineas_gitignore(capas: list[str]) -> list[str]:
    lineas = []
    for nombre in ["base", *capas]:
        ruta = os.path.join(PLANTILLAS, "gitignore", nombre)
        if os.path.isfile(ruta):
            with open(ruta, encoding="utf-8") as f:
                for linea in f.read().splitlines():
                    if linea.strip() and not linea.startswith("#") and linea not in lineas:
                        lineas.append(linea)
    return lineas


def _leer_texto(ruta: str) -> str:
    with open(ruta, encoding="utf-8", errors="replace") as f:
        return f.read()


def faltantes(proyecto: str, capas: list[str]) -> tuple[list[str], list[str]]:
    """(secciones de capa que faltan en CLAUDE.md, líneas que faltan en .gitignore), de los que existen."""
    secciones, lineas = [], []
    claude = os.path.join(proyecto, "CLAUDE.md")
    if os.path.isfile(claude):
        actual = _leer_texto(claude)
        secciones = [c for c in capas if _titulo_seccion(c) not in actual]
    gitignore = os.path.join(proyecto, ".gitignore")
    if os.path.isfile(gitignore):
        actuales = set(_leer_texto(gitignore).splitlines())
        lineas = [linea for linea in lineas_gitignore(capas) if linea not in actuales]
    return secciones, lineas


def preparar(proyecto: str, capas: list[str], nombre: str, descripcion: str) -> dict[str, list[str]]:
    """Crea lo que falta. Devuelve {"creados": [...], "existentes": [...], "faltan": [...]}."""
    docs = os.path.join(proyecto, "Docs")
    if os.path.exists(docs) and not os.path.isdir(docs):
        raise ErrorArnes(f"{docs} existe pero no es una carpeta; no se creó nada")
    informe = {"creados": [], "existentes": [], "faltan": []}

    def crear(relativa: str, contenido: str) -> None:
        ruta = os.path.join(proyecto, relativa)
        if os.path.exists(ruta):
            informe["existentes"].append(relativa)
            return
        try:
            os.makedirs(os.path.dirname(ruta), exist_ok=True)
            with open(ruta, "x", encoding="utf-8") as f:  # "x": falla si apareció entretanto
                f.write(contenido)
        except OSError as error:
            hechos = ", ".join(informe["creados"]) or "nada"
            raise ErrorArnes(f"no se pudo crear {relativa} ({error.strerror}). Ya se había creado: {hechos}") from None
        informe["creados"].append(relativa)

    valores = {"nombre": nombre, "descripcion": descripcion, "capas": _lista(capas) if capas else "solo el núcleo"}
    secciones = "\n".join(seccion(c) for c in capas)
    claude = string.Template(_leer_plantilla("CLAUDE.plantilla.md")).safe_substitute(valores)
    crear("CLAUDE.md", claude.rstrip() + "\n" + ("\n" + secciones if secciones else ""))
    for doc in DOCS:
        crear(os.path.join("Docs", doc), string.Template(_leer_plantilla("docs", doc)).safe_substitute(valores))
    crear(".gitignore", "\n".join(lineas_gitignore(capas)) + "\n")

    secciones_faltan, lineas_faltan = faltantes(proyecto, capas)
    informe["faltan"] += [f"CLAUDE.md: sección «{_titulo_seccion(c)}»" for c in secciones_faltan]
    informe["faltan"] += [f".gitignore: {linea}" for linea in lineas_faltan]
    return informe


def _agregar_al_final(ruta: str, texto: str) -> None:
    actual = _leer_texto(ruta)
    separador = "" if not actual or actual.endswith("\n") else "\n"
    with open(ruta, "a", encoding="utf-8") as f:
        f.write(separador + texto)


def completar(proyecto: str, capas: list[str]) -> list[str]:
    """Agrega al final solo lo que falta en CLAUDE.md y .gitignore existentes. Devuelve lo agregado."""
    secciones, lineas = faltantes(proyecto, capas)
    agregado = []
    try:
        if secciones:
            _agregar_al_final(os.path.join(proyecto, "CLAUDE.md"), "\n" + "\n".join(seccion(c) for c in secciones))
            agregado += [f"CLAUDE.md: sección «{_titulo_seccion(c)}»" for c in secciones]
        if lineas:
            _agregar_al_final(os.path.join(proyecto, ".gitignore"), "\n".join(lineas) + "\n")
            agregado += [f".gitignore: {linea}" for linea in lineas]
    except OSError as error:
        raise ErrorArnes(f"no se pudo completar ({error.strerror}). Ya se agregó: {', '.join(agregado) or 'nada'}") from None
    return agregado


# ---------------------------------------------------------------------------
# Interfaz de línea de comandos


def _imprimir_estado(proyecto: str, raiz: str) -> None:
    disponibles = capas_disponibles(raiz)
    activas = capas_activas(leer_settings(proyecto), disponibles)
    print(f"Proyecto: {proyecto}")
    print("Capas activas en este proyecto: " + _lista(activas))
    print("Capas disponibles:")
    for capa, descripcion in disponibles.items():
        print(f"  {'●' if capa in activas else '○'} {capa} — {descripcion}")
    if activas and not marketplace_local():
        print(
            "Aviso: en este computador el marketplace no viene de una carpeta local, así que una capa anotada "
            "puede no cargar hasta instalarla. Si no aparece en la conversación nueva, ejecuta en una terminal, "
            f"en esta carpeta: claude plugin install <capa>@{MARKETPLACE} --scope project"
        )
    faltan = [f for f in ("CLAUDE.md", ".gitignore", "Docs") if not os.path.exists(os.path.join(proyecto, f))]
    if faltan:
        print("Faltan en el proyecto: " + ", ".join(faltan))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="arnes.py", description="Capas del arnés en un proyecto.")
    parser.add_argument("--proyecto", default=os.getcwd(), help="carpeta del proyecto (por defecto, la actual)")
    sub = parser.add_subparsers(dest="orden", required=True)
    sub.add_parser("estado")
    for orden in ("aplicar", "agregar", "completar"):
        sub.add_parser(orden).add_argument("capas", nargs="+")
    p_preparar = sub.add_parser("preparar")
    p_preparar.add_argument("capas", nargs="+")
    p_preparar.add_argument("--nombre")
    p_preparar.add_argument("--descripcion", default="Descripción pendiente.")
    sub.add_parser("seccion").add_argument("capa")
    args = parser.parse_args(argv)
    proyecto = os.path.abspath(args.proyecto)

    try:
        raiz = raiz_marketplace()
        if raiz is None:
            if args.orden == "estado":
                print(f"✗ {NO_REGISTRADO[0].upper()}{NO_REGISTRADO[1:]}.")
                print("  Ejecuta en una terminal: claude plugin marketplace add <carpeta del arnés>")
                return 0
            raise ErrorArnes(NO_REGISTRADO)
        disponibles = capas_disponibles(raiz)
        if args.orden == "seccion":
            capas = expandir([args.capa], disponibles)
            if len(capas) != 1:
                raise ErrorArnes("indica una sola capa (no `sistema` ni `ninguna`)")
            print(seccion(capas[0]), end="")
            return 0
        comprobar_proyecto(proyecto, raiz)
        if args.orden == "estado":
            _imprimir_estado(proyecto, raiz)
        elif args.orden in ("aplicar", "agregar"):
            capas = expandir(args.capas, disponibles)
            if args.orden == "agregar":
                activas, cambio = agregar(proyecto, capas, disponibles)
            else:
                activas, cambio = aplicar(proyecto, capas, disponibles)
            if cambio:
                print("✓ Capas activas en este proyecto: " + _lista(activas))
                print("  Abre una conversación nueva para que carguen.")
            else:
                print("Sin cambios. Capas activas en este proyecto: " + _lista(activas))
        elif args.orden == "preparar":
            informe = preparar(proyecto, expandir(args.capas, disponibles),
                               args.nombre or os.path.basename(proyecto), args.descripcion)
            for etiqueta, clave in (("Creado", "creados"), ("Ya existía (no se tocó)", "existentes"), ("Falta", "faltan")):
                for item in informe[clave]:
                    print(f"{etiqueta}: {item}")
        elif args.orden == "completar":
            agregado = completar(proyecto, expandir(args.capas, disponibles))
            for item in agregado:
                print(f"Agregado: {item}")
            if not agregado:
                print("No faltaba nada.")
    except ErrorArnes as error:
        print(f"✗ {error}", file=sys.stderr)
        return 1
    except OSError as error:
        print(f"✗ {error.filename or 'archivo'}: {error.strerror}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
