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

## Hardware y optimización
- **Datos de hardware con fuente:** registros, pines, tiempos y límites eléctricos salen del datasheet, el manual de referencia o el esquemático, citando documento y sección. Si no están ahí, se pregunta. Nunca se inventan.
- **Sin medición no hay optimización:** medir antes y después, en las mismas condiciones y el mismo hardware, y reportar los números (tiempo, ciclos, memoria, consumo).
- **No grabar, borrar ni cambiar fuses sin un OK explícito.** Lo irreversible (eFuses, fuses, lock bits, option bytes, protección de lectura, OTP) lo ejecuta el responsable a mano. El hook del arnés lo refuerza, pero no ve dentro de los scripts propios.

## Dependencias
- Antes de agregar una dependencia, justificarla. Preferir las mantenidas y portables (Linux x86 y ARM64).
