# EEO / Tactical Fighter

Juego de escritorio por turnos, inspirado en Street Fighter, hecho con Python
3.11+ y Pygame. Usa sprites locales de pixel art y escenarios y efectos dibujados
con Pygame. No requiere navegador ni acceso a internet para jugar.

## Instalación y Ejecución en Windows (PowerShell)

Requiere Python 3.11 o superior. Después de clonar el repositorio, abre
PowerShell en la carpeta del proyecto y sigue estos tres pasos:

1. **Crea tu propio entorno virtual:**

   ```powershell
   python -m venv .venv
   ```

   Si `python` no funciona, usa `py -m venv .venv`.

2. **Instala las dependencias dentro del entorno:**

   ```powershell
   .\.venv\Scripts\pip install -r requirements.txt
   ```

3. **Ejecuta el juego:**

   ```powershell
   .\.venv\Scripts\python main.py
   ```

El entorno `.venv` se genera en cada computadora y no se comparte en Git,
porque contiene rutas locales. No es necesario activarlo para usar estos
comandos. Las carpetas de caché también están excluidas del repositorio.

## Controles

- Selección: clic en los luchadores, hora, modo y profundidad. Clic en
  **Iniciar Combate**, o **Enter**. El lugar se elige aleatoriamente entre los
  cinco escenarios al iniciar cada pelea y cada revancha; puede repetirse.
- Jugador vs IA: P1 usa los botones inferiores; P2 responde después de 700 ms.
  Los botones apagados explican sus condiciones al pasar el cursor.
- IA vs IA: un turno cada 1.2 segundos. **Espacio** o **Pausar / Reanudar**
  controla la reproducción. **Flecha derecha** o **Siguiente paso** pausa y
  ejecuta exactamente una jugada, respetando la animación en curso.
- En IA vs IA, **Exposición: ambos inteligentes** está activado por defecto:
  prepara condiciones reales para que cada luchador use su inteligente antes
  del K.O., también si eliges personajes iguales. Después Minimax cierra la
  pelea con acciones y poderes normales, sin repetir los inteligentes.
  **Competitivo: Minimax** conserva la estrategia de ganar y su prioridad
  inteligente; en ese modo no se garantiza mostrar todos los movimientos.
  En Jugador vs IA las decisiones humanas impiden garantizar esa secuencia.
- Inspector: rueda del mouse sobre el historial para consultar otros turnos.
  Las filas rojas identifican operadores inteligentes. La lista Minimax muestra
  las mejores jugadas consideradas, su puntuación y la elección marcada con `›`.
- Haz clic en cualquier turno del historial, durante la pelea o en K.O., para
  consultar sus reglas. Verás cada precondición con el valor que tenía antes del
  movimiento, los efectos del operador y la normalización del siguiente turno.
  Las instantáneas quedan guardadas: no se recalculan con el estado de otro turno.
  También puedes pulsar **Ver reglas** junto al último movimiento o hacer clic
  derecho en un botón de acción para consultar requisitos antes de ejecutarlo.
  La pelea se detiene durante la consulta; usa **Anterior / Siguiente** para
  recorrer turnos y **Esc** para volver al combate o al resumen de K.O.
- **Esc** vuelve al menú desde el combate; desde el menú, cierra el juego.
- El overlay de K.O. conserva un resumen sin límite de tiempo: ganador, turnos,
  vida final, daño causado por cada personaje, especiales e inteligentes usados.
  Incluye un historial completo que se recorre con la rueda del mouse. El daño
  propio del bloqueo se distingue del daño causado al rival. Usa Revancha para
  repetir los luchadores y ajustes con un nuevo sorteo de escenario, o Volver
  al menú cuando termines de revisarlo.

## Motor y presentación

- [engine/models.py](engine/models.py): tupla EEO, dominios y estados inmutables.
- [engine/operators.py](engine/operators.py): precondiciones y efectos de los
  17 operadores de la especificación v7.
- [engine/ai.py](engine/ai.py): Minimax de profundidad 2 o 3 y prioridad inteligente.
- [engine/exhibition.py](engine/exhibition.py): planificación EEO por objetivos
  y verificación de los 16 planes legales de exposición.
- [ui/renderer.py](ui/renderer.py): fondos, figuras, interpolación y efectos.
- [ui/sprites.py](ui/sprites.py): ocho poses por personaje, transparencia,
  orientación, anclajes y caché de sprites.
- [ui/hud.py](ui/hud.py): controles, tooltips, vida, super e inspector.
- [ui/screens.py](ui/screens.py): selección, turnos y K.O.
- [main.py](main.py): eventos y bucle principal, limitado a 60 FPS.

El motor sigue [las reglas EEO v7](docs/3_1_an_lisis_eeo_2_operadores_y_reglas_v7_definitivo.md).
La UI utiliza directamente sus contratos para habilitar botones, explicar
requisitos y conservar las instantáneas de cada movimiento. Minimax calcula
sobre estados inmutables en un hilo auxiliar; los eventos y Pygame se resuelven
en el hilo principal.

- **Golpear:** válido en Cerca o Contacto, desde Neutral o Desplazamiento,
  sin estar Atacando y contra un rival Vulnerable. Resta 100 HP y activa recarga.
- **Cargar energía:** ambos comienzan con super 0 y recarga 0. Golpear o Agarrar
  activa recarga 1; al estar en Reposo o Cargando y en tierra puedes consumir
  ese permiso para sumar un bloque de super. Moverse permite pasar de Atacando
  a Reposo. Cada carga deja recarga 0: no puedes cargar tres veces seguidas.
- **Bloquear:** prepara guardia en Media, Cerca o Contacto; solo cobra 10 HP
  si el rival conserva la acción Atacando. No recupera daño previo.
- **Agarrar:** rompe Defendiendo en Cerca o Contacto, resta 150 HP y conserva
  la distancia. Los poderes e inteligentes también pueden superar la guardia
  cuando sus contratos no exigen Vulnerable.
- **Aterrizar:** es la acción voluntaria para salir del aire; también un impacto
  puede derribarte. La postura aérea no desaparece al comenzar otro turno.
- **N2/N3:** al preparar un turno caduca la colisión ofensiva del rival y se
  limpia el indicador de impacto propio. No se borran acciones ni guardias.
  N1 normaliza posturas en los efectos de los operadores y N0 termina el K.O.
  La figura derrotada se dibuja a partir de salud 0, sin añadir estados al EEO.

En Competitivo, la CPU mantiene prioridad obligatoria de inteligentes y detecta tres turnos
consecutivos sin daño para preparar o ejecutar un ataque legal. Entre dos
Bison prepara golpes en Contacto desde el inicio para evitar drenajes
reversibles en Cerca. El inspector identifica la política de iniciativa.
Las corridas del documento son elecciones manuales legales con barras iniciales
preparadas (3 y 2); no obligan a Minimax a repetir esa misma secuencia.

La exposición usa planes calculados por búsqueda en haz sobre los operadores
EEO originales. Los PNG y los planes se incluyen en el repositorio: no hay que
generarlos al instalar ni al comenzar una partida. Los 16 cruces muestran ambos
inteligentes en 5–26 turnos partiendo de super 0 y salud 1000, sin regalar energía
ni restaurar vida. El inspector distingue **Plan EEO** de **Minimax / cierre** y
muestra el cumplimiento de P1/P2. Durante el plan, el puntaje mostrado es una
referencia heurística, no una comparación Minimax.

Si cambias las reglas, puedes recompilar los planes desde PowerShell:

```powershell
.\.venv\Scripts\python.exe -m engine.exhibition
```

Los banners distinguen **Especial** (consume 3 de super) de **Operador
inteligente** (aplica el cambio de medidor definido en su propia regla).
El HUD indica `SUPER 0/3` a `SUPER 3/3`, y el historial conserva transiciones
como `S3→0` o `S3→3`. Por ejemplo, Lectura Intuitiva Karate de Makoto llena
el medidor y puede mantenerlo en 3; Seichusen Godanzuki lo consume de 3 a 0.

Cada uno de los 17 movimientos tiene una coreografía en
[ui/animations.py](ui/animations.py): preparación, contacto y recuperación.
Los sprites de ocho poses muestran pasos, patadas, agarres, giros, parry y
carga; los poderes añaden estelas y efectos propios. Los impactos incorporan
retroceso, partículas, caída de K.O. y una breve pausa visual de 55 ms.
La sacudida solo afecta a la arena. Las animaciones duran 600 ms y no cambian
el estado EEO, la decisión de Minimax ni las esperas de 700/1200 ms del combate.
Los banners ocupan una esquina para dejar visibles los movimientos del centro.
Las cuatro hojas de sprites se incluyen en [assets/fighters/](assets/fighters/),
con sus prompts y procedencia en [su README](assets/fighters/README.md).
Si falta un PNG, el renderizador utiliza las figuras geométricas de respaldo.

## Verificación

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe .\main.py --smoke-test
```

Las pruebas gráficas utilizan el controlador virtual de SDL y no abren una
ventana visible. El modo `--smoke-test` comprueba seis fotogramas del bucle real,
incluyendo selección y combate, y termina automáticamente.

La suite reproduce las 36 transiciones de las dos corridas v7, también con los
lados invertidos, y comprueba las 32 combinaciones de personajes y profundidad
de IA hasta K.O. Los casos gráficos verifican el gasto de super de los cuatro
poderes normales para ambos jugadores, los requisitos y el resumen de combate.
