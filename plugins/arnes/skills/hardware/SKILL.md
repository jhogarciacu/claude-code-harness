---
name: hardware
description: Activa la capa hardware del arnés en el proyecto actual, sin quitar las demás capas activas. Capa hardware: KiCad, ERC/DRC, BOM y límites eléctricos. Úsalo cuando el usuario escriba /arnes:hardware o pida activar la capa hardware del arnés.
---

# /arnes:hardware: activar la capa `hardware`

Responde siempre en español. `ARNES` significa `python3 "<carpeta de este skill>/../capas/arnes.py"`: el script está en la carpeta hermana `capas`. Ejecútalo desde la carpeta raíz del proyecto.

**Todo cambio pasa por `arnes.py`.** No edites a mano `.claude/settings.json`, `CLAUDE.md` ni `.gitignore`. Si `arnes.py` termina con error (`✗`), muestra el mensaje tal cual y **detente**.

1. Ejecuta `ARNES agregar hardware` y muestra el resultado en una línea. Conserva las capas que ya estaban activas.
2. Ejecuta `ARNES estado`. Si dice que faltan `CLAUDE.md`, `Docs` o `.gitignore`, pregunta si se crean desde las plantillas del arnés. Con el OK, pide en una línea el nombre y una descripción corta del proyecto (si no da nombre, omite `--nombre`) y ejecuta `ARNES preparar <capas activas> --nombre "<nombre>" --descripcion "<descripción>"`.
   - Si `preparar` informa líneas "Falta:" (secciones o líneas que les faltan a archivos que ya existían), muéstralas y pregunta si se agregan. Solo con el OK ejecuta `ARNES completar <capas activas>`.
3. Cierre en dos o tres líneas: capas activas ahora, archivos creados si los hay y, si hubo cambio de capas, **"Abre una conversación nueva para que las capas carguen."**

Para quitar capas o elegir varias a la vez, el usuario tiene `/arnes:capas`.
