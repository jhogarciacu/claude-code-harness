*Esqueleto: las reglas completas y la lista de revisión de esta capa llegan en A-03.*

- **Datos del micro con fuente:** registros, pines, tiempos y límites salen del datasheet o del manual de referencia, citando documento y sección. Si no están, se pregunta.
- **Grabar, borrar o tocar fuses solo con OK explícito.** Lo irreversible lo ejecuta el responsable a mano; el hook del núcleo lo refuerza.
- **Archivos generados** (STM32CubeMX, `sdkconfig`, Kconfig, código de protobuf/nanopb): se cambia la fuente y se regeneran; nunca se editan a mano.
- **Código sensible:** drivers, interrupciones y secciones críticas no se simplifican ni reordenan sin OK; un `volatile` o una lectura "redundante" de un registro suele ser intencional.
- **Sin placa no hay ✅:** lo que solo compiló o corrió en simulador se reporta como "no verificado en hardware".
