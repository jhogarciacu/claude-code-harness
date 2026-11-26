"""Pruebas del hook proteger_kicad.  Ejecutar: python3 -m unittest discover -s plugins/hardware/hooks"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from proteger_kicad import evaluar, motivo  # noqa: E402

SCRIPT = os.path.join(os.path.dirname(__file__), "proteger_kicad.py")


class PruebasRuta(unittest.TestCase):
    def test_piden_confirmacion(self):
        for ruta in ["placa.kicad_sch", "/p/hw/placa.kicad_pcb", "/p/lib/mio.kicad_sym",
                     "/p/lib/mio.pretty/QFN-32.kicad_mod", "/p/placa.kicad_pro", "/p/PLACA.KICAD_PCB",
                     "/p/fab/placa-F_Cu.gbr", "/p/fab/placa-job.gbrjob", "/p/fab/placa.drl", "/p/fab/placa.GTL",
                     "/p/fab/placa.gko", "/p/fab/placa.g4", "/p/fab/placa.GM12", "/p/fab/placa-top.pos", "/p/placa-backups/placa-2026-11-26_120000.zip"]:
            with self.subTest(ruta=ruta):
                self.assertIsNotNone(motivo(ruta))

    def test_no_piden_confirmacion(self):
        for ruta in ["/p/placa.kicad_dru", "/p/fp-lib-table", "/p/sym-lib-table", "/p/Docs/bom.md",
                     "/p/bom.csv", "/p/erc.json", "/p/main/kicad_sch.c", "/p/placa.kicad_sch.md",
                     "/p/backups/notas.md", "/p/scripts/exportar.py", "/p/fab/placa.gx", "/p/fab/placa.g"]:
            with self.subTest(ruta=ruta):
                self.assertIsNone(motivo(ruta))

    def test_symlink_a_un_pcb(self):
        with tempfile.TemporaryDirectory() as tmp:
            real = os.path.join(tmp, "placa.kicad_pcb")
            open(real, "w").close()
            enlace = os.path.join(tmp, "enlace.txt")
            os.symlink(real, enlace)
            self.assertIsNotNone(motivo(enlace))


class PruebasRutaRelativa(unittest.TestCase):
    def test_backups_fuera_del_proyecto_no_cuenta(self):
        with tempfile.TemporaryDirectory() as tmp:
            proyecto = os.path.join(tmp, "viejos-backups", "proy")
            os.makedirs(proyecto)
            self.assertIsNone(motivo(os.path.join(proyecto, "src", "main.c"), proyecto))
            self.assertIsNotNone(motivo(os.path.join(proyecto, "placa-backups", "x.zip"), proyecto))


class PruebasEntrada(unittest.TestCase):
    def test_herramientas_y_entradas_raras(self):
        for herramienta in ("Edit", "Write", "MultiEdit"):
            with self.subTest(herramienta=herramienta):
                self.assertIsNotNone(evaluar(herramienta, {"file_path": "/p/placa.kicad_pcb"}))
        self.assertIsNone(evaluar("Read", {"file_path": "/p/placa.kicad_pcb"}))
        self.assertIsNone(evaluar("Bash", {"command": "sed -i s/a/b/ placa.kicad_pcb"}))
        self.assertIsNone(evaluar("Edit", None))
        self.assertIsNone(evaluar("Edit", {"file_path": 5}))
        self.assertIsNone(evaluar("Edit", {"file_path": ""}))
        self.assertIsNone(evaluar(["Edit"], {"file_path": "/p/placa.kicad_pcb"}))
        self.assertIsNone(evaluar({}, {"file_path": "/p/placa.kicad_pcb"}))
        self.assertIsNone(evaluar("Edit", {"file_path": "/p/pla\x00ca.kicad_pcb"}))

    def correr(self, entrada):
        return subprocess.run([sys.executable, SCRIPT], input=entrada, capture_output=True, text=True, timeout=10)

    def test_cwd_como_base(self):
        with tempfile.TemporaryDirectory() as tmp:
            proyecto = os.path.join(tmp, "x-backups")
            os.makedirs(proyecto)
            entrada = json.dumps({"tool_name": "Edit", "cwd": proyecto,
                                  "tool_input": {"file_path": os.path.join(proyecto, "main.c")}})
            entorno = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
            r = subprocess.run([sys.executable, SCRIPT], input=entrada, capture_output=True, text=True,
                               timeout=10, env=entorno)
            self.assertEqual((r.returncode, r.stdout), (0, ""), r.stderr)

    def test_salida_ask(self):
        r = self.correr(json.dumps({"tool_name": "Edit", "tool_input": {"file_path": "/p/placa.kicad_sch",
                                                                        "old_string": "a", "new_string": "b"}}))
        self.assertEqual(r.returncode, 0, r.stderr)
        salida = json.loads(r.stdout)["hookSpecificOutput"]
        self.assertEqual(salida["hookEventName"], "PreToolUse")
        self.assertEqual(salida["permissionDecision"], "ask")
        self.assertIn("capa hardware", salida["permissionDecisionReason"])
        self.assertIn("placa.kicad_sch", salida["permissionDecisionReason"])

    def test_sin_salida_y_entradas_invalidas(self):
        for entrada in ['{"tool_name": "Edit", "tool_input": {"file_path": "/p/placa.kicad_dru"}}',
                        "no es json", "[1]", "null", "",
                        '{"tool_name": ["Edit"], "tool_input": {}}',
                        '{"tool_name": "Edit", "tool_input": {"file_path": "/p/a\\u0000.kicad_pcb"}}']:
            with self.subTest(entrada=entrada):
                r = self.correr(entrada)
                self.assertEqual((r.returncode, r.stdout), (0, ""), r.stderr)


if __name__ == "__main__":
    unittest.main()
