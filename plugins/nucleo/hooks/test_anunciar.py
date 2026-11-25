"""Pruebas del hook anunciar.  Ejecutar: python3 -m unittest discover -s plugins/nucleo/hooks"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from anunciar import construir  # noqa: E402

SCRIPT = os.path.join(os.path.dirname(__file__), "anunciar.py")


def plugin_falso(raiz: str, manifiesto, reglas: str | None = None) -> None:
    os.makedirs(os.path.join(raiz, ".claude-plugin"))
    with open(os.path.join(raiz, ".claude-plugin", "plugin.json"), "w", encoding="utf-8") as f:
        f.write(manifiesto if isinstance(manifiesto, str) else json.dumps(manifiesto))
    if reglas is not None:
        with open(os.path.join(raiz, "reglas.md"), "w", encoding="utf-8") as f:
            f.write(reglas)


class PruebasConstruir(unittest.TestCase):
    def test_sin_reglas_solo_anuncia(self):
        with tempfile.TemporaryDirectory() as raiz:
            plugin_falso(raiz, {"name": "nucleo", "version": "0.3.0"})
            salida = construir(raiz)
        self.assertEqual(salida["systemMessage"], "Arnés activo: nucleo 0.3.0")
        self.assertEqual(salida["hookSpecificOutput"]["hookEventName"], "SessionStart")
        self.assertNotIn("Reglas", salida["hookSpecificOutput"]["additionalContext"])

    def test_con_reglas_las_inyecta(self):
        with tempfile.TemporaryDirectory() as raiz:
            plugin_falso(raiz, {"name": "firmware", "version": "0.1.0"}, "- No grabar sin OK.\n")
            contexto = construir(raiz)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Arnés activo: firmware 0.1.0", contexto)
        self.assertIn("- No grabar sin OK.", contexto)

    def test_reglas_vacias_no_agregan_seccion(self):
        with tempfile.TemporaryDirectory() as raiz:
            plugin_falso(raiz, {"name": "ia", "version": "0.1.0"}, "  \n")
            self.assertNotIn("Reglas", construir(raiz)["hookSpecificOutput"]["additionalContext"])

    def test_reglas_no_utf8_anuncia_sin_reglas(self):
        with tempfile.TemporaryDirectory() as raiz:
            plugin_falso(raiz, {"name": "firmware", "version": "0.1.0"})
            with open(os.path.join(raiz, "reglas.md"), "wb") as f:
                f.write(b"\xe1\xff reglas")
            salida = construir(raiz)
        self.assertEqual(salida["systemMessage"], "Arnés activo: firmware 0.1.0")

    def test_manifiesto_roto_no_anuncia(self):
        for manifiesto in ["no es json", "[]", json.dumps({"version": "1"})]:
            with self.subTest(manifiesto=manifiesto), tempfile.TemporaryDirectory() as raiz:
                plugin_falso(raiz, manifiesto)
                self.assertIsNone(construir(raiz))

    def test_sin_manifiesto_no_anuncia(self):
        with tempfile.TemporaryDirectory() as raiz:
            self.assertIsNone(construir(raiz))


class PruebasScript(unittest.TestCase):
    def test_anuncia_el_nucleo_real(self):
        r = subprocess.run([sys.executable, SCRIPT], capture_output=True, text=True, timeout=10)
        self.assertEqual(r.returncode, 0, r.stderr)
        salida = json.loads(r.stdout)
        self.assertTrue(salida["systemMessage"].startswith("Arnés activo: nucleo "))


if __name__ == "__main__":
    unittest.main()
