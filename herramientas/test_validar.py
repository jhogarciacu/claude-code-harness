"""Pruebas del validador.  Ejecutar: python3 -m unittest discover -s herramientas"""

import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from validar import validar  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def escribir(raiz, relativa, contenido):
    ruta = os.path.join(raiz, relativa)
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(contenido if isinstance(contenido, str) else json.dumps(contenido))


def repo_minimo(raiz, plugins=("nucleo",), extra_manifiesto=None):
    escribir(raiz, ".claude-plugin/marketplace.json", {
        "name": "m", "owner": {"name": "x"},
        "plugins": [{"name": p, "source": f"./plugins/{p}"} for p in plugins],
    })
    for p in plugins:
        manifiesto = {"name": p, "version": "0.1.0", **(extra_manifiesto or {}).get(p, {})}
        escribir(raiz, f"plugins/{p}/.claude-plugin/plugin.json", manifiesto)


class PruebasValidar(unittest.TestCase):
    def setUp(self):
        self.raiz = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.raiz)

    def test_el_repo_real_es_valido(self):
        self.assertEqual(validar(REPO), [])

    def test_repo_minimo_valido(self):
        repo_minimo(self.raiz)
        self.assertEqual(validar(self.raiz), [])

    def test_sin_marketplace(self):
        self.assertTrue(any("no existe" in e for e in validar(self.raiz)))

    def test_source_con_puntos_o_absoluto(self):
        for source in ["../fuera", "/abs/ruta", "plugins/x", "./a/../b"]:
            with self.subTest(source=source):
                escribir(self.raiz, ".claude-plugin/marketplace.json",
                         {"name": "m", "owner": {}, "plugins": [{"name": "x", "source": source}]})
                self.assertTrue(any("ruta de este repo" in e for e in validar(self.raiz)))

    def test_carpeta_inexistente(self):
        escribir(self.raiz, ".claude-plugin/marketplace.json",
                 {"name": "m", "owner": {}, "plugins": [{"name": "x", "source": "./plugins/x"}]})
        self.assertTrue(any("no existe" in e for e in validar(self.raiz)))

    def test_nombre_distinto(self):
        repo_minimo(self.raiz)
        escribir(self.raiz, "plugins/nucleo/.claude-plugin/plugin.json", {"name": "otro", "version": "1.0.0"})
        self.assertTrue(any("se llama" in e for e in validar(self.raiz)))

    def test_sin_version(self):
        repo_minimo(self.raiz)
        escribir(self.raiz, "plugins/nucleo/.claude-plugin/plugin.json", {"name": "nucleo"})
        self.assertTrue(any("versión" in e for e in validar(self.raiz)))

    def test_dependencias(self):
        repo_minimo(self.raiz, ("nucleo", "firmware"), {"firmware": {"dependencies": ["nucleo"]}})
        self.assertEqual(validar(self.raiz), [])
        repo_minimo(self.raiz, ("nucleo", "sistema"), {"sistema": {"dependencies": ["nucleo", "fantasma@m"]}})
        self.assertTrue(any("fantasma" in e for e in validar(self.raiz)))

    def test_claude_md_en_plugin(self):
        repo_minimo(self.raiz)
        escribir(self.raiz, "plugins/nucleo/CLAUDE.md", "# reglas")
        self.assertTrue(any("CLAUDE.md" in e for e in validar(self.raiz)))

    def test_hook_con_archivo_inexistente(self):
        repo_minimo(self.raiz)
        escribir(self.raiz, "plugins/nucleo/hooks/hooks.json", {"hooks": {"SessionStart": [{"hooks": [
            {"type": "command", "command": 'python3 "${CLAUDE_PLUGIN_ROOT}/hooks/falta.py"'}]}]}})
        self.assertTrue(any("falta.py" in e for e in validar(self.raiz)))

    def test_hooks_sin_envoltorio(self):
        repo_minimo(self.raiz)
        escribir(self.raiz, "plugins/nucleo/hooks/hooks.json", {"SessionStart": []})
        self.assertTrue(any("`hooks`" in e for e in validar(self.raiz)))

    def test_entradas_mal_formadas_no_revientan(self):
        casos = [
            ("marketplace como lista", ".claude-plugin/marketplace.json", []),
            ("plugins como objeto", ".claude-plugin/marketplace.json", {"name": "m", "owner": {}, "plugins": {}}),
            ("plugin que no es objeto", ".claude-plugin/marketplace.json", {"name": "m", "owner": {}, "plugins": ["x"]}),
        ]
        for nombre, ruta, contenido in casos:
            with self.subTest(caso=nombre):
                escribir(self.raiz, ruta, contenido)
                self.assertTrue(validar(self.raiz))
        repo_minimo(self.raiz)
        escribir(self.raiz, "plugins/nucleo/.claude-plugin/plugin.json", [])
        self.assertTrue(any("objeto" in e for e in validar(self.raiz)))
        repo_minimo(self.raiz)
        for hooks in [{"hooks": {"X": {}}}, {"hooks": {"X": [{"hooks": None}]}},
                      {"hooks": {"X": [{"hooks": [{"command": ["lista"]}, "texto"]}]}}]:
            with self.subTest(hooks=hooks):
                escribir(self.raiz, "plugins/nucleo/hooks/hooks.json", hooks)
                validar(self.raiz)  # no debe lanzar excepción

    def test_rutas_con_comillas_o_sin_llaves(self):
        repo_minimo(self.raiz)
        for comando in ['"${CLAUDE_PLUGIN_ROOT}"/hooks/falta.sh', "$CLAUDE_PLUGIN_ROOT/hooks/falta.sh",
                        "${CLAUDE_PLUGIN_ROOT}/hooks/falta.sh;echo"]:
            with self.subTest(comando=comando):
                escribir(self.raiz, "plugins/nucleo/hooks/hooks.json",
                         {"hooks": {"S": [{"hooks": [{"type": "command", "command": comando}]}]}})
                self.assertIn("`hooks/falta.sh`", " ".join(validar(self.raiz)))

    def test_plugin_sin_registrar(self):
        repo_minimo(self.raiz)
        escribir(self.raiz, "plugins/huerfano/.claude-plugin/plugin.json", {"name": "huerfano", "version": "0.1.0"})
        self.assertTrue(any("huerfano" in e and "registrado" in e for e in validar(self.raiz)))

    def test_dependencia_de_otro_marketplace(self):
        for dep in ["nucleo@otro", {"name": "nucleo", "marketplace": "otro"}]:
            with self.subTest(dep=dep):
                repo_minimo(self.raiz, ("nucleo", "firmware"), {"firmware": {"dependencies": [dep]}})
                self.assertTrue(any("otro marketplace" in e for e in validar(self.raiz)))
        repo_minimo(self.raiz, ("nucleo", "firmware"),
                    {"firmware": {"dependencies": ["nucleo@m", {"name": "nucleo", "marketplace": "m"}]}})
        self.assertEqual(validar(self.raiz), [])

    def test_version_con_sufijo(self):
        repo_minimo(self.raiz)
        escribir(self.raiz, "plugins/nucleo/.claude-plugin/plugin.json", {"name": "nucleo", "version": "1.0.0-beta.1"})
        self.assertEqual(validar(self.raiz), [])

    def test_reglas_demasiado_largas(self):
        repo_minimo(self.raiz)
        escribir(self.raiz, "plugins/nucleo/reglas.md", "x" * 9001)
        self.assertTrue(any("reglas.md" in e for e in validar(self.raiz)))
        escribir(self.raiz, "plugins/nucleo/reglas.md", "x" * 9000)
        self.assertEqual(validar(self.raiz), [])

    def test_copias_de_anunciar(self):
        repo_minimo(self.raiz, ("nucleo", "firmware"))
        escribir(self.raiz, "plugins/nucleo/hooks/anunciar.py", "print('a')\n")
        escribir(self.raiz, "plugins/firmware/hooks/anunciar.py", "print('a')\n")
        self.assertEqual(validar(self.raiz), [])
        escribir(self.raiz, "plugins/firmware/hooks/anunciar.py", "print('b')\n")
        self.assertTrue(any("difiere" in e for e in validar(self.raiz)))


if __name__ == "__main__":
    unittest.main()
