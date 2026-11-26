# Reglas generales de trabajo (todos los proyectos)

Estas reglas aplican en cualquier proyecto. **Si el `CLAUDE.md` del proyecto dice otra cosa, manda el del proyecto.**

## Idioma
- Respuestas, documentación, comentarios, logs y mensajes de commit en **español**, salvo los nombres de librerías y términos técnicos estándar.

## Forma de trabajar
- **Planear antes de construir:** en un proyecto nuevo o un cambio grande, primero se documentan la visión, los requisitos y el plan. Después viene el código.
- **No cambiar código sin una tarea aprobada.** Si algo no está en el plan o no está aprobado, proponerlo y preguntar.
- **Antes de arrancar una tarea, explicar qué voy a hacer** (archivos, enfoque, dependencias nuevas y riesgos) y esperar el OK.
- **Una tarea a la vez.** Al terminarla:
  1. cumplir la definición de terminado del proyecto;
  2. actualizar su estado y la verificación en el plan;
  3. registrar las decisiones nuevas.
- Si en medio de una tarea aparece algo fuera de su alcance, anotarlo como propuesta. No meterlo en la misma tarea.
- Preguntar solo lo que de verdad es decisión del responsable. Lo demás se resuelve con un criterio razonable y se dice cuál se usó.

## Calidad
- Lógica nueva con **pruebas automáticas**. Antes de dar algo por terminado: pruebas, lint y formato en verde.
- Al cerrar una tarea, usar los agentes del arnés: **verificador** → **simplificador** → **revisor**.
- **Reportar con honestidad:** decir qué se verificó, cómo, y qué no se pudo verificar (por ejemplo, sin hardware o sin SDK). Nunca decir que algo funciona sin haberlo ejecutado.
- No "corregir a ciegas" algo que depende del mundo físico o de una decisión del responsable. Preguntar.
- Los archivos generados no se editan a mano: se cambia su fuente y se regeneran.

## Git
- **Commit y push solo cuando el responsable lo pida.**
- Trabajar en ramas `<ID-tarea>/<descripcion>`. El responsable hace el merge, normalmente en GitHub.
- Un commit por tarea, con el ID de la tarea: `S-03: configuración validada`.
- No reescribir la historia publicada, no hacer push directo a la rama principal y no borrar ramas remotas sin pedirlo.

## Seguridad y privacidad
- Nunca versionar claves de API, contraseñas ni tokens: usar variables de entorno o un `.env` ignorado.
- No guardar datos personales (audio, video, rostros, documentos) por defecto.
- No publicar nada (repos públicos, artefactos, servicios externos) sin permiso explícito.
- Validar en los dos lados lo que pueda causar daño físico o de datos.

## Datos técnicos y acciones irreversibles
- **Datos técnicos con fuente:** registros, pines, tiempos, límites eléctricos, APIs y parámetros salen de su documento de origen (datasheet, manual de referencia, esquemático, documentación oficial), citando documento y sección. Si no están ahí, se pregunta. Nunca se inventan.
- **Nada irreversible sin un OK explícito:** grabar o borrar un dispositivo, tocar fuses, eFuses, lock bits, option bytes, protección de lectura u OTP, o escribir sobre un disco. Lo irreversible lo ejecuta el responsable a mano. El hook del núcleo lo refuerza, pero no ve dentro de los scripts propios.

## Áreas del arnés
- El núcleo está activo en todos los proyectos. Las áreas (`firmware`, `hardware`, `software`, `ia` y `sistema` para el proyecto completo) se activan **por proyecto**, en su `.claude/settings.json`.
- Al empezar la sesión, cada plugin activo anuncia "Arnés activo: <nombre> <versión>". No aplicar reglas de un área que no esté activa en el proyecto.
- Para ver o cambiar las capas de un proyecto: `/arnes:capas`, o los atajos `/arnes:firmware`, `/arnes:hardware`, `/arnes:software`, `/arnes:ia` y `/arnes:sistema`.

## Dependencias
- Antes de agregar una dependencia, justificarla. Preferir las mantenidas y portables (Linux x86 y ARM64).
