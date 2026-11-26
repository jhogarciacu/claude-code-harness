"""Pruebas del hook proteger_generados.  Ejecutar: python3 -m unittest discover -s plugins/firmware/hooks"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from proteger_generados import evaluar, motivo_por_ruta  # noqa: E402

SCRIPT = os.path.join(os.path.dirname(__file__), "proteger_generados.py")

MAIN_CUBEMX = """/* Archivo generado por STM32CubeMX */
#include "main.h"
/* USER CODE BEGIN Includes */
#include "sensor.h"
/* USER CODE END Includes */
int main(void)
{
  HAL_Init();
  /* USER CODE BEGIN 2 */
  sensor_init();
  /* USER CODE END 2 */
  while (1) {}
}
"""


class PruebasRuta(unittest.TestCase):
    def test_piden_confirmacion(self):
        for ruta in ["sdkconfig", "/p/firmware/sdkconfig", "placa.ioc", "/p/Core/proto/medida.pb.c",
                     "medida.pb.h", "/p/managed_components/espressif__led/led.c",
                     "/p/Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal.c", "/p/Drivers/CMSIS/Include/core_cm4.h",
                     "/p/build/config/sdkconfig.h", "/p/.pio/build/esp32/x.c", "/p/cmake-build-debug/main.c",
                     "/p/build-nrf/zephyr/include/generated/autoconf.h", "/p/Middlewares/Third_Party/FreeRTOS/x.c",
                     "/p/Middlewares/ST/STM32_USB_Device_Library/y.c", "/p/Core/Startup/startup_stm32f411retx.s",
                     "/p/STM32F411RETX_FLASH.ld", "/p/dependencies.lock", "/p/proto/m.pb-c.c", "/p/proto/m.pb.cc"]:
            with self.subTest(ruta=ruta):
                self.assertIsNotNone(motivo_por_ruta(ruta))

    def test_no_piden_confirmacion(self):
        for ruta in ["sdkconfig.defaults", "/p/main/main.c", "/p/proto/medida.proto", "/p/medida.options",
                     "/p/Kconfig.projbuild", "/p/Core/Src/sensor.c", "/p/Drivers/BSP/mi_placa.c",
                     "/p/src/builder.c", "/p/docs/build.md", "/p/Middlewares/Mio/x.c", "/p/linker/mi.ld"]:
            with self.subTest(ruta=ruta):
                self.assertIsNone(motivo_por_ruta(ruta))


class PruebasRutaRelativa(unittest.TestCase):
    def test_build_fuera_del_proyecto_no_cuenta(self):
        with tempfile.TemporaryDirectory() as tmp:
            proyecto = os.path.join(tmp, "build", "proy")
            os.makedirs(os.path.join(proyecto, "Core", "Src"))
            app = os.path.join(proyecto, "Core", "Src", "app.c")
            self.assertIsNone(motivo_por_ruta(app, proyecto))
            self.assertIsNotNone(motivo_por_ruta(os.path.join(proyecto, "build", "x.c"), proyecto))

    def test_symlink_a_generado(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "build"))
            real = os.path.join(tmp, "build", "sdk.h")
            open(real, "w").close()
            enlace = os.path.join(tmp, "gen.h")
            os.symlink(real, enlace)
            self.assertIsNotNone(motivo_por_ruta(enlace, tmp))


class PruebasCubeMX(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.main = os.path.join(self.tmp.name, "main.c")
        with open(self.main, "w", encoding="utf-8") as f:
            f.write(MAIN_CUBEMX)

    def tearDown(self):
        self.tmp.cleanup()

    def edit(self, viejo):
        return evaluar("Edit", {"file_path": self.main, "old_string": viejo, "new_string": "x"})

    def test_dentro_de_user_code_no_pregunta(self):
        self.assertIsNone(self.edit("  sensor_init();\n"))
        self.assertIsNone(self.edit('#include "sensor.h"'))

    def test_fuera_de_user_code_pregunta(self):
        self.assertIsNotNone(self.edit("  HAL_Init();"))
        self.assertIsNotNone(self.edit('#include "main.h"'))

    def test_que_cruza_el_limite_pregunta(self):
        self.assertIsNotNone(self.edit("  sensor_init();\n  /* USER CODE END 2 */"))

    def test_bloque_vacio_anclado_en_el_marcador(self):
        marca = "/* USER CODE BEGIN 2 */"
        self.assertIsNone(evaluar("Edit", {"file_path": self.main, "old_string": marca,
                                           "new_string": marca + "\n  otra();"}))

    def test_cambiar_el_marcador_pregunta(self):
        self.assertIsNotNone(evaluar("Edit", {"file_path": self.main, "old_string": "/* USER CODE BEGIN 2 */",
                                              "new_string": "/* nada */"}))

    def test_replace_all_dentro_y_fuera(self):
        with open(self.main, "w", encoding="utf-8") as f:
            f.write("/* USER CODE BEGIN 1 */\n  foo();\n/* USER CODE END 1 */\nvoid g(void) {\n  foo();\n}\n")
        edicion = {"file_path": self.main, "old_string": "  foo();", "new_string": "  bar();"}
        self.assertIsNone(evaluar("Edit", edicion))  # solo la primera, que está dentro
        self.assertIsNotNone(evaluar("Edit", {**edicion, "replace_all": True}))

    def test_bloque_sin_cerrar_no_deja_editar_lo_generado(self):
        with open(self.main, "w", encoding="utf-8") as f:
            f.write("/* USER CODE BEGIN A */\nx();\n  HAL_Init();\n/* USER CODE BEGIN B */\ny();\n/* USER CODE END B */\n")
        self.assertIsNotNone(evaluar("Edit", {"file_path": self.main, "old_string": "  HAL_Init();",
                                              "new_string": "  otra();"}))

    def test_multiedit_encadenado(self):
        # La segunda edición solo existe después de la primera: se evalúa sobre el texto ya editado.
        uno = {"old_string": "  sensor_init();", "new_string": "  sensor_init();\n  extra();"}
        dentro = {"old_string": "  extra();", "new_string": "  extra(1);"}
        fuera = {"old_string": "  HAL_Init();", "new_string": "  HAL_Init();\n  extra();"}
        self.assertIsNone(evaluar("MultiEdit", {"file_path": self.main, "edits": [uno, dentro]}))
        self.assertIsNotNone(evaluar("MultiEdit", {"file_path": self.main, "edits": [uno, fuera]}))

    def test_write_solo_cambia_bloques(self):
        nuevo = MAIN_CUBEMX.replace("  sensor_init();", "  sensor_init();\n  otra();")
        self.assertIsNone(evaluar("Write", {"file_path": self.main, "content": nuevo}))

    def test_write_pregunta(self):
        self.assertIsNotNone(evaluar("Write", {"file_path": self.main, "content": "nuevo"}))

    def test_multiedit(self):
        dentro = {"old_string": "  sensor_init();", "new_string": "x"}
        fuera = {"old_string": "  HAL_Init();", "new_string": "x"}
        self.assertIsNone(evaluar("MultiEdit", {"file_path": self.main, "edits": [dentro]}))
        self.assertIsNotNone(evaluar("MultiEdit", {"file_path": self.main, "edits": [dentro, fuera]}))

    def test_archivo_sin_user_code_o_nuevo(self):
        normal = os.path.join(self.tmp.name, "sensor.c")
        with open(normal, "w", encoding="utf-8") as f:
            f.write("int sensor_init(void) { return 0; }\n")
        self.assertIsNone(evaluar("Edit", {"file_path": normal, "old_string": "return 0;", "new_string": "x"}))
        self.assertIsNone(evaluar("Write", {"file_path": os.path.join(self.tmp.name, "nuevo.c"), "content": ""}))

    def test_texto_que_no_existe_no_pregunta(self):
        self.assertIsNone(self.edit("esto no está en el archivo"))


class PruebasEntrada(unittest.TestCase):
    def test_herramientas_y_entradas_raras(self):
        self.assertIsNone(evaluar("Read", {"file_path": "sdkconfig"}))
        self.assertIsNone(evaluar("Bash", {"command": "sed -i s/a/b/ sdkconfig"}))
        self.assertIsNone(evaluar("Edit", None))
        self.assertIsNone(evaluar("Edit", {"file_path": 5}))
        self.assertIsNotNone(evaluar("NotebookEdit", {"notebook_path": "/p/build/x.ipynb"}))

    def correr(self, entrada):
        return subprocess.run([sys.executable, SCRIPT], input=entrada, capture_output=True, text=True, timeout=10)

    def test_salida_ask(self):
        r = self.correr(json.dumps({"tool_name": "Edit", "tool_input": {"file_path": "/p/sdkconfig",
                                                                        "old_string": "a", "new_string": "b"}}))
        self.assertEqual(r.returncode, 0, r.stderr)
        salida = json.loads(r.stdout)["hookSpecificOutput"]
        self.assertEqual(salida["permissionDecision"], "ask")
        self.assertIn("menuconfig", salida["permissionDecisionReason"])

    def test_sin_salida_y_entradas_invalidas(self):
        for entrada in ['{"tool_name": "Edit", "tool_input": {"file_path": "/p/main/app.c"}}',
                        "no es json", "[1]", "null"]:
            with self.subTest(entrada=entrada):
                r = self.correr(entrada)
                self.assertEqual((r.returncode, r.stdout), (0, ""), r.stderr)


if __name__ == "__main__":
    unittest.main()
