"""Pruebas del hook proteger_hardware.

Ejecutar desde la raíz del repo:  python3 -m unittest discover -s hooks -v
"""

import json
import os
import shlex
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from proteger_hardware import ASK, DENY, evaluar  # noqa: E402

def _anidar(comando: str, niveles: int) -> str:
    for _ in range(niveles):
        comando = "bash -c " + shlex.quote(comando)
    return comando


# Pasado el límite de profundidad se pide confirmación, aunque el fondo sea inofensivo.
ANIDADO_PROFUNDO = _anidar("ls", 7)

SCRIPT = os.path.join(os.path.dirname(__file__), "proteger_hardware.py")

BLOQUEAR = [
    "espefuse.py --port /dev/ttyUSB0 burn_efuse JTAG_DISABLE",
    "espefuse burn-key BLOCK_KEY0 clave.bin XTS_AES_128_KEY",
    "python3 -m espefuse write_protect_efuse MAC",
    "idf.py efuse-burn --do-not-confirm",
    "idf.py -p /dev/ttyACM0 efuse-read-protect BLOCK_KEY0",
    "avrdude -c usbasp -p m328p -U lfuse:w:0xFF:m",
    "avrdude -p t85 -Uhfuse:w:0xDF:m",
    "avrdude -c usbasp -p m328p -U lock:w:0x0F:m",
    "STM32_Programmer_CLI -c port=SWD -ob RDP=0xBB",
    "st-flash --area=option write 0xfffff8aa",
    'openocd -f interface/stlink.cfg -f target/stm32f1x.cfg -c "init; stm32f1x lock 0; exit"',
    "nrfjprog --rbp ALL",
    "nrfutil device protection-set All",
    "pio run -t fuses",
    "platformio run --target bootloader",
    "picotool otp set 0x48 0x1",
    "arduino-cli burn-bootloader -b arduino:avr:uno -P usbasp",
    "bossac -p ttyACM0 -s",
    "stm32flash -j /dev/ttyUSB0",
    "sudo -E espefuse.py burn_bit BLOCK3 0",
    "cd build && espefuse.py burn_efuse FLASH_CRYPT_CNT",
    "bash -c 'avrdude -U efuse:w:0xFD:m'",
    'eval "espefuse.py burn_efuse X"',
    "true;(espefuse.py burn_efuse X)",
    "true;&espefuse.py burn_efuse X",
    # Hallazgos del revisor: palabras clave, envoltorios con valor y shells.
    "if true; then espefuse.py burn_efuse X; fi",
    "{ espefuse.py burn_efuse X; }",
    "timeout 30 espefuse.py burn_efuse X",
    "nice -n 10 espefuse.py burn_efuse X",
    "sudo -u root espefuse.py burn_efuse X",
    "xargs -n 1 espefuse.py burn_efuse",
    "docker run --rm -v $PWD:/p espressif/idf espefuse.py burn_efuse X",
    'ssh pi@placa "espefuse.py burn_efuse X"',
    'bash -lc "espefuse.py burn_efuse X"',
    'echo "$(espefuse.py burn_efuse X)"',
    "python3 $IDF_PATH/components/esptool_py/esptool/espefuse.py burn_efuse X",
    "python3 -I -m espefuse burn_efuse X",
    "pio pkg exec -- espefuse.py burn_efuse X",
    # Operaciones irreversibles que antes quedaban en ask o sin aviso.
    "openocd -f target/stm32l4x.cfg -c 'init; stm32l4x option_write 0 0x20 0xBB 0xFF; exit'",
    "st-flash --area=otp write otp.bin",
    "st-flash --area optcr write 0x0FFFAAED",
    "avrdude -c serialupdi -p t1614 -U syscfg0:w:0xC0:m",
    'avrdude -c usbasp -p m328p -T "write lfuse 0 0xFF"',
    "make fuses",
    "make burn-fuses",
    "make lockbits",
    "cmake --build build --target burn_fuses",
    "STM32_Programmer_CLI -c port=SWD -lockRDP2",
    "STM32_Programmer_CLI -c port=SWD -optionbytes RDP=0xBB",
    "flashrom -p ch341a_spi --wp-enable",
    "dfu-programmer atmega32u4 setsecure",
    "minipro -p ATMEGA328P -c config -w fuses.cfg",
    "pymcuprog write -m fuses -o 5 -l 0xC0",
    "blhost -p /dev/ttyACM0 efuse-program-once 0x2d 0x1",
    "commander device lock --debug enable",
    "fastboot flashing lock",
    # Segunda revisión: programas que ejecutan comandos.
    "git bisect run espefuse.py burn_efuse X 1",
    "git rebase -x 'espefuse.py burn_efuse X 1' main",
    "git submodule foreach make fuses",
    "git -c alias.x='!espefuse.py burn_efuse X 1' x",
    "bash <<EOF\nespefuse.py burn_efuse X\nEOF",
    "ssh pi@placa <<'EOF'\nespefuse.py burn_efuse X\nEOF",
    'git commit -m "bloquea `espefuse.py burn_efuse X`"',
    "blhost -p /dev/ttyACM0 flash-program-once 0x0 4 0x1",
    "avrdude -c usbasp -p m328p -T 'w fuse5 0xc9'",
    "avrdude -c usbasp -p m328p -T 'erase; write lfuse 0 0xff'",
]

PEDIR = [
    "idf.py -p /dev/ttyUSB0 flash monitor",
    "idf.py erase-flash",
    "idf.py app-flash",
    "esptool.py --chip esp32 write_flash 0x1000 bootloader.bin",
    "esptool erase-flash",
    "python -m esptool erase_region 0x9000 0x6000",
    "pio run -t upload",
    "pio run -e esp32dev --target=upload",
    "platformio run -tuploadfs",
    "west flash",
    "st-flash write firmware.bin 0x8000000",
    "STM32_Programmer_CLI -c port=SWD -w firmware.elf -v -rst",
    "STM32_Programmer_CLI -c port=SWD -e all",
    'openocd -f board/stm32f4discovery.cfg -c "program fw.elf verify reset exit"',
    "pyocd flash -t nrf52840 build/zephyr.hex",
    "probe-rs download --chip RP2040 target/firmware",
    "cargo flash --chip nRF52840_xxAA --release",
    "cargo embed",
    "nrfjprog --program zephyr.hex --chiperase --verify",
    "nrfutil device program --firmware app.zip",
    "avrdude -c arduino -p m328p -P /dev/ttyUSB0 -U flash:w:main.hex:i",
    "dfu-util -a 0 -D firmware.bin",
    "picotool load firmware.uf2",
    "arduino-cli upload -p /dev/ttyACM0 -b arduino:avr:uno",
    "arduino-cli compile --upload -b esp32:esp32:esp32",
    "bossac -p ttyACM0 -e -w -v -b firmware.bin",
    "stm32flash -w firmware.bin -v /dev/ttyUSB0",
    "flashrom -p ch341a_spi -w bios.bin",
    "teensy_loader_cli --mcu=TEENSY40 -w firmware.hex",
    "make flash",
    "make -C firmware upload",
    "ninja -C build flash",
    "cmake --build build --target flash",
    "cp build/firmware.uf2 /media/victus/RPI-RP2/",
    "sudo dd if=raspios.img of=/dev/sdb bs=4M",
    "make && make flash",
    "MAKEFLAGS=-j4 make program",
    "echo `esptool.py erase_flash`",
    "ls *.bin | xargs esptool.py write_flash 0x0",
    "ls&&(idf.py flash)",
    "cmake --build build --target=flash",
    "STM32_Programmer_CLI -c port=SWD -w32 0x08000000 0x1",
    "for p in /dev/ttyUSB0 /dev/ttyUSB1; do esptool.py -p $p write_flash 0 fw.bin; done",
    "while true; do idf.py flash; done",
    "sudo -E -u root idf.py flash",
    "xargs -I {} esptool.py -p {} write_flash 0 fw.bin",
    "bash -c -- 'idf.py flash'",
    "STM32_Programmer_CLI -c port=SWD -rdu",
    "openocd -f target/stm32f1x.cfg -c 'init; stm32f1x unlock 0; exit'",
    "openocd -f board/esp32-wrover-kit-3.3v.cfg -c 'program_esp fw.bin 0x10000 verify exit'",
    "nrfjprog --eraseuicr",
    "nrfutil dfu usb-serial -pkg app.zip -p /dev/ttyACM0",
    "avrdude -c arduino -p m328p -U main.hex",
    "dfu-programmer atmega32u4 configure HSB 0x9B",
    "pio test -e esp32dev",
    "cargo +nightly flash --chip RP2040",
    "espflash flash target/firmware",
    "cargo espflash flash --monitor",
    "cp -t /media/victus/RPI-RP2 fw.uf2",
    "cat fw.uf2 > /media/victus/RPI-RP2/fw.uf2",
    "cp build/fw.bin /media/victus/NODE_F411RE/",
    "pymcuprog write -f app.hex",
    "commander flash app.s37",
    "fastboot flash boot boot.img",
    "bmaptool copy imagen.wic /dev/sdb",
    "sudo mkfs.ext4 /dev/sdb1",
    "JFlashExe -openprjx.jflash -auto -exit",
    "openFPGALoader -b arty bitstream.bit",
    "git bisect run make flash",
    "make lock",
    "cat raspios.img > /dev/sdb",
    "dd if=fw.uf2 of=/media/victus/RPI-RP2/fw.uf2",
    "sed 's/x/espefuse burn_efuse X/e' f",  # ASK a propósito: ver _EJECUTORES
    """awk 'BEGIN{system("espefuse.py burn_efuse X 1")}'""",
    ANIDADO_PROFUNDO,
    "curl -d 'make fuses' https://ejemplo.invalid",
    "python3 -c \"print('make lock')\"",
]

PERMITIR = [
    "ls -la",
    "git status",
    "grep -rn flash src/",
    "idf.py build",
    "idf.py menuconfig",
    "espefuse.py summary",
    "espefuse.py dump",
    "esptool.py chip_id",
    "esptool read_flash 0 0x400000 respaldo.bin",
    "pio run",
    "pio test -e native",
    "west build -b nrf52840dk_nrf52840",
    "STM32_Programmer_CLI -c port=SWD -ob displ",
    "openocd -f interface/stlink.cfg -f target/stm32f4x.cfg",
    "avrdude -c usbasp -p m328p -U lfuse:r:-:h",
    "make",
    "make test",
    "cmake --build build",
    "cargo build --release",
    "cargo run",
    "cp build/firmware.uf2 artefactos/",
    "mv viejo.uf2 nuevo.uf2",
    "dd if=/dev/zero of=imagen.bin bs=1M count=4",
    "echo 'idf.py flash'",
    "picotool info -a",
    "nrfjprog --readcode respaldo.hex",
    "python3 -m pytest",
    "pyocd list",
    # Falsos positivos que señaló el revisor.
    "dd if=/dev/zero of=/dev/null bs=1M count=10",
    "idf.py -B build-flash build",
    "idf.py -C ~/proyectos/myflash build",
    "STM32_Programmer_CLI -c port=SWD -el ext.stldr -r32 0x90000000 0x100",
    'openocd -f "/home/u/Program Files/x.cfg"',
    'git commit -m "make flash y espefuse burn_efuse"',
    "pip install esptool",
    "sudo apt install avrdude openocd",
    "pio test -e native",
    "pio test --without-uploading",
    "cat README.md",
    "timeout 5 ls",
    "cd firmware && ls",
    # Segunda revisión: commits y documentación que mencionan comandos peligrosos.
    "git commit -m 'A-01: bloquea `espefuse burn_efuse` y `make fuses`'",
    "git commit -m \"$(cat <<'EOF'\nA-01: bloquea make lock y espefuse burn_efuse\n\nCo-Authored-By: x\nEOF\n)\"",
    "git commit -F- <<'EOF'\nespefuse burn_efuse y make fuses\nEOF",
    "cat > notas.md <<'EOF'\nespefuse.py burn_efuse X\nmake fuses\nEOF",
    "gh pr create --title A-01 --body 'bloquea make fuses y espefuse burn_efuse'",
    "st-flash --area=option read",
    "git log --oneline -5",
    "sed -i 's/make fuses/make fusibles/' doc.md",
    _anidar("ls", 3),
]


class PruebasEvaluar(unittest.TestCase):
    def test_bloquea_lo_irreversible(self):
        for comando in BLOQUEAR:
            with self.subTest(comando=comando):
                self.assertEqual(evaluar(comando)[0], DENY)

    def test_pide_confirmacion_al_grabar_o_borrar(self):
        for comando in PEDIR:
            with self.subTest(comando=comando):
                self.assertEqual(evaluar(comando)[0], ASK)

    def test_deja_pasar_lo_inofensivo(self):
        for comando in PERMITIR:
            with self.subTest(comando=comando):
                self.assertIsNone(evaluar(comando)[0])

    def test_gana_lo_mas_grave(self):
        self.assertEqual(evaluar("idf.py flash && espefuse.py burn_efuse X")[0], DENY)

    def test_comillas_sin_cerrar_no_rompen(self):
        self.assertEqual(evaluar("idf.py flash 'sin cerrar")[0], ASK)


class PruebasScript(unittest.TestCase):
    """Ejecuta el script como lo haría Claude Code: JSON por stdin."""

    def correr(self, entrada: str):
        return subprocess.run(
            [sys.executable, SCRIPT], input=entrada, capture_output=True, text=True, timeout=10
        )

    def decision(self, comando: str):
        r = self.correr(json.dumps({"tool_name": "Bash", "tool_input": {"command": comando}}))
        self.assertEqual(r.returncode, 0, r.stderr)
        if not r.stdout.strip():
            return None
        return json.loads(r.stdout)["hookSpecificOutput"]

    def test_salida_deny(self):
        salida = self.decision("espefuse.py burn_efuse X")
        self.assertEqual(salida["hookEventName"], "PreToolUse")
        self.assertEqual(salida["permissionDecision"], "deny")
        self.assertIn("a mano", salida["permissionDecisionReason"])

    def test_salida_ask(self):
        self.assertEqual(self.decision("west flash")["permissionDecision"], "ask")

    def test_sin_salida_si_es_inofensivo(self):
        self.assertIsNone(self.decision("ls"))

    def test_ignora_otras_herramientas(self):
        r = self.correr(json.dumps({"tool_name": "Read", "tool_input": {"file_path": "x"}}))
        self.assertEqual((r.returncode, r.stdout), (0, ""))

    def test_entrada_invalida_no_bloquea(self):
        for entrada in ["esto no es json", "[1, 2]", '"texto"', "null",
                        '{"tool_name": "Bash", "tool_input": null}',
                        '{"tool_name": "Bash", "tool_input": {"command": 5}}']:
            with self.subTest(entrada=entrada):
                r = self.correr(entrada)
                self.assertEqual((r.returncode, r.stdout), (0, ""), r.stderr)


if __name__ == "__main__":
    unittest.main()
