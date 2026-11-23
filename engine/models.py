"""Tabla 1: estados inmutables y dominios del combate."""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import TypeAlias


class Hora(str, Enum):
    DIA = "Día"
    TARDE = "Tarde"
    NOCHE = "Noche"


class Lugar(str, Enum):
    BASE = "Base Subterránea Shadaloo"
    LABORATORIO = "Laboratorio Secreto"
    PSYCHO_DRIVE = "Cámara del Psycho Drive"
    DOJO = "Dojo Rindokan (Tosa, Japón)"
    ESTADIO = "Estadio Street Fighter"


class Nombre(str, Enum):
    JULI = "Juli"
    CAMMY = "Cammy"
    BISON = "M. Bison"
    MAKOTO = "Makoto"


class Postura(str, Enum):
    NEUTRAL = "Neutral"
    DESPLAZAMIENTO = "Desplazamiento"
    AEREO = "Desplazamiento Aéreo"


class Distancia(str, Enum):
    LEJOS = "Lejos"
    MEDIA = "Media"
    CERCA = "Cerca"
    CONTACTO = "Contacto"


class Accion(str, Enum):
    REPOSO = "Reposo"
    CARGANDO = "Cargando"
    ATACANDO = "Atacando"
    DEFENDIENDO = "Defendiendo"
    AGARRE = "Ejecutando Agarre"
    RECUPERACION = "Recuperacion"
    DANO = "Recibiendo_daño"


class Colision(str, Enum):
    VULNERABLE = "Vulnerable"
    ATACANDO = "Atacando"
    INVENCIBLE = "Invencible"
    INVULNERABLE = "Invulnerable"


class Vista(str, Enum):
    IZQUIERDA = "Izquierda"
    DERECHA = "Derecha"


class Especial(str, Enum):
    NORMAL = "Normal"
    ACTIVO = "Activo"
    LIBERADA = "Liberada"


class Actor(str, Enum):
    P1 = "p1"
    P2 = "p2"

    @property
    def rival(self) -> Actor:
        return Actor.P2 if self is Actor.P1 else Actor.P1


RGB: TypeAlias = tuple[int, int, int]
Paleta: TypeAlias = tuple[RGB, RGB, RGB]


@dataclass(frozen=True, slots=True)
class Apariencia:
    color: Paleta
    diseno: str


def apariencia(nombre: Nombre) -> Apariencia:
    return {
        Nombre.JULI: Apariencia(((15, 30, 75), (255, 210, 35), (210, 35, 45)), "Uniforme azul marino, detalles amarillos y boina roja"),
        Nombre.CAMMY: Apariencia(((35, 115, 65), (210, 35, 45), (225, 185, 70)), "Traje verde delta, guantes rojos y trenzas doradas"),
        Nombre.BISON: Apariencia(((185, 25, 40), (190, 195, 205), (20, 20, 25)), "Uniforme rojo comandante, armadura plateada y botas negras"),
        Nombre.MAKOTO: Apariencia(((240, 240, 230), (250, 205, 40), (25, 25, 25)), "Gi blanco, cinta amarilla y cabello negro"),
    }[nombre]


@dataclass(frozen=True, slots=True)
class Personaje:
    nombre: Nombre
    color: Paleta
    diseno: str
    puntos_salud: int = 1000
    postura: Postura = Postura.NEUTRAL
    distancia: Distancia = Distancia.LEJOS
    acciones: Accion = Accion.REPOSO
    medidor_super: int = 0
    recarga_energia: int = 0
    colision: Colision = Colision.VULNERABLE
    vista: Vista = Vista.DERECHA
    especial: Especial = Especial.NORMAL
    dano_recibido: int = 0

    def __post_init__(self) -> None:
        dominios: tuple[tuple[Enum, type[Enum]], ...] = (
            (self.nombre, Nombre), (self.postura, Postura),
            (self.distancia, Distancia), (self.acciones, Accion),
            (self.colision, Colision), (self.vista, Vista),
            (self.especial, Especial),
        )
        if any(not isinstance(valor, dominio) for valor, dominio in dominios):
            raise ValueError("Los atributos categóricos deben usar su Enum EEO")
        for valor, minimo, maximo in ((self.puntos_salud, 0, 1000), (self.medidor_super, 0, 3), (self.recarga_energia, 0, 1), (self.dano_recibido, 0, 1)):
            if type(valor) is not int or not minimo <= valor <= maximo:
                raise ValueError(f"Valor fuera del dominio EEO: {valor}")
        if self.puntos_salud % 10:
            raise ValueError("La salud EEO debe ser múltiplo de 10")
        if not isinstance(self.color, tuple) or len(self.color) != 3 or any(not isinstance(rgb, tuple) or len(rgb) != 3 or any(type(c) is not int or not 0 <= c <= 255 for c in rgb) for rgb in self.color):
            raise ValueError("La paleta debe contener tres colores RGB")


@dataclass(frozen=True, slots=True)
class Escenario:
    hora: Hora = Hora.DIA
    lugar: Lugar = Lugar.ESTADIO

    def __post_init__(self) -> None:
        if not isinstance(self.hora, Hora) or not isinstance(self.lugar, Lugar):
            raise ValueError("Hora y lugar deben pertenecer a sus dominios EEO")


@dataclass(frozen=True, slots=True)
class Estado:
    escenario: Escenario
    p1: Personaje
    p2: Personaje

    def __post_init__(self) -> None:
        if self.p1.distancia is not self.p2.distancia:
            raise ValueError("La distancia entre los luchadores debe ser simétrica")

    def personaje(self, actor: Actor) -> Personaje:
        return self.p1 if actor is Actor.P1 else self.p2

    def con_personajes(self, actor: Actor, propio: Personaje, rival: Personaje) -> Estado:
        return replace(self, p1=propio, p2=rival) if actor is Actor.P1 else replace(self, p1=rival, p2=propio)

    @property
    def terminado(self) -> bool:
        return self.p1.puntos_salud == 0 or self.p2.puntos_salud == 0

    @property
    def ganador(self) -> Actor | None:
        if not self.terminado or self.p1.puntos_salud == self.p2.puntos_salud:
            return None
        return Actor.P1 if self.p1.puntos_salud > 0 else Actor.P2


def crear_personaje(nombre: Nombre, vista: Vista = Vista.DERECHA) -> Personaje:
    arte = apariencia(nombre)
    return Personaje(nombre=nombre, color=arte.color, diseno=arte.diseno, vista=vista,
                     especial=Especial.ACTIVO if nombre is Nombre.JULI else Especial.NORMAL)


def crear_estado(p1: Nombre = Nombre.JULI, p2: Nombre = Nombre.BISON, hora: Hora = Hora.DIA, lugar: Lugar = Lugar.ESTADIO) -> Estado:
    return Estado(Escenario(hora, lugar), crear_personaje(p1), crear_personaje(p2, Vista.IZQUIERDA))


def finalizar(estado: Estado) -> Estado:
    """N0: el K.O. se deriva de la salud; conserva el estado final de la v7."""
    return estado


def iniciar_turno(estado: Estado, actor: Actor) -> Estado:
    """N2/N3: caduca la colisión ofensiva rival y limpia el impacto propio.

    No borra acciones, guardias ni posturas: el aire exige Aterrizar o impacto.
    La normalización terrestre N1 pertenece a los efectos de cada operador.
    Es idempotente y no modifica un estado terminal (N0).
    """
    if estado.terminado:
        return finalizar(estado)
    p = estado.personaje(actor)
    r = estado.personaje(actor.rival)
    p = replace(p, dano_recibido=0)
    if r.colision in (Colision.ATACANDO, Colision.INVENCIBLE):
        r = replace(r, colision=Colision.VULNERABLE)
    return estado.con_personajes(actor, p, r)
