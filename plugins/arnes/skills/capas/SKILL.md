---
name: capas
description: Menú de capas del arnés. Muestra qué capas (firmware, hardware, software, ia, sistema) están activas en el proyecto actual, deja elegir cuáles activar o quitar, y prepara CLAUDE.md, Docs/ y .gitignore si faltan. Úsalo cuando el usuario escriba /arnes:capas o pida ver, elegir o quitar capas del arnés en este proyecto.
---

# /arnes:capas: capas del arnés en este proyecto

Responde siempre en español. El script `arnes.py` está en la misma carpeta que este archivo (la carpeta base del skill). En los pasos, `ARNES` significa `python3 "<carpeta del skill>/arnes.py"`. Ejecútalo desde la carpeta raíz del proyecto, o pasa `--proyecto <carpeta>`. Las capas van separadas por espacios.

**Todo cambio pasa por `arnes.py`.** No edites a mano `.claude/settings.json`, `CLAUDE.md` ni `.gitignore`. Si `arnes.py` termina con error (`✗`), muestra el mensaje tal cual y **detente**: no intentes arreglarlo por tu cuenta.

## 1. Estado
Ejecuta `ARNES estado` y resume en dos o tres líneas qué capas tiene activas el proyecto y qué le falta (por ejemplo, `CLAUDE.md`). Si imprime un aviso o un comando para la terminal, muéstralo tal cual.

## 2. Qué quiere el usuario
**Si el usuario ya lo dijo al invocar el comando** (por ejemplo `/arnes:capas firmware software`, `/arnes:capas sistema` o `/arnes:capas ninguna`), sáltate los pasos 2 y 3 y ve al paso 4 con eso.

Si no, haz **una** pregunta (AskUserQuestion) de **selección única**, con estas cuatro opciones:
- **Proyecto completo (sistema)**: activa las cinco capas y el contrato entre capas.
- **Elegir capas**: elegir una o varias.
- **Quitar todas las capas**: el proyecto queda solo con el núcleo.
- **Dejarlo como está**.

## 3. Elegir capas (solo si eligió "Elegir capas")
Haz **una** pregunta de **selección múltiple** (`multiSelect: true`) con las capas que muestra `estado`, sin `sistema`: `firmware`, `hardware`, `software`, `ia`. Cada opción lleva la descripción que da `estado`, y en el texto de la pregunta di cuáles están activas hoy (el selector no permite dejarlas marcadas). Si `estado` muestra más de cuatro capas sin contar `sistema`, divídelas en dos preguntas.

Si no marca ninguna, no ejecutes nada: pregunta si quería quitar todas las capas.

## 4. Aplicar
- Proyecto completo → `ARNES aplicar sistema`
- Elegir capas → `ARNES aplicar <capas elegidas>`
- Quitar todas → `ARNES aplicar ninguna`
- Dejarlo como está → no ejecutes nada.

Muestra el resultado.

## 5. Preparar el proyecto (solo si faltan piezas)
Si `estado` dijo que faltan `CLAUDE.md`, `Docs` o `.gitignore`, pregunta si se crean desde las plantillas del arnés. Si dice que sí, pide en una línea el nombre y una descripción corta del proyecto y ejecuta:

`ARNES preparar <capas activas> --nombre "<nombre>" --descripcion "<descripción>"`

Si el usuario no da nombre, omite `--nombre` (se usa el de la carpeta). Si el proyecto quedó sin capas, usa `ninguna`.

`preparar` **nunca sobrescribe**. Si informa líneas "Falta:" (secciones de capa en un `CLAUDE.md` que ya existía, o líneas del `.gitignore`), muéstraselas y pregunta si se agregan. Solo con su OK ejecuta `ARNES completar <capas activas>`.

## 6. Cierre
Termina con un resumen corto:
- capas activas ahora;
- archivos creados o completados, si los hay;
- si hubo cambio de capas: **"Abre una conversación nueva para que las capas carguen. Ahí puedes preguntar «¿qué arnés está activo?»."** Esta conversación no se recarga sola.
