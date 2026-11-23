"""Coreografías visuales puras: no alteran estados, daño ni tiempos de turno."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import pi, sin

from engine.models import RGB
from engine.operators import TipoOperador as T


DURACION = 600


class Estilo(str, Enum):
    DASH = "dash"
    PASO = "paso"
    RETIRADA = "retirada"
    PUNO = "puño"
    ESCUDO = "escudo"
    SALTO = "salto"
    ATERRIZAJE = "aterrizaje"
    AGARRE = "agarre"
    CARGA = "carga"
    GIRO = "giro"
    PATADA = "patada"
    CRUSHER = "crusher"
    RAFAGA = "ráfaga"
    LIBERACION = "liberación"
    FINTA = "finta"
    DRENAJE = "drenaje"
    PARRY = "parry"


@dataclass(frozen=True, slots=True)
class Coreografia:
    estilo: Estilo
    color: RGB
    impacto: int = 210
    pausa: int = 55
    fuerza: float = 1.0


COREOGRAFIAS: dict[T, Coreografia] = {
    T.DESPLAZAR: Coreografia(Estilo.DASH, (120, 205, 255), pausa=0),
    T.ACERCAR: Coreografia(Estilo.PASO, (120, 205, 255), pausa=0),
    T.ALEJAR: Coreografia(Estilo.RETIRADA, (120, 205, 255), pausa=0),
    T.GOLPEAR: Coreografia(Estilo.PUNO, (255, 215, 100)),
    T.BLOQUEAR: Coreografia(Estilo.ESCUDO, (80, 210, 255), pausa=0),
    T.SALTAR: Coreografia(Estilo.SALTO, (185, 225, 255), pausa=0),
    T.ATERRIZAR: Coreografia(Estilo.ATERRIZAJE, (210, 225, 235), pausa=0),
    T.AGARRAR: Coreografia(Estilo.AGARRE, (255, 165, 85), impacto=260, fuerza=1.3),
    T.CARGAR: Coreografia(Estilo.CARGA, (255, 218, 85), pausa=0),
    T.SPIN_DRIVE: Coreografia(Estilo.GIRO, (100, 180, 255), fuerza=1.7),
    T.KILLER_BEE: Coreografia(Estilo.PATADA, (255, 222, 85), fuerza=1.7),
    T.PSYCHO_CRUSHER: Coreografia(Estilo.CRUSHER, (200, 100, 255), fuerza=2.0),
    T.SEICHUSEN: Coreografia(Estilo.RAFAGA, (255, 245, 200), fuerza=1.9),
    T.LIBERAR: Coreografia(Estilo.LIBERACION, (255, 75, 120), fuerza=2.0),
    T.FINTA: Coreografia(Estilo.FINTA, (95, 255, 185), fuerza=1.7),
    T.DRENAR: Coreografia(Estilo.DRENAJE, (190, 100, 255), fuerza=0.6),
    T.LECTURA: Coreografia(Estilo.PARRY, (100, 255, 210), fuerza=1.4),
}


def suave(valor: float) -> float:
    x = max(0.0, min(1.0, valor))
    return x * x * (3 - 2 * x)


@dataclass(frozen=True, slots=True)
class Pose:
    avance: float = 0
    elevacion: float | None = None
    giro: float = 0
    inclinacion: float = 0
    extension: float = 0
    patada: float = 0
    guardia: float = 0
    zancada: float = 0
    agarre: float = 0
    carga: float = 0
    uppercut: float = 0
    caida: float = 0


@dataclass(frozen=True, slots=True)
class Fotograma:
    pose: Pose
    tiempo: float
    progreso: float
    llegada: float
    impacto: bool
    reaccion: float
    congelado: bool


def fotograma(tipo: T, edad: int) -> Fotograma:
    """Preparación → contacto congelado → recuperación, dentro de 600 ms.

    El hit stop congela únicamente el reloj de dibujo; nunca bloquea Pygame.
    La salud y el medidor siempre siguen siendo los del motor EEO.
    """
    c = COREOGRAFIAS[tipo]
    edad = max(0, edad)
    congelado = c.pausa > 0 and c.impacto <= edad < c.impacto + c.pausa
    tiempo = float(edad if edad < c.impacto else max(c.impacto, edad - c.pausa))
    progreso = min(1.0, tiempo / (DURACION - c.pausa))
    llegada = suave(tiempo / c.impacto)
    activo = edad < DURACION
    contacto = edad >= c.impacto
    reaccion = 1 - suave((tiempo - c.impacto) / 260) if contacto and activo else 0.0
    impulso = suave(tiempo / c.impacto) * (1 - suave((tiempo - c.impacto) / 240)) if activo else 0.0
    preparar = sin(pi * min(1, tiempo / c.impacto)) if not contacto else 0.0
    ciclo = sin(progreso * pi * 4) * sin(progreso * pi) if activo else 0.0
    e = c.estilo
    pose = Pose()
    if e in (Estilo.DASH, Estilo.PASO, Estilo.RETIRADA):
        signo = -1 if e is Estilo.RETIRADA else 1
        pose = Pose(inclinacion=signo * 12 * sin(pi * progreso), zancada=ciclo,
                    elevacion=abs(ciclo) * 5, avance=signo * 4 * sin(pi * progreso))
    elif e is Estilo.PUNO:
        pose = Pose(avance=18 * impulso - 7 * preparar, inclinacion=12 * impulso,
                    extension=impulso - preparar * 0.35)
    elif e is Estilo.ESCUDO:
        pose = Pose(guardia=1, inclinacion=-8 * sin(pi * progreso), avance=-7 * sin(pi * progreso))
    elif e is Estilo.SALTO:
        pose = Pose(elevacion=62 * suave(progreso * 2) + 35 * sin(pi * progreso),
                    zancada=0.7 * sin(pi * progreso), guardia=0.5)
    elif e is Estilo.ATERRIZAJE:
        pose = Pose(elevacion=62 * (1 - suave(progreso * 2)),
                    inclinacion=10 * sin(pi * progreso), guardia=0.3)
    elif e is Estilo.AGARRE:
        pose = Pose(avance=23 * impulso, inclinacion=18 * impulso, agarre=impulso)
    elif e is Estilo.CARGA:
        pose = Pose(carga=sin(pi * progreso), guardia=0.4, elevacion=3 * sin(pi * progreso))
    elif e in (Estilo.GIRO, Estilo.LIBERACION):
        pose = Pose(giro=720 * suave(progreso), patada=impulso,
                    elevacion=28 * sin(pi * progreso), avance=12 * impulso)
    elif e is Estilo.PATADA:
        pose = Pose(patada=impulso, elevacion=38 * sin(pi * progreso), inclinacion=-28 * impulso,
                    avance=18 * impulso, guardia=0.5)
    elif e is Estilo.CRUSHER:
        pose = Pose(giro=90 * impulso, elevacion=38 * sin(pi * progreso), extension=impulso,
                    patada=impulso * 0.7)
    elif e is Estilo.RAFAGA:
        pose = Pose(uppercut=impulso, extension=impulso * 0.65, avance=20 * impulso,
                    inclinacion=8 * impulso)
    elif e is Estilo.FINTA:
        pose = Pose(elevacion=62 * suave(progreso * 2) + 53 * sin(pi * progreso),
                    giro=360 * suave(progreso), patada=impulso)
    elif e is Estilo.DRENAJE:
        pose = Pose(guardia=1, carga=impulso, inclinacion=-9 * impulso)
    elif e is Estilo.PARRY:
        pose = Pose(guardia=1 - impulso, extension=impulso, avance=12 * impulso,
                    inclinacion=-15 * preparar + 12 * impulso)
    return Fotograma(pose, tiempo, progreso, llegada, contacto, reaccion, congelado)


def reaccion_receptor(frame: Fotograma, tipo: T, derrotado: bool, aire_inicial: bool) -> Pose:
    """Retroceso, elevación del agarre y caída de K.O. sin tocar el estado."""
    if not frame.impacto:
        return Pose()
    caida = suave((frame.tiempo - COREOGRAFIAS[tipo].impacto) / 270) if derrotado else 0.0
    elevacion = 62 * frame.reaccion if aire_inicial else 0.0
    if tipo is T.AGARRAR:
        elevacion += 42 * sin(pi * (1 - frame.reaccion))
    return Pose(avance=-30 * frame.reaccion, inclinacion=-22 * frame.reaccion,
                giro=-88 * caida, elevacion=elevacion - caida * 65, caida=caida)
