"""Pruebas de arnes.py.  Ejecutar: python3 -m unittest discover -s plugins/arnes/skills/capas"""

import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

sys.path.insert(0, os.path.dirname(__file__))

import arnes  # noqa: E402

DISPONIBLES = {"firmware": "f", "hardware": "h", "software": "s", "ia": "i", "sistema": "todo"}
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))


class Base(unittest.TestCase):
    def setUp(self):
        self.proyecto = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.proyecto)

    def settings(self):
        with open(os.path.join(self.proyecto, ".claude", "settings.json"), encoding="utf-8") as f:
            return json.load(f)

    def escribir_settings(self, contenido):
        os.makedirs(os.path.join(self.proyecto, ".claude"), exist_ok=True)
        with open(os.path.join(self.proyecto, ".claude", "settings.json"), "w", encoding="utf-8") as f:
            f.write(contenido if isinstance(contenido, str) else json.dumps(contenido))


class PruebasExpandir(unittest.TestCase):
    def test_orden_del_marketplace(self):
        self.assertEqual(arnes.expandir(["software", "firmware"], DISPONIBLES), ["firmware", "software"])

    def test_sistema_activa_todas(self):
        self.assertEqual(arnes.expandir(["sistema"], DISPONIBLES), list(DISPONIBLES))
        self.assertEqual(arnes.expandir(["ia", "sistema"], DISPONIBLES), list(DISPONIBLES))

    def test_ninguna(self):
        self.assertEqual(arnes.expandir(["ninguna"], DISPONIBLES), [])
        with self.assertRaises(arnes.ErrorArnes):
            arnes.expandir(["ninguna", "ia"], DISPONIBLES)

    def test_mayusculas_y_espacios(self):
        self.assertEqual(arnes.expandir([" Firmware "], DISPONIBLES), ["firmware"])

    def test_comas_y_vacio(self):
        self.assertEqual(arnes.expandir(["firmware,software"], DISPONIBLES), ["firmware", "software"])
        self.assertEqual(arnes.expandir(["firmware software"], DISPONIBLES), ["firmware", "software"])
        for vacio in ([" "], [""], [","]):
            with self.subTest(vacio=vacio), self.assertRaises(arnes.ErrorArnes):
                arnes.expandir(vacio, DISPONIBLES)

    def test_desconocida(self):
        with self.assertRaises(arnes.ErrorArnes) as e:
            arnes.expandir(["fpga"], DISPONIBLES)
        self.assertIn("fpga", str(e.exception))


class PruebasAplicar(Base):
    def test_proyecto_sin_claude(self):
        self.assertEqual(arnes.aplicar(self.proyecto, ["firmware"], DISPONIBLES), (["firmware"], True))
        self.assertEqual(self.settings(), {"enabledPlugins": {"firmware@claude-code-harness": True}})

    def test_reemplaza_la_seleccion(self):
        arnes.aplicar(self.proyecto, ["firmware", "software"], DISPONIBLES)
        arnes.aplicar(self.proyecto, ["ia"], DISPONIBLES)
        self.assertEqual(self.settings()["enabledPlugins"], {"ia@claude-code-harness": True})

    def test_quitar_todas(self):
        arnes.aplicar(self.proyecto, list(DISPONIBLES), DISPONIBLES)
        self.assertEqual(arnes.aplicar(self.proyecto, [], DISPONIBLES), ([], True))
        self.assertEqual(self.settings()["enabledPlugins"], {})

    def test_sin_cambio_no_escribe(self):
        arnes.aplicar(self.proyecto, ["ia"], DISPONIBLES)
        ruta = os.path.join(self.proyecto, ".claude", "settings.json")
        antes = os.stat(ruta).st_mtime_ns
        self.assertEqual(arnes.aplicar(self.proyecto, ["ia"], DISPONIBLES), (["ia"], False))
        self.assertEqual(os.stat(ruta).st_mtime_ns, antes)

    def test_sigue_symlink_y_conserva_permisos(self):
        real = os.path.join(self.proyecto, "real.json")
        with open(real, "w", encoding="utf-8") as f:
            f.write("{}")
        os.chmod(real, 0o640)
        os.makedirs(os.path.join(self.proyecto, ".claude"))
        enlace = os.path.join(self.proyecto, ".claude", "settings.json")
        os.symlink(real, enlace)
        arnes.aplicar(self.proyecto, ["firmware"], DISPONIBLES)
        self.assertTrue(os.path.islink(enlace))
        self.assertEqual(os.stat(real).st_mode & 0o777, 0o640)
        with open(real, encoding="utf-8") as f:
            self.assertIn("firmware@claude-code-harness", f.read())

    def test_quitar_sin_archivo_no_lo_crea(self):
        arnes.aplicar(self.proyecto, [], DISPONIBLES)
        self.assertFalse(os.path.exists(os.path.join(self.proyecto, ".claude")))

    def test_conserva_lo_demas(self):
        self.escribir_settings({
            "permissions": {"allow": ["Bash(make)"]},
            "enabledPlugins": {"otro@market": True, "arnes@claude-code-harness": True,
                               "hardware@claude-code-harness": True},
        })
        arnes.aplicar(self.proyecto, ["firmware"], DISPONIBLES)
        datos = self.settings()
        self.assertEqual(datos["permissions"], {"allow": ["Bash(make)"]})
        self.assertEqual(datos["enabledPlugins"], {"otro@market": True, "arnes@claude-code-harness": True,
                                                   "firmware@claude-code-harness": True})

    def test_json_roto_no_se_toca(self):
        self.escribir_settings("{ roto")
        with self.assertRaises(arnes.ErrorArnes):
            arnes.aplicar(self.proyecto, ["firmware"], DISPONIBLES)
        with open(os.path.join(self.proyecto, ".claude", "settings.json"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "{ roto")

    def test_forma_inesperada(self):
        for contenido in ([], {"enabledPlugins": []}):
            with self.subTest(contenido=contenido):
                self.escribir_settings(contenido)
                with self.assertRaises(arnes.ErrorArnes):
                    arnes.aplicar(self.proyecto, ["firmware"], DISPONIBLES)

    def test_activas_ignora_falsos(self):
        settings = {"enabledPlugins": {"firmware@claude-code-harness": False, "ia@claude-code-harness": True}}
        self.assertEqual(arnes.capas_activas(settings, DISPONIBLES), ["ia"])


class PruebasAgregar(Base):
    def test_conserva_las_que_estaban(self):
        arnes.aplicar(self.proyecto, ["firmware"], DISPONIBLES)
        self.assertEqual(arnes.agregar(self.proyecto, ["software"], DISPONIBLES), (["firmware", "software"], True))

    def test_ya_activa_sin_cambio(self):
        arnes.aplicar(self.proyecto, ["ia"], DISPONIBLES)
        self.assertEqual(arnes.agregar(self.proyecto, ["ia"], DISPONIBLES), (["ia"], False))

    def test_sistema_activa_todas(self):
        arnes.aplicar(self.proyecto, ["ia"], DISPONIBLES)
        self.assertEqual(arnes.agregar(self.proyecto, ["sistema"], DISPONIBLES)[0], list(DISPONIBLES))

    def test_sin_capas_es_error(self):
        with self.assertRaises(arnes.ErrorArnes):
            arnes.agregar(self.proyecto, [], DISPONIBLES)

    def test_cli_no_acepta_ninguna(self):
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()) as errores, \
                mock.patch.object(arnes, "raiz_marketplace", return_value=REPO):
            self.assertEqual(arnes.main(["--proyecto", self.proyecto, "agregar", "ninguna"]), 1)
        self.assertIn("aplicar ninguna", errores.getvalue())


class PruebasPreparar(Base):
    def test_carpeta_vacia(self):
        informe = arnes.preparar(self.proyecto, ["firmware", "ia"], "sensor", "Un sensor.")
        self.assertIn("CLAUDE.md", informe["creados"])
        self.assertIn(".gitignore", informe["creados"])
        self.assertEqual(informe["existentes"], [])
        with open(os.path.join(self.proyecto, "CLAUDE.md"), encoding="utf-8") as f:
            claude = f.read()
        self.assertIn("# sensor", claude)
        self.assertIn("Un sensor.", claude)
        self.assertIn("firmware, ia", claude)
        self.assertIn("## Revisión: firmware", claude)
        self.assertIn("## Revisión: ia", claude)
        self.assertNotIn("## Revisión: hardware", claude)
        self.assertNotIn("$", claude)  # no quedan marcadores sin reemplazar
        for doc in arnes.DOCS:
            self.assertTrue(os.path.isfile(os.path.join(self.proyecto, "Docs", doc)))
        with open(os.path.join(self.proyecto, ".gitignore"), encoding="utf-8") as f:
            gitignore = f.read().splitlines()
        self.assertIn(".env", gitignore)
        self.assertIn(".pio/", gitignore)
        self.assertIn("*.safetensors", gitignore)
        self.assertNotIn("*.kicad_prl", gitignore)

    def test_no_sobrescribe(self):
        with open(os.path.join(self.proyecto, "CLAUDE.md"), "w", encoding="utf-8") as f:
            f.write("# Mío\n")
        with open(os.path.join(self.proyecto, ".gitignore"), "w", encoding="utf-8") as f:
            f.write(".env\n")
        informe = arnes.preparar(self.proyecto, ["firmware"], "x", "y")
        with open(os.path.join(self.proyecto, "CLAUDE.md"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "# Mío\n")
        self.assertEqual(sorted(informe["existentes"]), [".gitignore", "CLAUDE.md"])
        self.assertIn("CLAUDE.md: sección «## Revisión: firmware»", informe["faltan"])
        self.assertIn(".gitignore: .pio/", informe["faltan"])
        self.assertNotIn(".gitignore: .env", informe["faltan"])  # ya estaba

    def test_docs_como_archivo_no_crea_nada(self):
        with open(os.path.join(self.proyecto, "Docs"), "w", encoding="utf-8") as f:
            f.write("x")
        with self.assertRaises(arnes.ErrorArnes):
            arnes.preparar(self.proyecto, ["firmware"], "x", "y")
        self.assertFalse(os.path.exists(os.path.join(self.proyecto, "CLAUDE.md")))

    def test_completar_agrega_solo_lo_que_falta(self):
        with open(os.path.join(self.proyecto, "CLAUDE.md"), "w", encoding="utf-8") as f:
            f.write("# Mío")  # sin salto final
        with open(os.path.join(self.proyecto, ".gitignore"), "w", encoding="utf-8") as f:
            f.write("node_modules")  # sin salto final
        agregado = arnes.completar(self.proyecto, ["firmware"])
        self.assertTrue(any("Revisión: firmware" in a for a in agregado))
        with open(os.path.join(self.proyecto, "CLAUDE.md"), encoding="utf-8") as f:
            claude = f.read()
        self.assertTrue(claude.startswith("# Mío\n"))
        self.assertIn("## Revisión: firmware", claude)
        with open(os.path.join(self.proyecto, ".gitignore"), encoding="utf-8") as f:
            lineas = f.read().splitlines()
        self.assertEqual(lineas[0], "node_modules")
        self.assertIn(".env", lineas)
        self.assertEqual(arnes.completar(self.proyecto, ["firmware"]), [])  # la segunda vez no agrega nada

    def test_completar_sin_archivos_no_crea(self):
        self.assertEqual(arnes.completar(self.proyecto, ["ia"]), [])
        self.assertFalse(os.path.exists(os.path.join(self.proyecto, "CLAUDE.md")))

    def test_sin_capas(self):
        arnes.preparar(self.proyecto, [], "x", "y")
        with open(os.path.join(self.proyecto, "CLAUDE.md"), encoding="utf-8") as f:
            claude = f.read()
        self.assertIn("solo el núcleo", claude)
        self.assertNotIn("## Revisión:", claude)

    def test_segunda_vez_no_crea_nada(self):
        arnes.preparar(self.proyecto, ["software"], "x", "y")
        informe = arnes.preparar(self.proyecto, ["software"], "x", "y")
        self.assertEqual(informe["creados"], [])
        self.assertEqual(informe["faltan"], [])

    def test_campos_de_firmware_solo_con_firmware(self):
        arnes.preparar(self.proyecto, ["firmware"], "x", "y")
        with open(os.path.join(self.proyecto, "CLAUDE.md"), encoding="utf-8") as f:
            claude = f.read()
        for texto in ("### Comandos de firmware", "Grabar (solo con OK)", "Presupuesto: flash",
                      "### Reglas para los agentes", "**Simplificador:**"):
            self.assertIn(texto, claude)
        otro = tempfile.mkdtemp()
        try:
            arnes.preparar(otro, ["software"], "x", "y")
            with open(os.path.join(otro, "CLAUDE.md"), encoding="utf-8") as f:
                self.assertNotIn("Comandos de firmware", f.read())
        finally:
            shutil.rmtree(otro)

    def test_todas_las_capas_tienen_seccion(self):
        for capa in DISPONIBLES:
            with self.subTest(capa=capa):
                self.assertTrue(arnes.seccion(capa).startswith("## Revisión: "))


class PruebasMarketplace(unittest.TestCase):
    def test_registrado(self):
        with tempfile.TemporaryDirectory() as tmp:
            conocidos = os.path.join(tmp, "known.json")
            with open(conocidos, "w", encoding="utf-8") as f:
                json.dump({"claude-code-harness": {"installLocation": REPO}}, f)
            self.assertEqual(arnes.raiz_marketplace(conocidos), REPO)

    def test_sin_registro_usa_el_repo_del_skill(self):
        self.assertEqual(arnes.raiz_marketplace("/no/existe.json"), REPO)

    def test_capas_del_repo_real(self):
        capas = arnes.capas_disponibles(REPO)
        self.assertNotIn("arnes", capas)
        self.assertEqual(list(capas), ["firmware", "hardware", "software", "ia", "sistema"])

    def test_marketplace_local(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = os.path.join(tmp, "k.json")
            for fuente, esperado in [({"source": "directory", "path": "/x"}, True),
                                     ({"source": "github", "repo": "a/b"}, False), (None, False)]:
                with open(ruta, "w", encoding="utf-8") as f:
                    json.dump({"claude-code-harness": {"source": fuente}}, f)
                self.assertEqual(arnes.marketplace_local(ruta), esperado)
            self.assertFalse(arnes.marketplace_local(os.path.join(tmp, "no.json")))


class PruebasCLI(Base):
    def correr(self, *args):
        salida, errores = io.StringIO(), io.StringIO()
        with redirect_stdout(salida), redirect_stderr(errores), \
                mock.patch.object(arnes, "raiz_marketplace", return_value=REPO):
            codigo = arnes.main(["--proyecto", self.proyecto, *args])
        return codigo, salida.getvalue(), errores.getvalue()

    def test_flujo_completo(self):
        codigo, salida, _ = self.correr("estado")
        self.assertEqual(codigo, 0)
        self.assertIn("Capas activas en este proyecto: ninguna", salida)
        self.assertIn("Faltan en el proyecto", salida)
        codigo, salida, _ = self.correr("aplicar", "firmware", "software")
        self.assertEqual(codigo, 0)
        self.assertIn("firmware, software", salida)
        codigo, salida, _ = self.correr("preparar", "firmware", "software", "--nombre", "demo")
        self.assertIn("Creado: CLAUDE.md", salida)
        codigo, salida, _ = self.correr("estado")
        self.assertIn("● firmware", salida)
        self.assertIn("○ hardware", salida)
        self.assertNotIn("Faltan en el proyecto", salida)

    def test_error_sin_traceback(self):
        codigo, _, errores = self.correr("aplicar", "fpga")
        self.assertEqual(codigo, 1)
        self.assertIn("capas desconocidas", errores)
        self.assertNotIn("Traceback", errores)

    def test_sin_cambio(self):
        self.correr("aplicar", "ia")
        codigo, salida, _ = self.correr("aplicar", "ia")
        self.assertEqual(codigo, 0)
        self.assertIn("Sin cambios", salida)
        self.assertNotIn("conversación nueva", salida)

    def test_seccion_invalida(self):
        for capa in ("ninguna", "sistema_x"):
            with self.subTest(capa=capa):
                codigo, _, errores = self.correr("seccion", capa)
                self.assertEqual(codigo, 1)
                self.assertNotIn("Traceback", errores)
        codigo, salida, _ = self.correr("seccion", "Hardware")
        self.assertEqual(codigo, 0)

    def test_aviso_si_el_marketplace_no_es_local(self):
        self.correr("aplicar", "ia")
        with mock.patch.object(arnes, "marketplace_local", return_value=False):
            _, salida, _ = self.correr("estado")
        self.assertIn("claude plugin install", salida)
        with mock.patch.object(arnes, "marketplace_local", return_value=True):
            _, salida, _ = self.correr("estado")
        self.assertNotIn("claude plugin install", salida)

    def test_seccion(self):
        codigo, salida, _ = self.correr("seccion", "hardware")
        self.assertEqual(codigo, 0)
        self.assertTrue(salida.startswith("## Revisión: hardware"))

    def test_sin_marketplace(self):
        salida, errores = io.StringIO(), io.StringIO()
        with redirect_stdout(salida), redirect_stderr(errores), \
                mock.patch.object(arnes, "raiz_marketplace", return_value=None):
            self.assertEqual(arnes.main(["--proyecto", self.proyecto, "estado"]), 0)
            self.assertEqual(arnes.main(["--proyecto", self.proyecto, "aplicar", "ia"]), 1)
        self.assertIn("no está registrado", salida.getvalue())



class PruebasCarpetasProhibidas(unittest.TestCase):
    def test_home_raiz_y_repo(self):
        with tempfile.TemporaryDirectory() as home, mock.patch.dict(os.environ, {"HOME": home}):
            for carpeta in (home, os.sep):
                with self.subTest(carpeta=carpeta), self.assertRaises(arnes.ErrorArnes):
                    arnes.comprobar_proyecto(carpeta, REPO)
            with self.assertRaises(arnes.ErrorArnes):
                arnes.comprobar_proyecto(REPO, REPO)
            proyecto = os.path.join(home, "proyectos", "sensor")
            os.makedirs(proyecto)
            arnes.comprobar_proyecto(proyecto, REPO)  # una carpeta normal sí se acepta

    def test_settings_enlazado_al_de_usuario(self):
        with tempfile.TemporaryDirectory() as home, mock.patch.dict(os.environ, {"HOME": home}):
            os.makedirs(os.path.join(home, ".claude"))
            usuario = os.path.join(home, ".claude", "settings.json")
            with open(usuario, "w", encoding="utf-8") as f:
                f.write("{}")
            proyecto = os.path.join(home, "p")
            os.makedirs(os.path.join(proyecto, ".claude"))
            os.symlink(usuario, os.path.join(proyecto, ".claude", "settings.json"))
            with self.assertRaises(arnes.ErrorArnes):
                arnes.comprobar_proyecto(proyecto, REPO)

    def test_cli_en_home_no_toca_nada(self):
        with tempfile.TemporaryDirectory() as home, mock.patch.dict(os.environ, {"HOME": home}), \
                mock.patch.object(arnes, "raiz_marketplace", return_value=REPO), \
                redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()) as errores:
            for orden in (["estado"], ["aplicar", "sistema"], ["preparar", "ia"]):
                self.assertEqual(arnes.main(["--proyecto", home, *orden]), 1)
            self.assertEqual(os.listdir(home), [])
        self.assertIn("carpeta personal", errores.getvalue())


if __name__ == "__main__":
    unittest.main()
