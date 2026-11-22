# EEO / Tactical Fighter

Juego de escritorio por turnos, inspirado en Street Fighter, hecho con Python
3.11+ y Pygame. Los personajes, escenarios y efectos se dibujan con geometría;
no requiere navegador, imágenes externas ni acceso a internet para jugar.

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

- Selección: clic en los luchadores, escenario, hora, modo y profundidad. Clic
  en **Iniciar Combate**, o **Enter**.
- Jugador vs IA: P1 usa los botones inferiores; P2 responde después de 700 ms.
  Los botones apagados explican sus condiciones al pasar el cursor.
- IA vs IA: un turno cada 1.2 segundos. **Espacio** o **Pausar / Reanudar**
  controla la reproducción. **Flecha derecha** o **Siguiente paso** pausa y
  ejecuta exactamente una jugada, respetando la animación en curso.
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
  repetir la configuración o Volver al menú cuando termines de revisarlo.

## Motor y presentación

- [engine/models.py](engine/models.py): tupla EEO, dominios y estados inmutables.
- [engine/operators.py](engine/operators.py): precondiciones y efectos de los
  13 operadores, más las transiciones auxiliares.
- [engine/ai.py](engine/ai.py): Minimax de profundidad 2 o 3 y prioridad inteligente.
- [ui/renderer.py](ui/renderer.py): fondos, figuras, interpolación y efectos.
- [ui/hud.py](ui/hud.py): controles, tooltips, vida, super e inspector.
- [ui/screens.py](ui/screens.py): selección, turnos y K.O.
- [main.py](main.py): eventos y bucle principal, limitado a 60 FPS.

La UI aplica directamente el operador del motor y normaliza al actor entrante.
Conserva una instantánea del impacto durante la animación para mostrar el daño
antes de esa normalización. Minimax calcula sobre estados inmutables en un hilo
auxiliar; el hilo principal mantiene el control de los eventos y de Pygame.

Las reglas se conservan según la tabla EEO: bloquear descuenta 10 HP adicionales
sin revertir el ataque anterior, y Finta Aérea Delta conserva el medidor. Volver
a neutral prepara otra acción si el personaje sigue en Atacando o Agachada.

La estrategia de la CPU detecta tres turnos consecutivos sin daño y limita las
opciones de Minimax a ataques válidos o su preparación inmediata. En Contacto,
si no hay un ataque aplicable, vuelve a Cerca para poder golpear según la tabla.
El inspector muestra «Iniciativa: atacar o preparar un ataque» al activarse esta
política. Entre dos Bison prepara Psycho Crusher desde el inicio para evitar
un intercambio infinito de drenajes en Cerca. Esta planificación conserva las
precondiciones, el daño y la prioridad de los operadores inteligentes.

Los banners distinguen **Especial** (consume 3 de super) de **Operador
inteligente** (aplica el cambio de medidor definido en su propia regla).
El HUD indica `SUPER 0/3` a `SUPER 3/3`, y el historial conserva transiciones
como `S3→0` o `S3→3`. Por ejemplo, Lectura Intuitiva Karate de Makoto llena
el medidor y puede mantenerlo en 3; Seichusen Godanzuki lo consume de 3 a 0.

## Verificación

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe .\main.py --smoke-test
```

Las pruebas gráficas utilizan el controlador virtual de SDL y no abren una
ventana visible. El modo `--smoke-test` comprueba seis fotogramas del bucle real,
incluyendo selección y combate, y termina automáticamente.
